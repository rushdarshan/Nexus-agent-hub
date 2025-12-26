"""Hybrid Memory Architecture.

Implements:
- ShortTermMemory: Immediate task context (in-memory)
- LongTermMemory: Historical data with vector search
- Checkpointing: Save/restore workflow state for recovery
"""
from __future__ import annotations

import asyncio
import json
import logging
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import pickle

if TYPE_CHECKING:
    from browser_use.enterprise.orchestrator import WorkflowState, Task

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry with metadata."""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: Optional[int] = None  # Time to live
    
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds
    
    def touch(self) -> None:
        """Update access time and count."""
        self.accessed_at = datetime.now()
        self.access_count += 1


class ShortTermMemory:
    """
    In-memory storage for immediate task context.
    
    Features:
    - Fast key-value access
    - Automatic expiration (TTL)
    - Size limits with LRU eviction
    """
    
    def __init__(self, max_entries: int = 1000, default_ttl: int = 3600):
        self._store: Dict[str, MemoryEntry] = {}
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a value with optional TTL."""
        # Evict if at capacity
        if len(self._store) >= self.max_entries:
            self._evict_lru()
        
        content = json.dumps(value) if not isinstance(value, str) else value
        entry_id = hashlib.md5(f"{key}:{content}".encode()).hexdigest()[:12]
        
        self._store[key] = MemoryEntry(
            id=entry_id,
            content=content,
            metadata=metadata or {},
            ttl_seconds=ttl or self.default_ttl,
        )
        
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value, returning default if not found or expired."""
        entry = self._store.get(key)
        
        if entry is None:
            return default
            
        if entry.is_expired():
            del self._store[key]
            return default
        
        entry.touch()
        
        try:
            return json.loads(entry.content)
        except json.JSONDecodeError:
            return entry.content
    
    def delete(self, key: str) -> bool:
        """Remove a key."""
        if key in self._store:
            del self._store[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all entries."""
        self._store.clear()
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._store:
            return
        
        # Find entry with oldest access time
        oldest_key = min(
            self._store.keys(),
            key=lambda k: self._store[k].accessed_at
        )
        del self._store[oldest_key]
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        expired = [k for k, v in self._store.items() if v.is_expired()]
        for key in expired:
            del self._store[key]
        return len(expired)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "entries": len(self._store),
            "max_entries": self.max_entries,
            "utilization": len(self._store) / self.max_entries,
        }


class VectorStore(ABC):
    """Abstract base for vector storage backends."""
    
    @abstractmethod
    async def add(self, id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        pass
    
    @abstractmethod
    async def search(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass


class SimpleVectorStore(VectorStore):
    """
    Simple in-memory vector store using cosine similarity.
    
    For production, replace with Pinecone, pgvector, Chroma, etc.
    """
    
    def __init__(self):
        self._vectors: Dict[str, Dict[str, Any]] = {}
    
    async def add(self, id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        self._vectors[id] = {
            "embedding": embedding,
            "metadata": metadata,
        }
    
    async def search(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Find most similar vectors using cosine similarity."""
        if not self._vectors:
            return []
        
        scores = []
        for id, data in self._vectors.items():
            similarity = self._cosine_similarity(embedding, data["embedding"])
            scores.append({
                "id": id,
                "score": similarity,
                "metadata": data["metadata"],
            })
        
        # Sort by similarity (descending)
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]
    
    async def delete(self, id: str) -> bool:
        if id in self._vectors:
            del self._vectors[id]
            return True
        return False
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


class LongTermMemory:
    """
    Persistent memory with vector search for semantic retrieval.
    
    Features:
    - Vector embeddings for semantic search
    - Persistent storage (file-based or external DB)
    - Relevance-based retrieval
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_model: Any = None,
        storage_path: Optional[Path] = None,
    ):
        self.vector_store = vector_store or SimpleVectorStore()
        self.embedding_model = embedding_model  # LLM or sentence transformer
        self.storage_path = storage_path or Path.home() / ".browser_use" / "memory"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._metadata_store: Dict[str, MemoryEntry] = {}
        
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        category: str = "general",
    ) -> str:
        """Store content with vector embedding for later retrieval."""
        entry_id = hashlib.md5(f"{content}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Generate embedding
        embedding = await self._get_embedding(content)
        
        # Store in vector DB
        full_metadata = {
            "content": content,
            "category": category,
            "created_at": datetime.now().isoformat(),
            **(metadata or {}),
        }
        await self.vector_store.add(entry_id, embedding, full_metadata)
        
        # Store metadata
        self._metadata_store[entry_id] = MemoryEntry(
            id=entry_id,
            content=content,
            embedding=embedding,
            metadata=full_metadata,
        )
        
        logger.debug(f"Stored memory: {entry_id}")
        return entry_id
    
    async def recall(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memories based on semantic similarity."""
        query_embedding = await self._get_embedding(query)
        
        results = await self.vector_store.search(query_embedding, top_k=top_k * 2)
        
        # Filter by category if specified
        if category:
            results = [r for r in results if r["metadata"].get("category") == category]
        
        return results[:top_k]
    
    async def forget(self, entry_id: str) -> bool:
        """Remove a memory entry."""
        success = await self.vector_store.delete(entry_id)
        if entry_id in self._metadata_store:
            del self._metadata_store[entry_id]
        return success
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if self.embedding_model:
            # Use provided embedding model
            return await self._model_embedding(text)
        else:
            # Simple hash-based pseudo-embedding (for demo)
            return self._simple_embedding(text)
    
    async def _model_embedding(self, text: str) -> List[float]:
        """Get embedding from model (OpenAI, Gemini, etc.)."""
        # Placeholder - integrate with actual embedding API
        # Example with OpenAI:
        # response = await openai.embeddings.create(input=text, model="text-embedding-3-small")
        # return response.data[0].embedding
        return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Generate a simple hash-based embedding (for demo purposes)."""
        # Not suitable for production - use real embeddings
        import hashlib
        
        # Create deterministic pseudo-random embedding from text
        hash_bytes = hashlib.sha384(text.encode()).digest()
        embedding = []
        for i in range(0, len(hash_bytes), 2):
            value = (hash_bytes[i] + hash_bytes[i + 1] * 256) / 65535.0 * 2 - 1
            embedding.append(value)
        
        # Pad or truncate to desired dimension
        while len(embedding) < dim:
            embedding.extend(embedding[:dim - len(embedding)])
        
        return embedding[:dim]
    
    async def save_to_disk(self) -> None:
        """Persist memory to disk."""
        data = {
            "metadata": {k: asdict(v) for k, v in self._metadata_store.items()},
            "vectors": self.vector_store._vectors if hasattr(self.vector_store, '_vectors') else {},
        }
        
        file_path = self.storage_path / "long_term_memory.json"
        with open(file_path, "w") as f:
            json.dump(data, f, default=str)
        
        logger.info(f"Saved long-term memory to {file_path}")
    
    async def load_from_disk(self) -> None:
        """Load memory from disk."""
        file_path = self.storage_path / "long_term_memory.json"
        
        if not file_path.exists():
            return
        
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Restore metadata
        for id, entry_data in data.get("metadata", {}).items():
            entry_data["created_at"] = datetime.fromisoformat(entry_data["created_at"])
            entry_data["accessed_at"] = datetime.fromisoformat(entry_data["accessed_at"])
            self._metadata_store[id] = MemoryEntry(**entry_data)
        
        # Restore vectors
        if hasattr(self.vector_store, '_vectors'):
            self.vector_store._vectors = data.get("vectors", {})
        
        logger.info(f"Loaded {len(self._metadata_store)} memories from disk")


@dataclass
class Checkpoint:
    """Snapshot of workflow state for recovery."""
    id: str
    workflow_id: str
    state_data: bytes  # Pickled WorkflowState
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    """
    Manages workflow checkpoints for crash recovery.
    
    Enables resuming workflows from the last known good state.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".browser_use" / "checkpoints"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._checkpoints: Dict[str, Checkpoint] = {}
    
    def save(
        self,
        workflow_id: str,
        state: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save a checkpoint of workflow state.
        
        Args:
            workflow_id: Unique workflow identifier
            state: State data (dict, WorkflowState, or any picklable object)
            metadata: Additional metadata
            
        Returns:
            Checkpoint ID
        """
        checkpoint_id = f"ckpt_{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Serialize state
        state_data = pickle.dumps(state)
        
        checkpoint = Checkpoint(
            id=checkpoint_id,
            workflow_id=workflow_id,
            state_data=state_data,
            metadata=metadata or {},
        )
        
        self._checkpoints[checkpoint_id] = checkpoint
        
        # Save to disk
        file_path = self.storage_path / f"{checkpoint_id}.ckpt"
        with open(file_path, "wb") as f:
            pickle.dump(checkpoint, f)
        
        logger.info(f"💾 Checkpoint saved: {checkpoint_id}")
        return checkpoint_id
    
    async def save_async(
        self,
        workflow_state: "WorkflowState",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save a checkpoint of the current workflow state (async version)."""
        return self.save(
            workflow_id=workflow_state.workflow_id,
            state=workflow_state,
            metadata=metadata,
        )
    
    async def load(self, checkpoint_id: str) -> "WorkflowState":
        """Load workflow state from a checkpoint."""
        # Try memory first
        if checkpoint_id in self._checkpoints:
            checkpoint = self._checkpoints[checkpoint_id]
        else:
            # Load from disk
            file_path = self.storage_path / f"{checkpoint_id}.ckpt"
            if not file_path.exists():
                raise ValueError(f"Checkpoint not found: {checkpoint_id}")
            
            with open(file_path, "rb") as f:
                checkpoint = pickle.load(f)
            
            self._checkpoints[checkpoint_id] = checkpoint
        
        # Deserialize state
        workflow_state = pickle.loads(checkpoint.state_data)
        logger.info(f"📂 Checkpoint loaded: {checkpoint_id}")
        
        return workflow_state
    
    async def list_checkpoints(
        self,
        workflow_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List available checkpoints."""
        checkpoints = []
        
        # Scan disk
        for file_path in self.storage_path.glob("*.ckpt"):
            try:
                with open(file_path, "rb") as f:
                    checkpoint = pickle.load(f)
                
                if workflow_id is None or checkpoint.workflow_id == workflow_id:
                    checkpoints.append({
                        "id": checkpoint.id,
                        "workflow_id": checkpoint.workflow_id,
                        "created_at": checkpoint.created_at.isoformat(),
                        "metadata": checkpoint.metadata,
                    })
            except Exception as e:
                logger.warning(f"Failed to read checkpoint {file_path}: {e}")
        
        return sorted(checkpoints, key=lambda x: x["created_at"], reverse=True)
    
    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
        
        file_path = self.storage_path / f"{checkpoint_id}.ckpt"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    async def cleanup_old(self, max_age_hours: int = 24) -> int:
        """Remove checkpoints older than max_age_hours."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        removed = 0
        
        for file_path in self.storage_path.glob("*.ckpt"):
            try:
                with open(file_path, "rb") as f:
                    checkpoint = pickle.load(f)
                
                if checkpoint.created_at < cutoff:
                    file_path.unlink()
                    removed += 1
            except Exception:
                pass
        
        return removed


class MemoryManager:
    """
    Unified interface for all memory systems.
    
    Provides:
    - Short-term memory for task context
    - Long-term memory for historical data
    - Checkpointing for workflow recovery
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        embedding_model: Any = None,
    ):
        self.storage_path = storage_path or Path.home() / ".browser_use" / "memory"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(
            storage_path=self.storage_path / "long_term",
            embedding_model=embedding_model,
        )
        self.checkpoints = CheckpointManager(
            storage_path=self.storage_path / "checkpoints"
        )
    
    async def store(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        long_term: bool = True,
    ) -> str:
        """
        Store data in memory.
        
        Args:
            key: Identifier for the data
            value: Data to store (will be JSON serialized)
            metadata: Additional metadata
            long_term: If True, store in long-term memory; else short-term
            
        Returns:
            Entry ID
        """
        content = json.dumps(value, default=str) if not isinstance(value, str) else value
        
        if long_term:
            return await self.long_term.store(
                content=content,
                metadata={"key": key, **(metadata or {})},
                category=metadata.get("category", "general") if metadata else "general",
            )
        else:
            self.short_term.set(key, value, metadata=metadata)
            return key
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memories based on query."""
        return await self.long_term.recall(query, top_k=top_k, category=category)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get from short-term memory."""
        return self.short_term.get(key, default)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set in short-term memory."""
        self.short_term.set(key, value, ttl=ttl)
    
    async def store_task_result(self, task: "Task") -> None:
        """Store a completed task in long-term memory."""
        if task.result:
            await self.long_term.store(
                content=json.dumps({
                    "intent": task.intent,
                    "result": task.result,
                }, default=str),
                metadata={
                    "task_id": task.id,
                    "agent": task.assigned_agent,
                    "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                },
                category="task_results",
            )
    
    async def recall_similar_tasks(
        self,
        intent: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find similar past tasks for learning."""
        return await self.long_term.recall(
            query=intent,
            top_k=top_k,
            category="task_results",
        )
    
    async def save_checkpoint(self, state: "WorkflowState") -> str:
        """Save workflow checkpoint."""
        return await self.checkpoints.save(state)
    
    async def load_checkpoint(self, checkpoint_id: str) -> "WorkflowState":
        """Load workflow from checkpoint."""
        return await self.checkpoints.load(checkpoint_id)
    
    async def persist_all(self) -> None:
        """Persist all memory to disk."""
        await self.long_term.save_to_disk()
    
    async def load_all(self) -> None:
        """Load all memory from disk."""
        await self.long_term.load_from_disk()
