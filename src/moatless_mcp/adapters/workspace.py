"""
Workspace adapter for managing project files and state
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import git
from git.exc import InvalidGitRepositoryError

from moatless_mcp.utils.config import Config

# Add moatless path to sys.path
current_file = Path(__file__).resolve()
# From: .../moatless-mcp-server/src/moatless_mcp/adapters/workspace.py
# To: .../moatless-tools (parent of moatless-mcp-server)
src_dir = current_file.parent.parent.parent  # .../moatless-mcp-server/src
mcp_server_dir = src_dir.parent  # .../moatless-mcp-server
moatless_tools_dir = mcp_server_dir.parent  # .../moatless-tools

if str(moatless_tools_dir) not in sys.path:
    sys.path.insert(0, str(moatless_tools_dir))

# Import moatless components for semantic search
try:
    from moatless.index import CodeIndex
    from moatless.index.settings import IndexSettings
    from moatless.repository import FileRepository
    MOATLESS_AVAILABLE = True
except ImportError:
    MOATLESS_AVAILABLE = False
    CodeIndex = None
    IndexSettings = None
    FileRepository = None

logger = logging.getLogger(__name__)


class FileContext:
    """Simple file context manager"""
    
    def __init__(self, workspace_path: Path, config: Config):
        self.workspace_path = workspace_path
        self.config = config
        self._file_cache: Dict[str, str] = {}
    
    def get_file_content(self, file_path: str) -> str:
        """Get file content with caching"""
        full_path = self.workspace_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self.config.is_file_allowed(full_path):
            raise PermissionError(f"File access not allowed: {file_path}")
        
        # Check file size
        if full_path.stat().st_size > self.config.max_file_size:
            raise ValueError(f"File too large: {file_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self._file_cache[file_path] = content
                return content
        except UnicodeDecodeError:
            # Try with different encoding
            with open(full_path, 'r', encoding='latin1') as f:
                content = f.read()
                self._file_cache[file_path] = content
                return content
    
    def write_file_content(self, file_path: str, content: str) -> None:
        """Write content to file"""
        full_path = self.workspace_path / file_path
        
        if not self.config.is_file_allowed(full_path):
            raise PermissionError(f"File access not allowed: {file_path}")
        
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Update cache
        self._file_cache[file_path] = content
    
    def list_files(self, directory: str = "", recursive: bool = False, 
                   max_results: int = 100) -> List[str]:
        """List files in directory"""
        base_path = self.workspace_path / directory if directory else self.workspace_path
        
        if not base_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        files = []
        
        try:
            if recursive:
                for file_path in base_path.rglob("*"):
                    if file_path.is_file() and self.config.is_file_allowed(file_path):
                        rel_path = file_path.relative_to(self.workspace_path)
                        files.append(str(rel_path))
                        if len(files) >= max_results:
                            break
            else:
                for file_path in base_path.iterdir():
                    if file_path.is_file() and self.config.is_file_allowed(file_path):
                        rel_path = file_path.relative_to(self.workspace_path)
                        files.append(str(rel_path))
                        if len(files) >= max_results:
                            break
        except PermissionError as e:
            logger.warning(f"Permission denied accessing directory {base_path}: {e}")
        
        return sorted(files)


class WorkspaceAdapter:
    """Adapter for managing workspace operations"""
    
    def __init__(self, workspace_path: str, config: Config):
        self.workspace_path = Path(workspace_path).resolve()
        self.config = config
        self.file_context = FileContext(self.workspace_path, config)
        
        # Initialize code index for semantic search
        self._code_index: Optional[CodeIndex] = None
        self._index_initialized = False
        
        # Try to initialize git repository
        self.git_repo: Optional[git.Repo] = None
        try:
            self.git_repo = git.Repo(self.workspace_path)
            logger.info(f"Git repository detected at {self.workspace_path}")
        except InvalidGitRepositoryError:
            logger.info(f"No git repository found at {self.workspace_path}")
        
        logger.info(f"Workspace initialized at {self.workspace_path}")
    
    @property
    def code_index(self) -> Optional[CodeIndex]:
        """Get the code index for semantic search"""
        return self._code_index
    
    async def initialize_code_index(self, force_rebuild: bool = False) -> bool:
        """Initialize code index for semantic search"""
        if not MOATLESS_AVAILABLE:
            logger.warning("Moatless is not available. Semantic search will be limited.")
            return False
        
        if self._index_initialized and not force_rebuild and self._code_index:
            return True
        
        try:
            # Check for existing index
            index_dir = self.workspace_path / ".moatless_index"
            
            if index_dir.exists() and not force_rebuild:
                logger.info("Loading existing code index...")
                file_repo = FileRepository(str(self.workspace_path))
                self._code_index = await CodeIndex.from_persist_dir_async(
                    str(index_dir), 
                    file_repo=file_repo
                )
                logger.info("Code index loaded successfully")
            else:
                logger.info("Building new code index...")
                await self._build_code_index()
                logger.info("Code index built successfully")
            
            self._index_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize code index: {e}")
            return False
    
    async def _build_code_index(self) -> None:
        """Build code index from scratch"""
        try:
            # Determine the programming language
            language = self._detect_primary_language()
            logger.info(f"Detected primary language: {language}")
            
            # Configure index settings - use python but with larger chunks to reduce parsing complexity
            settings = IndexSettings(
                language=language,
                embed_model="jina-embeddings-v3",
                dimensions=1024,
                min_chunk_size=500,  # Larger chunks to reduce parsing issues
                chunk_size=2000,     # Larger chunks
                hard_token_limit=4000,
                max_chunks=50        # Fewer chunks to reduce complexity
            )
            logger.info("Index settings configured")
            
            # Create file repository
            file_repo = FileRepository(repo_path=str(self.workspace_path))
            logger.info("File repository created")
            
            # Import and create Jina AI embedding model explicitly
            from moatless.index.embed_model import JinaAIEmbedding
            embed_model = JinaAIEmbedding(model_name="jina-embeddings-v3")
            
            # Create code index with explicit embedding model
            self._code_index = CodeIndex(
                file_repo=file_repo,
                settings=settings,
                embed_model=embed_model,
                max_results=25
            )
            logger.info("Code index object created")
            
            # Run ingestion in a thread to avoid blocking
            logger.info("Starting code ingestion...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self._code_index.run_ingestion,
                str(self.workspace_path)
            )
            logger.info("Code ingestion completed")
            
            # Persist index
            index_dir = self.workspace_path / ".moatless_index"
            index_dir.mkdir(exist_ok=True)
            
            logger.info("Persisting index...")
            await loop.run_in_executor(
                None,
                self._code_index.persist,
                str(index_dir)
            )
            logger.info("Index persisted successfully")
            
        except Exception as e:
            logger.error(f"Error in _build_code_index: {e}")
            raise
    
    def _detect_primary_language(self) -> str:
        """Detect the primary programming language in the workspace"""
        language_counts = {}
        
        # Count files by extension
        for file_path in self.workspace_path.rglob("*"):
            if file_path.is_file() and self.config.is_file_allowed(file_path):
                ext = file_path.suffix.lower()
                if ext in ['.py', '.pyw']:
                    language_counts['python'] = language_counts.get('python', 0) + 1
                elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                    language_counts['javascript'] = language_counts.get('javascript', 0) + 1
                elif ext in ['.java']:
                    language_counts['java'] = language_counts.get('java', 0) + 1
                elif ext in ['.cpp', '.cxx', '.cc', '.c']:
                    language_counts['cpp'] = language_counts.get('cpp', 0) + 1
        
        # Return the most common language, default to python
        if language_counts:
            return max(language_counts, key=language_counts.get)
        return 'python'
    
    def get_file_context(self) -> FileContext:
        """Get file context manager"""
        return self.file_context
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """Get workspace information"""
        info = {
            "path": str(self.workspace_path),
            "exists": self.workspace_path.exists(),
            "is_git_repo": self.git_repo is not None,
            "moatless_available": MOATLESS_AVAILABLE,
            "index_initialized": self._index_initialized,
        }
        
        if self.git_repo:
            try:
                info["git_branch"] = self.git_repo.active_branch.name
                info["git_remote"] = [remote.name for remote in self.git_repo.remotes]
            except Exception as e:
                logger.warning(f"Error getting git info: {e}")
        
        return info
    
    def search_files(self, pattern: str, max_results: int = 100) -> List[str]:
        """Search for files matching a pattern"""
        import fnmatch
        
        matching_files = []
        
        try:
            for file_path in self.workspace_path.rglob("*"):
                if file_path.is_file() and self.config.is_file_allowed(file_path):
                    rel_path = file_path.relative_to(self.workspace_path)
                    if fnmatch.fnmatch(str(rel_path), pattern):
                        matching_files.append(str(rel_path))
                        if len(matching_files) >= max_results:
                            break
        except Exception as e:
            logger.error(f"Error searching files: {e}")
        
        return sorted(matching_files)
    
    def grep_files(self, pattern: str, file_pattern: str = "*", 
                   max_results: int = 100) -> List[Dict[str, Any]]:
        """Search for text pattern in files"""
        import re
        import fnmatch
        
        results = []
        regex = re.compile(pattern, re.IGNORECASE)
        
        try:
            for file_path in self.workspace_path.rglob(file_pattern):
                if (file_path.is_file() and 
                    self.config.is_file_allowed(file_path) and
                    file_path.stat().st_size <= self.config.max_file_size):
                    
                    try:
                        content = self.file_context.get_file_content(
                            str(file_path.relative_to(self.workspace_path))
                        )
                        
                        for line_num, line in enumerate(content.splitlines(), 1):
                            if regex.search(line):
                                results.append({
                                    "file": str(file_path.relative_to(self.workspace_path)),
                                    "line": line_num,
                                    "content": line.strip()
                                })
                                
                                if len(results) >= max_results:
                                    return results
                                    
                    except Exception as e:
                        logger.warning(f"Error reading file {file_path}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error during grep: {e}")
        
        return results