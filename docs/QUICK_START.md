# Quick Start Guide

This guide will help you get started with the Moatless MCP Server in just a few minutes.

## Prerequisites

- Python 3.10 or higher
- An MCP-compatible client (e.g., Claude Desktop, Cline)

## Installation

### 1. Install the Server

```bash
# Option 1: Install from source
git clone <repository-url>
cd moatless-mcp-server
pip install -e .

# Option 2: Install from PyPI (when available)
pip install moatless-mcp-server
```

### 2. Verify Installation

```bash
moatless-mcp-server --help
```

## Configuration

### For Claude Desktop

Add this to your `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:

```json
{
  "mcpServers": {
    "moatless": {
      "command": "moatless-mcp-server",
      "args": ["--workspace", "/path/to/your/project"]
    }
  }
}
```

### For Cline (VS Code Extension)

In your VS Code settings:

```json
{
  "cline.mcpServers": {
    "moatless": {
      "command": "moatless-mcp-server",
      "args": ["--workspace", "${workspaceFolder}"]
    }
  }
}
```

## First Steps

### 1. Start with Workspace Info

```
Use the workspace_info tool to understand your project structure.
```

### 2. Explore Files

```
Use list_files with recursive=true to see all files in your project.
```

### 3. Read Code

```
Use read_file to examine specific files. Try reading your main application file.
```

### 4. Search for Patterns

```
Use grep to search for specific functions, classes, or patterns in your code.
```

## Common Workflows

### Code Review Workflow

1. **Get project overview**: `workspace_info`
2. **List recent files**: `find_files` with patterns like `*.py` or `*test*`
3. **Read key files**: `read_file` on main application files
4. **Search for issues**: `grep` for patterns like `TODO`, `FIXME`, or `XXX`

### Bug Investigation Workflow

1. **Search for error messages**: `grep` with the error text
2. **Find related files**: `find_files` with relevant file patterns
3. **Read problematic code**: `read_file` on identified files
4. **Trace function calls**: `grep` for function names

### Refactoring Workflow

1. **Find all occurrences**: `grep` for the code you want to change
2. **Read context**: `read_file` around each occurrence
3. **Make changes**: `string_replace` for each file
4. **Verify changes**: `read_file` to confirm modifications

## Examples

### Example 1: Finding and Reading a Configuration File

```bash
# 1. Find config files
find_files: {"pattern": "*config*"}

# 2. Read the config file
read_file: {"file_path": "config/settings.py"}
```

### Example 2: Searching for a Function

```bash
# 1. Search for function definitions
grep: {"pattern": "def process_data", "file_pattern": "*.py"}

# 2. Read the file containing the function
read_file: {"file_path": "src/data_processor.py", "start_line": 45, "end_line": 65}
```

### Example 3: Making a Simple Change

```bash
# 1. Find where to make the change
grep: {"pattern": "old_variable_name", "file_pattern": "*.py"}

# 2. Read the context
read_file: {"file_path": "src/main.py", "start_line": 20, "end_line": 30}

# 3. Make the change
string_replace: {
  "file_path": "src/main.py",
  "old_str": "old_variable_name",
  "new_str": "new_variable_name"
}

# 4. Verify the change
read_file: {"file_path": "src/main.py", "start_line": 20, "end_line": 30}
```

## Tips and Best Practices

### File Operations
- Always use relative paths from the workspace root
- Use line ranges with `read_file` for large files
- Check file existence with `list_files` before reading

### Search Operations
- Start with broad patterns and narrow down
- Use file patterns to limit search scope
- Combine `grep` and `find_files` for complex searches

### Making Changes
- Always read files before modifying them
- Use `string_replace` with specific occurrence numbers for precision
- Verify changes by reading the modified sections

### Performance
- Use `max_results` parameters to limit large result sets
- Use specific file patterns instead of searching everything
- Read only the lines you need with line range parameters

## Troubleshooting

### Tool Not Found

If you get "tool not found" errors:

1. Check that the MCP server is properly configured
2. Restart your MCP client
3. Verify the server is installed: `moatless-mcp-server --help`

### Permission Errors

If you get permission errors:

1. Check that the workspace path exists and is accessible
2. Ensure the user running the server has appropriate permissions
3. Try with a different workspace directory

### Large File Issues

If you encounter issues with large files:

1. Use line range parameters: `read_file` with `start_line` and `end_line`
2. Use more specific search patterns to reduce result size
3. Increase timeout settings if needed

## Next Steps

- Read the full [README](../README.md) for detailed documentation
- Check out the [examples](./examples/) directory for more complex use cases
- Explore the [API reference](./API.md) for complete tool documentation

## Getting Help

- Check the [troubleshooting section](../README.md#troubleshooting) in the README
- Open an issue on GitHub for bugs or feature requests
- Review the logs with `--debug` flag for detailed diagnostics