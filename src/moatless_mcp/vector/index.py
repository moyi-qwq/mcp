"""
Vector index implementation using FAISS.
"""

import logging
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

from .code_splitter import CodeChunk

logger = logging.getLogger(__name__)


class VectorIndex:
    """FAISS-based vector index for code chunks."""
    
    def __init__(self, index_dir: str, dimension: int = 1024):
        """
        Initialize vector index.
        
        Args:
            index_dir: Directory to store index files
            dimension: Vector dimension (1024 for Jina embeddings v3)
        """
        self.index_dir = Path(index_dir)
        self.dimension = dimension
        self.index = None
        self.chunks = []  # Store chunk metadata
        self.chunk_map = {}  # Map chunk IDs to indices
        
        # Ensure index directory exists
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is not available. Install faiss-cpu or faiss-gpu.")
        
        # File paths
        self.index_file = self.index_dir / "vector_index.faiss"
        self.metadata_file = self.index_dir / "chunks_metadata.json"
        self.chunk_data_file = self.index_dir / "chunks_data.pkl"
    
    def create_index(self, embeddings: List[List[float]], chunks: List[CodeChunk]) -> bool:
        """
        Create a new vector index from embeddings and chunks.
        
        Args:
            embeddings: List of embedding vectors
            chunks: List of corresponding CodeChunk objects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if len(embeddings) != len(chunks):
                raise ValueError("Number of embeddings must match number of chunks")
            
            if not embeddings:
                logger.warning("No embeddings provided, creating empty index")
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for similarity
                self.chunks = []
                self.chunk_map = {}
                return True
            
            # Convert embeddings to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Normalize vectors for cosine similarity
            faiss.normalize_L2(embeddings_array)
            
            # Create FAISS index
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product after normalization = cosine similarity
            self.index.add(embeddings_array)
            
            # Store chunk metadata
            self.chunks = chunks
            self.chunk_map = {chunk.id: i for i, chunk in enumerate(chunks)}
            
            logger.info(f"Created vector index with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            return False
    
    def save(self) -> bool:
        """Save the index and metadata to disk."""
        try:
            if self.index is None:
                logger.warning("No index to save")
                return False
            
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_file))
            
            # Save chunk metadata as JSON
            metadata = []
            for chunk in self.chunks:
                chunk_dict = {
                    "id": chunk.id,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "chunk_type": chunk.chunk_type,
                    "name": chunk.name,
                    "parent_name": chunk.parent_name,
                    "language": chunk.language,
                    "metadata": chunk.metadata
                }
                metadata.append(chunk_dict)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Save full chunk objects using pickle for content
            with open(self.chunk_data_file, 'wb') as f:
                pickle.dump(self.chunks, f)
            
            logger.info(f"Saved vector index to {self.index_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save vector index: {e}")
            return False
    
    def load(self) -> bool:
        """Load the index and metadata from disk."""
        try:
            if not all(p.exists() for p in [self.index_file, self.metadata_file, self.chunk_data_file]):
                logger.info("Index files not found, starting with empty index")
                self.index = faiss.IndexFlatIP(self.dimension)
                self.chunks = []
                self.chunk_map = {}
                return True
            
            # Load FAISS index
            self.index = faiss.read_index(str(self.index_file))
            
            # Load chunk objects
            with open(self.chunk_data_file, 'rb') as f:
                self.chunks = pickle.load(f)
            
            # Rebuild chunk map
            self.chunk_map = {chunk.id: i for i, chunk in enumerate(self.chunks)}
            
            logger.info(f"Loaded vector index with {len(self.chunks)} chunks from {self.index_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load vector index: {e}")
            # Create empty index as fallback
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunks = []
            self.chunk_map = {}
            return False
    
    def search(self, query_embedding: List[float], k: int = 10) -> List[Tuple[CodeChunk, float]]:
        """
        Search for similar code chunks.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            
        Returns:
            List of (CodeChunk, similarity_score) tuples
        """
        try:
            if self.index is None or len(self.chunks) == 0:
                return []
            
            # Convert query to numpy array and normalize
            query_array = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_array)
            
            # Search
            scores, indices = self.index.search(query_array, min(k, len(self.chunks)))
            
            # Return results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and idx < len(self.chunks):
                    chunk = self.chunks[idx]
                    results.append((chunk, float(score)))
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def add_chunks(self, embeddings: List[List[float]], chunks: List[CodeChunk]) -> bool:
        """
        Add new chunks to existing index.
        
        Args:
            embeddings: List of embedding vectors
            chunks: List of corresponding CodeChunk objects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if len(embeddings) != len(chunks):
                raise ValueError("Number of embeddings must match number of chunks")
            
            if not embeddings:
                return True
            
            if self.index is None:
                return self.create_index(embeddings, chunks)
            
            # Convert embeddings to numpy array and normalize
            embeddings_array = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings_array)
            
            # Add to index
            self.index.add(embeddings_array)
            
            # Update chunks and mapping
            start_idx = len(self.chunks)
            self.chunks.extend(chunks)
            
            for i, chunk in enumerate(chunks):
                self.chunk_map[chunk.id] = start_idx + i
            
            logger.info(f"Added {len(chunks)} chunks to index, total: {len(self.chunks)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add chunks to index: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        stats = {
            "total_chunks": len(self.chunks),
            "index_exists": self.index is not None,
            "dimension": self.dimension,
            "index_dir": str(self.index_dir)
        }
        
        if self.chunks:
            # Count by type
            type_counts = {}
            language_counts = {}
            file_counts = {}
            
            for chunk in self.chunks:
                type_counts[chunk.chunk_type] = type_counts.get(chunk.chunk_type, 0) + 1
                language_counts[chunk.language] = language_counts.get(chunk.language, 0) + 1
                file_counts[chunk.file_path] = file_counts.get(chunk.file_path, 0) + 1
            
            stats.update({
                "chunk_types": type_counts,
                "languages": language_counts,
                "total_files": len(file_counts),
                "avg_chunks_per_file": len(self.chunks) / len(file_counts) if file_counts else 0
            })
        
        return stats
    
    def exists(self) -> bool:
        """Check if index files exist on disk."""
        return all(p.exists() for p in [self.index_file, self.metadata_file, self.chunk_data_file])
    
    def clear(self) -> bool:
        """Clear the index and delete files."""
        try:
            # Remove files
            for file_path in [self.index_file, self.metadata_file, self.chunk_data_file]:
                if file_path.exists():
                    file_path.unlink()
            
            # Reset in-memory state
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunks = []
            self.chunk_map = {}
            
            logger.info("Cleared vector index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False