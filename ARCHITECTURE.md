# Architecture & Implementation

## Project Structure

```
home-file-analyzer/
├── analyzer.py              # Flask backend + platform detection
├── templates/
│   └── index.html          # Single-page web UI (HTML/CSS/JS)
├── README.md               # Setup & usage guide
├── FEATURES.md             # Cross-platform feature details
├── QUICKSTART.txt          # Quick start (plain text)
└── ARCHITECTURE.md         # This file
```

## Backend (analyzer.py)

### Platform Detection Layer

**Operating System Detection**
```python
get_platform_info()
  → sys.platform (win32, darwin, linux*)
  → Returns: {"os": "Windows|macOS|Linux", "platform": "win32|darwin|linux"}
```

**Shell Detection**
```python
get_shell_info()
  → Inspects: SHELL, COMSPEC, TERM, TERM_PROGRAM env vars
  → Identifies: Bash, Zsh, Fish, PowerShell, cmd.exe, Git Bash
  → Returns: string identifying shell
```

**Home Folder Detection**
```python
get_home_folder()
  → Tries: $HOME, $USERPROFILE, $HOMEDRIVE+$HOMEPATH
  → Fallback: Path.home()
  → Returns: absolute path to user's home directory
```

### Core Scanning

**File Inventory**
```python
scan_directory(root_path, exclude_system=True)
  → os.walk() to traverse directory tree
  → Collects: filename, size, modified time
  → Aggregates by file extension
  → Tracks: largest files, recently modified, stale (1yr+)
```

**Cross-Platform Exclusions**

EXCLUDE_DIRS includes patterns for:
- All platforms: `.git`, `node_modules`, `.cache`, `.venv`, etc.
- macOS: `.Trash`, `Library`, `.Spotlight-V100`, etc.
- Windows: `AppData`, `Temp`, `$RECYCLE.BIN`, etc.
- Linux: `.local`, `.config`, etc.

### API Endpoints

```
GET /
  → Renders index.html with context:
    - home: detected home folder
    - shortcuts: platform-aware quick links (Downloads, Documents, etc.)
    - platform_os: "Windows|macOS|Linux"
    - shell: detected shell name

GET /platform
  → JSON: {os, shell, home}
  → Called by frontend on page load

POST /scan
  → JSON input: {path, exclude_system}
  → JSON output: {
      total_size, total_files, total_folders,
      ext_breakdown: [{ext, count, size, pct}],
      largest_files: [{name, path, size, mtime}],
      recent_files: [{...}],
      stale_files: [{...}],
      stale_count, stale_total_size
    }
  → Returns 400 on error with descriptive message
```

## Frontend (index.html)

### Styling

- **Font stack:** IBM Plex Sans (body), IBM Plex Mono (paths/data)
- **Color palette:**
  - Primary: `#1F6F5C` (teal)
  - Accent: `#C4622D` (clay/rust)
  - Backgrounds: `#F5F6F3` (light), `#FFFFFF` (paper)
  - Text: `#14181C` (ink)
  - Borders: `#E1E4DF` (subtle)
- **Layout:** Max 1040px width, responsive down to mobile
- **Rounded corners:** 10px for cards, 7px for inputs

### Key Components

**Path Input**
- Text field accepts any format: `~/path`, `C:\path`, `/path`, `./path`
- Both forward and backslashes accepted
- JavaScript pre-scan validation (whitespace trim)

**Scan Controls**
- Platform-aware shortcuts (dynamically generated)
- "Skip hidden & system folders" toggle (default: checked)
- Error display with OS-specific path examples

**Results Display**

1. **Storage Bar** — Segmented by file type with legend
2. **Stats Cards** — Total size, files, folders, stale space
3. **Extensions Table** — File type breakdown with counts & sizes
4. **Tabbed File Lists:**
   - Largest files
   - Recently modified
   - Old & untouched (1yr+)

### JavaScript Patterns

**Platform Awareness**
```javascript
initPlatform()
  → Fetch /platform endpoint
  → Store PLATFORM_INFO = {os, shell, home}
  → Update UI header with detected environment
  
expandPath(path)
  → Replace ~ with known home folder
  → Called before sending to backend
  
normalizePath(path)
  → Trim whitespace
  → Python's Path() handles / vs \ transparently
```

**Cross-Platform Error Handling**
```javascript
if (path_error){
  if (PLATFORM_INFO.os === 'Windows'){
    suggest C:\Users\YourName or ~/
  } else if (PLATFORM_INFO.os === 'macOS'){
    suggest ~/Downloads or ~/Documents
  } else {
    suggest ~/Downloads or ~/snap
  }
}
```

## Path Handling Strategy

### Why It Works Cross-Platform

**Python's pathlib.Path is smart:**
```python
Path("C:\\Users\\user\\Downloads")  # Accepts backslashes
Path("C:/Users/user/Downloads")     # Accepts forward slashes
Path("~/Downloads")                 # Works on all OSes
Path("./relative")                  # Relative paths work

# All .resolve() to absolute paths correctly on their native OS
```

**Backend doesn't care about path format:**
- Path separators are normalized by Python's pathlib
- Tilde expansion: `Path().expanduser()`
- Relative paths: `Path().resolve()`

**Frontend expands tilde before sending:**
```javascript
// Frontend knows home folder from /platform endpoint
const expanded = path.replace('~', PLATFORM_INFO.home);
// Send to backend with properly expanded path
```

## Environment Variable Fallback Chain

When Flask starts:

```
1. Check SHELL env var    → Likely set in bash/zsh/Fish
2. Check COMSPEC env var  → Set by PowerShell/cmd.exe
3. Check TERM env var     → Unix-like hint
4. Check USERPROFILE      → Windows-set home
5. Check HOME             → Unix-like home
6. Fallback Path.home()   → Most reliable
```

This ensures the app works correctly no matter:
- Which shell launched Python
- What shell the user prefers
- What OS they're on
- What environment variables are set

## Testing Coverage

**Simulated Environments:**
- macOS with zsh
- Windows with PowerShell
- Windows with cmd.exe  
- Linux with bash
- Git Bash on Windows
- Cross-shell path formats

**Path Formats Tested:**
- Unix: `~/Downloads`, `/home/user/docs`
- Windows: `C:\Users\user\Downloads`, `C:/Users/user/Downloads`
- Relative: `./folder`, `../other`
- Tilde: `~/any/path`

**Error Cases:**
- Non-existent paths
- Permission denied
- Invalid characters
- Empty input

## Performance

**Scanning:**
- Uses `os.walk()` for efficient directory traversal
- Single pass through filesystem
- File stats cached during walk
- Sorting happens in-memory (small overhead)

**Memory:**
- All files held in memory during scan
- For typical home folder: negligible
- For extreme folders (1M+ files): may use several GB

**UI:**
- Async fetch for scan requests
- Results stream back as JSON
- List rendering: JavaScript loops (not jQuery, no framework overhead)
- Color palette is pre-computed on page load

## Security Considerations

**Local-Only:**
- No network calls except to localhost Flask server
- No data transmission
- No persistent storage

**File Access:**
- Respects OS file permissions (silent skip on PermissionError)
- Only reads metadata (size, timestamp)
- Does not read file contents

**Path Injection:**
- Backend uses Python's pathlib (safe)
- Path.resolve() normalizes all paths
- No shell commands executed
- No eval() or similar unsafe patterns

## Dependencies

**Production:**
- Flask (only web framework)
- Python 3.7+ (built-ins: pathlib, os, sys, platform)

**No other dependencies required.**

## Deployment Notes

**Development:** Flask built-in server (`app.run()`) — fine for local use

**Production:** Replace with proper WSGI server (Gunicorn, uWSGI, etc.)
```bash
gunicorn -w 4 -b 127.0.0.1:5050 analyzer:app
```

**Port:** Hardcoded to 5050 (non-standard, unlikely to conflict)

**Binding:** Localhost only (127.0.0.1) — no network exposure
