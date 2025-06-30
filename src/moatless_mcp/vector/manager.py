"""
Vector database manager coordinating embedding, indexing, and search.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .embeddings import JinaEmbeddingProvider, EmbeddingResult
from .code_splitter import CodeSplitter, CodeChunk
from .index import VectorIndex
from moatless_mcp.utils.config import Config

logger = logging.getLogger(__name__)


class VectorManager:
    """Manages the complete vector database pipeline."""
    
    def __init__(self, workspace_root: str, config: Config, index_dir: Optional[str] = None):
        """
        Initialize the vector manager.
        
        Args:
            workspace_root: Root directory of the workspace
            config: Configuration object
            index_dir: Directory to store vector index (defaults to .vector_cache in workspace)
        """
        self.workspace_root = Path(workspace_root)
        self.config = config
        
        # Set up index directory
        if index_dir is None:
            self.index_dir = self.workspace_root / ".vector_cache"
        else:
            self.index_dir = Path(index_dir)
        
        # Initialize components
        self.code_splitter = CodeSplitter(config, workspace_root)
        self.vector_index = VectorIndex(str(self.index_dir))
        self.embedding_provider = None
        
        # Load existing index
        self.vector_index.load()
    
    def initialize_embeddings(self, api_key: str, model: str = "jina-embeddings-v3") -> bool:
        """
        Initialize the embedding provider.
        
        Args:
            api_key: Jina AI API key
            model: Embedding model name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.embedding_provider = JinaEmbeddingProvider(api_key, model)
            logger.info(f"Initialized embedding provider with model: {model}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize embedding provider: {e}")
            return False
    
    def build_index(self, file_patterns: Optional[List[str]] = None, 
                   force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Build the vector index from code files.
        
        Args:
            file_patterns: Optional list of glob patterns to filter files
            force_rebuild: Force rebuild even if index exists
            
        Returns:
            Dictionary with build results and statistics
        """
        try:
            if not self.embedding_provider:
                return {
                    "success": False,
                    "error": "Embedding provider not initialized. Please provide Jina API key."
                }
            
            # Check if index already exists
            if not force_rebuild and self.vector_index.exists():
                stats = self.vector_index.get_stats()
                if stats["total_chunks"] > 0:
                    return {
                        "success": True,
                        "message": "Vector index already exists",
                        "stats": stats,
                        "rebuild_required": False
                    }
            
            logger.info("Starting vector index build process")
            
            # Step 1: Split code into chunks
            logger.info("Splitting code files into semantic chunks...")
            chunks = self.code_splitter.split_workspace(file_patterns)
            
            if not chunks:
                return {
                    "success": False,
                    "error": "No code chunks found. Check file patterns and workspace content."
                }
            
            logger.info(f"Created {len(chunks)} code chunks")
            
            # Step 2: Generate embeddings
            logger.info("Generating embeddings for code chunks...")
            texts = [self._chunk_to_text(chunk) for chunk in chunks]
            
            embedding_result = self.embedding_provider.embed_texts_batch(texts, task="retrieval.passage")
            
            if not embedding_result.success:
                return {
                    "success": False,
                    "error": f"Failed to generate embeddings: {embedding_result.error}"
                }
            
            logger.info(f"Generated {len(embedding_result.embeddings)} embeddings")
            
            # Step 3: Create vector index
            logger.info("Building vector index...")
            if force_rebuild:
                self.vector_index.clear()
            
            success = self.vector_index.create_index(embedding_result.embeddings, chunks)
            
            if not success:
                return {
                    "success": False,
                    "error": "Failed to create vector index"
                }
            
            # Step 4: Save index to disk
            logger.info("Saving vector index...")
            save_success = self.vector_index.save()
            
            if not save_success:
                return {
                    "success": False,
                    "error": "Failed to save vector index"
                }
            
            # Get final statistics
            stats = self.vector_index.get_stats()
            
            result = {
                "success": True,
                "message": "Vector index built successfully",
                "stats": stats,
                "embedding_usage": embedding_result.usage,
                "rebuild_required": False
            }
            
            logger.info(f"Vector index build complete: {stats['total_chunks']} chunks indexed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to build vector index: {e}")
            return {
                "success": False,
                "error": f"Index build failed: {str(e)}"
            }
    
    def search(self, query: str, k: int = 10, filter_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Search the vector index with a natural language query.
        
        Args:
            query: Natural language search query
            k: Number of results to return
            filter_type: Optional filter by chunk type ('class', 'function', 'method', etc.)
            
        Returns:
            Dictionary with search results
        """
        try:
            if not self.embedding_provider:
                return {
                    "success": False,
                    "error": "Embedding provider not initialized"
                }
            
            if self.vector_index.get_stats()["total_chunks"] == 0:
                return {
                    "success": False,
                    "error": "Vector index is empty. Please build the index first."
                }
            
            # Generate query embedding
            embedding_result = self.embedding_provider.embed_texts([query], task="retrieval.query")
            
            if not embedding_result.success:
                return {
                    "success": False,
                    "error": f"Failed to embed query: {embedding_result.error}"
                }
            
            # Search vector index
            results = self.vector_index.search(embedding_result.embeddings[0], k * 2)  # Get more for filtering
            
            # Apply filters
            if filter_type:
                results = [(chunk, score) for chunk, score in results if chunk.chunk_type == filter_type]
            
            # Limit to requested number
            results = results[:k]
            
            # Format results
            formatted_results = []
            for chunk, score in results:
                formatted_results.append({
                    "chunk_id": chunk.id,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "chunk_type": chunk.chunk_type,
                    "name": chunk.name,
                    "parent_name": chunk.parent_name,
                    "language": chunk.language,
                    "similarity_score": score,
                    "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    "metadata": chunk.metadata
                })
            
            return {
                "success": True,
                "query": query,
                "total_results": len(formatted_results),
                "results": formatted_results,
                "filter_type": filter_type
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "success": False,
                "error": f"Search failed: {str(e)}"
            }
    
    def get_chunk_content(self, chunk_id: str) -> Optional[str]:
        """Get the full content of a specific chunk."""
        try:
            chunk_idx = self.vector_index.chunk_map.get(chunk_id)
            if chunk_idx is not None and chunk_idx < len(self.vector_index.chunks):
                return self.vector_index.chunks[chunk_idx].content
            return None
        except Exception as e:
            logger.error(f"Failed to get chunk content: {e}")
            return None
    
    def get_index_status(self) -> Dict[str, Any]:
        """Get the current status of the vector index."""
        try:
            stats = self.vector_index.get_stats()
            
            status = {
                "index_exists": self.vector_index.exists(),
                "index_loaded": self.vector_index.index is not None,
                "embedding_provider_ready": self.embedding_provider is not None,
                "stats": stats
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get index status: {e}")
            return {
                "index_exists": False,
                "index_loaded": False,
                "embedding_provider_ready": False,
                "error": str(e)
            }
    
    def clear_index(self) -> bool:
        """Clear the vector index and delete all files."""
        try:
            return self.vector_index.clear()
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False
    
    def _chunk_to_text(self, chunk: CodeChunk) -> str:
        """
        Convert a code chunk to text for embedding.
        
        This creates a rich text representation that includes context
        for better semantic understanding.
        """
        parts = []
        
        # Add type and context
        if chunk.chunk_type == "method" and chunk.parent_name:
            parts.append(f"Method {chunk.name} in class {chunk.parent_name}")
        elif chunk.chunk_type == "function":
            parts.append(f"Function {chunk.name}")
        elif chunk.chunk_type == "class_header":
            parts.append(f"Class {chunk.name} definition")
        elif chunk.chunk_type == "class":
            parts.append(f"Class {chunk.name}")
        else:
            parts.append(f"{chunk.chunk_type.title()} {chunk.name}")
        
        # Add language context
        if chunk.language != "unknown":
            parts.append(f"({chunk.language})")
        
        # Add file context
        parts.append(f"in {chunk.file_path}")
        
        # Add metadata context
        if chunk.metadata:
            if "parameters" in chunk.metadata and chunk.metadata["parameters"]:
                params = ", ".join(chunk.metadata["parameters"])
                parts.append(f"with parameters: {params}")
            
            if "decorators" in chunk.metadata and chunk.metadata["decorators"]:
                decorators = ", ".join(chunk.metadata["decorators"])
                parts.append(f"decorators: {decorators}")
        
        # Combine context with code
        context = " ".join(parts)
        
        return f"{context}\n\n{chunk.content}"