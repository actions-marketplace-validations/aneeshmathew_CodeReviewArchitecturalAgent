import hashlib
import math
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from ..config import settings
from .chunker import CodeChunk


class CodeVectorStore:
    """Manages indexing and semantic search over code chunks using Qdrant and Gemini Embeddings."""

    VECTOR_SIZE = 768

    def __init__(
        self,
        collection_name: Optional[str] = None,
        location: Optional[str] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
    ):
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.location = location or settings.qdrant_path
        self.gemini_api_key = api_key or settings.gemini_api_key
        self.url = url or settings.qdrant_url
        self.qdrant_api_key = qdrant_api_key or settings.qdrant_api_key

        # Initialize Qdrant Client (Cloud URL, in-memory, or persistent local path)
        if self.url:
            try:
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.qdrant_api_key or None,
                    timeout=3,
                    check_compatibility=False
                )
                self._init_collection()
            except Exception:
                # Fallback to transient in-memory store if network is isolated/offline
                self.client = QdrantClient(":memory:")
                self._init_collection()
        elif self.location == ":memory:":
            self.client = QdrantClient(":memory:")
            self._init_collection()
        else:
            self.client = QdrantClient(path=self.location)
            self._init_collection()

    def _init_collection(self):
        """Ensures the target collection exists with Cosine distance."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=qmodels.Distance.COSINE
                )
            )

    def _get_embedding(self, text: str) -> List[float]:
        """Generates embedding using Gemini API if key is present, else deterministic fallback."""
        if self.gemini_api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.gemini_api_key)
                response = client.models.embed_content(
                    model=settings.gemini_embedding_model,
                    contents=text
                )
                if hasattr(response, "embeddings") and response.embeddings:
                    vals = response.embeddings[0].values
                    if len(vals) == self.VECTOR_SIZE:
                        return vals
            except Exception:
                # Fallback to local embedding on API error or rate limit
                pass

        return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str) -> List[float]:
        """Fast, deterministic local embedding vector based on hash projections."""
        vector = [0.0] * self.VECTOR_SIZE
        words = text.split()
        if not words:
            return vector

        for word in words:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.VECTOR_SIZE
            sign = 1.0 if (h % 2 == 0) else -1.0
            vector[idx] += sign

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        return vector

    def index_chunks(self, chunks: List[CodeChunk]) -> int:
        """Indexes a list of code chunks into Qdrant."""
        if not chunks:
            return 0

        points = []
        for i, chunk in enumerate(chunks):
            embedding = self._get_embedding(f"{chunk.name}\n{chunk.code}")
            # Generate deterministic int ID
            point_id = int(hashlib.sha256(chunk.chunk_id.encode("utf-8")).hexdigest()[:8], 16)
            payload = {
                "chunk_id": chunk.chunk_id,
                "file_path": chunk.file_path,
                "name": chunk.name,
                "kind": chunk.kind,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "code": chunk.code,
                **chunk.metadata
            }
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            )

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception:
            # Fallback to local in-memory client
            self.client = QdrantClient(":memory:")
            self._init_collection()
            self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    def search_similar_code(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Finds logically or semantically related code chunks."""
        query_vector = self._get_embedding(query)
        try:
            result = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit
            )
            points = result.points
        except Exception:
            return []

        results = []
        for hit in points:
            results.append({
                "score": hit.score,
                "payload": hit.payload
            })
        return results
