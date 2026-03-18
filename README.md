# Atenea CLI & MCP Server

Atenea is a local, self-hosted code context engine. This package provides the CLI tool for management and the MCP server for IDE integration.

## Installation

```bash
pip install .
```

## CLI Usage

### Index a Directory
```bash
atenea index .
```
This scans the current directory and sends it to the Atenea server for indexing.

### Check Status
```bash
atenea status
```

### Query Context
```bash
atenea query "How does indexing work?"
```

## IDE Integration (Antigravity / Cursor)

To use Atenea as an MCP server in your IDE, add the following to your MCP configuration:

```json
{
  "mcpServers": {
    "atenea-context-engine": {
      "command": "atenea",
      "args": ["serve"],
      "env": {
        "ATENEA_SERVER": "http://localhost:8080"
      }
    }
  }
}
```

- **command**: `atenea` (ensure it's in your PATH or use absolute path to the executable).
- **args**: `["serve"]` starts the MCP bridge.
- **ATENEA_SERVER**: (Optional) URL to your Atenea server. Defaults to `http://localhost:8080`.

## Backend Requirement
This CLI requires an **Atenea Server** instance running. See the `atenea-server` package for setup instructions.
