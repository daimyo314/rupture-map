# Windows adoption and agent handoff

Rupture Map 1.0 includes a browser map and a **Linux/Proton-only live tracker**. The manual map and local notes may work on Windows, but neither the Windows setup below nor a native live tracker has been tested on Windows. A coding agent can use this file as a starting point for a Windows port; this document is not a claim that one already exists.

## Try the manual map

1. Install **64-bit Python 3** from [python.org](https://www.python.org/downloads/windows/). Install [Git for Windows](https://git-scm.com/downloads/win), or download and extract the repository ZIP.
2. In PowerShell, clone and enter the project folder:

   ```powershell
   git clone https://github.com/daimyo314/rupture-map.git
   cd rupture-map
   ```

   If you downloaded the ZIP, open PowerShell in the extracted project folder instead.
3. Start the local server:

   ```powershell
   py -3 server.py
   ```

   If `py` is unavailable but Python is on PATH, try `python server.py`. No `pip install` is needed.
4. Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Expand **Field Notes**, choose **Add marker**, then click the map. Keep PowerShell open while using the app; press Ctrl+C to stop it.

The tracker will report unavailable on Windows until a native backend is implemented. If port 8765 is already in use, run `py -3 server.py --port 8766` and open `http://127.0.0.1:8766/`. The browser stores maps and notes by address and port; export a backup before moving between them. New multiplayer server entries are created when the tracker can identify a connection; the current interface does not provide a manual add-world button.

## Give this to a coding agent

Open the repository folder in Claude, Codex, Grok, or another coding agent and ask, for example:

> Read `AGENTS.md`, `README.md`, and `WINDOWS-ADOPTION.md`. Help me adapt Rupture Map's Linux/Proton tracker to my Windows installation while preserving the existing Linux behavior and local browser data. First inspect the current implementation and identify my installed game build and Steam library. Implement read-only Windows process access where the build and data layouts can be verified, test what is possible on my machine, and report what remains unverified.

The agent should use the actual machine and user's instructions as its source of truth. Do not claim live Windows support until the relevant features have been tested on Windows.

## Current architecture and porting boundaries

- `server.py` runs the localhost HTTP server, serves the browser assets and implements `/api/position`, `/api/resources`, `/api/objectives`, `/api/infection-hud`, `/api/death-drops`, `/api/buildings`, `/api/rails`, and `/api/bases`. It discovers the game through `/proc`, reads process memory using `os.pread`, hard-codes the Linux Steam game directory, and reads the Proton log for multiplayer connection identity.
- `buildings.py` and `base_tracker.py` read process memory for buildings and base/cyst progress. `infection_tracker.py` reads the tumor HUD; `wave_visuals.py` reads replicated visual states. `rails.py` supplies helpers used by the building/rail scanner. A port must inspect all of these, not just position.
- `index.html`, `app.js`, `style.css`, `resource-clusters.js`, `forecast.js`, `infection-areas.js`, and `shared-known.js` implement the browser UI, grouping, cycle indicators and locally stored data. Preserve API response behavior and existing IndexedDB and backup compatibility when possible.
- The shipped tracker gates live position on **Steam build 26781824 / CL127004**. The game executable, process layout, Unreal structures and offsets must be verified for the actual Windows build before use. A Proton observation does not establish Windows compatibility. Game updates can invalidate assumptions.

A Windows implementation can introduce a shared, read-only process abstraction for game discovery, module base, bounded reads and handle cleanup, while preserving the Linux backend. Python `ctypes` can use Microsoft's documented [Tool Help functions](https://learn.microsoft.com/en-us/windows/win32/toolhelp/tool-help-functions), [`OpenProcess`](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess), and [`ReadProcessMemory`](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory). Use only permissions needed for querying and reading; close all handles; handle missing processes, process restarts, access denial, short reads and unsupported builds. Do not write to the game, inject code, disable security software, or assume administrator access is necessary.

Discover or configure Steam libraries instead of assuming a single drive. Windows logs may be under `%LOCALAPPDATA%\StarRupture\Saved\Logs`; verify the actual location. Multiplayer routing uses connection state and a local hash derived from the last server address in the game log. Avoid saving or exposing raw addresses, query strings or credentials; if a connection cannot be identified reliably, do not silently mix its discoveries with another world. The current app does not automatically distinguish separate single-player saves.

## Validation on a Windows machine

1. Confirm the manual page loads and notes can be added, exported and imported. Verify the server listens on localhost and browser data survives reloads.
2. Verify game start, world entry, disconnect and restart; return clear unavailable or unsupported-build statuses rather than unsafe or misleading data.
3. Compare position and heading with the in-game map while moving and turning, in single-player and as a multiplayer client where available.
4. Check other-player markers and connection lines, nearby discoveries, building types, zip rails, bases, cysts, objectives and death drops against observed game data. Distinguish unavailable, unloaded and stale data.
5. Check the timer, frequency, phase and visual-state readings through changes and pauses. The Moon Phase display is inferred from growback, and the next-phase countdown is not necessarily impact time.
6. Verify world routing and privacy: server-specific data stays separate, shared locations exclude player-built objects, and neither private notes nor raw server addresses are sent elsewhere. Report the Windows version, game build, roles tested and any missing coverage.
