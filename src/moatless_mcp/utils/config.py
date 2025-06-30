"""
Configuration management for Moatless MCP Server
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional


@dataclass
class Config:
    """Configuration for Moatless MCP Server"""
    
    # File operations
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_lines_per_file: int = 10000
    
    # Search configuration
    max_search_results: int = 100
    search_timeout: int = 30  # seconds
    
    # Tree-sitter configuration
    enable_parsing: bool = True
    supported_languages: Dict[str, str] = field(default_factory=lambda: {
        ".py": "python",
        ".java": "java",
    })
    
    # Security settings
    allowed_file_extensions: set = field(default_factory=lambda: {
        # Programming languages
        ".py", ".java", ".js", ".ts", ".jsx", ".tsx", 
        ".c", ".cpp", ".h", ".hpp", ".cs", ".php", 
        ".rb", ".go", ".rs", ".swift", ".kt", ".scala",
        ".dart", ".lua", ".perl", ".sh", ".bash", ".zsh",
        ".ps1", ".bat", ".cmd", ".asm", ".s",
        
        # Web technologies
        ".html", ".css", ".scss", ".sass", ".less",
        ".vue", ".svelte", ".astro",
        
        # Data and config
        ".json", ".yaml", ".yml", ".toml", ".xml",
        ".cfg", ".ini", ".conf", ".properties", ".env",
        ".sql", ".graphql", ".proto",
        
        # Documentation
        ".md", ".txt", ".rst", ".adoc", ".tex",
        
        # Build and project files
        ".dockerfile", ".dockerignore", ".gitignore",
        ".gitattributes", ".editorconfig", ".eslintrc",
        ".prettierrc", ".babelrc", ".tsconfig",
        
        # Data files
        ".csv", ".tsv", ".log",
        
        # Files without extension (common in Unix)
        ""
    })
    
    forbidden_paths: set = field(default_factory=lambda: {
        # Only essential forbidden paths for security
        "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache"
    })
    
    # Allow access to version control and hidden files
    allow_hidden_files: bool = True
    allow_version_control: bool = True
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables"""
        config = cls()
        
        # Override from environment
        if max_size := os.getenv("MOATLESS_MAX_FILE_SIZE"):
            config.max_file_size = int(max_size)
            
        if max_results := os.getenv("MOATLESS_MAX_SEARCH_RESULTS"):
            config.max_search_results = int(max_results)
            
        if timeout := os.getenv("MOATLESS_SEARCH_TIMEOUT"):
            config.search_timeout = int(timeout)
            
        # Security settings from environment
        if os.getenv("MOATLESS_ALLOW_HIDDEN_FILES", "true").lower() == "true":
            config.allow_hidden_files = True
            
        if os.getenv("MOATLESS_ALLOW_VERSION_CONTROL", "true").lower() == "true":
            config.allow_version_control = True
            
        return config
    
    def is_file_allowed(self, file_path: Path) -> bool:
        """Check if a file is allowed to be accessed"""
        
        # Check forbidden paths first (most restrictive)
        for part in file_path.parts:
            if part in self.forbidden_paths:
                return False
        
        # Check version control access
        if not self.allow_version_control:
            version_control_dirs = {".git", ".svn", ".hg"}
            for part in file_path.parts:
                if part in version_control_dirs:
                    return False
        
        # Check hidden files access
        if not self.allow_hidden_files:
            for part in file_path.parts:
                if part.startswith('.') and part not in {'.', '..'}:
                    return False
        
        # Check file extension (more permissive now)
        file_ext = file_path.suffix.lower()
        if file_ext not in self.allowed_file_extensions:
            # Allow files without extension or check if it's a text file
            if file_ext == "" or self._is_likely_text_file(file_path):
                return True
            return False
        
        return True
    
    def _is_likely_text_file(self, file_path: Path) -> bool:
        """Check if a file is likely a text file by common patterns"""
        name_lower = file_path.name.lower()
        
        # Common text files without extensions
        text_files = {
            'readme', 'license', 'changelog', 'makefile', 'dockerfile',
            'pipfile', 'gemfile', 'rakefile', 'gulpfile', 'gruntfile',
            'procfile', 'buildfile', 'justfile'
        }
        
        return name_lower in text_files
    
    def get_language_for_file(self, file_path: Path) -> Optional[str]:
        """Get language identifier for a file"""
        return self.supported_languages.get(file_path.suffix.lower())