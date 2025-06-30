"""Advanced code search tools for MCP server."""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from moatless_mcp.utils.config import Config

# Import our own tree-sitter backend
try:
    from moatless_mcp.treesitter import CodeParser, detect_language, is_tree_sitter_available
    TREE_SITTER_AVAILABLE = is_tree_sitter_available()
except ImportError as e:
    logging.debug(f"Tree-sitter parsing not available: {e}")
    CodeParser = None
    detect_language = None
    TREE_SITTER_AVAILABLE = False

logger = logging.getLogger(__name__)


class AdvancedSearchTools:
    """Advanced code search functionality."""
    
    def __init__(self, config: Config, workspace_root: str = "."):
        self.config = config
        self.workspace_root = Path(workspace_root)
    
    async def find_class(self, class_name: str, file_pattern: Optional[str] = None) -> Dict[str, Any]:
        """Find class definitions in the codebase using tree-sitter when available.
        
        Args:
            class_name: Name of the class to find
            file_pattern: Optional file pattern to limit search (e.g., "src/**/*.py")
        
        Returns:
            Dictionary with search results including file paths and line numbers
        """
        try:
            # Validate inputs
            if not class_name or not class_name.strip():
                return {"error": "Class name cannot be empty"}
            
            # Clean class name - extract just the class name if fully qualified
            clean_class_name = class_name.split(".")[-1] if "." in class_name else class_name
            
            results = []
            search_paths = []
            
            # Determine search paths
            if file_pattern:
                # Use glob pattern to find matching files
                try:
                    search_paths = list(self.workspace_root.glob(file_pattern))
                except Exception as e:
                    logger.warning(f"Invalid file pattern {file_pattern}: {e}")
                    search_paths = []
            
            if not search_paths:
                # Search all allowed files
                search_paths = []
                for root, dirs, files in os.walk(self.workspace_root):
                    for file in files:
                        file_path = Path(root) / file
                        if self.config.is_file_allowed(file_path):
                            search_paths.append(file_path)
            
            # Use tree-sitter parser if available
            if TREE_SITTER_AVAILABLE:
                parser = CodeParser()
                
                for file_path in search_paths:
                    if not self.config.is_file_allowed(file_path):
                        continue
                    
                    try:
                        # Use tree-sitter to find classes
                        classes = parser.find_classes(str(file_path), clean_class_name)
                        
                        for class_def in classes:
                            # Extract the class definition line
                            lines = class_def.text.split('\n')
                            class_line = lines[0].strip() if lines else ""
                            
                            results.append({
                                "file_path": str(file_path.relative_to(self.workspace_root)),
                                "line_number": class_def.start_line,
                                "class_definition": class_line,
                                "match_text": class_line,
                                "language": detect_language(str(file_path)) if detect_language else "unknown",
                                "tree_sitter": True
                            })
                    
                    except Exception as e:
                        logger.debug(f"Tree-sitter parsing failed for {file_path}: {e}")
                        # Fall back to regex for this file
                        self._find_class_regex(file_path, clean_class_name, results)
            else:
                # Fallback to regex search
                for file_path in search_paths:
                    if not self.config.is_file_allowed(file_path):
                        continue
                    self._find_class_regex(file_path, clean_class_name, results)
            
            return {
                "class_name": clean_class_name,
                "results": results,
                "total_matches": len(results),
                "search_pattern": file_pattern,
                "tree_sitter_used": TREE_SITTER_AVAILABLE
            }
            
        except Exception as e:
            logger.error(f"Error in find_class: {e}")
            return {"error": f"Search failed: {str(e)}"}
    
    def _find_class_regex(self, file_path: Path, class_name: str, results: List[Dict]):
        """Fallback regex-based class finding."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            class_pattern = re.compile(rf'^\s*class\s+{re.escape(class_name)}\s*[\(:]', re.MULTILINE)
            matches = list(class_pattern.finditer(content))
            
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                lines = content.split('\n')
                class_line = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                
                results.append({
                    "file_path": str(file_path.relative_to(self.workspace_root)),
                    "line_number": line_num,
                    "class_definition": class_line,
                    "match_text": match.group().strip(),
                    "language": "unknown",
                    "tree_sitter": False
                })
        
        except Exception as e:
            logger.debug(f"Error reading file {file_path}: {e}")
    
    async def find_function(self, function_name: str, file_pattern: Optional[str] = None) -> Dict[str, Any]:
        """Find function definitions in the codebase using tree-sitter when available.
        
        Args:
            function_name: Name of the function to find
            file_pattern: Optional file pattern to limit search
        
        Returns:
            Dictionary with search results including file paths and line numbers
        """
        try:
            if not function_name or not function_name.strip():
                return {"error": "Function name cannot be empty"}
            
            clean_function_name = function_name.strip()
            results = []
            search_paths = []
            
            # Determine search paths
            if file_pattern:
                try:
                    search_paths = list(self.workspace_root.glob(file_pattern))
                except Exception as e:
                    logger.warning(f"Invalid file pattern {file_pattern}: {e}")
                    search_paths = []
            
            if not search_paths:
                search_paths = []
                for root, dirs, files in os.walk(self.workspace_root):
                    for file in files:
                        file_path = Path(root) / file
                        if self.config.is_file_allowed(file_path):
                            search_paths.append(file_path)
            
            # Use tree-sitter parser if available
            if TREE_SITTER_AVAILABLE:
                parser = CodeParser()
                
                for file_path in search_paths:
                    if not self.config.is_file_allowed(file_path):
                        continue
                    
                    try:
                        # Use tree-sitter to find functions
                        functions = parser.find_functions(str(file_path), clean_function_name)
                        
                        for func_def in functions:
                            # Extract the function definition line
                            lines = func_def.text.split('\n')
                            func_line = lines[0].strip() if lines else ""
                            
                            # Determine if it's a method (has parent class)
                            func_type = "method" if func_def.parent else "function"
                            
                            results.append({
                                "file_path": str(file_path.relative_to(self.workspace_root)),
                                "line_number": func_def.start_line,
                                "function_definition": func_line,
                                "match_text": func_line,
                                "language": detect_language(str(file_path)) if detect_language else "unknown",
                                "function_type": func_type,
                                "parent_class": func_def.parent.name if func_def.parent else None,
                                "parameters": func_def.parameters if hasattr(func_def, 'parameters') else [],
                                "tree_sitter": True
                            })
                    
                    except Exception as e:
                        logger.debug(f"Tree-sitter parsing failed for {file_path}: {e}")
                        # Fall back to regex for this file
                        self._find_function_regex(file_path, clean_function_name, results)
            else:
                # Fallback to regex search
                for file_path in search_paths:
                    if not self.config.is_file_allowed(file_path):
                        continue
                    self._find_function_regex(file_path, clean_function_name, results)
            
            # Remove duplicates (same file and line)
            unique_results = []
            seen = set()
            for result in results:
                key = (result["file_path"], result["line_number"])
                if key not in seen:
                    seen.add(key)
                    unique_results.append(result)
            
            return {
                "function_name": clean_function_name,
                "results": unique_results,
                "total_matches": len(unique_results),
                "search_pattern": file_pattern,
                "tree_sitter_used": TREE_SITTER_AVAILABLE
            }
            
        except Exception as e:
            logger.error(f"Error in find_function: {e}")
            return {"error": f"Search failed: {str(e)}"}
    
    def _find_function_regex(self, file_path: Path, function_name: str, results: List[Dict]):
        """Fallback regex-based function finding."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Search for function definitions (supports multiple languages)
            patterns = [
                # Python functions
                (re.compile(rf'^\s*def\s+{re.escape(function_name)}\s*\(', re.MULTILINE), "python"),
                # JavaScript/TypeScript functions
                (re.compile(rf'^\s*function\s+{re.escape(function_name)}\s*\(', re.MULTILINE), "javascript"),
                (re.compile(rf'^\s*const\s+{re.escape(function_name)}\s*=\s*\(', re.MULTILINE), "javascript_const"),
                (re.compile(rf'^\s*{re.escape(function_name)}\s*:\s*function\s*\(', re.MULTILINE), "javascript_object"),
                # Java methods
                (re.compile(rf'^\s*(?:public|private|protected|static|\s)*\s+\w+\s+{re.escape(function_name)}\s*\(', re.MULTILINE), "java"),
                # C/C++ functions
                (re.compile(rf'^\s*\w+\s+{re.escape(function_name)}\s*\(', re.MULTILINE), "c_cpp"),
            ]
            
            for pattern, lang in patterns:
                matches = list(pattern.finditer(content))
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    lines = content.split('\n')
                    function_line = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                    
                    results.append({
                        "file_path": str(file_path.relative_to(self.workspace_root)),
                        "line_number": line_num,
                        "function_definition": function_line,
                        "match_text": match.group().strip(),
                        "language": lang,
                        "function_type": "function",
                        "parent_class": None,
                        "parameters": [],
                        "tree_sitter": False
                    })
        
        except Exception as e:
            logger.debug(f"Error reading file {file_path}: {e}")
    
    async def view_code(self, file_path: str, start_line: Optional[int] = None, 
                       end_line: Optional[int] = None, span_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """View specific code sections with intelligent context.
        
        Args:
            file_path: Path to the file to view
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)
            span_ids: List of span IDs to view (class names, function names, etc.)
        
        Returns:
            Dictionary with code content and metadata
        """
        try:
            # Validate and normalize file path
            full_path = self.workspace_root / file_path
            if not self.config.is_file_allowed(full_path):
                return {"error": "File access not allowed"}
            if not full_path.exists():
                return {"error": f"File not found: {file_path}"}
            
            if not full_path.is_file():
                return {"error": f"Path is not a file: {file_path}"}
            
            # Read file content
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                return {"error": f"Cannot read file: {str(e)}"}
            
            lines = content.split('\n')
            total_lines = len(lines)
            
            result = {
                "file_path": file_path,
                "total_lines": total_lines,
                "content_sections": []
            }
            
            # Handle span_ids (enhanced implementation)
            if span_ids:
                for span_id in span_ids:
                    found_matches = []
                    
                    # Handle different span_id formats
                    if '.' in span_id:
                        # Handle ClassName.method_name format
                        parts = span_id.split('.')
                        if len(parts) == 2:
                            class_name, method_name = parts
                            found_matches.extend(self._find_class_method(content, lines, class_name, method_name))
                    else:
                        # Handle simple class or function names
                        found_matches.extend(self._find_simple_span(content, lines, span_id))
                    
                    # Process matches
                    for match_line, span_type, end_line in found_matches:
                        try:
                            # Validate line numbers
                            if match_line > len(lines) or match_line < 1:
                                continue
                            
                            # Extract the content
                            start_idx = match_line - 1  # Convert to 0-based index
                            end_idx = min(end_line, total_lines)
                            
                            section_content = '\n'.join(lines[start_idx:end_idx])
                            result["content_sections"].append({
                                "span_id": span_id,
                                "span_type": span_type,
                                "start_line": match_line,
                                "end_line": end_idx,
                                "content": section_content
                            })
                        except Exception as e:
                            logger.warning(f"Error processing span_id {span_id}: {e}")
                            continue
                
                # If no matches found for span_ids, add error info
                if not result["content_sections"]:
                    result["content_sections"].append({
                        "error": f"No matches found for span_ids: {', '.join(span_ids)}",
                        "start_line": 1,
                        "end_line": 1,
                        "content": f"# No code blocks found matching: {', '.join(span_ids)}\n# Available in this file, please use line numbers or search for specific patterns."
                    })
            
            # Handle line range
            elif start_line is not None:
                start_idx = max(1, start_line) - 1
                end_idx = min(total_lines, end_line or start_line) if end_line else start_idx + 1
                
                if start_idx >= total_lines:
                    return {"error": f"Start line {start_line} exceeds file length {total_lines}"}
                
                section_content = '\n'.join(lines[start_idx:end_idx])
                result["content_sections"].append({
                    "start_line": start_idx + 1,
                    "end_line": end_idx,
                    "content": section_content
                })
            
            # Return entire file if no specific range requested
            else:
                if total_lines > 1000:  # Limit large files
                    result["content_sections"].append({
                        "start_line": 1,
                        "end_line": 100,
                        "content": '\n'.join(lines[:100]) + f"\n... (file has {total_lines} total lines, showing first 100)"
                    })
                else:
                    result["content_sections"].append({
                        "start_line": 1,
                        "end_line": total_lines,
                        "content": content
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in view_code: {e}")
            return {"error": f"Failed to view code: {str(e)}"}
    
    def _find_simple_span(self, content: str, lines: List[str], span_id: str) -> List[tuple]:
        """Find simple class or function definitions using tree-sitter when available."""
        found_matches = []
        
        # Try tree-sitter first if available
        if TREE_SITTER_AVAILABLE:
            try:
                ts_matches = self._find_with_tree_sitter(content, span_id, lines)
                if ts_matches:
                    return ts_matches
            except Exception as e:
                logger.debug(f"Tree-sitter parsing failed, falling back to regex: {e}")
        
        # Fallback to regex patterns
        patterns = [
            (re.compile(rf'^\s*class\s+{re.escape(span_id)}\s*[\(:]', re.MULTILINE), "class"),
            (re.compile(rf'^\s*def\s+{re.escape(span_id)}\s*\(', re.MULTILINE), "function"),
            # JavaScript/TypeScript patterns
            (re.compile(rf'^\s*function\s+{re.escape(span_id)}\s*\(', re.MULTILINE), "function"),
            (re.compile(rf'^\s*const\s+{re.escape(span_id)}\s*=.*=>', re.MULTILINE), "function"),
            (re.compile(rf'^\s*const\s+{re.escape(span_id)}\s*=.*function', re.MULTILINE), "function"),
            (re.compile(rf'^\s*{re.escape(span_id)}\s*:\s*function', re.MULTILINE), "function"),
            (re.compile(rf'^\s*{re.escape(span_id)}\s*:\s*\(.*\)\s*=>', re.MULTILINE), "function"),
            # Java method patterns
            (re.compile(rf'^\s*(?:public|private|protected|static|\s)*\s+\w+\s+{re.escape(span_id)}\s*\(', re.MULTILINE), "method"),
        ]
        
        for pattern, span_type in patterns:
            matches = list(pattern.finditer(content))
            for match in matches:
                match_line = content[:match.start()].count('\n') + 1
                end_line = self._find_block_end(lines, match_line, span_type)
                found_matches.append((match_line, span_type, end_line))
        
        return found_matches
    
    def _find_class_method(self, content: str, lines: List[str], class_name: str, method_name: str) -> List[tuple]:
        """Find method within a specific class."""
        found_matches = []
        
        # Try tree-sitter first if available
        if TREE_SITTER_AVAILABLE:
            try:
                ts_matches = self._find_class_method_with_tree_sitter(content, class_name, method_name)
                if ts_matches:
                    return ts_matches
            except Exception as e:
                logger.debug(f"Tree-sitter class method parsing failed, falling back to regex: {e}")
        
        # Fallback to regex approach
        # First, find the class
        class_pattern = re.compile(rf'^\s*class\s+{re.escape(class_name)}\s*[\(:]', re.MULTILINE)
        class_matches = list(class_pattern.finditer(content))
        
        for class_match in class_matches:
            class_start_line = content[:class_match.start()].count('\n') + 1
            class_end_line = self._find_block_end(lines, class_start_line, "class")
            
            # Now find methods within this class range
            method_patterns = [
                re.compile(rf'^\s+def\s+{re.escape(method_name)}\s*\(', re.MULTILINE),  # Python
                re.compile(rf'^\s+{re.escape(method_name)}\s*\(', re.MULTILINE),  # Python (simple)
                re.compile(rf'^\s+(?:public|private|protected|static|\s)*\s+\w+\s+{re.escape(method_name)}\s*\(', re.MULTILINE),  # Java
            ]
            
            for method_pattern in method_patterns:
                method_matches = list(method_pattern.finditer(content))
                for method_match in method_matches:
                    method_line = content[:method_match.start()].count('\n') + 1
                    
                    # Check if this method is within the class bounds
                    if class_start_line < method_line < class_end_line:
                        method_end_line = self._find_block_end(lines, method_line, "method")
                        found_matches.append((method_line, "method", method_end_line))
        
        return found_matches
    
    def _find_block_end(self, lines: List[str], start_line: int, block_type: str) -> int:
        """Find the end line of a code block using indentation and context."""
        if start_line > len(lines):
            return start_line
        
        base_line = lines[start_line - 1]
        base_indent = len(base_line) - len(base_line.lstrip())
        total_lines = len(lines)
        
        # Special handling for different block types
        if block_type == "class":
            return self._find_class_end(lines, start_line, base_indent)
        elif block_type in ["method", "function"]:
            return self._find_function_end(lines, start_line, base_indent)
        else:
            return self._find_generic_block_end(lines, start_line, base_indent)
    
    def _find_class_end(self, lines: List[str], start_line: int, base_indent: int) -> int:
        """Find the end of a class definition."""
        total_lines = len(lines)
        
        # Look for the next class or function at the same or lesser indentation level
        for i in range(start_line, min(start_line + 1000, total_lines)):
            if i >= len(lines):
                break
            line = lines[i]
            
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            current_indent = len(line) - len(line.lstrip())
            
            # Found a line at same or lesser indentation that's not a continuation
            if current_indent <= base_indent and i > start_line:
                stripped = line.strip()
                # Check if it's the start of a new top-level construct
                if (stripped.startswith('class ') or 
                    stripped.startswith('def ') or
                    stripped.startswith('import ') or 
                    stripped.startswith('from ') or
                    (current_indent == 0 and not self._is_continuation_line(stripped))):
                    return i
        
        return min(start_line + 200, total_lines)
    
    def _find_function_end(self, lines: List[str], start_line: int, base_indent: int) -> int:
        """Find the end of a function/method definition."""
        total_lines = len(lines)
        in_docstring = False
        docstring_delim = None
        
        # Look for the end of the function
        for i in range(start_line, min(start_line + 200, total_lines)):
            if i >= len(lines):
                break
            line = lines[i]
            stripped = line.strip()
            
            # Handle docstrings
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    docstring_delim = stripped[:3]
                    in_docstring = True
                    if stripped.count(docstring_delim) >= 2:  # Single line docstring
                        in_docstring = False
                    continue
            else:
                if docstring_delim in stripped:
                    in_docstring = False
                continue
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            current_indent = len(line) - len(line.lstrip())
            
            # Found a line at same or lesser indentation
            if current_indent <= base_indent and i > start_line:
                # Check if it's not a continuation
                if not self._is_continuation_line(stripped):
                    return i
            
            # Special case: found a return statement - include a few more lines
            if current_indent > base_indent and stripped.startswith('return'):
                # Look ahead for a few more lines to include any cleanup code
                for j in range(i + 1, min(i + 5, total_lines)):
                    if j >= len(lines):
                        break
                    next_line = lines[j]
                    next_stripped = next_line.strip()
                    next_indent = len(next_line) - len(next_line.lstrip())
                    
                    if (next_indent <= base_indent and next_stripped and 
                        not self._is_continuation_line(next_stripped)):
                        return j
                
                return min(i + 3, total_lines)
        
        return min(start_line + 50, total_lines)
    
    def _find_generic_block_end(self, lines: List[str], start_line: int, base_indent: int) -> int:
        """Find the end of a generic code block."""
        total_lines = len(lines)
        
        for i in range(start_line, min(start_line + 50, total_lines)):
            if i >= len(lines):
                break
            line = lines[i]
            
            if not line.strip():
                continue
            
            current_indent = len(line) - len(line.lstrip())
            
            if current_indent <= base_indent and i > start_line:
                if not self._is_continuation_line(line.strip()):
                    return i
        
        return min(start_line + 30, total_lines)
    
    def _is_continuation_line(self, stripped_line: str) -> bool:
        """Check if a line is a continuation of a multi-line construct."""
        continuations = [
            ')', ']', '}', ',', '->', ':', 
            '"""', "'''", 'else:', 'elif', 'except:', 'finally:', 'catch'
        ]
        return any(stripped_line.startswith(cont) for cont in continuations)
    
    def _find_with_tree_sitter(self, content: str, span_id: str, lines: List[str]) -> List[tuple]:
        """Use tree-sitter to find code blocks accurately."""
        if not TREE_SITTER_AVAILABLE:
            return []
        
        found_matches = []
        
        try:
            parser = CodeParser()
            
            # Parse the content directly (no file path needed)
            # Create a temporary file path for language detection
            temp_path = "temp.py"  # Default to Python
            
            result = parser.parse_file(temp_path, content)
            if not result.success:
                return []
            
            # Search for matching blocks
            for block in result.all_blocks:
                if block.name == span_id:
                    found_matches.append((block.start_line, block.type, block.end_line))
            
            return found_matches
            
        except Exception as e:
            logger.debug(f"Tree-sitter parsing error: {e}")
            return []
    
    def _search_blocks_recursive(self, block, span_id: str, found_matches: List[tuple]):
        """Recursively search through code blocks."""
        if not block:
            return
        
        # Check if this block matches our span_id
        if hasattr(block, 'identifier') and block.identifier == span_id:
            span_type = self._convert_tree_sitter_type(block.type)
            
            # Get line numbers - check different possible attributes
            start_line = getattr(block, 'start_line', 0) + 1  # Convert to 1-based
            end_line = getattr(block, 'end_line', start_line) + 1
            
            # Alternative: use span if available
            if hasattr(block, 'span') and block.span:
                start_line = block.span.start_line + 1
                end_line = block.span.end_line + 1
            
            found_matches.append((start_line, span_type, end_line))
        
        # Recursively search children
        if hasattr(block, 'children'):
            for child in block.children:
                self._search_blocks_recursive(child, span_id, found_matches)
        
        # Also check if block has find_blocks method for additional search
        if hasattr(block, 'find_blocks') and callable(block.find_blocks):
            try:
                for sub_block in block.find_blocks():
                    if sub_block != block:  # Avoid infinite recursion
                        self._search_blocks_recursive(sub_block, span_id, found_matches)
            except:
                pass  # Ignore errors in recursive search
    
    def _find_class_method_with_tree_sitter(self, content: str, class_name: str, method_name: str) -> List[tuple]:
        """Use tree-sitter to find method within a specific class."""
        if not TREE_SITTER_AVAILABLE:
            return []
        
        found_matches = []
        
        try:
            parser = CodeParser()
            
            # Parse the content
            temp_path = "temp.py"  # Default to Python
            result = parser.parse_file(temp_path, content)
            if not result.success:
                return []
            
            # Find methods using our tree-sitter backend
            methods = parser.find_class_method(temp_path, class_name, method_name, content)
            
            for method in methods:
                found_matches.append((method.start_line, "method", method.end_line))
            
            return found_matches
            
        except Exception as e:
            logger.debug(f"Tree-sitter class method parsing error: {e}")
            return []
    
    def _find_class_blocks_recursive(self, block, class_name: str, class_blocks: List):
        """Recursively find class blocks with matching name."""
        if not block:
            return
        
        # Check if this is a matching class
        if (hasattr(block, 'type') and hasattr(block, 'identifier') and 
            block.identifier == class_name):
            # Check if it's a class type (handle both enum and string representations)
            block_type_str = str(block.type).lower() if hasattr(block, 'type') else ""
            if 'class' in block_type_str:
                class_blocks.append(block)
        
        # Recursively search children
        if hasattr(block, 'children'):
            for child in block.children:
                self._find_class_blocks_recursive(child, class_name, class_blocks)
    
    def _find_method_in_class_recursive(self, class_block, method_name: str, method_blocks: List):
        """Recursively find method blocks within a class."""
        if not class_block:
            return
        
        # Check if this is a matching method
        if hasattr(class_block, 'identifier') and class_block.identifier == method_name:
            # Check if it's a function/method type
            block_type_str = str(class_block.type).lower() if hasattr(class_block, 'type') else ""
            if any(t in block_type_str for t in ['function', 'method', 'constructor']):
                method_blocks.append(class_block)
        
        # Recursively search children
        if hasattr(class_block, 'children'):
            for child in class_block.children:
                self._find_method_in_class_recursive(child, method_name, method_blocks)
    
    def _convert_tree_sitter_type(self, block_type) -> str:
        """Convert tree-sitter CodeBlockType to our span type string."""
        if not TREE_SITTER_AVAILABLE or not block_type:
            return "unknown"
        
        type_mapping = {
            CodeBlockType.CLASS: "class",
            CodeBlockType.FUNCTION: "function",
            CodeBlockType.CONSTRUCTOR: "function",
            CodeBlockType.METHOD: "method",
        }
        
        return type_mapping.get(block_type, "unknown")