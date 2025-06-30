# API Reference

Complete reference for all tools available in the Moatless MCP Server.

## File Operations

### read_file

Read file contents with optional line range support.

**Parameters:**
- `file_path` (string, required): Path to the file relative to workspace root
- `start_line` (integer, optional): Start line number (1-based)
- `end_line` (integer, optional): End line number (1-based)

**Returns:**
- `message`: File contents or specified range
- `properties`:
  - `file_path`: The file path that was read
  - `total_lines`: Total number of lines in the file
  - `displayed_lines`: Number of lines displayed (if range specified)
  - `start_line`: Actual start line displayed
  - `end_line`: Actual end line displayed
  - `size_bytes`: File size in bytes (full file only)

**Examples:**

```json
// Read entire file
{
  "file_path": "src/main.py"
}

// Read specific line range
{
  "file_path": "src/main.py",
  "start_line": 10,
  "end_line": 20
}

// Read from line 50 to end
{
  "file_path": "src/main.py",
  "start_line": 50
}
```

**Error Cases:**
- File not found
- File too large (>10MB by default)
- File type not allowed
- Invalid line range

---

### write_file

Write content to a file, creating parent directories if needed.

**Parameters:**
- `file_path` (string, required): Path to the file relative to workspace root
- `content` (string, required): Content to write to the file

**Returns:**
- `message`: Success message with statistics
- `properties`:
  - `file_path`: The file path that was written
  - `lines_written`: Number of lines written
  - `size_bytes`: Size of written content in bytes

**Example:**

```json
{
  "file_path": "src/new_module.py",
  "content": "def hello_world():\n    print('Hello, World!')\n"
}
```

**Error Cases:**
- Permission denied
- Invalid file path
- File type not allowed

---

### list_files

List files and directories in the workspace.

**Parameters:**
- `directory` (string, optional): Directory path relative to workspace root (default: "")
- `recursive` (boolean, optional): Whether to list files recursively (default: false)
- `max_results` (integer, optional): Maximum number of files to return (default: 100, max: 1000)

**Returns:**
- `message`: Formatted list of files
- `properties`:
  - `directory`: Directory that was listed
  - `file_count`: Number of files found
  - `recursive`: Whether recursive listing was used
  - `truncated`: Whether results were truncated due to max_results

**Examples:**

```json
// List files in root directory
{
  "directory": "",
  "recursive": false
}

// List all Python files recursively
{
  "directory": "src",
  "recursive": true,
  "max_results": 50
}
```

---

### string_replace

Replace occurrences of a string in a file with validation.

**Parameters:**
- `file_path` (string, required): Path to the file to modify
- `old_str` (string, required): String to find and replace
- `new_str` (string, required): String to replace with
- `occurrence` (integer, optional): Which occurrence to replace (1-based, 0 for all, default: 1)

**Returns:**
- `message`: Success message with replacement count
- `properties`:
  - `file_path`: The file that was modified
  - `replacements_made`: Number of replacements made
  - `total_occurrences`: Total occurrences of old_str found
  - `old_str`: The string that was replaced
  - `new_str`: The replacement string

**Examples:**

```json
// Replace first occurrence
{
  "file_path": "src/main.py",
  "old_str": "old_function_name",
  "new_str": "new_function_name"
}

// Replace all occurrences
{
  "file_path": "src/main.py",
  "old_str": "debug_mode = True",
  "new_str": "debug_mode = False",
  "occurrence": 0
}

// Replace specific occurrence
{
  "file_path": "src/config.py",
  "old_str": "localhost",
  "new_str": "production.example.com",
  "occurrence": 2
}
```

**Error Cases:**
- String not found in file
- Occurrence number out of range
- File not found or not writable

## Search Tools

### grep

Search for text patterns in files using regular expressions.

**Parameters:**
- `pattern` (string, required): Regular expression pattern to search for
- `file_pattern` (string, optional): File glob pattern to limit search (default: "*")
- `max_results` (integer, optional): Maximum number of results (default: 100, max: 1000)

**Returns:**
- `message`: Formatted search results with file:line:content
- `properties`:
  - `pattern`: The regex pattern used
  - `file_pattern`: The file pattern filter used
  - `match_count`: Number of matches found
  - `truncated`: Whether results were truncated

**Examples:**

```json
// Find function definitions
{
  "pattern": "def\\s+\\w+",
  "file_pattern": "*.py"
}

// Find TODO comments
{
  "pattern": "TODO|FIXME|XXX",
  "file_pattern": "*.py",
  "max_results": 50
}

// Find class definitions in specific directory
{
  "pattern": "class\\s+\\w+",
  "file_pattern": "src/**/*.py"
}

// Find imports
{
  "pattern": "^import\\s+|^from\\s+.+\\s+import",
  "file_pattern": "*.py"
}
```

**Regex Tips:**
- Use `\\s+` for whitespace
- Use `\\w+` for word characters
- Use `^` for line start, `$` for line end
- Use `|` for OR conditions
- Escape special characters with `\\`

---

### find_files

Find files by name pattern using glob syntax.

**Parameters:**
- `pattern` (string, required): Glob pattern to match file names
- `max_results` (integer, optional): Maximum number of results (default: 100, max: 1000)

**Returns:**
- `message`: List of matching file paths
- `properties`:
  - `pattern`: The glob pattern used
  - `file_count`: Number of files found
  - `truncated`: Whether results were truncated

**Examples:**

```json
// Find Python files
{
  "pattern": "*.py"
}

// Find test files
{
  "pattern": "*test*.py"
}

// Find configuration files
{
  "pattern": "*config*"
}

// Find files in specific directory
{
  "pattern": "src/**/*.java"
}

// Find files with specific extension in subdirectories
{
  "pattern": "**/*.json"
}
```

**Glob Patterns:**
- `*`: Matches any characters within a filename
- `**`: Matches any characters across directory boundaries
- `?`: Matches any single character
- `[abc]`: Matches any character in brackets
- `{py,java,js}`: Matches any of the alternatives

---

### workspace_info

Get information about the current workspace.

**Parameters:** None

**Returns:**
- `message`: Formatted workspace information
- `properties`:
  - `path`: Absolute path to workspace
  - `exists`: Whether the workspace path exists
  - `is_git_repo`: Whether the workspace is a git repository
  - `git_branch`: Current git branch (if applicable)
  - `git_remote`: List of git remotes (if applicable)

**Example:**

```json
{}
```

**Example Response:**
```
Workspace Path: /home/user/my-project
Exists: true
Git Repository: true
Git Branch: main
Git Remotes: origin
```

## Error Handling

All tools return consistent error information:

**Error Response Format:**
- `success`: false
- `message`: Descriptive error message
- `properties`: May include additional error context

**Common Error Types:**

1. **File Not Found**
   ```
   Error in read_file: File not found: nonexistent.py
   ```

2. **Permission Denied**
   ```
   Error in write_file: File access not allowed: /etc/passwd
   ```

3. **Invalid Arguments**
   ```
   Error in string_replace: Missing required argument: old_str
   ```

4. **File Too Large**
   ```
   Error in read_file: File too large: large_file.txt
   ```

5. **Pattern Not Found**
   ```
   String not found in main.py: 'nonexistent_string'
   ```

## Security and Limitations

### File Type Restrictions

Only the following file types are allowed:

**Code Files:**
`.py`, `.java`, `.js`, `.ts`, `.jsx`, `.tsx`, `.c`, `.cpp`, `.h`, `.hpp`, `.cs`, `.php`, `.rb`, `.go`, `.rs`, `.swift`, `.kt`, `.scala`

**Configuration Files:**
`.json`, `.yaml`, `.yml`, `.toml`, `.cfg`, `.ini`, `.conf`, `.xml`

**Documentation Files:**
`.md`, `.txt`, `.html`, `.css`

### Forbidden Directories

The following directories are blocked for security:
`.git`, `.svn`, `.hg`, `__pycache__`, `.pytest_cache`, `node_modules`, `.venv`, `.env`, `venv`, `env`

### Size Limits

- **Maximum file size**: 10MB (configurable)
- **Maximum search results**: 1000 per query
- **Maximum list results**: 1000 per query

### Path Restrictions

- All paths must be relative to the workspace root
- Path traversal (`../`) is blocked
- Absolute paths are not allowed

## Configuration

Environment variables for customization:

```bash
# File size limit (bytes)
export MOATLESS_MAX_FILE_SIZE=10485760

# Search result limits
export MOATLESS_MAX_SEARCH_RESULTS=100

# Search timeout (seconds)
export MOATLESS_SEARCH_TIMEOUT=30
```

## Performance Tips

1. **Use file patterns** to limit search scope
2. **Use line ranges** for large files
3. **Set appropriate max_results** for searches
4. **Use specific regex patterns** instead of broad searches
5. **List directories before reading** files to understand structure