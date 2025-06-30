"""
Language detection and parser management for tree-sitter.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from tree_sitter_languages import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    get_language = None
    get_parser = None

logger = logging.getLogger(__name__)

# Language mappings
LANGUAGE_EXTENSIONS = {
    'python': ['.py', '.pyw'],
    'javascript': ['.js', '.jsx', '.mjs'],
    'typescript': ['.ts', '.tsx'],
    'java': ['.java'],
    'c': ['.c', '.h'],
    'cpp': ['.cpp', '.cxx', '.cc', '.hpp', '.hxx'],
    'rust': ['.rs'],
    'go': ['.go'],
    'ruby': ['.rb'],
    'php': ['.php'],
    'c_sharp': ['.cs'],
}

# Reverse mapping for quick lookup
EXTENSION_TO_LANGUAGE = {}
for lang, exts in LANGUAGE_EXTENSIONS.items():
    for ext in exts:
        EXTENSION_TO_LANGUAGE[ext] = lang


def detect_language(file_path: str, content: Optional[str] = None) -> str:
    """
    Detect the programming language of a file.
    
    Args:
        file_path: Path to the file
        content: Optional file content for content-based detection
        
    Returns:
        Language name or 'unknown' if not detected
    """
    # First try extension-based detection
    ext = Path(file_path).suffix.lower()
    if ext in EXTENSION_TO_LANGUAGE:
        return EXTENSION_TO_LANGUAGE[ext]
    
    # Content-based detection for common shebangs
    if content:
        first_line = content.split('\n')[0].strip()
        if first_line.startswith('#!'):
            if 'python' in first_line:
                return 'python'
            elif 'node' in first_line or 'javascript' in first_line:
                return 'javascript'
            elif 'ruby' in first_line:
                return 'ruby'
            elif 'php' in first_line:
                return 'php'
    
    return 'unknown'


def get_parser_for_language(language: str):
    """
    Get a tree-sitter parser for the specified language.
    
    Args:
        language: Programming language name
        
    Returns:
        Tree-sitter parser instance or None if not available
    """
    if not TREE_SITTER_AVAILABLE:
        logger.debug("Tree-sitter not available")
        return None
    
    try:
        # Handle language aliases
        lang_map = {
            'javascript': 'javascript',
            'typescript': 'typescript', 
            'python': 'python',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'c_sharp': 'c_sharp',
            'rust': 'rust',
            'go': 'go',
            'ruby': 'ruby',
            'php': 'php'
        }
        
        mapped_lang = lang_map.get(language, language)
        if get_parser is None:
            return None
        return get_parser(mapped_lang)
        
    except Exception as e:
        logger.debug(f"Failed to get parser for {language}: {e}")
        return None


def is_tree_sitter_available() -> bool:
    """Check if tree-sitter is available."""
    return TREE_SITTER_AVAILABLE