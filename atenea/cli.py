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

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("atenea.cli")

class AteneaCLI:
    def __init__(self, server_url: str):
        self.http_client = AteneaHTTPClient(server_url)
        self.scanner = Scanner()

    async def status(self):
        try:
            data = await self.http_client.get_status()
            print(f"Server: {data.get('engine', 'Unknown')}")
            print(f"Status: {data.get('status', 'Unknown')}")
            collections = data.get('collections', [])
            print(f"Available Codebases: {', '.join(collections) if collections else 'None'}")
        except Exception as e:
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

    async def index(self, directory: str, collection: Optional[str] = None):
        print(f"Scanning directory: {directory}")
        if collection:
            print(f"Targeting codebase: {collection}")
        files_to_send = self.scanner.scan_directory(directory)

        if not files_to_send:
            print("No indexable files found.")
            return

        print(f"Found {len(files_to_send)} files. Sending to server...")
        
        batch_size = 5
        failed_batches = []
        total_batches = (len(files_to_send) + batch_size - 1) // batch_size
        
        with tqdm(total=total_batches, desc="Indexing") as pbar:
            for i in range(0, len(files_to_send), batch_size):
                batch = files_to_send[i : i + batch_size]
                batch_num = i // batch_size + 1
                success = False
                
                for attempt in range(3):
                    try:
                        await self.http_client.index_files(batch, collection=collection)
                        success = True
                        break
                    except Exception as e:
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)  # 1s, 2s backoff
                        else:
                            tqdm.write(f"  ⚠ Batch {batch_num} failed after 3 attempts: {e}")
                            failed_batches.append(batch_num)
                pbar.update(1)

        if failed_batches:
            print(f"\nIndexing finished with {len(failed_batches)} failed batch(es): {failed_batches}")
        else:
            print("\nIndexing complete.")

    async def close(self):
        await self.http_client.close()

def main():
    parser = argparse.ArgumentParser(description="Atenea Context Engine CLI Client")
    parser.add_argument("--server", default=os.environ.get("ATENEA_SERVER", "http://localhost:8080"), help="Server URL (default: http://localhost:8080)")
    
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

    # Serve (MCP Server)
    subparsers.add_parser("serve", help="Start the MCP server for IDE integration")

    args = parser.parse_args()
    
    if args.command == "serve":
        from .mcp_server import main as run_mcp
        # Note: environment variable ATENEA_SERVER is already picked up by mcp_server.main
        run_mcp()
        return

    cli = AteneaCLI(args.server)
    
    async def run_command():
        if args.command == "status":
            await cli.status()
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
            await cli.index(directory, name)
        else:
            parser.print_help()
        await cli.close()

    asyncio.run(run_command())

if __name__ == "__main__":
    main()
