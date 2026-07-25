# Cross-Platform Features

## Auto-Detection

The app auto-detects your environment on startup:

### Operating System Detection
- **Windows** — via `sys.platform == "win32"` or `platform.system() == "Windows"`
- **macOS** — via `sys.platform == "darwin"` or `platform.system() == "Darwin"`
- **Linux** — all other platforms

### Shell Detection
Detects and displays your shell:
- **Windows:** PowerShell, Command Prompt, Git Bash
- **Unix-like:** Bash, Zsh, Fish, Sh
- **Method:** inspects `SHELL`, `COMSPEC`, `TERM`, `TERM_PROGRAM` env vars

### Home Folder Detection
Tries multiple environment variables to find the home folder:
1. `$HOME` (Unix-like)
2. `$USERPROFILE` (Windows)
3. `$HOMEDRIVE + $HOMEPATH` (Windows)
4. Falls back to `Path.home()` (most reliable)

This ensures the app works correctly no matter which shell launched it.

## Cross-Platform Path Handling

### Input Formats
The app accepts paths in multiple formats — all work on any OS:
- Unix-style: `/Users/you/Downloads`, `/home/user/docs`
- Windows-style: `C:\Users\YourName\Downloads`, `C:/Users/YourName/Downloads`
- Tilde expansion: `~/Downloads`, `~/Documents` (works on all platforms)
- Relative paths: `./subfolder`, `../other`

### Backend Handling
Python's `pathlib.Path` normalizes all formats transparently:
```python
Path("C:\\Users\\user\\Downloads").resolve()  # Works on any OS
Path("~/Downloads").expanduser().resolve()    # Tilde expansion
Path("./relative").resolve()                  # Relative paths
```

## Smart Exclusions

The exclusion list includes clutter from all three major OSes:

**All platforms:**
- `.git`, `.svn`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.cache`, `.npm`
- `.vs`, `.vscode`, `.idea`, `.gradle`, `build`, `dist`, `target`

**macOS:**
- `.Trash`, `Library`, `.Spotlight-V100`, `.fseventsd`, `.DocumentRevisions-V100`

**Windows:**
- `AppData`, `Temp`, `$RECYCLE.BIN`, `System Volume Information`

**Linux:**
- `.local`, `.config`, `.bashrc`, `.zshrc`

## UI Context Awareness

The interface adapts to the detected platform:

### Header Display
Shows `Platform · Shell · local scan` (e.g., "Windows · PowerShell · local scan")

### Path Examples in Errors
If a path doesn't exist, the error message suggests OS-specific examples:
- **Windows:** "Try: C:\Users\YourName\Downloads or ~/Downloads"
- **macOS:** "Try: ~/Downloads or ~/Documents"
- **Linux:** "Try: ~/Downloads or ~/Documents or ~/snap"

### Shortcut Buttons
Dynamically generates quicklinks for common folders that exist on the current system:
- Windows: Home, Downloads, Documents, Desktop
- macOS: Home, Downloads, Documents, Desktop
- Linux: Home, Downloads, Documents, Desktop (if they exist)

## Environment Variable Support

The app works correctly regardless of how Python was invoked:

| Shell | Detected Via | Example Env |
|-------|-------------|-----------|
| bash | `SHELL=/bin/bash` | `HOME=/home/user` |
| zsh | `SHELL=/bin/zsh` | `HOME=/Users/user` |
| Fish | `SHELL=/usr/bin/fish` | `HOME=/home/user` |
| PowerShell | `COMSPEC=C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` | `USERPROFILE=C:\Users\user` |
| Command Prompt | `COMSPEC=C:\Windows\System32\cmd.exe` | `USERPROFILE=C:\Users\user` |
| Git Bash | `SHELL=/usr/bin/bash` (Git-aware) | `USERPROFILE=C:\Users\user` (Git Bash sets this) |

## What Doesn't Require User Configuration

✅ No manual OS selection in the UI  
✅ No shell script tricks needed  
✅ Works with relative paths (`.`, `./folder`)  
✅ Works with tilde paths (`~/Downloads`)  
✅ Works with absolute paths in any format (`C:\`, `/home/`, `/Users/`)  
✅ Works on any shell (bash, zsh, PowerShell, cmd.exe, Git Bash, etc.)  
✅ Home folder is auto-detected and pre-filled  
✅ Shortcuts are generated dynamically based on what exists  

## How It Works

### Startup Sequence
1. Python starts the Flask app
2. `get_platform_info()` detects OS
3. `get_shell_info()` detects shell from environment
4. `get_home_folder()` resolves home directory from multiple env vars
5. Startup message displays detected environment
6. Web server starts at `http://127.0.0.1:5050`

### First Load in Browser
1. JavaScript calls `/platform` endpoint
2. Backend returns `{os, shell, home}`
3. UI updates header to show "Windows · PowerShell" (or whatever was detected)
4. JavaScript expands paths: `~` → actual home folder
5. Auto-scans the home folder

### Path Input
1. User enters a path (any format)
2. JavaScript normalizes whitespace
3. JavaScript expands `~` using known home folder
4. Path is sent to backend `/scan` endpoint
5. Python's `Path().resolve()` handles both `/` and `\` transparently
6. Scan results returned

## Testing

To test with different shells/OSes, set environment variables before running:

```bash
# Simulate Windows PowerShell
export COMSPEC='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
export USERPROFILE='/root'
python3 analyzer.py

# Simulate macOS
export SHELL='/bin/zsh'
export HOME='/Users/testuser'
python3 analyzer.py

# Simulate Linux Bash
export SHELL='/bin/bash'
export HOME='/home/testuser'
python3 analyzer.py
```
