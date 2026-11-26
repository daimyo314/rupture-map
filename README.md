# Rupture Map

A private, local browser companion map for **StarRupture**. See your position and heading on a second screen, remember discoveries and notes, and follow other players on supported multiplayer servers. The tracker reads game data without modifying the game.

## Run on Linux

1. Install Python 3 and run the game through Steam/Proton.
2. In this directory, run `python3 server.py`.
3. Open <http://127.0.0.1:8765/> in a browser. Stop the server with Ctrl+C.

Live tracking currently supports **Steam build 26781824 / CL127004** and expects the game under `/legames/steamapps/common/StarRupture`. Different installs require changing the paths in `server.py`. The game and tracker must run as the same user, with permission to read the game process. Game updates can invalidate the offsets. Python's standard library is the only runtime dependency.

**Windows:** Manual mapping is available, but live tracking has not been ported or tested. See [Windows setup and porting notes](docs/WINDOWS.md).

## Features

- **Live map:** Follow your position and facing, zoom, pan, and display other players' replicated positions and directions. Multiplayer updates may be intermittent; faded player markers have not changed recently.
- **Worlds and radiation:** Keep separate world data and automatically switch the terrain image between the supported radiation states. Select a state under Filters if it is unknown.
- **Discoveries:** Remember nearby resources, ore deposits, buildings, zip-rails, bases, cysts and landmarks. Replicated lootable-body locations may be shown beyond the nearby scan radius. Choose layers and resource types under Filters.
- **Shared knowledge:** Locations discovered in other worlds appear as transparent icons. Building locations and world-specific progress remain separate. A marker is not a guarantee that an object is currently available or reachable.
- **Infection and death drops:** A purple glow approximates places visited while the tumor tracker is active. It is a sampled footprint, not a precise boundary. Skull markers represent currently loaded player death drops and disappear if they are looted **or unloaded**.
- **Wave timer:** Shows time until the next reported wave phase, not necessarily impact, and the world frequency. Red effects warn as that phase approaches.
- **Private notes:** Add markers and notes; collapse the notes panel to save space. Click a Habitat to give it a local name.

## Storage and limits

Worlds, discoveries, shared locations and notes are stored in the browser's IndexedDB for the current address and profile. Use **Export** to back them up before clearing browser data, changing profiles or ports, or moving computers; **Import** adds worlds and merges shared locations. The app listens on localhost and makes no external network requests. Server-to-world associations use a local hash of the server address; they are not included in the repository.

Live data depends on what the game client loads or replicates. Saved discoveries and building locations can become stale. Radiation artwork is not a guarantee of safety. Infection-area clearing when the HUD disappears is a heuristic and may be wrong if the game hides its HUD for another reason. Position alignment has been checked near the landing area but not exhaustively calibrated across the map.

The terrain images are assembled from game assets. The ore and landmark coordinate catalogs are derived from [MapExtension_Plugin](https://github.com/Mralexandresys/MapExtension_Plugin); see [ORE-CATALOG-LICENSE.txt](ORE-CATALOG-LICENSE.txt). Bundled Google Material Icons are covered by [their license](assets/MATERIAL-ICONS-LICENSE.txt).
