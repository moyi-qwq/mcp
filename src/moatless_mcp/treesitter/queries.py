"""
Data structures for representing parsed code elements.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class CodeBlock:
    """Represents a code block with location information."""
    name: str
    start_line: int  # 1-based
    end_line: int    # 1-based
    start_byte: int
    end_byte: int
    text: str
    type: str = 'block'  # 'class', 'function', 'method', etc.
    parent: Optional['CodeBlock'] = None
    children: List['CodeBlock'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass 
class FunctionDef(CodeBlock):
    """Represents a function definition."""
    parameters: List[str] = None
    return_type: Optional[str] = None
    decorators: List[str] = None
    is_async: bool = False
    is_static: bool = False
    is_class_method: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        if self.parameters is None:
            self.parameters = []
        if self.decorators is None:
            self.decorators = []
        self.type = 'function'


@dataclass
class ClassDef(CodeBlock):
    """Represents a class definition."""
    base_classes: List[str] = None
    decorators: List[str] = None
    methods: List[FunctionDef] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.base_classes is None:
            self.base_classes = []
        if self.decorators is None:
            self.decorators = []
        if self.methods is None:
            self.methods = []
        self.type = 'class'


@dataclass
class ParseResult:
    """Result of parsing a code file."""
    language: str
    classes: List[ClassDef]
    functions: List[FunctionDef] 
    all_blocks: List[CodeBlock]
    success: bool = True
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.classes is None:
            self.classes = []
        if self.functions is None:
            self.functions = []
        if self.all_blocks is None:
            self.all_blocks = []