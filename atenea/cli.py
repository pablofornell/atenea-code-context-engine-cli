import os
import asyncio
import argparse
from typing import Optional
import sys
import logging
from tqdm import tqdm

from .http_client import AteneaHTTPClient
from .scanner import Scanner
from .utils import get_project_root
from .ui import WelcomeDashboard
from .config import get_server_url, save_config, load_config

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("atenea.cli")

class AteneaCLI:
    def __init__(self, server_url: str):
        self.http_client = AteneaHTTPClient(server_url)
        self.scanner = Scanner()

    async def status(self, dashboard: bool = False):
        try:
            data = await self.http_client.get_status()
            if dashboard:
                WelcomeDashboard().render(data)
            else:
                print(f"Server: {data.get('engine', 'Unknown')}")
                print(f"Status: {data.get('status', 'Unknown')}")
                collections = data.get('collections', [])
                print(f"Available Codebases: {', '.join(collections) if collections else 'None'}")
        except Exception as e:
            if dashboard:
                WelcomeDashboard().render(None)
            else:
                print(f"Error connecting to server: {e}")
            sys.exit(1)

    async def list_codebases(self):
        try:
            data = await self.http_client.get_codebases()
            collections = data.get("collections", [])
            if not collections:
                print("No codebases found.")
            else:
                print("Available codebases:")
                for c in collections:
                    print(f"  - {c}")
        except Exception as e:
            print(f"Error listing codebases: {e}")
            sys.exit(1)

    async def clean(self, collection: Optional[str] = None):
        try:
            await self.http_client.clean(collection)
            print(f"Index {collection or 'default'} cleared successfully.")
        except Exception as e:
            print(f"Error clearing index: {e}")
            sys.exit(1)

    async def query(self, query_text: str, limit: int = 20, collection: Optional[str] = None):
        try:
            data = await self.http_client.query(query_text, limit, collection)
            print(data.get("results", "No results found."))
        except Exception as e:
            print(f"Error querying: {e}")
            sys.exit(1)

    async def index(self, directory: str, collection: Optional[str] = None, full: bool = False):
        print(f"Scanning directory: {directory}")
        if collection:
            print(f"Targeting codebase: {collection}")
        
        all_files = self.scanner.scan_directory(directory)
        if not all_files:
            print("No indexable files found.")
            return

        files_to_send = all_files
        deleted_files = []

        if not full:
            # Fetch existing hashes from server
            server_hashes = await self.http_client.get_file_hashes(collection)
            
            local_files_map = {f["path"]: f for f in all_files}
            
            new_files = []
            modified_files = []
            unchanged_count = 0
            
            for path, f in local_files_map.items():
                if path not in server_hashes:
                    new_files.append(f)
                elif f["content_hash"] != server_hashes[path]:
                    modified_files.append(f)
                else:
                    unchanged_count += 1
            
            # Find deleted files (on server but not in local)
            for path in server_hashes:
                if path not in local_files_map:
                    deleted_files.append(path)
            
            files_to_send = new_files + modified_files
            
            print(f"Incremental Indexing Summary:")
            print(f"  - {len(new_files)} new files")
            print(f"  - {len(modified_files)} modified files")
            print(f"  - {len(deleted_files)} deleted files")
            print(f"  - {unchanged_count} unchanged files (skipped)")
            
            if not files_to_send and not deleted_files:
                print("\nEverything is up to date.")
                return
        else:
            print("Force full re-index requested.")

        if files_to_send:
            print(f"\nProcessing {len(files_to_send)} changed files. Sending to server...")
        elif deleted_files:
            print(f"\nRemoving {len(deleted_files)} deleted files...")
        
        batch_size = 5
        failed_batches = []
        # Total batches for files_to_send, plus 1 if we only have deletions
        total_batches = (len(files_to_send) + batch_size - 1) // batch_size
        if total_batches == 0 and deleted_files:
            total_batches = 1
        
        with tqdm(total=total_batches, desc="Indexing") as pbar:
            # Handle the first batch specially to include deleted files
            first_batch_metadata = files_to_send[:batch_size]
            first_batch_to_send = []
            for meta in first_batch_metadata:
                content = self.scanner.get_file_content(directory, meta["path"])
                if content:
                    first_batch_to_send.append({
                        "path": meta["path"],
                        "content": content,
                        "content_hash": meta["content_hash"]
                    })
            
            try:
                if first_batch_to_send or deleted_files:
                    await self.http_client.index_files(first_batch_to_send, collection=collection, deleted_files=deleted_files)
                pbar.update(1)
            except Exception as e:
                tqdm.write(f"  ⚠ First batch failed: {e}")
                failed_batches.append(1)
                pbar.update(1)

            # Handle remaining batches
            for i in range(batch_size, len(files_to_send), batch_size):
                batch_metadata = files_to_send[i : i + batch_size]
                batch_to_send = []
                for meta in batch_metadata:
                    content = self.scanner.get_file_content(directory, meta["path"])
                    if content:
                        batch_to_send.append({
                            "path": meta["path"],
                            "content": content,
                            "content_hash": meta["content_hash"]
                        })
                
                batch_num = i // batch_size + 1
                if not batch_to_send:
                    pbar.update(1)
                    continue
                    
                success = False
                for attempt in range(3):
                    try:
                        await self.http_client.index_files(batch_to_send, collection=collection)
                        success = True
                        break
                    except Exception as e:
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)
                        else:
                            tqdm.write(f"  ⚠ Batch {batch_num} failed: {e}")
                            failed_batches.append(batch_num)
                pbar.update(1)

        if failed_batches:
            print(f"\nIndexing finished with {len(failed_batches)} failed batch(es).")
        else:
            print("\nIndexing complete.")

    async def close(self):
        await self.http_client.close()

def main():
    parser = argparse.ArgumentParser(description="Atenea Context Engine CLI Client")
    parser.add_argument("--server", default=None, help=f"Server URL (default from config: {get_server_url()})")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status
    subparsers.add_parser("status", help="Check server status")
    
    # Clean
    clean_parser = subparsers.add_parser("clean", help="Clear the index")
    clean_parser.add_argument("--name", help="Specify codebase name to clear")
    
    # List
    subparsers.add_parser("list", help="List available codebases")
    
    # Query
    query_parser = subparsers.add_parser("query", help="Query the context engine")
    query_parser.add_argument("text", help="Query text")
    query_parser.add_argument("--limit", type=int, default=20, help="Number of results to return")
    query_parser.add_argument("--name", help="Specify codebase name to search in")
    
    # Index
    index_parser = subparsers.add_parser("index", help="Index a directory")
    index_parser.add_argument("directory", nargs="?", default=None, help="Directory path to index (defaults to current project root)")
    index_parser.add_argument("--name", help="Specify codebase name (defaults to 'atenea_code')")
    index_parser.add_argument("--full", action="store_true", help="Force a full re-index (bypass incremental logic)")

    # Serve (MCP Server)
    subparsers.add_parser("serve", help="Start the MCP server for IDE integration")

    # Config
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="Config commands")
    
    set_server_parser = config_subparsers.add_parser("set-server", help="Set the server URL")
    set_server_parser.add_argument("url", help="Server URL (e.g. http://localhost:8080)")

    args = parser.parse_args()
    
    if args.command == "serve":
        from .mcp_server import main as run_mcp
        # Note: environment variable ATENEA_SERVER is already picked up by mcp_server.main
        run_mcp()
        return

    server_url = args.server or get_server_url()
    
    if args.command == "config":
        if args.config_command == "set-server":
            config = load_config()
            config["server_url"] = args.url
            save_config(config)
            print(f"Server URL updated to: {args.url}")
        else:
            config_parser.print_help()
        return

    cli = AteneaCLI(server_url)
    
    async def run_command():
        if args.command == "status":
            await cli.status(dashboard=True)
        elif args.command == "list":
            await cli.list_codebases()
        elif args.command == "clean":
            await cli.clean(args.name)
        elif args.command == "query":
            name = args.name or os.path.basename(os.path.abspath(get_project_root()))
            await cli.query(args.text, args.limit, name)
        elif args.command == "index":
            directory = args.directory or get_project_root()
            name = args.name or os.path.basename(os.path.abspath(directory))
            await cli.index(directory, name, full=args.full)
        elif args.command is None:
            await cli.status(dashboard=True)
        else:
            parser.print_help()
        await cli.close()

    asyncio.run(run_command())

if __name__ == "__main__":
    main()
