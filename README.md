# Rupture Map

A private, local browser map for StarRupture. This early version provides separate worlds, an extracted preliminary game map, and markers with notes. Live position tracking uses a read-only process reader for game build CL127004. The game remains unchanged.

## Run

From this directory run `python3 server.py`, then open http://127.0.0.1:8765/ in your browser. Stop the server with Ctrl+C. Python's standard library is the only runtime dependency; no internet connection is needed.

The default map is assembled from 36 in-game terrain tiles extracted from your installed game. The position mapping uses the game’s terrain-grid metadata, but its on-screen accuracy has not yet been confirmed against the in-game map. You can replace it with a PNG, JPEG, or WebP image, but replacing an image can misalign existing markers. Click Add marker and then a spot on the image. Drag to pan, scroll to zoom, and use the side list to edit a marker. Add a world to keep different sessions separate. Export a JSON backup to preserve worlds, images, and notes; importing adds worlds rather than overwriting them.

All data is stored in the browser's IndexedDB for this local address and browser profile. Clearing site data, changing browser profiles, or changing the port can make it unavailable; export backups. The app makes no network requests apart from loading its own files from localhost. Local-only storage does not protect your notes from other users or software with access to your browser profile or backups.

## Live position

Start the game and use `python3 server.py` instead of `python3 -m http.server`. If an older server is running on port 8765, stop it first. The server reads your local player coordinates from the running game process in read-only mode and listens only on 127.0.0.1. It does not inject code or write to the game. The tracker recognizes only Steam build 26781824 / CL127004; game updates will disable it until its offsets are checked. Linux process access restrictions may prevent the reader from opening the game; the status line reports this.

The current map uses the game's terrain tile metadata to calculate a player position automatically. The view starts zoomed in and follows the player; dragging or pressing Fit turns following off, and Follow me turns it back on. There is no manual alignment step. The axis orientation was cross-checked against an independently mapped reference and compared with the player’s reported location near the landing pod. Fine-grained placement has not yet been verified against the in-game map. If you previously saved markers on the older QA map, that world stays on the old image to keep those markers in place. A separate **Live map** world is created for the new terrain image. Live tracking is shown on worlds using the terrain image, not on old or custom images.

The tracker was tested reading a live client under Proton; the on-map placement still requires confirmation against the in-game map. Save a backup before clearing browser data. No map calibration or notes are sent to the game or other players.

## Nearby discoveries

While the app is open and tracking on the included terrain map, it scans approximately every 10 seconds for supported gatherable actors within 100 metres of your player. Discoveries are saved in the selected world's browser data, remain after you leave, and are included in exports. Colored markers and labels show resource types, with a matching legend in the sidebar. Click a marker for its details; use Show names on map to hide labels when they overlap. A faded square means the client reported it depleted when last observed. A normal square does not guarantee it is currently available. Use the checkbox to hide discoveries or Clear to remove them from the selected world; nearby items may be rediscovered on the next scan.

The reader identifies Hydrobulb, Polifruit, Oxallop, Purplant, Serpent Root, Prickler, Prism Herb, Sulheart, Star Tears, Grubbler, Glowcap, Vulpir and Coralion eggs, supported ore chunks (including Ignitium and Quartz), and supported ground ore sockets when those objects are loaded in the client. Some types have not been encountered in a live test; classes not explicitly recognized are skipped. Detection depends on objects loaded and replicated to your client; other resources and distant, unloaded objects are not comprehensive. It does not use line of sight and may mark a resource behind terrain. Locations and depletion are snapshots, not guarantees that an item remains present. Discoveries are local to this browser profile and selected world. The reader only supports CL127004, and stores no discoveries in the game.

Ground ore discovery also reads nearby extractor socket positions. A bundled text-only coordinate catalog from [MapExtension_Plugin](https://github.com/Mralexandresys/MapExtension_Plugin) identifies matching Calcium, Goethite, Helium-3, Sulphur, Titanium and Wolfram sockets. The catalog is only used to name a socket observed in the running client within 100 m. Unmatched or ambiguous sockets remain labeled as unknown; their current availability and purity are not established. Catalog data is derived from game assets, may be stale after updates, and is provided with attribution in ORE-CATALOG-LICENSE.txt.

Google Material Icons are bundled locally under the Apache 2.0 license; see assets/MATERIAL-ICONS-LICENSE.txt. Resource names and colors remain available in the legend, and Show names on map controls the labels. Zoom now reaches 2000%; image detail is limited by the extracted terrain map resolution.

Meteorite bodies are tracked separately from loose mineral chunks. The reader identifies loaded descendants of the game's `CrMeteOreActor` class within the normal 100-metre radius. The depletion flag is a last-observed state, and a saved meteorite marker can become stale after it is harvested or the world changes. Meteorites can contain several different resources, so their individual minerals are not inferred from the body marker.

The small player marker points in the horizontal direction of your current camera/control rotation. If the game does not supply a valid angle, the app falls back to a dot. The map itself stays north-up while following your position.

## Objectives and landmarks

The Objectives & landmarks checkbox controls the entire layer and remembers its on/off setting locally. When enabled, the app reads tutorial objective status from the live game and displays active tutorial objective names and any counters available. The text comes from the installed game's CL127004 objective table. The current reader does not map a live objective to a destination or cover every type of game objective.

Nearby fixed landmarks (abandoned bases, caves, geo scanners, monoliths, the Forgotten Engine and lander) appear as separate blue markers when within 100 metres, then remain saved in the current world. They are reference locations, not necessarily active objective destinations. The landmark coordinate catalog is game-derived from the public MapExtension_Plugin project and may become stale; the existing ORE-CATALOG-LICENSE.txt contains the project license. The layer does not read or write in-game markers, and disabling it stops its objective and landmark polling.

## Map controls

Use **Filters** beside the zoom controls to show or hide objectives, landmarks, nearby discoveries and resource names, and to see the resource legend. **Notes** collapses or reopens the left panel; the app remembers that choice. Objective status remains visible over the map when its layer is enabled.

Nearby buildings are read from the running client within approximately 100 metres and saved locally per world. The layer currently tracks confirmed standalone Solar Generators, Habitats, Ore Excavators, Smelters and Fabricators; stations, airlocks, platforms, stairs, ramps, rails and other individual pieces are excluded. Use Filters to turn the layer on or off and select building categories. Solid icons were observed in the latest scan; faded icons are last-known locations and may have been moved or removed. You can hide or clear remembered buildings. Only actors loaded by your client are detectable, and attached building roots are skipped when their world positions cannot be determined. Scanning is read-only and supports the same game build as live position tracking.

Click a Habitat marker and enter and save a private local name. Hover over the icon to see its name at the pointer. Names are included in world backups and are removed if you clear remembered buildings.

The current remote server is associated with James World using a local hash of its IP address and port, obtained from the latest game connection log while the client is connected. The map switches to that world on connection; discoveries pause when another world is selected or the server cannot be identified. This association is tied to the address and may need updating if it changes. World data is saved to the browser immediately when changed and also checkpointed every 30 seconds while the page is open. Server mappings are local to this installation; world backups include their associated hash.

The title-bar rupture timer uses the game's replicated next wave-phase deadline and server clock. It counts down to the next reported phase, which is not necessarily the moment of fire-wave impact; a paused or unavailable timer is shown as such. Wave frequency can be changed by world settings, so the app does not assume a fixed maximum interval.

The timer shows WF (the world's replicated fire-wave frequency: Rarely, Normal or Often). A red glow surrounds the map at five minutes remaining, and a translucent red tint covers it at two minutes. These warnings refer to the next reported wave phase, which may precede or differ from the fire-wave impact.

Zip-rail routes appear as cyan lines under Filters. The tracker samples nearby loaded zip-rail spline geometry within approximately 100 metres and saves it per world. Solid lines were observed in the latest scan; dashed lines are last-known and may no longer exist. Use Clear to remove remembered routes. Only supported zip-rail spline pieces with validated root transforms are drawn; other zipline types and unloaded or unsupported segments may be missing. Lines use the game's recorded geometry rather than guessing connections based on proximity.

The wave countdown follows the game's clock rather than assuming it advances at the same rate as real time. If the client clock stops updating, the displayed time holds at its last confirmed value and the header says CLOCK NOT UPDATING; it resumes when new clock data arrives. Small clock corrections do not make the display jump backward, while larger corrections and new wave phases can change it.

Abandoned bases and infection cysts have separate switches under Filters. The base markers use the named coordinate catalog and the current world's replicated base records; hover or click a marker for foundable, blueprint chest, story item, and infection cyst completion totals. Cyst markers are read from supported loaded game actors and include the replicated destruction flag where available. Faded icons indicate last-known or destroyed data. Only objects loaded by the client can be mapped; dynamic or unsupported cyst types may be missing. Both data sets are stored locally per selected world and included in backups.
