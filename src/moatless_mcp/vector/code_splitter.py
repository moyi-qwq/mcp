"""
Code splitting using tree-sitter for semantic chunks.
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from moatless_mcp.treesitter import CodeParser, detect_language, is_tree_sitter_available
from moatless_mcp.utils.config import Config

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """Represents a semantic code chunk for embedding."""
    id: str  # Unique identifier
    content: str  # The actual code content
    file_path: str  # Relative path to the file
    start_line: int  # 1-based line number
    end_line: int  # 1-based line number  
    chunk_type: str  # 'class', 'function', 'method', 'block', etc.
    name: str  # Name of the code element (class name, function name, etc.)
    parent_name: Optional[str] = None  # Parent class name for methods
    language: str = "unknown"  # Programming language
    metadata: Dict[str, Any] = None  # Additional metadata
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Generate ID from content hash if not provided
        if not self.id:
            content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
            self.id = f"{self.file_path}:{self.start_line}:{content_hash}"


class CodeSplitter:
    """Split code files into semantic chunks using tree-sitter."""
    
    def __init__(self, config: Config, workspace_root: str = "."):
        self.config = config
        self.workspace_root = Path(workspace_root)
        self.parser = CodeParser() if is_tree_sitter_available() else None
        
        # Configuration for chunk sizes (in tokens)
        self.max_tokens = 7000      # Max tokens per chunk (leave buffer for Jina's 8194 limit)
        self.max_chunk_size = 2000  # Max characters per chunk (fallback)
        self.min_chunk_size = 50    # Min characters per chunk
        self.overlap_size = 100     # Overlap between chunks
        
        # Initialize tokenizer if available
        self.tokenizer = None
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
            except Exception as e:
                logger.warning(f"Failed to initialize tokenizer: {e}")
                self.tokenizer = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.debug(f"Token counting failed: {e}")
        
        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4
    
    def split_large_content(self, content: str, max_tokens: int = None) -> List[str]:
        """Split large content into smaller chunks that fit token limits."""
        if max_tokens is None:
            max_tokens = self.max_tokens
        
        # If content is within limits, return as is
        if self.count_tokens(content) <= max_tokens:
            return [content]
        
        # Split by lines to preserve code structure
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for line in lines:
            line_tokens = self.count_tokens(line + '\n')
            
            # If single line exceeds limit, we need to split it further
            if line_tokens > max_tokens:
                # Add current chunk if it has content
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split the long line by characters
                while line:
                    # Take a portion that fits in token limit
                    chunk_size = min(len(line), max_tokens * 4)  # rough estimate
                    chunk_part = line[:chunk_size]
                    
                    # Adjust to actual token limit
                    while self.count_tokens(chunk_part) > max_tokens and len(chunk_part) > 1:
                        chunk_part = chunk_part[:len(chunk_part) * 3 // 4]
                    
                    chunks.append(chunk_part)
                    line = line[len(chunk_part):]
                
                continue
            
            # Check if adding this line would exceed token limit
            if current_tokens + line_tokens > max_tokens:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_tokens = line_tokens
            else:
                current_chunk.append(line)
                current_tokens += line_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def _create_chunks_from_content(self, content: str, file_path: str, start_line: int, 
                                   chunk_type: str, name: str, language: str, 
                                   parent_name: str = None, metadata: Dict = None) -> List[CodeChunk]:
        """Create one or more CodeChunk objects from content, splitting if it exceeds token limits."""
        if not content or len(content.strip()) < self.min_chunk_size:
            return []
        
        # Check if content exceeds token limit
        token_count = self.count_tokens(content)
        if token_count > self.max_tokens:
            logger.debug(f"Large content detected: {name} has {token_count} tokens (limit: {self.max_tokens})")
        
        if token_count <= self.max_tokens:
            # Content fits in one chunk
            return [CodeChunk(
                id="",
                content=content,
                file_path=file_path,
                start_line=start_line,
                end_line=start_line + content.count('\n'),
                chunk_type=chunk_type,
                name=name,
                parent_name=parent_name,
                language=language,
                metadata=metadata or {}
            )]
        
        # Content too large, split into multiple chunks
        split_contents = self.split_large_content(content, self.max_tokens)
        chunks = []
        
        lines_processed = 0
        for i, split_content in enumerate(split_contents):
            if not split_content.strip():
                continue
                
            chunk_lines = split_content.count('\n')
            chunk_name = f"{name}_part{i+1}" if len(split_contents) > 1 else name
            
            chunks.append(CodeChunk(
                id="",
                content=split_content,
                file_path=file_path,
                start_line=start_line + lines_processed,
                end_line=start_line + lines_processed + chunk_lines,
                chunk_type=chunk_type,
                name=chunk_name,
                parent_name=parent_name,
                language=language,
                metadata={
                    **(metadata or {}),
                    "is_split": len(split_contents) > 1,
                    "part_number": i + 1 if len(split_contents) > 1 else None,
                    "total_parts": len(split_contents) if len(split_contents) > 1 else None
                }
            ))
            
            lines_processed += chunk_lines
        
        return chunks
    
    def split_file(self, file_path: str, content: Optional[str] = None) -> List[CodeChunk]:
        """
        Split a file into semantic code chunks.
        
        Args:
            file_path: Path to the file (relative to workspace)
            content: Optional file content (will read from file if not provided)
            
        Returns:
            List of CodeChunk objects
        """
        try:
            full_path = self.workspace_root / file_path
            
            # Validate file access
            if not self.config.is_file_allowed(full_path):
                logger.debug(f"File not allowed: {file_path}")
                return []
            
            # Read content if not provided
            if content is None:
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    logger.debug(f"Failed to read file {file_path}: {e}")
                    return []
            
            if not content.strip():
                return []
            
            # Detect language
            language = detect_language(str(full_path), content) if detect_language else "unknown"
            
            # Use tree-sitter parsing if available
            if self.parser and language != "unknown":
                chunks = self._split_with_tree_sitter(file_path, content, language)
                if chunks:
                    return chunks
            
            # Fallback to text-based splitting
            return self._split_with_text(file_path, content, language)
            
        except Exception as e:
            logger.error(f"Error splitting file {file_path}: {e}")
            return []
    
    def _split_with_tree_sitter(self, file_path: str, content: str, language: str) -> List[CodeChunk]:
        """Split code using tree-sitter parsing."""
        chunks = []
        
        try:
            # Parse the file
            result = self.parser.parse_file(file_path, content)
            if not result.success:
                logger.debug(f"Tree-sitter parsing failed for {file_path}: {result.error}")
                return []
            
            lines = content.split('\n')
            
            # Process classes
            for cls in result.classes:
                # Add the class header as a chunk
                class_header = self._extract_class_header(cls, lines)
                if class_header:
                    header_chunks = self._create_chunks_from_content(
                        content=class_header,
                        file_path=file_path,
                        start_line=cls.start_line,
                        chunk_type="class_header",
                        name=cls.name,
                        language=language,
                        metadata={
                            "base_classes": getattr(cls, 'base_classes', []),
                            "decorators": getattr(cls, 'decorators', [])
                        }
                    )
                    chunks.extend(header_chunks)
                
                # Add methods as individual chunks
                for method in cls.methods:
                    method_content = self._extract_block_content(method, lines)
                    if method_content and len(method_content) >= self.min_chunk_size:
                        method_chunks = self._create_chunks_from_content(
                            content=method_content,
                            file_path=file_path,
                            start_line=method.start_line,
                            chunk_type="method",
                            name=method.name,
                            language=language,
                            parent_name=cls.name,
                            metadata={
                                "parameters": getattr(method, 'parameters', []),
                                "decorators": getattr(method, 'decorators', []),
                                "is_async": getattr(method, 'is_async', False),
                                "is_static": getattr(method, 'is_static', False)
                            }
                        )
                        chunks.extend(method_chunks)
            
            # Process standalone functions
            for func in result.functions:
                func_content = self._extract_block_content(func, lines)
                if func_content and len(func_content) >= self.min_chunk_size:
                    func_chunks = self._create_chunks_from_content(
                        content=func_content,
                        file_path=file_path,
                        start_line=func.start_line,
                        chunk_type="function",
                        name=func.name,
                        language=language,
                        metadata={
                            "parameters": getattr(func, 'parameters', []),
                            "decorators": getattr(func, 'decorators', []),
                            "is_async": getattr(func, 'is_async', False)
                        }
                    )
                    chunks.extend(func_chunks)
            
            # If we have very few chunks, add some larger context chunks
            if len(chunks) < 3:
                chunks.extend(self._create_context_chunks(file_path, content, language, lines))
            
            return chunks
            
        except Exception as e:
            logger.debug(f"Tree-sitter splitting failed for {file_path}: {e}")
            return []
    
    def _extract_class_header(self, cls, lines: List[str]) -> str:
        """Extract class header including docstring."""
        try:
            start_idx = cls.start_line - 1
            
            # Find the end of class definition (after ':')
            end_idx = start_idx
            for i in range(start_idx, min(start_idx + 10, len(lines))):
                if ':' in lines[i]:
                    end_idx = i + 1
                    break
            
            # Include docstring if present
            if end_idx < len(lines):
                next_line = lines[end_idx].strip()
                if next_line.startswith('"""') or next_line.startswith("'''"):
                    # Find end of docstring
                    quote = next_line[:3]
                    for i in range(end_idx, min(end_idx + 20, len(lines))):
                        if quote in lines[i] and i > end_idx:
                            end_idx = i + 1
                            break
            
            return '\n'.join(lines[start_idx:end_idx])
        except:
            return ""
    
    def _extract_block_content(self, block, lines: List[str]) -> str:
        """Extract content of a code block."""
        try:
            start_idx = block.start_line - 1
            end_idx = min(block.end_line, len(lines))
            content = '\n'.join(lines[start_idx:end_idx])
            
            # Truncate if too large
            if len(content) > self.max_chunk_size:
                content = content[:self.max_chunk_size] + "\n# ... (truncated)"
            
            return content
        except:
            return ""
    
    def _create_context_chunks(self, file_path: str, content: str, language: str, lines: List[str]) -> List[CodeChunk]:
        """Create larger context chunks for files with few semantic blocks."""
        chunks = []
        
        # Split into reasonably sized chunks
        chunk_lines = self.max_chunk_size // 50  # Rough estimate of lines per chunk
        
        for i in range(0, len(lines), chunk_lines):
            chunk_content = '\n'.join(lines[i:i + chunk_lines])
            
            if len(chunk_content.strip()) >= self.min_chunk_size:
                chunks.append(CodeChunk(
                    id="",
                    content=chunk_content,
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=min(i + chunk_lines, len(lines)),
                    chunk_type="context",
                    name=f"context_{i // chunk_lines + 1}",
                    language=language
                ))
        
        return chunks
    
    def _split_with_text(self, file_path: str, content: str, language: str) -> List[CodeChunk]:
        """Fallback text-based splitting."""
        chunks = []
        lines = content.split('\n')
        
        # Simple line-based chunking
        chunk_lines = self.max_chunk_size // 50
        
        for i in range(0, len(lines), chunk_lines):
            chunk_content = '\n'.join(lines[i:i + chunk_lines])
            
            if len(chunk_content.strip()) >= self.min_chunk_size:
                chunks.append(CodeChunk(
                    id="",
                    content=chunk_content,
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=min(i + chunk_lines, len(lines)),
                    chunk_type="text_chunk",
                    name=f"chunk_{i // chunk_lines + 1}",
                    language=language
                ))
        
        return chunks
    
    def split_workspace(self, file_patterns: Optional[List[str]] = None) -> List[CodeChunk]:
        """
        Split all files in the workspace into chunks.
        
        Args:
            file_patterns: Optional list of glob patterns to filter files
            
        Returns:
            List of all CodeChunk objects
        """
        all_chunks = []
        processed_files = 0
        
        # Determine files to process
        if file_patterns:
            files_to_process = []
            for pattern in file_patterns:
                files_to_process.extend(self.workspace_root.glob(pattern))
        else:
            # Process all allowed files
            files_to_process = []
            for file_path in self.workspace_root.rglob("*"):
                if file_path.is_file() and self.config.is_file_allowed(file_path):
                    files_to_process.append(file_path)
        
        logger.info(f"Processing {len(files_to_process)} files for code splitting")
        
        for file_path in files_to_process:
            try:
                relative_path = file_path.relative_to(self.workspace_root)
                chunks = self.split_file(str(relative_path))
                
                if chunks:
                    all_chunks.extend(chunks)
                    processed_files += 1
                    
                    if processed_files % 50 == 0:
                        logger.info(f"Processed {processed_files} files, {len(all_chunks)} chunks created")
                
            except Exception as e:
                logger.debug(f"Error processing file {file_path}: {e}")
                continue
        
        logger.info(f"Code splitting complete: {processed_files} files, {len(all_chunks)} chunks")
        return all_chunks