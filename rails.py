"""Extract a nearby zip-rail's replicated spline in world coordinates."""
import math
import struct


def extract(read, u64, i32, actor, player, radius_m):
    spline = u64(actor + 0x6c8)
    if not spline or spline != u64(actor + 0x1b8) or u64(spline + 0xc8):
        return None  # Attached transforms need additional validation.
    transform = read(spline + 0x140, 72)
    if len(transform) != 72:
        return None
    x, y, z, pitch, yaw, roll, sx, sy, sz = struct.unpack('<9d', transform)
    if not all(math.isfinite(v) for v in (x, y, z, pitch, yaw, roll, sx, sy, sz)):
        return None
    # Other rotations have not been validated against this game build.
    if abs(pitch) > 0.01 or abs(roll) > 0.01 or any(abs(s - 1) > .001 for s in (sx, sy, sz)):
        return None
    count = i32(spline + 0x550)
    address = u64(spline + 0x548)
    if not 2 <= count <= 32 or not address:
        return None
    data = read(address, count * 0x58)
    if len(data) != count * 0x58:
        return None
    controls = []
    for index in range(count):
        off = index * 0x58
        key = struct.unpack_from('<f', data, off)[0]
        pos = struct.unpack_from('<3d', data, off + 8)
        arrive = struct.unpack_from('<3d', data, off + 0x20)
        leave = struct.unpack_from('<3d', data, off + 0x38)
        mode = data[off + 0x50]
        if mode not in (0, 1, 3, 4, 5) or not all(math.isfinite(v) and abs(v) < 1e7 for v in (key, *pos, *arrive, *leave)):
            return None
        controls.append((key, pos, arrive, leave, mode))
    angle = math.radians(yaw)
    cosine, sine = math.cos(angle), math.sin(angle)
    def world(v):
        return [round(x + cosine*v[0] - sine*v[1], 1), round(y + sine*v[0] + cosine*v[1], 1), round(z + v[2], 1)]
    points = []
    for a, b in zip(controls, controls[1:]):
        span = b[0] - a[0]
        if not 0 < span < 10000:
            return None
        for n in range(8):
            t = n / 8
            if a[4] == 0:
                v = [a[1][j]*(1-t) + b[1][j]*t for j in range(3)]
            else:
                h00, h10 = 2*t**3-3*t*t+1, t**3-2*t*t+t
                h01, h11 = -2*t**3+3*t*t, t**3-t*t
                v = [h00*a[1][j]+h10*span*a[3][j]+h01*b[1][j]+h11*span*b[2][j] for j in range(3)]
            points.append(world(v))
    points.append(world(controls[-1][1]))
    if not all(all(math.isfinite(v) and abs(v) < 1e7 for v in p) for p in points):
        return None
    def distance(a, b):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = dx*dx+dy*dy
        t = max(0, min(1, ((player['x']-a[0])*dx+(player['y']-a[1])*dy)/length)) if length else 0
        return math.hypot(player['x']-a[0]-t*dx, player['y']-a[1]-t*dy)
    if min(distance(a,b) for a,b in zip(points, points[1:])) > radius_m*100:
        return None
    ends = sorted(tuple(round(value/100) for value in point) for point in (points[0], points[-1]))
    return {'key': 'ziprail:' + ':'.join(str(v) for end in ends for v in end), 'points': points}
