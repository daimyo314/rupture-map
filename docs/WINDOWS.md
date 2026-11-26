# Windows guide and live-tracking port

## Current support

Rupture Map's browser interface and included map assets are platform-independent, but **live game tracking currently supports Linux/Proton only**. The application has not been tested on Windows. Running the current server on Windows does not enable live player position, facing, resource or building discovery, zip-rail routes, base completion, cyst tracking, objectives, the rupture timer, or automatic multiplayer world selection.

You can try the manual map and private notes on Windows while a native tracker is developed. The map and marker data are stored in the browser profile on that computer; changing browser profiles, ports, or clearing site data can make them unavailable. Use **Export** for a backup. The app listens on localhost and does not send notes to the game.

## Try the manual map on Windows

1. Install 64-bit Python 3 from [python.org](https://www.python.org/downloads/windows/) and [Git for Windows](https://git-scm.com/downloads/win), or download and extract this repository's ZIP file.
2. Open PowerShell and clone the repository:

   ```powershell
   git clone https://github.com/daimyo314/rupture-map.git
   cd rupture-map
   ```

   If using the ZIP, open PowerShell in the extracted `rupture-map` folder instead.
3. Start the server:

   ```powershell
   py -3 server.py
   ```

   If `py` is unavailable but Python is on your PATH, use `python server.py` instead. The server uses the Python standard library; it does not require `pip install`.
4. Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/) in a browser. Keep PowerShell open while using the map; press **Ctrl+C** there to stop the server.
5. Use **Add marker** and click the map to save a personal marker and note. The live-tracking status will report an error because its backend is Linux-specific. Manual world selection and notes remain available.

If port 8765 is in use, run `py -3 server.py --port 8766` and open `http://127.0.0.1:8766/`. Browser storage is scoped to the address and port, so markers saved on one port do not automatically appear on another.

These steps are based on the current code and still need validation on Windows. If the server or interface fails, report the Python version and the error without including private game logs or server addresses.

## What must change for live tracking

This is guidance for a contributor implementing native Windows support; it is **not** an existing Windows backend.

### Process access

The current reader finds the game through `/proc`, reads its module mappings, and uses `/proc/<pid>/mem` and `os.pread`. Windows provides neither that process interface nor `os.pread`. In particular, process reads occur in `server.py`, `buildings.py`, and `base_tracker.py`; a Windows port must cover all of them, not just the position endpoint.

Introduce a shared, read-only process abstraction for finding the game, locating the executable's module base, reading bytes at an address, and closing the process handle. Keep the Linux backend and existing error handling working. A Windows backend could use Python's `ctypes` and these documented Win32 APIs:

- [Tool Help](https://learn.microsoft.com/en-us/windows/win32/toolhelp/tool-help-functions) to enumerate the game process and its modules.
- [`OpenProcess`](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess) with only the permissions needed for querying and reading.
- [`ReadProcessMemory`](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory), which requires `PROCESS_VM_READ`, for bounded reads. Close process and snapshot handles with `CloseHandle`.

Use a 64-bit Python process for the 64-bit game. Validate addresses and read lengths, handle game restarts and access-denied errors, and never write to or inject code into the game. Do not assume administrator privileges are needed or ask users to disable security software.

### Game installation, version, and connection

`server.py` currently hard-codes a Linux Steam library under `/legames` and a Proton log path. Replace those assumptions with configurable or discovered Windows paths. Steam libraries can be on another drive; don't assume the default installation path. The game's Windows log will normally be under `%LOCALAPPDATA%\StarRupture\Saved\Logs`, but verify it on the user's installation.

The current code deliberately restricts live reads to Steam build **26781824 / CL127004**. The offsets, class layouts, and module identity must be verified against the actual Windows executable and build before enabling any reader; do not assume they are valid merely because Proton runs a Windows executable. Return a clear unsupported-build status when validation fails.

Automatic world selection currently combines the network connection state with a local fingerprint of the latest server IP and port extracted from the connection log. Port this separately, and avoid retaining or exposing log query strings, credentials, or server addresses. The local `server-worlds.json` mapping is ignored by Git and must be configured on each installation. If a server cannot be identified reliably, do not silently save discoveries to the wrong world.

### Validation before claiming Windows support

Test on an actual Windows machine with the matching game build. At minimum:

1. Start and stop the game, enter and leave a world, and verify safe recovery when the process is missing or access is denied.
2. Compare player position and facing with the in-game map while moving and turning; check single-player and a multiplayer client separately.
3. Verify resource, building, zip-rail, base-progress, and cyst readings against observed game objects. Confirm unobserved or stale data is labeled correctly.
4. Compare the rupture timer and wave frequency with game data across pauses, client stalls, and phase changes; do not treat the next phase as a confirmed impact time without verification.
5. Verify world selection isolates saved data, browser notes and backups survive reloads, and the HTTP server remains bound to localhost.
6. Recheck behavior on unsupported game builds and when game data is temporarily unavailable. Report what was actually tested, including the OS, game build, and single-player or multiplayer role.
