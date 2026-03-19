import asyncio
import os
import logging
import time
import threading
from typing import Optional
from mcp.server.fastmcp import FastMCP
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .http_client import AteneaHTTPClient
from .scanner import Scanner
from .utils import get_project_root
from .constants import is_ignored

# Setup logging to stderr
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("atenea.mcp_server")

class CodebaseWatcher(FileSystemEventHandler):
    def __init__(self, mcp_server, directory_path: str, debounce_seconds: float = 22.0):
        self.mcp_server = mcp_server
        self.directory_path = directory_path
        self.debounce_seconds = debounce_seconds
        self.last_event_time = 0.0
        self.timer = None
        self.observer = Observer()

    def start(self):
        self.observer.schedule(self, self.directory_path, recursive=True)
        self.observer.start()
        logger.info(f"Started codebase watcher on: {self.directory_path}")

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def on_any_event(self, event):
        if event.is_directory:
            return
            
        # Use centralized ignore logic
        if is_ignored(event.src_path):
            return

        self.last_event_time = time.time()
        if self.timer:
            self.timer.cancel()
            self.timer = None
        
        self.timer = threading.Timer(self.debounce_seconds, self._trigger_sync)
        self.timer.start()

    def _trigger_sync(self):
        logger.info("Change detected, triggering incremental indexing...")
        # Since this runs in a watchdog thread, we need to schedule it in the MCP's event loop
        asyncio.run_coroutine_threadsafe(
            self.mcp_server.sync_index(self.directory_path),
            self.mcp_server.loop
        )

class AteneaMCPServer:
    def __init__(self, server_url: str):
        self.mcp = FastMCP("Atenea Context Engine")
        self.http_client = AteneaHTTPClient(server_url)
        self.scanner = Scanner()
        self.loop = None
        self.watcher = None
        
        # Register tools
        self.mcp.tool()(self.codebase_retrieval)

    async def sync_index(self, directory_path: str):
        """Perform incremental indexing for a specific directory."""
        collection_name = os.path.basename(directory_path.rstrip(os.sep))
        
        try:
            # 1. Ensure backend is status "ok" and already indexed
            status = await self.http_client.get_status()
            collections = status.get("collections", [])
            
            if collection_name not in collections:
                logger.debug(f"Skipping auto-indexing for non-indexed codebase: {collection_name}")
                return
            
            # 2. Incremental Indexing
            logger.info(f"Indexing updates for: {directory_path} ({collection_name})")
            all_local_files = self.scanner.scan_directory(directory_path)
            if not all_local_files:
                logger.warning("No indexable files found.")
                return

            server_hashes = await self.http_client.get_file_hashes(collection_name)
            local_files_map = {f["path"]: f for f in all_local_files}
            files_to_send = []
            deleted_files = []
            
            for path, f in local_files_map.items():
                if path not in server_hashes or f["content_hash"] != server_hashes[path]:
                    files_to_send.append(f)
            
            for path in server_hashes:
                if path not in local_files_map:
                    deleted_files.append(path)

            if files_to_send or deleted_files:
                logger.info(f"Auto-syncing: {len(files_to_send)} changed, {len(deleted_files)} deleted.")
                batch_size = 5
                first_batch = files_to_send[:batch_size]
                await self.http_client.index_files(first_batch, collection=collection_name, deleted_files=deleted_files)
                for i in range(batch_size, len(files_to_send), batch_size):
                    batch = files_to_send[i : i + batch_size]
                    await self.http_client.index_files(batch, collection=collection_name)
                logger.info(f"Auto-sync complete for {collection_name}.")
            else:
                logger.info(f"No changes to sync for {collection_name}.")
        except Exception as e:
            logger.error(f"Error during auto-sync: {e}")

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

        # 3. Check if already indexed
        if not is_indexed:
            return "This code base is not indexed, tell the user to index it first using the 'index' command."

        # 4. Incremental Indexing (just-in-time check)
        await self.sync_index(directory_path)

        # 5. Query the backend
        try:
            result = await self.http_client.query(information_request, collection=collection_name)
            return result.get("results", "No results found.")
        except Exception as e:
            return f"Error querying Atenea backend: {e}"

    def run(self):
        # Start watcher in the background
        root = get_project_root()
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
        self.watcher = CodebaseWatcher(self, root)
        self.watcher.start()
        
        try:
            self.mcp.run()
        finally:
            if self.watcher:
                self.watcher.stop()

def main():
    server_url = os.environ.get("ATENEA_SERVER", "http://localhost:8080")
    server = AteneaMCPServer(server_url)
    server.run()

if __name__ == "__main__":
    main()
