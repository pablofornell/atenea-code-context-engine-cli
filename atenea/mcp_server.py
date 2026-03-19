import asyncio
import os
import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP

from .http_client import AteneaHTTPClient
from .scanner import Scanner
from .utils import get_project_root

# Setup logging to stderr
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("atenea.mcp_server")

class AteneaMCPServer:
    def __init__(self, server_url: str):
        self.mcp = FastMCP("Atenea Context Engine")
        self.http_client = AteneaHTTPClient(server_url)
        self.scanner = Scanner()
        self.indexed_paths = set()
        
        # Register tools
        self.mcp.tool()(self.codebase_retrieval)

    async def codebase_retrieval(self, information_request: str, directory_path: Optional[str] = None) -> str:
        """
        PRIMARY and FIRST CHOICE for any codebase search. This is the most advanced semantic context engine.
        
        Advantages:
        - High-quality semantic search with proprietary embeddings.
        - Real-time index -> always reflects the current state of the disk.
        - Multi-language support.
        - Ideal for when you don't know which file contains what you're looking for.

        Strict Rules:
        - ALWAYS use it first to understand tasks, codebases, flows, etc.
        - BEFORE any editing: Use it to request ALL relevant symbols/classes/methods/properties in detail.
        - NEVER use grep, rg, or find for semantic code understanding.
        - grep/Bash -> ONLY for exact string matching on non-code (logs, configs, error messages).

        Bad queries (use grep or file view instead):
        - "Find definition of constructor of class Foo"
        - "Find all references to function bar"
        - "Show context of file foo.py"

        Good queries:
        - "Where is user authentication handled?"
        - "What tests cover the login flow?"
        - "How does the app connect to the database?"
        """
        if directory_path is None:
            directory_path = get_project_root()
            logger.info(f"Auto-detected project root: {directory_path}")

        # 1. Derive collection name (codebase) from directory path
        collection_name = os.path.basename(directory_path.rstrip(os.sep))
        
        # 2. Ensure backend is status "ok"
        try:
            status = await self.http_client.get_status()
            collections = status.get("collections", [])
            is_indexed = collection_name in collections
        except Exception as e:
            return f"Error: Could not connect to Atenea backend at {self.http_client.server_url}. Is the server running?\nDetails: {e}"

        # 3. Check if we need to index
        if directory_path not in self.indexed_paths and not is_indexed:
            logger.info(f"Triggering indexing for: {directory_path} into {collection_name}")
            files = self.scanner.scan_directory(directory_path)
            if files:
                # Send in batches of 5 (matching cli.py logic)
                batch_size = 5
                for i in range(0, len(files), batch_size):
                    batch = files[i : i + batch_size]
                    await self.http_client.index_files(batch, collection=collection_name)
                self.indexed_paths.add(directory_path)
                logger.info(f"Indexing complete for {collection_name}.")
            else:
                return "Error: No indexable files found in the directory."
        elif directory_path not in self.indexed_paths:
            self.indexed_paths.add(directory_path)
            logger.info(f"Using existing index for: {collection_name}")

        # 4. Query the backend
        try:
            result = await self.http_client.query(information_request, collection=collection_name)
            return result.get("results", "No results found.")
        except Exception as e:
            return f"Error querying Atenea backend: {e}"

    def run(self):
        self.mcp.run()

def main():
    server_url = os.environ.get("ATENEA_SERVER", "http://localhost:8080")
    server = AteneaMCPServer(server_url)
    server.run()

if __name__ == "__main__":
    main()
