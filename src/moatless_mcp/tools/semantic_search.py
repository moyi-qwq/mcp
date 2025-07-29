"""Enhanced semantic search functionality using vector embeddings and code understanding."""

import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from moatless_mcp.utils.config import Config

# Add moatless path to sys.path
current_file = Path(__file__).resolve()
# From: .../Industrial_Software_MCP/src/moatless_mcp/tools/semantic_search.py
# To: .../moatless-tools (parent of Industrial_Software_MCP)
src_dir = current_file.parent.parent.parent  # .../Industrial_Software_MCP/src
mcp_server_dir = src_dir.parent  # .../Industrial_Software_MCP
moatless_tools_dir = mcp_server_dir.parent  # .../moatless-tools

if str(moatless_tools_dir) not in sys.path:
    sys.path.insert(0, str(moatless_tools_dir))

# Import moatless components
try:
    from moatless.index import CodeIndex
    from moatless.index.types import SearchCodeResponse, SearchCodeHit
    MOATLESS_AVAILABLE = True
except ImportError:
    MOATLESS_AVAILABLE = False
    CodeIndex = None
    SearchCodeResponse = None
    SearchCodeHit = None

logger = logging.getLogger(__name__)


class EnhancedSemanticSearch:
    """Enhanced semantic search using vector embeddings and code understanding."""
    
    def __init__(self, config: Config, workspace_root: str = ".", code_index: Optional[CodeIndex] = None):
        self.config = config
        self.workspace_root = Path(workspace_root)
        self.code_index = code_index
        
        # Fallback to keyword search if moatless is not available
        self._fallback_search = not MOATLESS_AVAILABLE or code_index is None
        
        if self._fallback_search:
            logger.warning("Using fallback keyword-based search. For better results, ensure moatless is available and code index is initialized.")
    
    async def semantic_search(self, query: str, file_pattern: Optional[str] = None, 
                            max_results: int = 10, category: Optional[str] = None) -> Dict[str, Any]:
        """Search for code using natural language queries with vector embeddings.
        
        Args:
            query: Natural language description of what to find
            file_pattern: Optional pattern to limit search to specific files
            max_results: Maximum number of results to return
            category: Category filter ('implementation', 'test', or None)
        
        Returns:
            Dictionary with search results ranked by semantic relevance
        """
        try:
            if not query or not query.strip():
                return {"error": "Query cannot be empty"}
            
            # Use vector-based search if available
            if not self._fallback_search and self.code_index:
                results = await self._vector_semantic_search(query, file_pattern, max_results, category)
                search_method = "vector_based"
            else:
                # Fallback to enhanced keyword search
                results = await self._enhanced_keyword_search(query, file_pattern, max_results, category)
                search_method = "enhanced_keyword_based"
            
            return {
                "query": query,
                "results": results,
                "total_results": len(results),
                "search_method": search_method,
                "file_pattern": file_pattern,
                "category": category,
                "moatless_available": MOATLESS_AVAILABLE,
                "code_index_available": self.code_index is not None
            }
            
        except Exception as e:
            logger.error(f"Error in semantic_search: {e}")
            return {"error": f"Semantic search failed: {str(e)}"}
    
    async def _vector_semantic_search(self, query: str, file_pattern: Optional[str], 
                                    max_results: int, category: Optional[str]) -> List[Dict[str, Any]]:
        """Vector-based semantic search using moatless CodeIndex."""
        if not self.code_index:
            raise ValueError("Code index not available")
        
        # Perform semantic search using moatless
        search_response: SearchCodeResponse = await self.code_index.semantic_search(
            query=query,
            file_pattern=file_pattern,
            category=category,
            max_results=max_results,
            max_tokens=8000,
            exact_match_if_possible=True
        )
        
        results = []
        for hit in search_response.hits:
            # Get file content to extract context
            file_content = await self._get_file_content(hit.file_path)
            if not file_content:
                continue
            
            # Extract relevant code spans
            code_sections = []
            for span in hit.spans:
                span_info = await self._extract_span_info(hit.file_path, span.span_id, file_content)
                if span_info:
                    code_sections.append(span_info)
            
            # Calculate semantic relevance score (normalized)
            relevance_score = self._calculate_relevance_score(hit, query)
            
            results.append({
                "file_path": hit.file_path,
                "relevance_score": relevance_score,
                "code_sections": code_sections,
                "match_type": "semantic",
                "summary": self._generate_hit_summary(hit, query),
                "total_spans": len(hit.spans)
            })
        
        # Sort by relevance score
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results
    
    async def _enhanced_keyword_search(self, query: str, file_pattern: Optional[str], 
                                     max_results: int, category: Optional[str]) -> List[Dict[str, Any]]:
        """Enhanced keyword-based semantic search with better analysis."""
        # Enhanced query analysis
        keywords, intent, semantic_patterns = self._enhanced_query_analysis(query)
        
        results = []
        search_paths = await self._get_search_paths(file_pattern, category)
        
        # Search files for relevant content
        for file_path in search_paths:
            try:
                content = await self._get_file_content(str(file_path.relative_to(self.workspace_root)))
                if not content:
                    continue
                
                # Enhanced scoring with semantic patterns
                file_score, matches = self._enhanced_score_file_content(
                    content, keywords, intent, semantic_patterns, str(file_path)
                )
                
                if file_score > 0:
                    results.append({
                        "file_path": str(file_path.relative_to(self.workspace_root)),
                        "relevance_score": file_score,
                        "matches": matches,
                        "match_type": "keyword_enhanced",
                        "preview": self._generate_enhanced_preview(content, matches),
                        "intent": intent,
                        "matched_patterns": [m["keyword"] for m in matches]
                    })
                    
            except Exception as e:
                logger.debug(f"Error reading file {file_path}: {e}")
                continue
        
        # Sort by score and return top results
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:max_results]
    
    def _enhanced_query_analysis(self, query: str) -> Tuple[List[str], str, List[str]]:
        """Enhanced query analysis with semantic pattern detection."""
        query_lower = query.lower()
        
        # Enhanced intent detection
        intent_patterns = {
            "find_function": ["function", "method", "def", "implement", "call"],
            "find_class": ["class", "object", "type", "model", "entity"],
            "find_variable": ["variable", "constant", "config", "setting"],
            "find_import": ["import", "module", "library", "dependency"],
            "find_test": ["test", "spec", "unittest", "pytest"],
            "find_error": ["error", "exception", "bug", "fix", "debug"],
            "find_documentation": ["doc", "comment", "readme", "documentation"],
            "find_pattern": ["pattern", "example", "usage", "how to"],
        }
        
        intent = "general"
        for intent_type, patterns in intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                intent = intent_type
                break
        
        # Extract semantic patterns (programming concepts)
        semantic_patterns = []
        programming_concepts = [
            "authentication", "authorization", "validation", "serialization",
            "database", "orm", "query", "migration", "model",
            "api", "endpoint", "route", "handler", "controller",
            "middleware", "decorator", "factory", "singleton",
            "async", "await", "promise", "callback", "event",
            "exception", "error", "logging", "debug",
            "test", "mock", "fixture", "assertion",
            "configuration", "settings", "environment",
            "cache", "redis", "session", "cookie"
        ]
        
        for concept in programming_concepts:
            if concept in query_lower:
                semantic_patterns.append(concept)
        
        # Enhanced keyword extraction
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", 
            "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had",
            "do", "does", "did", "will", "would", "could", "should", "can", "may", "might",
            "how", "what", "where", "when", "why", "which", "who"
        }
        
        # Extract meaningful keywords
        words = re.findall(r'\b\w+\b', query_lower)
        keywords = []
        
        for word in words:
            if len(word) > 2 and word not in stop_words:
                keywords.append(word)
        
        # Add camelCase and snake_case variations
        for keyword in keywords.copy():
            if '_' in keyword:
                # Add camelCase version
                camel_case = ''.join(word.capitalize() for word in keyword.split('_'))
                keywords.append(camel_case)
            elif any(c.isupper() for c in keyword[1:]):
                # Add snake_case version
                snake_case = re.sub(r'([A-Z])', r'_\1', keyword).lower().strip('_')
                keywords.append(snake_case)
        
        return list(set(keywords)), intent, semantic_patterns
    
    def _enhanced_score_file_content(self, content: str, keywords: List[str], intent: str, 
                                   semantic_patterns: List[str], file_path: str) -> Tuple[float, List[Dict[str, Any]]]:
        """Enhanced scoring with semantic understanding."""
        content_lower = content.lower()
        lines = content.split('\n')
        
        score = 0.0
        matches = []
        
        # File type and name bonuses
        file_ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).name.lower()
        
        # Intent-based file type bonus
        if intent == "find_test" and ("test" in file_path.lower() or file_ext in [".test.js", ".spec.js"] or file_name.startswith("test_")):
            score += 3.0
        elif intent == "find_class" and file_ext in [".py", ".java", ".cpp", ".ts"]:
            score += 1.5
        elif intent == "find_function" and file_ext in [".py", ".js", ".ts", ".java"]:
            score += 1.5
        
        # Semantic pattern matching
        for pattern in semantic_patterns:
            if pattern in content_lower:
                score += 2.0
                matches.append({
                    "keyword": pattern,
                    "match_type": "semantic_pattern",
                    "context": "file_content",
                    "score": 2.0
                })
        
        # Enhanced keyword matching with context
        for keyword in keywords:
            keyword_pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
            keyword_matches = list(keyword_pattern.finditer(content))
            
            for match in keyword_matches:
                line_num = content[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                
                # Enhanced context-based scoring
                keyword_score = self._calculate_context_score(line_content, keyword, intent)
                
                score += keyword_score
                matches.append({
                    "keyword": keyword,
                    "line_number": line_num,
                    "line_content": line_content.strip(),
                    "match_type": self._classify_enhanced_match_type(line_content, keyword),
                    "score": keyword_score,
                    "context_relevance": self._assess_context_relevance(line_content, intent)
                })
        
        # Proximity and clustering bonus
        proximity_bonus = self._calculate_enhanced_proximity_bonus(content, keywords, semantic_patterns)
        score += proximity_bonus
        
        return score, matches
    
    def _calculate_context_score(self, line: str, keyword: str, intent: str) -> float:
        """Calculate context-aware score for keyword matches."""
        base_score = 1.0
        line_lower = line.strip().lower()
        
        # Function/method definition context
        if self._is_function_definition(line):
            if intent in ["find_function", "find_pattern"]:
                base_score += 2.5
            else:
                base_score += 1.5
        
        # Class definition context
        elif self._is_class_definition(line):
            if intent in ["find_class", "find_pattern"]:
                base_score += 2.5
            else:
                base_score += 1.2
        
        # Import statement context
        elif self._is_import_statement(line):
            if intent == "find_import":
                base_score += 2.0
            else:
                base_score += 0.8
        
        # Comment/documentation context
        elif self._is_comment_or_docstring(line):
            if intent == "find_documentation":
                base_score += 1.5
            else:
                base_score += 0.8
        
        # Variable assignment context
        elif self._is_variable_assignment(line):
            if intent == "find_variable":
                base_score += 1.5
            else:
                base_score += 0.5
        
        # Test-related context
        elif any(test_word in line_lower for test_word in ["test", "assert", "expect", "mock"]):
            if intent == "find_test":
                base_score += 2.0
            else:
                base_score += 0.8
        
        return base_score
    
    def _is_function_definition(self, line: str) -> bool:
        """Enhanced function definition detection."""
        line_stripped = line.strip()
        patterns = [
            r'^\s*def\s+\w+\s*\(',  # Python
            r'^\s*function\s+\w+\s*\(',  # JavaScript
            r'^\s*async\s+def\s+\w+\s*\(',  # Python async
            r'^\s*const\s+\w+\s*=\s*\(',  # JavaScript arrow function
            r'^\s*(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\(',  # Java/C++
        ]
        return any(re.match(pattern, line_stripped) for pattern in patterns)
    
    def _is_class_definition(self, line: str) -> bool:
        """Enhanced class definition detection."""
        line_stripped = line.strip()
        patterns = [
            r'^\s*class\s+\w+',  # Python/Java
            r'^\s*export\s+class\s+\w+',  # TypeScript/JavaScript
            r'^\s*(public|private)?\s*class\s+\w+',  # Java/C++
        ]
        return any(re.match(pattern, line_stripped) for pattern in patterns)
    
    def _is_import_statement(self, line: str) -> bool:
        """Enhanced import statement detection."""
        line_stripped = line.strip()
        patterns = [
            r'^\s*import\s+',  # Python/JavaScript
            r'^\s*from\s+\w+\s+import\s+',  # Python
            r'^\s*#include\s*<',  # C/C++
            r'^\s*using\s+',  # C#
        ]
        return any(re.match(pattern, line_stripped) for pattern in patterns)
    
    def _is_comment_or_docstring(self, line: str) -> bool:
        """Enhanced comment detection."""
        line_stripped = line.strip()
        return (line_stripped.startswith("#") or
                line_stripped.startswith("//") or
                line_stripped.startswith("/*") or
                line_stripped.startswith('"""') or
                line_stripped.startswith("'''") or
                line_stripped.startswith("*"))
    
    def _is_variable_assignment(self, line: str) -> bool:
        """Enhanced variable assignment detection."""
        line_stripped = line.strip()
        if "=" not in line_stripped:
            return False
        
        # Exclude control structures
        if any(line_stripped.startswith(keyword) for keyword in ["if", "while", "for", "elif", "else"]):
            return False
        
        # Look for assignment patterns
        assignment_patterns = [
            r'^\s*\w+\s*=\s*',  # Simple assignment
            r'^\s*self\.\w+\s*=\s*',  # Instance variable
            r'^\s*const\s+\w+\s*=\s*',  # JavaScript const
            r'^\s*let\s+\w+\s*=\s*',  # JavaScript let
            r'^\s*var\s+\w+\s*=\s*',  # JavaScript var
        ]
        return any(re.match(pattern, line_stripped) for pattern in patterns)
    
    def _classify_enhanced_match_type(self, line: str, keyword: str) -> str:
        """Enhanced match type classification."""
        if self._is_function_definition(line):
            return "function_definition"
        elif self._is_class_definition(line):
            return "class_definition"
        elif self._is_import_statement(line):
            return "import_statement"
        elif self._is_comment_or_docstring(line):
            return "documentation"
        elif self._is_variable_assignment(line):
            return "variable_assignment"
        elif any(test_word in line.lower() for test_word in ["test", "assert", "expect"]):
            return "test_code"
        else:
            return "general_code"
    
    def _assess_context_relevance(self, line: str, intent: str) -> float:
        """Assess how relevant the context is to the search intent."""
        relevance_map = {
            "find_function": ["function_definition", "general_code"],
            "find_class": ["class_definition", "general_code"],
            "find_test": ["test_code", "function_definition"],
            "find_import": ["import_statement"],
            "find_documentation": ["documentation"],
            "find_variable": ["variable_assignment", "general_code"],
        }
        
        match_type = self._classify_enhanced_match_type(line, "")
        relevant_types = relevance_map.get(intent, ["general_code"])
        
        if match_type in relevant_types:
            return 1.0
        else:
            return 0.5
    
    def _calculate_enhanced_proximity_bonus(self, content: str, keywords: List[str], 
                                          semantic_patterns: List[str]) -> float:
        """Enhanced proximity calculation with semantic awareness."""
        bonus = 0.0
        lines = content.split('\n')
        all_terms = keywords + semantic_patterns
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            terms_in_line = [term for term in all_terms if term in line_lower]
            
            if len(terms_in_line) > 1:
                # Bonus for multiple terms in same line
                bonus += len(terms_in_line) * 0.8
            
            # Check proximity across lines (within 5 lines)
            if len(terms_in_line) >= 1:
                for j in range(max(0, i-5), min(len(lines), i+6)):
                    if j != i:
                        other_terms = [term for term in all_terms if term in lines[j].lower()]
                        if other_terms:
                            # Distance-based bonus
                            distance_factor = 1.0 / (abs(i - j) + 1)
                            bonus += 0.3 * len(other_terms) * distance_factor
        
        return min(bonus, 10.0)  # Cap the proximity bonus
    
    async def _get_search_paths(self, file_pattern: Optional[str], category: Optional[str]) -> List[Path]:
        """Get paths to search based on pattern and category."""
        search_paths = []
        
        if file_pattern:
            try:
                search_paths = list(self.workspace_root.glob(file_pattern))
            except Exception as e:
                logger.warning(f"Invalid file pattern {file_pattern}: {e}")
                search_paths = []
        
        if not search_paths:
            # Search all allowed files
            for root, dirs, files in os.walk(self.workspace_root):
                for file in files:
                    file_path = Path(root) / file
                    if self.config.is_file_allowed(file_path):
                        # Apply category filter
                        if category:
                            is_test_file = any(test_indicator in str(file_path).lower() 
                                             for test_indicator in ["test", "spec", "__test__"])
                            if category == "test" and not is_test_file:
                                continue
                            elif category == "implementation" and is_test_file:
                                continue
                        
                        search_paths.append(file_path)
        
        return search_paths
    
    async def _get_file_content(self, file_path: str) -> Optional[str]:
        """Get file content safely."""
        try:
            full_path = self.workspace_root / file_path
            if not full_path.exists() or not self.config.is_file_allowed(full_path):
                return None
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.debug(f"Error reading file {file_path}: {e}")
            return None
    
    async def _extract_span_info(self, file_path: str, span_id: str, content: str) -> Optional[Dict[str, Any]]:
        """Extract information about a code span."""
        try:
            # This is a simplified version - in a real implementation,
            # you would use the actual span information from moatless
            lines = content.split('\n')
            
            # Extract a reasonable context around the span
            # This is a placeholder - actual implementation would use span boundaries
            return {
                "span_id": span_id,
                "content_preview": '\n'.join(lines[:5]),  # First 5 lines as preview
                "span_type": "code_block"
            }
        except Exception as e:
            logger.debug(f"Error extracting span info: {e}")
            return None
    
    def _calculate_relevance_score(self, hit: Any, query: str) -> float:
        """Calculate relevance score from moatless search hit."""
        # This would be calculated based on the actual hit scores from moatless
        # For now, return a normalized score
        base_score = min(len(hit.spans) * 0.3, 1.0)
        return base_score
    
    def _generate_hit_summary(self, hit: Any, query: str) -> str:
        """Generate a summary for a search hit."""
        return f"Found {len(hit.spans)} relevant code sections in {hit.file_path}"
    
    def _generate_enhanced_preview(self, content: str, matches: List[Dict[str, Any]]) -> str:
        """Generate an enhanced preview of the relevant content."""
        if not matches:
            lines = content.split('\n')
            return '\n'.join(lines[:3]) + ("..." if len(lines) > 3 else "")
        
        # Get the best matches for preview
        best_matches = sorted(matches, key=lambda x: x["score"], reverse=True)[:3]
        lines = content.split('\n')
        
        preview_lines = []
        for match in best_matches:
            line_num = match["line_number"]
            start_line = max(0, line_num - 2)
            end_line = min(len(lines), line_num + 2)
            
            context = lines[start_line:end_line]
            if context:
                preview_lines.append(f"Match in {match['match_type']} (line {line_num}):")
                preview_lines.extend([f"  {line}" for line in context])
                preview_lines.append("---")
        
        preview = '\n'.join(preview_lines[:15])  # Limit preview size
        return preview


# Alias for backward compatibility
SemanticSearch = EnhancedSemanticSearch