import httpx
import logging
from typing import List, Dict, Optional

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

    async def index_files(self, files: List[Dict[str, str]]) -> Dict:
        try:
            response = await self.client.post(
                f"{self.server_url}/api/index",
                json={"files": files}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error indexing files: {e}")
            raise

    async def query(self, text: str, limit: int = 20) -> Dict:
        try:
            response = await self.client.post(
                f"{self.server_url}/api/query",
                json={"query": text, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error querying backend: {e}")
            raise

    async def clean(self) -> Dict:
        try:
            response = await self.client.delete(f"{self.server_url}/api/index")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error clearing index: {e}")
            raise

    async def close(self):
        await self.client.aclose()
