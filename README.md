# Atenea CLI & MCP Server

Atenea is a local, self-hosted code context engine. This package provides the CLI tool for management and the MCP server for IDE integration.

## Installation

```bash
pip install .
```

## CLI Usage

### Configuration

All settings are stored in `.atenea/conf.json` in the project root and can be overridden at any time with environment variables (which take precedence).

**Domain-based server (Option A):**
```bash
atenea config set-server https://atenea.yourdomain.com
atenea config set-api-key your-secret-key
```

**IP-based server with self-signed certificate (Option B):**

The recommended approach is to trust the server's CA certificate — this keeps full SSL verification:
```bash
atenea config set-server https://203.0.113.50
atenea config set-api-key your-secret-key
atenea config set-ca-cert ./caddy-root.crt   # exported from the server
```

Alternatively, disable SSL verification entirely (traffic is still encrypted, but the certificate is not authenticated):
```bash
atenea config set-verify-ssl false
```

> **Note**: The API key is only required when the server has `ATENEA_API_KEY` set. For local usage without authentication, you can skip that step.

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
        "ATENEA_SERVER": "https://atenea.yourdomain.com",
        "ATENEA_API_KEY": "your-secret-key"
      }
    }
  }
}
```

- **command**: `atenea` (ensure it's in your PATH or use absolute path to the executable).
- **args**: `["serve"]` starts the MCP bridge.
- **ATENEA_SERVER**: (Optional) URL to your Atenea server. Defaults to the value in `.atenea/conf.json` or `http://localhost:8080`.
- **ATENEA_API_KEY**: (Optional) API key for authentication. Only needed if the server has authentication enabled.
- **ATENEA_VERIFY_SSL**: (Optional) Set to `false` to disable SSL certificate verification (self-signed cert without CA export).
- **ATENEA_CA_CERT**: (Optional) Path to a custom CA certificate file for SSL verification (preferred over disabling verification).

## Backend Requirement
This CLI requires an **Atenea Server** instance running. See the `atenea-server` package for setup instructions.
