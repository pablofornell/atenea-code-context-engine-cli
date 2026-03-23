import asyncio
import os
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
from .config import get_server_url, get_api_key, get_verify_ssl, get_ca_cert
from .logging_config import setup_logging, get_logger

# Setup logging for MCP server (INFO level for status messages)
setup_logging(level="INFO")
logger = get_logger(__name__)

class CodebaseWatcher(FileSystemEventHandler):
    def __init__(self, mcp_server, directory_path: str, debounce_seconds: float = 2.0):
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
    def __init__(self, server_url: str, api_key: str | None = None, verify_ssl: bool = True, ca_cert: str | None = None):
        self.mcp = FastMCP("Atenea Context Engine")
        self.http_client = AteneaHTTPClient(server_url, api_key=api_key, verify_ssl=verify_ssl, ca_cert=ca_cert)
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
            all_local_metadata = self.scanner.scan_directory(directory_path)
            if not all_local_metadata:
                logger.warning("No indexable files found.")
                return

            server_hashes = await self.http_client.get_file_hashes(collection_name)
            
            files_to_send_metadata = []
            deleted_files = []
            
            for f in all_local_metadata:
                path = f["path"]
                if path not in server_hashes or f["content_hash"] != server_hashes[path]:
                    files_to_send_metadata.append(f)
            
            local_paths = {f["path"] for f in all_local_metadata}
            for path in server_hashes:
                if path not in local_paths:
                    deleted_files.append(path)

            if files_to_send_metadata or deleted_files:
                logger.info(f"Auto-syncing: {len(files_to_send_metadata)} changed, {len(deleted_files)} deleted.")
                
                # Process in batches to limit memory usage even further
                batch_size = 5
                for i in range(0, len(files_to_send_metadata), batch_size):
                    batch_metadata = files_to_send_metadata[i : i + batch_size]
                    batch_to_send = []
                    for meta in batch_metadata:
                        content = self.scanner.get_file_content(directory_path, meta["path"])
                        if content:
                            batch_to_send.append({
                                "path": meta["path"],
                                "content": content,
                                "content_hash": meta["content_hash"]
                            })
                    
                    # Send deletes only with the first batch
                    current_deleted = deleted_files if i == 0 else []
                    if batch_to_send or current_deleted:
                        await self.http_client.index_files(batch_to_send, collection=collection_name, deleted_files=current_deleted)
                
                # Handle case where there are ONLY deletions
                if not files_to_send_metadata and deleted_files:
                    await self.http_client.index_files([], collection=collection_name, deleted_files=deleted_files)

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
        # Lazily start the file watcher on first tool call (captures the running loop)
        self._ensure_watcher()

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
            logger.debug(f"Collection lookup: '{collection_name}' in {collections} = {is_indexed}")
        except Exception as e:
            return f"Error: Could not connect to Atenea backend at {self.http_client.server_url}. Is the server running?\nDetails: {e}"

        # 3. Check if already indexed
        if not is_indexed:
            logger.warning(f"Codebase not found: '{collection_name}'. Available: {collections}. CWD: {os.getcwd()}")
            return f"This codebase '{collection_name}' is not indexed. Available codebases: {collections}. Please index it first using: atenea index"

        # 4. Incremental Indexing (just-in-time check)
        await self.sync_index(directory_path)

        # 5. Query the backend
        try:
            result = await self.http_client.query(information_request, collection=collection_name)
            return result.get("results", "No results found.")
        except Exception as e:
            return f"Error querying Atenea backend: {e}"

    def _ensure_watcher(self):
        """Lazily start the file watcher, capturing the running event loop."""
        if self.loop is not None:
            return
        self.loop = asyncio.get_running_loop()
        root = get_project_root()
        self.watcher = CodebaseWatcher(self, root)
        self.watcher.start()

    def run(self):
        try:
            self.mcp.run()
        finally:
            if self.watcher:
                self.watcher.stop()

def main():
    server_url = get_server_url()
    api_key = get_api_key()
    verify_ssl = get_verify_ssl()
    ca_cert = get_ca_cert()
    server = AteneaMCPServer(server_url, api_key=api_key, verify_ssl=verify_ssl, ca_cert=ca_cert)
    server.run()

if __name__ == "__main__":
    main()
