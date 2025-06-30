"""Testing framework integration for MCP server."""

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from moatless_mcp.utils.config import Config

logger = logging.getLogger(__name__)


class TestingFramework:
    """Testing framework integration with support for multiple test runners."""
    
    def __init__(self, config: Config, workspace_root: str = "."):
        self.config = config
        self.workspace_root = Path(workspace_root)
    
    async def detect_test_framework(self) -> Dict[str, Any]:
        """Detect available testing frameworks in the project.
        
        Returns:
            Dictionary with detected frameworks and their configurations
        """
        frameworks = {}
        
        # Check for Python testing frameworks
        if (self.workspace_root / "pytest.ini").exists() or \
           (self.workspace_root / "pyproject.toml").exists() or \
           any(self.workspace_root.glob("**/test_*.py")) or \
           any(self.workspace_root.glob("**/*_test.py")):
            frameworks["pytest"] = {
                "detected": True,
                "config_files": [],
                "test_files": []
            }
            
            # Find pytest config files
            for config_file in ["pytest.ini", "pyproject.toml", "setup.cfg"]:
                if (self.workspace_root / config_file).exists():
                    frameworks["pytest"]["config_files"].append(config_file)
            
            # Find test files
            test_files = list(self.workspace_root.glob("**/test_*.py")) + \
                        list(self.workspace_root.glob("**/*_test.py"))
            frameworks["pytest"]["test_files"] = [str(f.relative_to(self.workspace_root)) for f in test_files[:10]]
        
        # Check for Node.js testing frameworks
        package_json = self.workspace_root / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                
                scripts = package_data.get("scripts", {})
                dev_deps = package_data.get("devDependencies", {})
                deps = package_data.get("dependencies", {})
                all_deps = {**dev_deps, **deps}
                
                # Jest
                if "jest" in all_deps or "test" in scripts:
                    frameworks["jest"] = {
                        "detected": True,
                        "config_files": [],
                        "test_script": scripts.get("test", "npm test")
                    }
                    
                    for config_file in ["jest.config.js", "jest.config.json", "__tests__"]:
                        if (self.workspace_root / config_file).exists():
                            frameworks["jest"]["config_files"].append(config_file)
                
                # Mocha
                if "mocha" in all_deps:
                    frameworks["mocha"] = {
                        "detected": True,
                        "config_files": [],
                        "test_script": scripts.get("test", "npm test")
                    }
                
            except Exception as e:
                logger.debug(f"Error reading package.json: {e}")
        
        # Check for Java testing frameworks
        if (self.workspace_root / "pom.xml").exists():
            frameworks["maven"] = {
                "detected": True,
                "config_files": ["pom.xml"],
                "test_command": "mvn test"
            }
        
        if (self.workspace_root / "build.gradle").exists() or (self.workspace_root / "build.gradle.kts").exists():
            frameworks["gradle"] = {
                "detected": True,
                "config_files": ["build.gradle", "build.gradle.kts"],
                "test_command": "./gradlew test"
            }
        
        # Check for Django
        if (self.workspace_root / "manage.py").exists():
            frameworks["django"] = {
                "detected": True,
                "config_files": ["manage.py"],
                "test_command": "python manage.py test"
            }
        
        return {
            "detected_frameworks": list(frameworks.keys()),
            "frameworks": frameworks,
            "workspace_root": str(self.workspace_root)
        }
    
    async def run_tests(self, framework: Optional[str] = None, test_path: Optional[str] = None, 
                       args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run tests using the specified framework.
        
        Args:
            framework: Testing framework to use (pytest, jest, maven, etc.)
            test_path: Specific test file or directory to run
            args: Additional arguments to pass to the test runner
        
        Returns:
            Dictionary with test results and output
        """
        try:
            # Auto-detect framework if not specified
            if not framework:
                detected = await self.detect_test_framework()
                available_frameworks = detected["detected_frameworks"]
                if not available_frameworks:
                    return {"error": "No testing framework detected"}
                framework = available_frameworks[0]  # Use first detected framework
            
            # Build test command
            command = await self._build_test_command(framework, test_path, args)
            if not command:
                return {"error": f"Unsupported or unconfigured framework: {framework}"}
            
            # Execute tests
            logger.info(f"Running tests with command: {' '.join(command)}")
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=str(self.workspace_root),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=None  # Use current environment
                )
                
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)  # 5 minute timeout
                return_code = process.returncode
                
            except asyncio.TimeoutError:
                return {"error": "Test execution timed out after 5 minutes"}
            except Exception as e:
                return {"error": f"Failed to execute tests: {str(e)}"}
            
            # Parse test results
            result = await self._parse_test_output(framework, stdout.decode('utf-8'), stderr.decode('utf-8'), return_code)
            result.update({
                "framework": framework,
                "command": ' '.join(command),
                "return_code": return_code
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in run_tests: {e}")
            return {"error": f"Test execution failed: {str(e)}"}
    
    async def _build_test_command(self, framework: str, test_path: Optional[str], 
                                 args: Optional[List[str]]) -> Optional[List[str]]:
        """Build the test command for the specified framework."""
        args = args or []
        
        if framework == "pytest":
            command = ["python", "-m", "pytest"]
            if test_path:
                # Add test path
                command.append(test_path)
            command.extend(args)
            # Add common pytest flags for better output
            if "-v" not in args and "--verbose" not in args:
                command.append("-v")
            return command
        
        elif framework == "jest":
            command = ["npm", "test"]
            if test_path:
                command.extend(["--", test_path])
            command.extend(args)
            return command
        
        elif framework == "mocha":
            command = ["npm", "test"]
            command.extend(args)
            return command
        
        elif framework == "maven":
            command = ["mvn", "test"]
            if test_path:
                command.extend(["-Dtest=" + test_path])
            command.extend(args)
            return command
        
        elif framework == "gradle":
            command = ["./gradlew", "test"]
            if test_path:
                command.extend(["--tests", test_path])
            command.extend(args)
            return command
        
        elif framework == "django":
            command = ["python", "manage.py", "test"]
            if test_path:
                command.append(test_path)
            command.extend(args)
            return command
        
        return None
    
    async def _parse_test_output(self, framework: str, stdout: str, stderr: str, return_code: int) -> Dict[str, Any]:
        """Parse test output based on the framework."""
        result = {
            "success": return_code == 0,
            "stdout": stdout,
            "stderr": stderr,
            "summary": {},
            "failed_tests": [],
            "passed_tests": []
        }
        
        if framework == "pytest":
            # Parse pytest output
            result["summary"] = self._parse_pytest_output(stdout)
            
        elif framework in ["jest", "mocha"]:
            # Parse JavaScript test output
            result["summary"] = self._parse_js_test_output(stdout)
            
        elif framework in ["maven", "gradle"]:
            # Parse Java test output
            result["summary"] = self._parse_java_test_output(stdout)
            
        elif framework == "django":
            # Parse Django test output
            result["summary"] = self._parse_django_output(stdout)
        
        return result
    
    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """Parse pytest output for test results."""
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        }
        
        # Look for pytest summary line
        summary_pattern = re.search(r'=+ (\d+) failed.*?(\d+) passed.*?in ([\d.]+)s =+', output)
        if summary_pattern:
            summary["failed"] = int(summary_pattern.group(1))
            summary["passed"] = int(summary_pattern.group(2))
            summary["total"] = summary["failed"] + summary["passed"]
            summary["duration"] = summary_pattern.group(3)
        else:
            # Try alternative patterns
            passed_pattern = re.search(r'=+ (\d+) passed.*?in ([\d.]+)s =+', output)
            if passed_pattern:
                summary["passed"] = int(passed_pattern.group(1))
                summary["total"] = summary["passed"]
                summary["duration"] = passed_pattern.group(2)
        
        return summary
    
    def _parse_js_test_output(self, output: str) -> Dict[str, Any]:
        """Parse JavaScript test framework output."""
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # Jest/Mocha patterns
        test_pattern = re.search(r'Tests:\s+(\d+) failed,\s+(\d+) passed,\s+(\d+) total', output)
        if test_pattern:
            summary["failed"] = int(test_pattern.group(1))
            summary["passed"] = int(test_pattern.group(2))
            summary["total"] = int(test_pattern.group(3))
        
        return summary
    
    def _parse_java_test_output(self, output: str) -> Dict[str, Any]:
        """Parse Java test framework output."""
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # Maven/Gradle patterns
        test_pattern = re.search(r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)', output)
        if test_pattern:
            summary["total"] = int(test_pattern.group(1))
            summary["failed"] = int(test_pattern.group(2)) + int(test_pattern.group(3))
            summary["skipped"] = int(test_pattern.group(4))
            summary["passed"] = summary["total"] - summary["failed"] - summary["skipped"]
        
        return summary
    
    def _parse_django_output(self, output: str) -> Dict[str, Any]:
        """Parse Django test output."""
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0
        }
        
        # Django test patterns
        if "OK" in output:
            test_pattern = re.search(r'Ran (\d+) test', output)
            if test_pattern:
                summary["total"] = int(test_pattern.group(1))
                summary["passed"] = summary["total"]
        else:
            failed_pattern = re.search(r'FAILED \(failures=(\d+)(?:, errors=(\d+))?\)', output)
            if failed_pattern:
                summary["failed"] = int(failed_pattern.group(1))
                summary["errors"] = int(failed_pattern.group(2) or 0)
        
        return summary