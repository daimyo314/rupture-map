"""Read replicated abandoned-base completion records without changing the game."""
import os
import struct

CATEGORIES = ('foundables', 'blueprints', 'story', 'cysts')

def progress(fd, base, catalog):
    def read(address, size):
        if address < 0x10000 or address >= 0x7fffffffffff:
            raise RuntimeError('Base data is unavailable')
        try:
            data = os.pread(fd, size, address)
        except OSError as exc:
            raise RuntimeError('Base data is unavailable') from exc
        if len(data) != size:
            raise RuntimeError('Incomplete base data')
        return data
    def u64(addr): return struct.unpack('<Q', read(addr, 8))[0]
    def i32(addr): return struct.unpack('<i', read(addr, 4))[0]
    world = u64(base + 0x0e0236d0)
    state = u64(world + 0x1b0)
    replicator = u64(state + 0x3a8)
    records = u64(replicator + 0x3f8)
    count = i32(replicator + 0x400)
    if not 0 <= count <= 1000 or (count and not records):
        raise RuntimeError('Invalid base data')
    by_id = {v['id']: v for v in catalog if v.get('kind') == 'abandoned_base'}
    result, cyst_status = [], {}
    for index in range(count):
        address = records + index*0x78
        guid = '-'.join(f'{v:08X}' for v in struct.unpack('<4I', read(address+0xc, 16)))
        landmark = by_id.get(guid)
        if not landmark:
            continue
        counts = {}
        for category, off in zip(CATEGORIES, (0x30,0x40,0x50,0x60)):
            ptr, total = u64(address+off), i32(address+off+8)
            if not 0 <= total <= 500 or (total and not ptr):
                raise RuntimeError('Invalid base collectible data')
            data = read(ptr, total*20) if total else b''
            flags = [data[j*20+16] for j in range(total)]
            if any(flag not in (0,1) for flag in flags):
                raise RuntimeError('Invalid base collectible status')
            counts[category] = {'collected': sum(flags), 'total': total}
            if category == 'cysts':
                for j, flag in enumerate(flags):
                    cyst_id = '-'.join(f'{v:08X}' for v in struct.unpack_from('<4I', data, j*20))
                    cyst_status[cyst_id] = bool(flag)
        result.append({'id': guid, 'name': landmark['name'], 'x': landmark['x'], 'y': landmark['y'], 'counts': counts})
    return result, cyst_status
