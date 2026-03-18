import os
import logging
from typing import List, Dict

logger = logging.getLogger("atenea.scanner")

# Shared ignore rules
IGNORED_DIRS = {
    ".git", "build", "node_modules", ".gradle", ".venv", "venv", 
    ".idea", "bin", "obj", "out", "metadata", ".next", "dist", 
    "target", "__pycache__", ".vscode", ".pytest_cache", ".mypy_cache"
}
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", 
    ".exe", ".dll", ".so", ".bin", ".jar", ".class", ".aar", ".xcf",
    ".svg", ".ttf", ".otf", ".woff", ".woff2", ".7z", ".tar", ".gz",
    ".dmg", ".iso", ".sqlite"
}
IGNORED_FILES = {
    "gradlew", "gradlew.bat", 
    ".gitignore", "gradle.properties", "settings.gradle", "package-lock.json",
    "yarn.lock", "pnpm-lock.yaml", ".DS_Store"
}

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
                            files_to_send.append({"path": rel_path, "content": content})
                except Exception as e:
                    logger.warning(f"Could not read {full_path}: {e}")
        
        return files_to_send
