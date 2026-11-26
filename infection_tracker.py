"""Read the local game's visible tumor counter without changing game state."""
import os, re, struct, threading, time

_lock = threading.Lock()
_cache = {'process': None, 'widget': 0, 'next_scan': 0}

def status(fd, base):
    def read(address, size):
        if not 0x10000 <= address < 0x7fffffffffff:
            return b''
        try: return os.pread(fd, size, address)
        except OSError: return b''
    def u64(address):
        data = read(address, 8)
        return struct.unpack('<Q', data)[0] if len(data) == 8 else 0
    def i32(address):
        data = read(address, 4)
        return struct.unpack('<i', data)[0] if len(data) == 4 else -1
    pool = base + 0xDFE7000 + 2678336
    names = {}
    def name(index):
        if index in names: return names[index]
        if not 0 <= index <= 0x1ffffff: return ''
        chunk = u64(pool + 0x10 + (index >> 16) * 8)
        address = chunk + 2 * (index & 65535)
        raw = read(address, 2)
        if len(raw) != 2: return ''
        header = struct.unpack('<H', raw)[0]
        length = header >> 6
        if not 0 < length <= 150: return ''
        try: result = read(address + 2, length * (2 if header & 1 else 1)).decode('utf-16le' if header & 1 else 'utf-8')
        except UnicodeError: result = ''
        names[index] = result
        return result
    def cls(obj): return name(i32(u64(obj + 0x10) + 0x18)) if obj else ''
    def objname(obj): return name(i32(obj + 0x18)) if obj else ''
    def visibility(widget):
        v = read(widget + 0xfc, 1)
        return v[0] if len(v) == 1 and v[0] <= 4 else None
    def displayed_text(widget):
        text_data = u64(widget + 0x1b0)
        ptr, length = u64(text_data + 0x20), i32(text_data + 0x28)
        if 0 < length <= 100:
            raw = read(ptr, length * 2)
        else:
            raw = read(u64(text_data + 0x18), 128)
        try: return raw.decode('utf-16le').split('\0', 1)[0].strip()
        except UnicodeError: return ''
    def widget_visible(widget):
        seen = set()
        while widget and widget not in seen and len(seen) < 32:
            seen.add(widget)
            v = visibility(widget)
            if v is None: return None
            if v in (1, 2): return False
            slot = u64(widget + 0x30)
            parent = u64(slot + 0x28) if slot else 0
            if parent and cls(parent) == 'WidgetSwitcher':
                slots, count, active = u64(parent + 0x190), i32(parent + 0x198), i32(parent + 0x1a8)
                if not 0 <= active < count <= 100: return None
                if u64(u64(slots + active * 8) + 0x30) != widget: return False
            widget = parent
        return True
    def is_live(widget):
        return (cls(widget) == 'WBP_AlienObeliskWarning_C' and
                objname(widget) == 'AlienObeliskWarning' and
                cls(u64(widget + 0x3b0)) == 'WBP_AbandonBaseCounter_C' and
                bool(u64(widget + 0x30)))
    with _lock:
        process = (base, os.fstat(fd).st_ino)
        if _cache['process'] != process: _cache.update(process=process, widget=0, next_scan=0)
        widget = _cache['widget']
        if not is_live(widget):
            widget = 0
            if time.monotonic() < _cache['next_scan']: return {'available': False}
            _cache['next_scan'] = time.monotonic() + 10
            objects = base + 0x0e359240
            chunks, count = u64(objects), i32(objects + 0x14)
            if not 0 < count <= 3000000: return {'available': False}
            candidates = []
            for chunk_idx in range((count + 65535) // 65536):
                chunk = u64(chunks + chunk_idx * 8)
                size = min(65536, count - chunk_idx * 65536)
                data = read(chunk, size * 24)
                if len(data) != size * 24: continue
                for index in range(size):
                    obj = struct.unpack_from('<Q', data, index * 24)[0]
                    if obj and is_live(obj): candidates.append(obj)
            if len(candidates) != 1: return {'available': False}
            widget = candidates[0]
            _cache['widget'] = widget
        counter = u64(widget + 0x3b0)
        visible = widget_visible(widget)
        counter_visible = widget_visible(counter)
        if visible is None or counter_visible is None: return {'available': False}
        if not visible or not counter_visible: return {'available': True, 'active': False}
        raw_count = displayed_text(u64(counter + 0x3a8))
        if not re.fullmatch(r'\d{1,4}', raw_count): return {'available': False}
        return {'available': True, 'active': True, 'tumors': int(raw_count)}
