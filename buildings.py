"""Read nearby placed-building actors from the supported StarRupture client."""
import math
import os
import re
import struct
import rails

# Only confirmed standalone buildings; do not collect stations or construction pieces.
STANDALONE_BUILDINGS = {'BP_SolarPowerGenerator_C', 'BP_HabitatSmall_C', 'BP_HabitatBig_C', 'BP_MechanicalDrill_C', 'BP_Smelter_C', 'BP_Crafter_C'}

# Explicit names are used where internal class names are less readable.
NAMES = {
    'BP_BaseCore_C': 'Base Core', 'BP_SolarPowerGenerator_C': 'Solar Generator',
    'BP_Exporter_C': 'Orbital Cargo Launcher', 'BP_Smelter_C': 'Smelter',
    'BP_Crafter_C': 'Fabricator', 'BP_Analyzer_C': 'Analyzing Station',
    'BP_ResearchTerminal_C': 'Corporate Terminal', 'BP_RecipeTable_C': 'Recipe Station',
    'BP_ItemPrinter_C': 'Basic Item Printer', 'BP_MechanicalDrill_C': 'Ore Excavator',
    'BP_HabitatSmall_C': 'Habitat', 'BP_HabitatBig_C': 'Habitat', 'BP_Airlock_C': 'Airlock',
    'BP_DroneRailT1_C': 'Drone Rail', 'BP_PersonalStorage_C': 'Personal Storage',
    'BP_Modular_ConnectingPlatformStability_C': 'Foundation',
    'BP_Modular_ConnectingPlatform_C': 'Platform', 'BP_Modular_BasePlatform_C': 'Base Platform',
    'BP_Modular_Stairs_C': 'Stairs', 'BP_VerticalBridge_C': 'Vertical Bridge',
}

def categorize(classname):
    name = classname.lower()
    if any(t in name for t in ('modular_', 'platform', 'foundation', 'stair', 'viewport', 'wall', 'roof', 'window', 'bridge', 'ladder', 'pillar', 'floor')):
        return 'Structures'
    if any(t in name for t in ('dronerail', 'dronepole', 'transport', 'conveyor', 'zipline', 'dispatcher', 'receiver', 'exporter', 'cargo')):
        return 'Logistics'
    if any(t in name for t in ('solar', 'power', 'generator', 'battery', 'reactor', 'electric')):
        return 'Power'
    if any(t in name for t in ('smelter', 'crafter', 'fabricator', 'refinery', 'drill', 'excavator', 'extractor', 'analyzer', 'production')):
        return 'Production'
    if any(t in name for t in ('basecore', 'habitat', 'airlock', 'terminal', 'recipetable', 'printer', 'storage', 'armory', 'bed')):
        return 'Facilities'
    return 'Other'

def friendly_name(classname):
    if classname in NAMES:
        return NAMES[classname]
    name = re.sub(r'^(?:BP_|BPP_)', '', classname)
    name = re.sub(r'_C$', '', name).replace('_', ' ')
    name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
    return name.strip() or 'Building'

def scan(fd, base, player, radius_m=100, scan_rails=False, scan_cysts=False, scan_drops=False):
    def read(addr, size):
        if not 0x10000 <= addr < 0x7fffffffffff:
            return b''
        try:
            return os.pread(fd, size, addr)
        except OSError:
            return b''
    def u64(addr):
        data = read(addr, 8)
        return struct.unpack('<Q', data)[0] if len(data) == 8 else 0
    def i32(addr):
        data = read(addr, 4)
        return struct.unpack('<i', data)[0] if len(data) == 4 else 0
    pool = base + 0xDFE7000 + 2678336
    name_cache = {}
    def name(idx):
        if idx in name_cache:
            return name_cache[idx]
        if not 0 <= idx <= 0x1ffffff:
            return ''
        chunk = u64(pool + 0x10 + (idx >> 16) * 8)
        address = chunk + 2 * (idx & 65535)
        header = read(address, 2)
        if len(header) != 2:
            return ''
        header = struct.unpack('<H', header)[0]
        length = header >> 6
        if not 0 < length <= 150:
            return ''
        try:
            value = read(address + 2, length * (2 if header & 1 else 1)).decode('utf-16le' if header & 1 else 'utf-8')
        except UnicodeError:
            value = ''
        name_cache[idx] = value
        return value
    class_cache = {}
    def classify(cls):
        if cls in class_cache:
            return class_cache[cls]
        current, seen, chain = cls, set(), []
        while current and current not in seen and len(seen) < 32:
            seen.add(current)
            cn = name(i32(current + 0x18))
            if not cn:
                break
            chain.append(cn)
            if cn == 'CrBuildingActorBase':
                break
            current = u64(current + 0x40)
        classname = chain[0] if chain else ''
        # Pre-placed ruins and the starting lander are not player-built structures.
        ignore = any(part in classname.lower() for part in ('abandonedbase', 'startinghub', 'startingitemprinter', '_lander'))
        result = ('CrBuildingActorBase' in chain and not ignore, classname)
        class_cache[cls] = result
        return result
    world = u64(base + 0x0E0236D0)
    levels, count = u64(world + 0x1c8), i32(world + 0x1d0)
    if not 0 < count < 5000:
        raise RuntimeError('World levels are unavailable')
    result, seen, keys = [], set(), set()
    skipped_attached = 0
    for index in range(count):
        level = u64(levels + index * 8)
        actors, n = u64(level + 0xa0), i32(level + 0xa8)
        if not 0 < n < 100000:
            continue
        data = read(actors, n * 8)
        if len(data) != n * 8:
            continue
        for (actor,) in struct.iter_unpack('<Q', data):
            if not actor or actor in seen:
                continue
            seen.add(actor)
            is_building, classname = classify(u64(actor + 0x10))
            if scan_drops:
                if classname not in ('BP_DeathDropItem_C','BP_DeathDropItem_Scientist_C','BP_DeathDropItem_Soldier_C','BP_DeathDropItem_Medic_C','BP_DeathDropItem_Engineer_C'):
                    continue
                root=u64(actor+0x1b8)
                if not root or u64(root+0xc8):continue
                raw=read(root+0x140,24)
                if len(raw)!=24:continue
                x,y,z=struct.unpack('<ddd',raw)
                if not all(math.isfinite(v) and abs(v)<1e7 for v in (x,y,z)):continue
                result.append({'key':f'deathdrop:{round(x/100)}:{round(y/100)}:{round(z/100)}','x':x,'y':y,'z':z})
                continue
            if scan_cysts:
                if classname not in ('BP_InfectionCyst_C', 'BP_InfectionCyst_WorldExterior_C', 'BP_StandaloneInfectionCyst_C'):
                    continue
                root=u64(actor+0x1b8)
                if not root or u64(root+0xc8):continue
                raw=read(root+0x140,24)
                if len(raw)!=24:continue
                x,y,z=struct.unpack('<ddd',raw)
                if not all(math.isfinite(v) and abs(v)<1e7 for v in (x,y,z)) or math.hypot(x-player['x'],y-player['y'])>radius_m*100:continue
                if classname == 'BP_StandaloneInfectionCyst_C':
                    key=f'standalone:{round(x/100)}:{round(y/100)}:{round(z/100)}';destroyed=None
                else:
                    guid=read(actor+0x388,16);flag=read(actor+0x3b8,1)
                    if len(guid)!=16 or not any(guid) or len(flag)!=1 or flag[0] not in (0,1):continue
                    key='-'.join(f'{v:08X}' for v in struct.unpack('<4I',guid));destroyed=bool(flag[0])
                if key not in keys:
                    keys.add(key);result.append({'key':key,'x':round(x,1),'y':round(y,1),'z':round(z,1),'destroyed':destroyed})
                continue
            if scan_rails:
                if classname == 'BP_ZipRail_C':
                    route = rails.extract(read, u64, i32, actor, player, radius_m)
                    if route and route['key'] not in keys:
                        keys.add(route['key']); result.append(route)
                continue
            if not is_building or classname not in STANDALONE_BUILDINGS:
                continue
            root = u64(actor + 0x1b8)
            # A relative location isn't a world position for an attached root.
            if u64(root + 0xc8):
                skipped_attached += 1
                continue
            raw = read(root + 0x140, 24)
            if len(raw) != 24:
                continue
            x, y, z = struct.unpack('<ddd', raw)
            if not all(math.isfinite(v) and abs(v) < 1e7 for v in (x, y, z)):
                continue
            if math.hypot(x - player['x'], y - player['y']) > radius_m * 100:
                continue
            key = f'{classname}:{round(x / 100)}:{round(y / 100)}:{round(z / 100)}'
            if key in keys:
                continue
            keys.add(key)
            result.append({'key': key, 'type': friendly_name(classname), 'category': categorize(classname),
                           'x': round(x, 1), 'y': round(y, 1), 'z': round(z, 1)})
    return {'ok': True, ('drops' if scan_drops else ('cysts' if scan_cysts else ('routes' if scan_rails else 'buildings'))): result, 'radius_m': radius_m, 'skipped_attached': skipped_attached}
