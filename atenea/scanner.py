import os
import logging
import hashlib
from typing import List, Dict

logger = logging.getLogger("atenea.scanner")

from .constants import IGNORED_DIRS, IGNORED_FILES, BINARY_EXTS

class Scanner:
    def scan_directory(self, directory: str) -> List[Dict[str, str]]:
        if not os.path.isdir(directory):
            logger.error(f"Error: {directory} is not a directory.")
            return []

        files_to_send = []
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
                            files_to_send.append({
                                "path": rel_path, 
                                "content": content,
                                "content_hash": content_hash
                            })
                except Exception as e:
                    logger.warning(f"Could not read {full_path}: {e}")
        
        return files_to_send
