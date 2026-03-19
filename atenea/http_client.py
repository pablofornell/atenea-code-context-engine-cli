import httpx
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger("atenea.http_client")

class AteneaHTTPClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=300.0)

    async def get_status(self) -> Dict:
        try:
            response = await self.client.get(f"{self.server_url}/api/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error connecting to server status: {e}")
            raise

            logger.error(f"Error listing codebases: {e}")
            raise

    async def get_file_hashes(self, collection: Optional[str] = None) -> Dict[str, str]:
        try:
            params = {}
            if collection:
                params["collection"] = collection
            response = await self.client.get(f"{self.server_url}/api/index/hashes", params=params)
            response.raise_for_status()
            return response.json().get("hashes", {})
        except Exception as e:
            logger.error(f"Error fetching file hashes: {e}")
            return {}

    async def index_files(self, files: List[Dict[str, str]], collection: Optional[str] = None, deleted_files: Optional[List[str]] = None) -> Dict:
        try:
            payload: Dict[str, Any] = {"files": files}
            if collection:
                payload["collection"] = collection
            if deleted_files:
                payload["deleted_files"] = deleted_files
            response = await self.client.post(
                f"{self.server_url}/api/index",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error indexing files: {e}")
            raise

    async def query(self, text: str, limit: int = 20, collection: Optional[str] = None) -> Dict:
        try:
            payload = {"query": text, "limit": limit}
            if collection:
                payload["collection"] = collection
            response = await self.client.post(
                f"{self.server_url}/api/query",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error querying backend: {e}")
            raise

    async def clean(self, collection: Optional[str] = None) -> Dict:
        try:
            payload = {}
            if collection:
                payload["collection"] = collection
            response = await self.client.request(
                "DELETE",
                f"{self.server_url}/api/index",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error clearing index: {e}")
            raise

    async def close(self):
        await self.client.aclose()
