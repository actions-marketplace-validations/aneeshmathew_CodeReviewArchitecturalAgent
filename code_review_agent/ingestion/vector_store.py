import hashlib
import logging
import math
from typing import Any, Dict, List, Optional
from ..config import settings
from .chunker import CodeChunk

logger = logging.getLogger(__name__)


class CodeVectorStore:
    """Manages indexing and semantic search over code chunks using Pinecone (Serverless) and Gemini Embeddings."""

    VECTOR_SIZE = 768

    def __init__(
        self,
        index_name: Optional[str] = None,
        api_key: Optional[str] = None,
        pinecone_api_key: Optional[str] = None,
        cloud: Optional[str] = None,
        region: Optional[str] = None,
    ):
        self.index_name = index_name or settings.pinecone_index_name
        self.gemini_api_key = api_key or settings.gemini_api_key
        self.pinecone_api_key = pinecone_api_key or settings.pinecone_api_key
        self.cloud = cloud or settings.pinecone_cloud
        self.region = region or settings.pinecone_region

        self.pc = None
        self.index = None
        self._in_memory_vectors: List[Dict[str, Any]] = []

        if self.pinecone_api_key:
            try:
                from pinecone import Pinecone, ServerlessSpec
                self.pc = Pinecone(api_key=self.pinecone_api_key)
                self._init_index(ServerlessSpec)
            except Exception as e:
                logger.warning(f"Could not connect to Pinecone: {e}. Using transient in-memory store.")
                self.pc = None
                self.index = None

    def _init_index(self, serverless_spec_cls):
        """Ensures the target Pinecone serverless index exists."""
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone serverless index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.VECTOR_SIZE,
                    metric="cosine",
                    spec=serverless_spec_cls(
                        cloud=self.cloud,
                        region=self.region
                    )
                )
            self.index = self.pc.Index(self.index_name)
        except Exception as e:
            logger.warning(f"Pinecone index initialization failed: {e}. Falling back to in-memory.")
            self.index = None

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

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Computes cosine similarity between two float vectors."""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)

    def index_chunks(self, chunks: List[CodeChunk]) -> int:
        """Indexes a list of code chunks into Pinecone (or in-memory fallback)."""
        if not chunks:
            return 0

        vectors = []
        for chunk in chunks:
            embedding = self._get_embedding(f"{chunk.name}\n{chunk.code}")
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
            vectors.append({
                "id": chunk.chunk_id,
                "values": embedding,
                "metadata": payload
            })

        if self.index is not None:
            try:
                # Batch upsert into Pinecone
                batch_size = 100
                for i in range(0, len(vectors), batch_size):
                    self.index.upsert(vectors=vectors[i:i + batch_size])
                return len(vectors)
            except Exception as e:
                logger.warning(f"Pinecone upsert failed: {e}. Falling back to in-memory vectors.")

        # In-memory storage
        self._in_memory_vectors.extend(vectors)
        return len(vectors)

    def search_similar_code(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Finds logically or semantically related code chunks."""
        query_vector = self._get_embedding(query)

        if self.index is not None:
            try:
                result = self.index.query(
                    vector=query_vector,
                    top_k=limit,
                    include_metadata=True
                )
                matches = getattr(result, "matches", []) or []
                results = []
                for match in matches:
                    results.append({
                        "score": getattr(match, "score", 0.0),
                        "payload": getattr(match, "metadata", {}) or {}
                    })
                return results
            except Exception as e:
                logger.warning(f"Pinecone query failed: {e}. Falling back to in-memory search.")

        # In-memory cosine similarity search
        scored = []
        for item in self._in_memory_vectors:
            score = self._cosine_similarity(query_vector, item["values"])
            scored.append({
                "score": score,
                "payload": item["metadata"]
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]
