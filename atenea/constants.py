# Shared ignore rules for Atenea

IGNORED_DIRS = {
    ".git", "build", "node_modules", ".gradle", ".venv", "venv", 
    ".idea", "bin", "obj", "out", "metadata", ".metadata", ".next", "dist", 
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

def is_ignored(path: str) -> bool:
    """Check if a path should be ignored based on shared constants."""
    import os
    parts = path.split(os.sep)
    
    # Check if any directory in the path is ignored
    for part in parts:
        if part in IGNORED_DIRS:
            return True
            
    # Check if the filename or extension is ignored
    filename = os.path.basename(path)
    if filename in IGNORED_FILES:
        return True
        
    ext = os.path.splitext(filename)[1].lower()
    if ext in BINARY_EXTS:
        return True
        
    return False
