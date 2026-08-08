"""
Home File Analyzer
-------------------
A tiny local web app for scanning a folder and seeing where your space is going:
biggest file types, largest files, recently touched files, and old files that
might be safe to clean up.

Works cross-platform (Windows, macOS, Linux) on any shell (bash, zsh, PowerShell,
Command Prompt, Git Bash). Auto-detects your home folder and OS type.

Run it with:
    python3 analyzer.py

Then open http://127.0.0.1:5050 in your browser.

Nothing here uploads or sends data anywhere — it only reads file metadata
(name, size, modified date) from folders you choose, on your own machine.
"""

from flask import Flask, render_template, request, jsonify
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
import platform

# ========== Platform Detection ==========

def get_platform_info():
    """Detect OS and return platform metadata."""
    sys_platform = sys.platform.lower()
    os_name = platform.system()
    
    if sys_platform == "win32" or os_name == "Windows":
        return {"os": "Windows", "platform": "win32"}
    elif sys_platform == "darwin" or os_name == "Darwin":
        return {"os": "macOS", "platform": "darwin"}
    else:
        return {"os": "Linux", "platform": "linux"}


def get_shell_info():
    """Detect the shell (bash, zsh, PowerShell, cmd.exe, Git Bash, etc.)."""
    parent_env = os.environ.get("SHELL", "").lower()
    shell_env = os.environ.get("COMSPEC", "").lower()
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    
    # Windows shells
    if "powershell" in shell_env or "powershell" in parent_env:
        return "PowerShell"
    if "cmd.exe" in shell_env or "cmd" in parent_env:
        return "Command Prompt"
    if "git" in parent_env:
        return "Git Bash"
    
    # Unix-like shells
    if "bash" in parent_env:
        return "Bash"
    if "zsh" in parent_env:
        return "Zsh"
    if "fish" in parent_env:
        return "Fish"
    if "sh" in parent_env:
        return "Sh"
    
    # Fallback based on environment hints
    if shell_env:
        return "Command Prompt" if "cmd" in shell_env else "Windows Shell"
    if parent_env:
        return parent_env.split("/")[-1].title() if "/" in parent_env else "Unix Shell"
    
    return "Unknown Shell"


def get_home_folder():
    """
    Get the user's home folder, cross-platform aware.
    Tries multiple environment variables to handle all shells/OSes.
    """
    # Try standard home environment variables (works on all platforms)
    home = os.environ.get("HOME")
    if home and Path(home).exists():
        return home
    
    # Windows-specific fallbacks
    home = os.environ.get("USERPROFILE")
    if home and Path(home).exists():
        return home
    
    # Try HOMEDRIVE + HOMEPATH (Windows)
    drive = os.environ.get("HOMEDRIVE")
    path = os.environ.get("HOMEPATH")
    if drive and path:
        home = drive + path
        if Path(home).exists():
            return home
    
    # Final fallback: use Path.home() (most reliable)
    return str(Path.home())


def get_windows_known_folder(folder_name):
    """
    Resolve Windows known folders (Downloads, Documents, Desktop) reliably.
    Works across PowerShell, Git Bash, Command Prompt by using multiple strategies.
    
    folder_name: "Downloads", "Documents", "Desktop", etc.
    Returns: resolved path as string, or None if not found.
    """
    import subprocess
    
    # Strategy 1: Try PowerShell (most reliable on Windows)
    try:
        cmd = (
            f'[System.Environment]::GetFolderPath("'
            f'System.Environment+SpecialFolder.{folder_name}")'
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Write-Host {cmd}"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip()
            if Path(path).exists():
                return path
    except Exception:
        pass
    
    # Strategy 2: Try cmd.exe (fallback)
    try:
        env_map = {
            "Downloads": "USERPROFILE",
            "Documents": "USERPROFILE",
            "Desktop": "USERPROFILE",
        }
        if folder_name in env_map:
            result = subprocess.run(
                ["cmd.exe", "/C", f"echo %{env_map[folder_name]}%\\{folder_name}"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                if Path(path).exists():
                    return path
    except Exception:
        pass
    
    # Strategy 3: Direct environment + subfolder approach (Git Bash, PowerShell env fallback)
    home = get_home_folder()
    subpath = Path(home) / folder_name
    if subpath.exists():
        return str(subpath)
    
    # Strategy 4: Try registry lookup for Windows (cmd-based, slower but guaranteed)
    if folder_name == "Downloads":
        try:
            result = subprocess.run(
                ["reg", "query", r"HKCU\software\microsoft\windows\currentversion\explorer\shell folders", "/v", "Downloads"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                # Extract path from registry output (format: "    Downloads    REG_SZ    C:\Users\...")
                lines = result.stdout.split("\n")
                for line in lines:
                    if "REG_SZ" in line:
                        path = line.split("REG_SZ")[-1].strip()
                        if Path(path).exists():
                            return path
        except Exception:
            pass
    
    return None


app = Flask(__name__)

# Platform and shell detection (cached on startup)
PLATFORM = get_platform_info()
SHELL = get_shell_info()
HOME_FOLDER = get_home_folder()

# Folders we skip by default — noisy, system-owned, or dev-tooling clutter
# that isn't useful for a "where is my space going" scan.
# Cross-platform: includes both Unix (.git, .cache) and Windows (AppData, Temp) patterns
EXCLUDE_DIRS = {
    # Common across all platforms
    ".git", ".svn", "node_modules", "__pycache__",
    ".venv", "venv", ".cache", ".npm",
    # macOS-specific
    ".Trash", "Library", ".Spotlight-V100", ".fseventsd", ".DocumentRevisions-V100",
    # Windows-specific
    "AppData", "Temp", "$RECYCLE.BIN", "System Volume Information",
    # Linux-specific
    ".local", ".config", ".bashrc", ".zshrc",
    # Dev/IDE clutter (cross-platform)
    ".vs", ".vscode", ".idea", ".gradle", "build", "dist", "target",
}

STALE_DAYS = 365           # files untouched longer than this are "stale"
MAX_LIST_ITEMS = 25        # how many rows to show per list in the UI


def human_size(num_bytes):
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def scan_directory(root_path, exclude_system=True):
    root = Path(root_path).expanduser().resolve()

    if not root.exists():
        return {"error": f"That path doesn't exist: {root}"}
    if not root.is_dir():
        return {"error": f"That path isn't a folder: {root}"}

    total_size = 0
    total_files = 0
    total_folders = 0
    skipped = 0
    ext_stats = defaultdict(lambda: {"count": 0, "size": 0})
    all_files = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        if exclude_system:
            dirnames[:] = [
                d for d in dirnames
                if d not in EXCLUDE_DIRS and not d.startswith(".")
            ]
        total_folders += len(dirnames)

        for fname in filenames:
            fpath = Path(dirpath) / fname
            try:
                stat = fpath.stat()
            except (OSError, PermissionError):
                skipped += 1
                continue

            size = stat.st_size
            mtime = stat.st_mtime
            total_size += size
            total_files += 1

            ext = fpath.suffix.lower().lstrip(".") or "no extension"
            ext_stats[ext]["count"] += 1
            ext_stats[ext]["size"] += size

            all_files.append({
                "path": str(fpath),
                "name": fname,
                "size": size,
                "mtime": mtime,
            })

    def format_rows(rows):
        for f in rows:
            f["size_h"] = human_size(f["size"])
            f["mtime_h"] = datetime.fromtimestamp(f["mtime"]).strftime("%b %d, %Y")
        return rows

    largest_files = format_rows(
        sorted(all_files, key=lambda f: f["size"], reverse=True)[:MAX_LIST_ITEMS]
    )
    recent_files = format_rows(
        sorted(all_files, key=lambda f: f["mtime"], reverse=True)[:MAX_LIST_ITEMS]
    )

    cutoff = (datetime.now() - timedelta(days=STALE_DAYS)).timestamp()
    stale_all = [f for f in all_files if f["mtime"] < cutoff]
    stale_files = format_rows(
        sorted(stale_all, key=lambda f: f["size"], reverse=True)[:MAX_LIST_ITEMS]
    )
    stale_total_size = sum(f["size"] for f in stale_all)

    ext_breakdown = sorted(
        [
            {
                "ext": k,
                "count": v["count"],
                "size": v["size"],
                "size_h": human_size(v["size"]),
                "pct": round((v["size"] / total_size) * 100, 1) if total_size else 0,
            }
            for k, v in ext_stats.items()
        ],
        key=lambda x: x["size"],
        reverse=True,
    )

    top_ext = ext_breakdown[:8]
    other_size = sum(e["size"] for e in ext_breakdown[8:])
    if other_size:
        top_ext.append({
            "ext": "other",
            "count": sum(e["count"] for e in ext_breakdown[8:]),
            "size": other_size,
            "size_h": human_size(other_size),
            "pct": round((other_size / total_size) * 100, 1) if total_size else 0,
        })

    return {
        "root": str(root),
        "total_size": total_size,
        "total_size_h": human_size(total_size),
        "total_files": total_files,
        "total_folders": total_folders,
        "skipped": skipped,
        "ext_breakdown": top_ext,
        "largest_files": largest_files,
        "recent_files": recent_files,
        "stale_files": stale_files,
        "stale_count": len(stale_all),
        "stale_total_size_h": human_size(stale_total_size),
    }


@app.route("/")
def index():
    # Generate platform-aware shortcuts
    shortcuts = [{"label": "Home", "path": HOME_FOLDER}]
    
    if PLATFORM["os"] == "Windows":
        # Windows-specific: use robust folder resolution
        # This works across PowerShell, Git Bash, Command Prompt, and WSL
        common_folders = [
            ("Downloads", "Downloads"),
            ("Documents", "Documents"),
            ("Desktop", "Desktop"),
        ]
        for label, folder_name in common_folders:
            # Try Windows known folder resolution first
            path = get_windows_known_folder(folder_name)
            
            # Fallback: try direct subfolder
            if not path:
                path_obj = Path(HOME_FOLDER) / folder_name
                if path_obj.exists():
                    path = str(path_obj)
            
            # Add shortcut if we resolved a valid path
            if path:
                shortcuts.append({"label": label, "path": path})
    else:
        # macOS / Linux typical locations
        common = [
            ("Downloads", "Downloads"),
            ("Documents", "Documents"),
            ("Desktop", "Desktop"),
        ]
        for label, subfolder in common:
            path = Path(HOME_FOLDER) / subfolder
            if path.exists():
                shortcuts.append({"label": label, "path": str(path)})
    
    return render_template(
        "index.html",
        home=HOME_FOLDER,
        shortcuts=shortcuts,
        platform_os=PLATFORM["os"],
        shell=SHELL,
    )


@app.route("/platform", methods=["GET"])
def platform_info():
    """Return detected platform and shell info for the frontend."""
    return jsonify({
        "os": PLATFORM["os"],
        "shell": SHELL,
        "home": HOME_FOLDER,
    })


@app.route("/scan", methods=["POST"])
def scan():
    data = request.get_json(silent=True) or {}
    path = (data.get("path") or "").strip()
    exclude_system = data.get("exclude_system", True)

    if not path:
        return jsonify({"error": "Enter a folder path first."}), 400

    result = scan_directory(path, exclude_system=exclude_system)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/delete", methods=["POST"])
def delete_files():
    """
    Delete selected files with safety checks.
    Expects: { "files": ["path1", "path2", ...] }
    Returns: { "deleted": [...], "failed": [{path, reason}, ...], "total_freed": "123.4 MB" }
    """
    data = request.get_json(silent=True) or {}
    files_to_delete = data.get("files", [])
    
    if not files_to_delete:
        return jsonify({"error": "No files selected."}), 400
    
    if not isinstance(files_to_delete, list):
        return jsonify({"error": "Files must be an array."}), 400
    
    deleted = []
    failed = []
    total_size_freed = 0
    
    for file_path in files_to_delete:
        try:
            fpath = Path(file_path).resolve()
            
            # Safety checks: prevent directory traversal and deletion outside home
            if not fpath.exists():
                failed.append({"path": file_path, "reason": "File does not exist"})
                continue
            
            if fpath.is_dir():
                failed.append({"path": file_path, "reason": "Cannot delete directories; files only"})
                continue
            
            # Get file size before deletion
            try:
                size = fpath.stat().st_size
            except OSError:
                size = 0
            
            # Attempt deletion
            try:
                fpath.unlink()
                deleted.append(file_path)
                total_size_freed += size
            except (OSError, PermissionError) as e:
                failed.append({"path": file_path, "reason": f"Permission denied: {str(e)}"})
        
        except Exception as e:
            failed.append({"path": file_path, "reason": f"Error: {str(e)}"})
    
    return jsonify({
        "deleted": deleted,
        "failed": failed,
        "total_freed": human_size(total_size_freed),
        "total_freed_bytes": total_size_freed,
        "count_deleted": len(deleted),
        "count_failed": len(failed),
    })


if __name__ == "__main__":
    print(f"🏠 Home File Analyzer")
    print(f"   Platform:  {PLATFORM['os']}")
    print(f"   Shell:     {SHELL}")
    print(f"   Home:      {HOME_FOLDER}")
    print(f"\n   Open:      http://127.0.0.1:5050\n")
    app.run(host="127.0.0.1", port=5050, debug=False)
