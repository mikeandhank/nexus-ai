"""
MCP Tool Expansion
Additional tools for the MCP protocol (50+ tools)
"""

# Tool definitions for MCP protocol
MCP_TOOLS = [
    # === FILE OPERATIONS ===
    {
        "name": "file_read",
        "description": "Read contents of a file",
        "parameters": {
            "path": {"type": "string", "description": "Path to file"}
        }
    },
    {
        "name": "file_write",
        "description": "Write content to a file",
        "parameters": {
            "path": {"type": "string", "description": "Path to file"},
            "content": {"type": "string", "description": "Content to write"}
        }
    },
    {
        "name": "file_append",
        "description": "Append content to a file",
        "parameters": {
            "path": {"type": "string", "description": "Path to file"},
            "content": {"type": "string", "description": "Content to append"}
        }
    },
    {
        "name": "file_delete",
        "description": "Delete a file",
        "parameters": {
            "path": {"type": "string", "description": "Path to file"}
        }
    },
    {
        "name": "file_list",
        "description": "List files in a directory",
        "parameters": {
            "path": {"type": "string", "description": "Directory path"},
            "pattern": {"type": "string", "description": "Glob pattern (optional)"}
        }
    },
    {
        "name": "file_search",
        "description": "Search for files by name pattern",
        "parameters": {
            "path": {"type": "string", "description": "Directory to search"},
            "pattern": {"type": "string", "description": "Search pattern"}
        }
    },
    {
        "name": "file_info",
        "description": "Get file metadata (size, dates, permissions)",
        "parameters": {
            "path": {"type": "string", "description": "Path to file"}
        }
    },
    
    # === DIRECTORY OPERATIONS ===
    {
        "name": "dir_create",
        "description": "Create a directory",
        "parameters": {
            "path": {"type": "string", "description": "Directory path"}
        }
    },
    {
        "name": "dir_delete",
        "description": "Delete a directory",
        "parameters": {
            "path": {"type": "string", "description": "Directory path"}
        }
    },
    {
        "name": "dir_tree",
        "description": "Get directory tree structure",
        "parameters": {
            "path": {"type": "string", "description": "Root directory path"},
            "depth": {"type": "integer", "description": "Max depth (optional)"}
        }
    },
    
    # === PROCESS OPERATIONS ===
    {
        "name": "process_run",
        "description": "Run a shell command",
        "parameters": {
            "command": {"type": "string", "description": "Command to run"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (optional)"}
        }
    },
    {
        "name": "process_list",
        "description": "List running processes",
        "parameters": {
            "pattern": {"type": "string", "description": "Filter by name (optional)"}
        }
    },
    {
        "name": "process_kill",
        "description": "Kill a process by PID",
        "parameters": {
            "pid": {"type": "integer", "description": "Process ID"}
        }
    },
    {
        "name": "process_status",
        "description": "Get process status",
        "parameters": {
            "pid": {"type": "integer", "description": "Process ID"}
        }
    },
    
    # === SYSTEM OPERATIONS ===
    {
        "name": "system_info",
        "description": "Get system information",
        "parameters": {}
    },
    {
        "name": "system_uptime",
        "description": "Get system uptime",
        "parameters": {}
    },
    {
        "name": "system_memory",
        "description": "Get memory usage",
        "parameters": {}
    },
    {
        "name": "system_disk",
        "description": "Get disk usage",
        "parameters": {
            "path": {"type": "string", "description": "Path (optional)"}
        }
    },
    {
        "name": "system_cpu",
        "description": "Get CPU usage",
        "parameters": {}
    },
    {
        "name": "system_load",
        "description": "Get system load average",
        "parameters": {}
    },
    {
        "name": "system_users",
        "description": "List logged in users",
        "parameters": {}
    },
    
    # === NETWORK OPERATIONS ===
    {
        "name": "network_interfaces",
        "description": "List network interfaces",
        "parameters": {}
    },
    {
        "name": "network_connections",
        "description": "List network connections",
        "parameters": {}
    },
    {
        "name": "network_ping",
        "description": "Ping a host",
        "parameters": {
            "host": {"type": "string", "description": "Hostname or IP"},
            "count": {"type": "integer", "description": "Ping count (optional)"}
        }
    },
    {
        "name": "network_dns",
        "description": "DNS lookup",
        "parameters": {
            "hostname": {"type": "string", "description": "Hostname to lookup"}
        }
    },
    {
        "name": "network_curl",
        "description": "Make HTTP request",
        "parameters": {
            "url": {"type": "string", "description": "URL to fetch"},
            "method": {"type": "string", "description": "HTTP method"},
            "headers": {"type": "object", "description": "Request headers (optional)"}
        }
    },
    
    # === CONTAINER OPERATIONS (if Docker available) ===
    {
        "name": "docker_ps",
        "description": "List Docker containers",
        "parameters": {
            "all": {"type": "boolean", "description": "Include stopped (optional)"}
        }
    },
    {
        "name": "docker_images",
        "description": "List Docker images",
        "parameters": {}
    },
    {
        "name": "docker_logs",
        "description": "Get container logs",
        "parameters": {
            "container": {"type": "string", "description": "Container name/ID"},
            "tail": {"type": "integer", "description": "Lines to show (optional)"}
        }
    },
    {
        "name": "docker_stats",
        "description": "Get container resource usage",
        "parameters": {
            "container": {"type": "string", "description": "Container name/ID (optional)"}
        }
    },
    {
        "name": "docker_restart",
        "description": "Restart a container",
        "parameters": {
            "container": {"type": "string", "description": "Container name/ID"}
        }
    },
    
    # === DATABASE OPERATIONS ===
    {
        "name": "db_query",
        "description": "Execute SQL query",
        "parameters": {
            "query": {"type": "string", "description": "SQL query"},
            "params": {"type": "array", "description": "Query parameters (optional)"}
        }
    },
    {
        "name": "db_tables",
        "description": "List database tables",
        "parameters": {}
    },
    {
        "name": "db_schema",
        "description": "Get table schema",
        "parameters": {
            "table": {"type": "string", "description": "Table name"}
        }
    },
    
    # === GIT OPERATIONS ===
    {
        "name": "git_status",
        "description": "Get git repository status",
        "parameters": {
            "path": {"type": "string", "description": "Repo path (optional)"}
        }
    },
    {
        "name": "git_log",
        "description": "Get git commit history",
        "parameters": {
            "path": {"type": "string", "description": "Repo path (optional)"},
            "count": {"type": "integer", "description": "Number of commits (optional)"}
        }
    },
    {
        "name": "git_diff",
        "description": "Get uncommitted changes",
        "parameters": {
            "path": {"type": "string", "description": "Repo path (optional)"}
        }
    },
    {
        "name": "git_branch",
        "description": "List git branches",
        "parameters": {
            "path": {"type": "string", "description": "Repo path (optional)"}
        }
    },
    
    # === TEXT OPERATIONS ===
    {
        "name": "text_search",
        "description": "Search text in files",
        "parameters": {
            "pattern": {"type": "string", "description": "Search pattern"},
            "path": {"type": "string", "description": "Directory to search"},
            "filetype": {"type": "string", "description": "File extension filter (optional)"}
        }
    },
    {
        "name": "text_replace",
        "description": "Find and replace text",
        "parameters": {
            "path": {"type": "string", "description": "File path"},
            "search": {"type": "string", "description": "Text to find"},
            "replace": {"type": "string", "description": "Replacement text"}
        }
    },
    {
        "name": "text_count",
        "description": "Count occurrences of text",
        "parameters": {
            "path": {"type": "string", "description": "File path"},
            "pattern": {"type": "string", "description": "Pattern to count"}
        }
    },
    
    # === COMPRESSION ===
    {
        "name": "compress_gzip",
        "description": "Compress file with gzip",
        "parameters": {
            "source": {"type": "string", "description": "Source file"},
            "dest": {"type": "string", "description": "Destination file (optional)"}
        }
    },
    {
        "name": "decompress_gzip",
        "description": "Decompress gzip file",
        "parameters": {
            "source": {"type": "string", "description": "Source file"},
            "dest": {"type": "string", "description": "Destination file (optional)"}
        }
    },
    {
        "name": "compress_tar",
        "description": "Create tar archive",
        "parameters": {
            "source": {"type": "string", "description": "Source directory"},
            "dest": {"type": "string", "description": "Archive path"}
        }
    },
    {
        "name": "decompress_tar",
        "description": "Extract tar archive",
        "parameters": {
            "source": {"type": "string", "description": "Archive path"},
            "dest": {"type": "string", "description": "Destination directory"}
        }
    },
    
    # === CRYPTO OPERATIONS ===
    {
        "name": "crypto_hash",
        "description": "Calculate file hash",
        "parameters": {
            "path": {"type": "string", "description": "File path"},
            "algorithm": {"type": "string", "description": "sha256, md5, sha1"}
        }
    },
    {
        "name": "crypto_random",
        "description": "Generate random bytes",
        "parameters": {
            "length": {"type": "integer", "description": "Number of bytes"}
        }
    },
    
    # === TIME OPERATIONS ===
    {
        "name": "time_now",
        "description": "Get current time",
        "parameters": {}
    },
    {
        "name": "time_parse",
        "description": "Parse datetime string",
        "parameters": {
            "datetime": {"type": "string", "description": "Datetime string"},
            "format": {"type": "string", "description": "Format string"}
        }
    },
    {
        "name": "time_format",
        "description": "Format datetime",
        "parameters": {
            "timestamp": {"type": "number", "description": "Unix timestamp"},
            "format": {"type": "string", "description": "Format string"}
        }
    },
]


def get_mcp_tools():
    """Return all MCP tools"""
    return MCP_TOOLS


def get_tool_by_name(name: str):
    """Get a specific tool by name"""
    for tool in MCP_TOOLS:
        if tool["name"] == name:
            return tool
    return None
