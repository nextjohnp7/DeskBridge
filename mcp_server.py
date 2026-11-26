"""DeskBridge MCP Server entry point.

Run over stdio:

    python mcp_server.py

Or configure in ~/.hermes/config.yaml:

    mcp_servers:
      deskbridge:
        command: "python"
        args: ["path/to/DeskBridge/mcp_server.py"]
"""

from core.mcp_server import main

if __name__ == "__main__":
    main()
