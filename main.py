import zlib
import struct
import math
import random
import binascii
import os

# Specification Constants
WIDTH, HEIGHT = 1024, 1024
SKY_TOP = (8, 10, 32)
SKY_MID = (13, 16, 44)
SKY_BOTTOM = (18, 20, 56)
SEA_TOP = (6, 8, 24)
SEA_BOTTOM = (4, 6, 18)
HORIZON_LINE = (28, 34, 66)
CLOUD_DARK = (31, 39, 66)
CLOUD_BASE = (39, 49, 79)
CLOUD_LIGHT = (46, 58, 94)
CLOUD_RIM_LIGHT = (61, 74, 117)
CLOUD_SHADOW = (22, 28, 51)
EYE_GLOW_TARGET = (27, 110, 122)
EYE_DISC = (53, 242, 200)
EYE_SOCKET = (10, 14, 36)
EYE_IRIS = (18, 230, 208)
EYE_PUPIL = (4, 16, 30)
EYE_GLINT = (232, 255, 249)
EYE_RIM_RING = (143, 255, 224)
LIGHTNING_GLOW = (27, 143, 168)
LIGHTNING_CORE = (234, 246, 255)
RAIN = (42, 51, 80)
SAIL_RED = (255, 92, 92)
SAIL_WHITE = (232, 238, 245)
HULL = (26, 32, 56)
MAST = (90, 100, 140)
WAKE = (40, 50, 90)

# Canvas
rows = [bytearray(WIDTH * 3) for _ in range(HEIGHT)]

def blend(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def fill_span(y, x0, x1, col):
    if not (0 <= y < HEIGHT): return
    x0, x1 = max(0, min(WIDTH, int(x0))), max(0, min(WIDTH, int(x1)))
    if x0 >= x1: return
    row = rows[y]
    for i in range(x0, x1):
        row[i*3:i*3+3] = bytes(col)

def fill_circle(cx, cy, r, col):
    for y in range(max(0, int(cy-r)), min(HEIGHT, int(cy+r+1))):
        dy = y - cy
        dx = math.sqrt(max(0, r*r - dy*dy))
        fill_span(y, cx - dx, cx + dx, col)

def draw_line(x0, y0, x1, y1, col, thick):
    dx, dy = x1 - x0, y1 - y0
    steps = int(max(abs(dx), abs(dy))) + 1
    for i in range(steps):
        t = i / steps
        x, y = x0 + dx * t, y0 + dy * t
        fill_circle(x, y, thick / 2, col)

def draw_bezier(p0, p1, p2, col, thick):
    # Quadratic bezier
    # n = int(chord * 2) + 8
    # Dense sampling
    # P(t) = (1-t)^2 P0 + 2(1-t)t P1 + t^2 P2
    chord = math.sqrt((p2[0]-p0[0])**2 + (p2[1]-p0[1])**2)
    n = int(chord * 2) + 8
    for i in range(n):
        t = i / (n-1)
        x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
        y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
        fill_circle(x, y, thick / 2, col)

def fill_polygon(pts, col):
    min_y = min(p[1] for p in pts)
    max_y = max(p[1] for p in pts)
    for y in range(min_y, max_y + 1):
        intersections = []
        for i in range(len(pts)):
            p1 = pts[i]
            p2 = pts[(i+1)%len(pts)]
            if min(p1[1], p2[1]) <= y < max(p1[1], p2[1]):
                # intersection x
                x = p1[0] + (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                intersections.append(x)
        intersections.sort()
        for i in range(0, len(intersections), 2):
            if i + 1 < len(intersections):
                fill_span(y, intersections[i], intersections[i+1], col)

def main():
    # 1. Sky
    for y in range(HEIGHT):
        if y < 0.6 * HEIGHT:
            t = y / (0.6 * HEIGHT)
            col = blend(SKY_TOP, SKY_MID, t)
        else:
            t = (y - 0.6 * HEIGHT) / (0.4 * HEIGHT)
            col = blend(SKY_MID, SKY_BOTTOM, t)
        fill_span(y, 0, WIDTH, col)

    # 2. Sea
    for y in range(830, HEIGHT):
        t = (y - 830) / (HEIGHT - 830)
        col = blend(SEA_TOP, SEA_BOTTOM, t)
        fill_span(y, 0, WIDTH, col)
    fill_span(830, 0, WIDTH, HORIZON_LINE)
    fill_span(831, 0, WIDTH, (22, 28, 56))

    # 3. Rain
    rng = random.Random(31337)
    for _ in range(150):
        x, y = rng.uniform(0, WIDTH), rng.uniform(420, 1000)
        length = rng.uniform(14, 30)
        for i in range(int(length)):
            px, py = int(x - i//4), int(y + i)
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                fill_span(py, px, px+1, RAIN)

    # 4. Eye glow (BEHIND the coil)
    # 12 concentric ellipse bands
    for k in range(12):
        q = 1 - k/12
        r = 215 * q
        bf = 0.38 * (1 - q)**1.4
        # Need to get sky row colour.
        # This is tricky because the sky is already drawn.
        # I can just sample it from the rows.
        col = blend(tuple(rows[420][:3]), EYE_GLOW_TARGET, bf)
        fill_circle(512, 420, r, col)

    # 5. Coil
    # Spiral geometry
    samples = []
    for i in range(201):
        f = i / 200
        theta = math.radians(90 + f * 1.3 * 360)
        r_spiral = 300 - f * 150
        x = 512 + r_spiral * math.cos(theta)
        y = 420 + r_spiral * math.sin(theta)
        arm_width = 62 - f * 18
        samples.append((x, y, arm_width))

    # Body
    for s in samples:
        fill_circle(s[0], s[1], s[2], CLOUD_BASE)

    # Cloud texture
    rng_cloud = random.Random(20261112)
    for i in range(0, 201, 30):
        s = samples[i]
        jx, jy = rng_cloud.uniform(-15, 15), rng_cloud.uniform(-15, 15)
        fill_circle(s[0] + jx, s[1] + jy, s[2] * 1.1, blend(CLOUD_BASE, CLOUD_LIGHT, 0.4))

    # Rim light / shadow
    for s in samples:
        dx, dy = s[0] - 512, s[1] - 420
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0:
            ux, uy = dx/dist, dy/dist
            fill_circle(s[0] + ux * 0.62 * s[2], s[1] + uy * 0.62 * s[2], 9, CLOUD_RIM_LIGHT)
            fill_circle(s[0] - ux * 0.62 * s[2], s[1] - uy * 0.62 * s[2], 9, CLOUD_SHADOW)

    # 6. Eye
    fill_circle(512, 420, 112, EYE_DISC)
    fill_circle(512, 420, 96, EYE_SOCKET)
    fill_circle(512, 420, 88, EYE_IRIS)
    fill_circle(512, 420, 48, EYE_PUPIL)
    fill_circle(482, 386, 14, EYE_GLINT)
    fill_circle(494, 398, 5, EYE_GLINT)

    # 7. Lightning
    lightning_pts = [(430, 640), (408, 690), (438, 730), (402, 775), (428, 812), (404, 845)]
    for i in range(len(lightning_pts)-1):
        draw_line(lightning_pts[i][0], lightning_pts[i][1], lightning_pts[i+1][0], lightning_pts[i+1][1], LIGHTNING_GLOW, 11)
        draw_line(lightning_pts[i][0], lightning_pts[i][1], lightning_pts[i+1][0], lightning_pts[i+1][1], LIGHTNING_CORE, 3)

    # 8. Boat (scale 1.5)
    fill_polygon([(476, 936), (548, 936), (536, 960), (488, 960)], HULL)
    draw_line(512, 936, 512, 891, MAST, 3)
    # Red: (514, 894), (514, 934), (557, 934)
    fill_polygon([(514, 894), (514, 934), (557, 934)], SAIL_RED)
    # White: (510, 900), (510, 934), (479, 934)
    fill_polygon([(510, 900), (510, 934), (479, 934)], SAIL_WHITE)
    # Wake
    fill_span(966, 467, 557, WAKE)

    # Write PNG
    compressed = zlib.compress(b''.join([b'\x00' + row for row in rows]), 9)
    def chunk(type, data):
        length = len(data)
        crc = binascii.crc32(type + data) & 0xFFFFFFFF
        return struct.pack('>I4s', length, type) + data + struct.pack('>I', crc)
    
    ihdr = struct.pack('>IIBBBBB', WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')
    
    out_dir = os.getenv('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'entry.png'), 'wb') as f:
        f.write(png)

if __name__ == '__main__':
    main()
