import os
import logging
import hashlib
from typing import List, Dict, Optional

logger = logging.getLogger("atenea.scanner")

from .constants import IGNORED_DIRS, IGNORED_FILES, BINARY_EXTS

class Scanner:
    def __init__(self):
        # Cache file contents read during scanning to avoid double reads
        self._content_cache: Dict[str, str] = {}

    def scan_directory(self, directory: str) -> List[Dict[str, str]]:
        if not os.path.isdir(directory):
            logger.error(f"Error: {directory} is not a directory.")
            return []

        self._content_cache.clear()
        files_metadata = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                if file in IGNORED_FILES:
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in BINARY_EXTS:
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, directory)

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if content.strip():
                            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                            self._content_cache[rel_path] = content
                            files_metadata.append({
                                "path": rel_path,
                                "content_hash": content_hash
                            })
                except Exception as e:
                    logger.warning(f"Could not read {full_path} for hashing: {e}")

        return files_metadata

    def get_file_content(self, directory: str, rel_path: str) -> Optional[str]:
        # Return cached content if available (avoids re-reading the file)
        cached = self._content_cache.pop(rel_path, None)
        if cached is not None:
            return cached

        full_path = os.path.join(directory, rel_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {full_path}: {e}")
            return None
