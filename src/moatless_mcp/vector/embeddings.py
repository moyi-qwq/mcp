"""
Jina AI embedding provider for code vectors.
"""

import logging
import requests
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result from embedding operation."""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None


class JinaEmbeddingProvider:
    """Jina AI embedding provider with batching support."""
    
    def __init__(self, api_key: str, model: str = "jina-embeddings-v3", batch_size: int = 50):
        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        self.base_url = "https://api.jina.ai/v1/embeddings"
        
        if not api_key:
            raise ValueError("Jina API key is required")
    
    def embed_texts(self, texts: List[str], task: str = "retrieval.passage") -> EmbeddingResult:
        """
        Embed a list of texts using Jina AI API.
        
        Args:
            texts: List of texts to embed
            task: Task type for embedding (ignored in new API)
            
        Returns:
            EmbeddingResult with embeddings and metadata
        """
        if not texts:
            return EmbeddingResult(
                embeddings=[], 
                model=self.model, 
                usage={}, 
                success=False, 
                error="No texts provided"
            )
        
        try:
            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "task": task,
                "input": texts,
                "dimensions": 1024
            }
            
            # Debug logging
            logger.debug(f"Jina API request data: {data}")
            
            # Make request with retry logic
            response = self._make_request_with_retry(headers, data)
            
            if response.status_code == 200:
                result = response.json()
                embeddings = [item["embedding"] for item in result["data"]]
                
                return EmbeddingResult(
                    embeddings=embeddings,
                    model=result.get("model", self.model),
                    usage=result.get("usage", {}),
                    success=True
                )
            else:
                error_msg = f"Jina API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return EmbeddingResult(
                    embeddings=[],
                    model=self.model,
                    usage={},
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            error_msg = f"Failed to get embeddings: {str(e)}"
            logger.error(error_msg)
            return EmbeddingResult(
                embeddings=[],
                model=self.model, 
                usage={},
                success=False,
                error=error_msg
            )
    
    def embed_texts_batch(self, texts: List[str], task: str = "retrieval.passage") -> EmbeddingResult:
        """
        Embed texts in batches to handle large datasets.
        
        Args:
            texts: List of texts to embed
            task: Task type for embedding (ignored in new API)
            
        Returns:
            Combined EmbeddingResult
        """
        if not texts:
            return EmbeddingResult(
                embeddings=[], 
                model=self.model, 
                usage={}, 
                success=False, 
                error="No texts provided"
            )
        
        all_embeddings = []
        total_usage = {"total_tokens": 0, "prompt_tokens": 0}
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            logger.info(f"Processing batch {i//self.batch_size + 1}/{(len(texts) + self.batch_size - 1)//self.batch_size} "
                       f"({len(batch)} texts)")
            
            result = self.embed_texts(batch, task)
            
            if not result.success:
                return result  # Return error immediately
            
            all_embeddings.extend(result.embeddings)
            
            # Accumulate usage stats
            if result.usage:
                total_usage["total_tokens"] += result.usage.get("total_tokens", 0)
                total_usage["prompt_tokens"] += result.usage.get("prompt_tokens", 0)
            
            # Rate limiting - small delay between batches
            if i + self.batch_size < len(texts):
                time.sleep(0.1)
        
        return EmbeddingResult(
            embeddings=all_embeddings,
            model=self.model,
            usage=total_usage,
            success=True
        )
    
    def _make_request_with_retry(self, headers: Dict, data: Dict, max_retries: int = 3) -> requests.Response:
        """Make request with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                # If rate limited, wait and retry
                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                
                wait_time = 2 ** attempt
                logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        raise Exception("Max retries exceeded")