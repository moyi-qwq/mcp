"""
Core tree-sitter parser implementation.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from .languages import get_parser_for_language, detect_language, is_tree_sitter_available
from .queries import CodeBlock, FunctionDef, ClassDef, ParseResult

logger = logging.getLogger(__name__)


class CodeParser:
    """Main parser class for extracting code structures using tree-sitter."""
    
    def __init__(self):
        self.available = is_tree_sitter_available()
        if not self.available:
            logger.warning("Tree-sitter not available, falling back to regex parsing")
    
    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParseResult:
        """
        Parse a code file and extract classes and functions.
        
        Args:
            file_path: Path to the file
            content: Optional file content (will read from file if not provided)
            
        Returns:
            ParseResult containing extracted code structures
        """
        if not self.available:
            return ParseResult(
                language='unknown',
                classes=[],
                functions=[],
                all_blocks=[],
                success=False,
                error="Tree-sitter not available"
            )
        
        # Read content if not provided
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                return ParseResult(
                    language='unknown',
                    classes=[],
                    functions=[],
                    all_blocks=[],
                    success=False,
                    error=f"Failed to read file: {e}"
                )
        
        # Detect language
        language = detect_language(file_path, content)
        if language == 'unknown':
            return ParseResult(
                language=language,
                classes=[],
                functions=[],
                all_blocks=[],
                success=False,
                error="Unknown language"
            )
        
        # Get parser
        parser = get_parser_for_language(language)
        if parser is None:
            return ParseResult(
                language=language,
                classes=[],
                functions=[],
                all_blocks=[],
                success=False,
                error=f"No parser available for {language}"
            )
        
        try:
            # Parse the code
            tree = parser.parse(bytes(content, 'utf8'))
            root_node = tree.root_node
            
            # Extract code blocks based on language
            if language == 'python':
                return self._parse_python(content, root_node, language)
            elif language in ['javascript', 'typescript']:
                return self._parse_javascript(content, root_node, language)
            elif language == 'java':
                return self._parse_java(content, root_node, language)
            else:
                return self._parse_generic(content, root_node, language)
                
        except Exception as e:
            return ParseResult(
                language=language,
                classes=[],
                functions=[],
                all_blocks=[],
                success=False,
                error=f"Parsing failed: {e}"
            )
    
    def find_functions(self, file_path: str, function_name: str, content: Optional[str] = None) -> List[FunctionDef]:
        """Find all functions with the given name."""
        result = self.parse_file(file_path, content)
        if not result.success:
            return []
        
        matches = []
        for func in result.functions:
            if func.name == function_name:
                matches.append(func)
        
        # Also search in class methods
        for cls in result.classes:
            for method in cls.methods:
                if method.name == function_name:
                    matches.append(method)
        
        return matches
    
    def find_classes(self, file_path: str, class_name: str, content: Optional[str] = None) -> List[ClassDef]:
        """Find all classes with the given name."""
        result = self.parse_file(file_path, content)
        if not result.success:
            return []
        
        matches = []
        for cls in result.classes:
            if cls.name == class_name:
                matches.append(cls)
        
        return matches
    
    def find_class_method(self, file_path: str, class_name: str, method_name: str, 
                         content: Optional[str] = None) -> List[FunctionDef]:
        """Find a specific method within a specific class."""
        classes = self.find_classes(file_path, class_name, content)
        matches = []
        
        for cls in classes:
            for method in cls.methods:
                if method.name == method_name:
                    matches.append(method)
        
        return matches
    
    def _parse_python(self, content: str, root_node, language: str) -> ParseResult:
        """Parse Python-specific constructs."""
        lines = content.split('\n')
        classes = []
        functions = []
        all_blocks = []
        
        def extract_python_blocks(node, parent_class=None, depth=0):
            indent = "  " * depth
            logger.debug(f"{indent}Processing node: {node.type}")
            
            if node.type == 'class_definition':
                logger.debug(f"{indent}Found class definition")
                class_def = self._extract_python_class(node, lines, parent_class)
                if class_def:
                    classes.append(class_def)
                    all_blocks.append(class_def)
                    logger.debug(f"{indent}Added class: {class_def.name}")
                    
                    # Parse methods within the class
                    for child in node.children:
                        if child.type == 'block':
                            for grandchild in child.children:
                                extract_python_blocks(grandchild, class_def, depth + 1)
            
            elif node.type == 'function_definition':
                logger.debug(f"{indent}Found function definition")
                func_def = self._extract_python_function(node, lines, parent_class)
                if func_def:
                    if parent_class:
                        parent_class.methods.append(func_def)
                        parent_class.children.append(func_def)
                    else:
                        functions.append(func_def)
                    all_blocks.append(func_def)
                    logger.debug(f"{indent}Added function: {func_def.name}")
            
            else:
                # Recursively process children
                for child in node.children:
                    extract_python_blocks(child, parent_class, depth + 1)
        
        extract_python_blocks(root_node)
        
        return ParseResult(
            language=language,
            classes=classes,
            functions=functions,
            all_blocks=all_blocks,
            success=True
        )
    
    def _extract_python_class(self, node, lines: List[str], parent=None) -> Optional[ClassDef]:
        """Extract Python class definition."""
        try:
            start_line = node.start_point[0] + 1  # Convert to 1-based
            end_line = node.end_point[0] + 1
            
            # Find class name
            name = None
            for child in node.children:
                if child.type == 'identifier':
                    name = child.text.decode('utf8')
                    break
            
            if not name:
                return None
            
            # Extract text
            text = '\n'.join(lines[start_line-1:end_line])
            
            # Extract base classes
            base_classes = []
            for child in node.children:
                if child.type == 'argument_list':
                    for arg in child.children:
                        if arg.type == 'identifier':
                            base_classes.append(arg.text.decode('utf8'))
            
            return ClassDef(
                name=name,
                start_line=start_line,
                end_line=end_line,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                text=text,
                parent=parent,
                base_classes=base_classes
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract Python class: {e}")
            return None
    
    def _extract_python_function(self, node, lines: List[str], parent_class=None) -> Optional[FunctionDef]:
        """Extract Python function definition."""
        try:
            start_line = node.start_point[0] + 1  # Convert to 1-based
            end_line = node.end_point[0] + 1
            
            # Find function name
            name = None
            for child in node.children:
                if child.type == 'identifier':
                    name = child.text.decode('utf8')
                    break
            
            if not name:
                return None
            
            # Extract text
            text = '\n'.join(lines[start_line-1:end_line])
            
            # Extract parameters
            parameters = []
            for child in node.children:
                if child.type == 'parameters':
                    for param in child.children:
                        if param.type == 'identifier':
                            parameters.append(param.text.decode('utf8'))
                        elif param.type == 'default_parameter':
                            for p_child in param.children:
                                if p_child.type == 'identifier':
                                    parameters.append(p_child.text.decode('utf8'))
                                    break
            
            # Check for decorators and async
            is_async = False
            decorators = []
            
            # Look at siblings for decorators (they come before the function)
            if node.parent:
                for sibling in node.parent.children:
                    if sibling.start_byte < node.start_byte:
                        if sibling.type == 'decorator':
                            dec_text = sibling.text.decode('utf8').strip()
                            decorators.append(dec_text)
                        elif sibling.type == 'async' or (hasattr(sibling, 'text') and 'async' in sibling.text.decode('utf8')):
                            is_async = True
            
            # Check if it's a static method or class method
            is_static = any('@staticmethod' in dec for dec in decorators)
            is_class_method = any('@classmethod' in dec for dec in decorators)
            
            return FunctionDef(
                name=name,
                start_line=start_line,
                end_line=end_line,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                text=text,
                parent=parent_class,
                parameters=parameters,
                decorators=decorators,
                is_async=is_async,
                is_static=is_static,
                is_class_method=is_class_method
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract Python function: {e}")
            return None
    
    def _parse_javascript(self, content: str, root_node, language: str) -> ParseResult:
        """Parse JavaScript/TypeScript-specific constructs."""
        lines = content.split('\n')
        classes = []
        functions = []
        all_blocks = []
        
        def extract_js_blocks(node, parent_class=None):
            if node.type == 'class_declaration':
                class_def = self._extract_js_class(node, lines, parent_class)
                if class_def:
                    classes.append(class_def)
                    all_blocks.append(class_def)
                    
                    # Parse methods within the class
                    for child in node.children:
                        if child.type == 'class_body':
                            for method_node in child.children:
                                if method_node.type == 'method_definition':
                                    extract_js_blocks(method_node, class_def)
            
            elif node.type in ['function_declaration', 'method_definition', 'arrow_function']:
                func_def = self._extract_js_function(node, lines, parent_class)
                if func_def:
                    if parent_class:
                        parent_class.methods.append(func_def)
                        parent_class.children.append(func_def)
                    else:
                        functions.append(func_def)
                    all_blocks.append(func_def)
            
            else:
                # Recursively process children
                for child in node.children:
                    extract_js_blocks(child, parent_class)
        
        extract_js_blocks(root_node)
        
        return ParseResult(
            language=language,
            classes=classes,
            functions=functions,
            all_blocks=all_blocks,
            success=True
        )
    
    def _extract_js_class(self, node, lines: List[str], parent=None) -> Optional[ClassDef]:
        """Extract JavaScript class definition."""
        try:
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # Find class name
            name = None
            for child in node.children:
                if child.type == 'identifier':
                    name = child.text.decode('utf8')
                    break
            
            if not name:
                return None
            
            text = '\n'.join(lines[start_line-1:end_line])
            
            return ClassDef(
                name=name,
                start_line=start_line,
                end_line=end_line,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                text=text,
                parent=parent
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract JavaScript class: {e}")
            return None
    
    def _extract_js_function(self, node, lines: List[str], parent_class=None) -> Optional[FunctionDef]:
        """Extract JavaScript function definition."""
        try:
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # Find function name
            name = None
            for child in node.children:
                if child.type == 'identifier':
                    name = child.text.decode('utf8')
                    break
                elif child.type == 'property_identifier':
                    name = child.text.decode('utf8')
                    break
            
            if not name:
                return None
            
            text = '\n'.join(lines[start_line-1:end_line])
            
            # Extract parameters
            parameters = []
            for child in node.children:
                if child.type == 'formal_parameters':
                    for param in child.children:
                        if param.type == 'identifier':
                            parameters.append(param.text.decode('utf8'))
            
            return FunctionDef(
                name=name,
                start_line=start_line,
                end_line=end_line,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                text=text,
                parent=parent_class,
                parameters=parameters
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract JavaScript function: {e}")
            return None
    
    def _parse_java(self, content: str, root_node, language: str) -> ParseResult:
        """Parse Java-specific constructs."""
        # Similar implementation for Java
        # For now, return basic structure
        return ParseResult(
            language=language,
            classes=[],
            functions=[],
            all_blocks=[],
            success=True
        )
    
    def _parse_generic(self, content: str, root_node, language: str) -> ParseResult:
        """Generic parser for unsupported languages."""
        return ParseResult(
            language=language,
            classes=[],
            functions=[],
            all_blocks=[],
            success=True
        )