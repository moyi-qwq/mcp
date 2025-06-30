"""
Tree-sitter backend for accurate code parsing and analysis.
"""

from .parser import CodeParser, ParseResult
from .languages import get_parser_for_language, detect_language, is_tree_sitter_available
from .queries import CodeBlock, FunctionDef, ClassDef

__all__ = [
    'CodeParser',
    'ParseResult', 
    'get_parser_for_language',
    'detect_language',
    'is_tree_sitter_available',
    'CodeBlock',
    'FunctionDef',
    'ClassDef'
]