# Home File Analyzer

A one-page local tool for seeing where your disk space is going on **Windows,
macOS, or Linux** — from any shell (bash, zsh, PowerShell, Command Prompt, Git
Bash, etc.). Point it at a folder, get a storage breakdown by file type, the
largest files, the most recently changed files, and files that haven't been
touched in a year+.

Everything runs locally in Flask — nothing is uploaded anywhere.

## Setup

**macOS / Linux (bash, zsh, Fish, etc.):**

```bash
cd home-file-analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
cd home-file-analyzer
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows (Command Prompt):**

```cmd
cd home-file-analyzer
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

**Git Bash (Windows):**

```bash
cd home-file-analyzer
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

## Run

Any shell / OS:

```bash
python3 analyzer.py
```

(On Windows, you can also use `python` instead of `python3`.)

Then open **http://127.0.0.1:5050** in your browser. The app auto-detects your
OS and shell and displays them in the header.

## Path Input

The tool accepts paths in multiple formats — use whatever's natural for your OS:

**macOS / Linux:**
- `~/Downloads` (tilde expansion)
- `/Users/you/Documents`
- `./some/relative/path`

**Windows:**
- `C:\Users\YourName\Downloads` (backslashes)
- `C:/Users/YourName/Downloads` (forward slashes also work)
- `~/Downloads` (tilde expansion)
- `.\relative\path`

Shortcuts (Home, Downloads, Documents, Desktop) appear at the top and work
cross-platform.

## Features

- **Storage breakdown by file type** — see what `.mp4`, `.pdf`, `.app`, etc.
  are taking up space.
- **Largest files** — find the big stuff.
- **Recently changed** — scan by modification date.
- **Old & heavy** — files untouched for 1+ year (candidates for cleanup).
- **Smart exclusions** — skips system clutter by default (`.git`, `node_modules`,
  `Library`, `AppData`, `Temp`, etc.) — toggle to include everything.

## Notes

- Works cross-platform: Windows, macOS, Linux.
- Works cross-shell: PowerShell, Command Prompt, bash, zsh, Fish, Git Bash, etc.
  — auto-detects your environment.
- Hidden folders and common dev clutter (`.git`, `node_modules`, `.Trash`,
  `Library`, `AppData`, etc.) are skipped by default — uncheck "Skip hidden &
  system folders" to include everything.
- Large folders (100k+ files) may take a few seconds to scan.
- Nothing is uploaded or sent anywhere — it only reads file metadata (names,
  sizes, modified dates) from folders you choose, on your own machine.
- To stop the server, go back to the terminal and press `Ctrl+C`.

## Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started, submit pull requests, or report issues. Please also adhere to our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

