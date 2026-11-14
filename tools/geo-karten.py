"""Erzeugt Lagekarten (SVG) für den Geo-Stapel aus Natural-Earth-Daten.
Aufruf: python3 -I tools/geo-karten.py <natural-earth-ordner> <ausgabe-ordner>"""
import json, math, os, sys

NE, OUT = sys.argv[1], sys.argv[2]
_cache = {}
def load(name):
    if name not in _cache:
        with open(os.path.join(NE, name + '.geojson'), encoding='utf-8') as f:
            _cache[name] = json.load(f)['features']
    return _cache[name]

# ---------- Farben ----------
SEA, LAND, LAND_HI, BORDER, RIVER, TXT, MUTED = '#cfe5f2', '#f4f0e6', '#fde3bd', '#b3aa98', '#79b0d3', '#22313d', '#6b7a86'
OR, OR_D = '#f39a2b', '#b8681a'

# ---------- Projektion (Lambert, flächentreu) ----------
class Map:
    def __init__(self, lon0, lat0, lon1, lat1, W=820):
        self.c = ((lon0 + lon1) / 2, (lat0 + lat1) / 2)
        pts = [self.raw(lon0 + (lon1 - lon0) * i / 20, lat) for i in range(21) for lat in (lat0, lat1)] + \
              [self.raw(lon, lat0 + (lat1 - lat0) * i / 20) for i in range(21) for lon in (lon0, lon1)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        self.x0, self.y1 = min(xs), max(ys)
        self.s = W / (max(xs) - self.x0)
        self.W, self.H = W, round((max(ys) - min(ys)) * self.s)
        self.parts = []
    def raw(self, lon, lat):
        l0, p0 = map(math.radians, self.c); l, p = math.radians(lon), math.radians(lat)
        k = math.sqrt(2 / (1 + math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(l - l0)))
        return k * math.cos(p) * math.sin(l - l0), k * (math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l - l0))
    def P(self, lon, lat):
        x, y = self.raw(lon, lat)
        return (x - self.x0) * self.s, (self.y1 - y) * self.s

# ---------- Geometrie-Helfer ----------
def dp(pts, tol):
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop(); ax, ay = pts[a]; bx, by = pts[b]; dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy) or 1e-9
        best, bi = -1, -1
        for i in range(a + 1, b):
            d = abs(dy * (pts[i][0] - ax) - dx * (pts[i][1] - ay)) / L
            if d > best: best, bi = d, i
        if best > tol: keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]

def clip_poly(pts, xmin, ymin, xmax, ymax):
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            cur, prev = pts[i], pts[i - 1]
            if inside(cur):
                if not inside(prev): out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev): out.append(inter(prev, cur))
        return out
    def ix(x):  return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / ((b[0] - a[0]) or 1e-9))
    def iy(y):  return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / ((b[1] - a[1]) or 1e-9), y)
    for inside, inter in ((lambda p: p[0] >= xmin, ix(xmin)), (lambda p: p[0] <= xmax, ix(xmax)),
                          (lambda p: p[1] >= ymin, iy(ymin)), (lambda p: p[1] <= ymax, iy(ymax))):
        if not pts: break
        pts = clip(pts, inside, inter)
    return pts

def area(pts): return abs(sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))) / 2
def f1(v): return ('%.1f' % v).rstrip('0').rstrip('.')
def d_of(pts, close):
    return 'M' + 'L'.join(f1(x) + ',' + f1(y) for x, y in pts) + ('Z' if close else '')

def rings(geom):
    t, c = geom['type'], geom['coordinates']
    if t == 'Polygon': return c
    if t == 'MultiPolygon': return [r for poly in c for r in poly]
    return []
def lines(geom):
    t, c = geom['type'], geom['coordinates']
    return [c] if t == 'LineString' else c if t == 'MultiLineString' else []

def poly_path(m, feats, tol=0.6, minarea=3, pad=20):
    out = []
    for f in feats:
        for r in rings(f['geometry']):
            pts = [m.P(*p[:2]) for p in r]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            if max(xs) < -pad or min(xs) > m.W + pad or max(ys) < -pad or min(ys) > m.H + pad: continue
            pts = clip_poly(pts, -pad, -pad, m.W + pad, m.H + pad)
            if len(pts) < 3: continue
            h = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
            pts = dp(pts[:h + 1], tol)[:-1] + dp(pts[h:] + [pts[0]], tol)[:-1]
            if len(pts) >= 3 and area(pts) >= minarea: out.append(d_of(pts, True))
    return ''.join(out)

def line_path(m, feats, tol=0.6, pad=20):
    out = []
    for f in feats:
        for ln in lines(f['geometry']):
            seg = []
            for p in ln:
                x, y = m.P(*p[:2])
                if -pad <= x <= m.W + pad and -pad <= y <= m.H + pad: seg.append((x, y))
                else:
                    if len(seg) > 1: out.append(d_of(dp(seg, tol), False))
                    seg = []
            if len(seg) > 1: out.append(d_of(dp(seg, tol), False))
    return ''.join(out)

def lonlat_path(m, pts, close=False): return d_of([m.P(*p) for p in pts], close)

# ---------- Grundkarte ----------
def base(m, land='ne_10m_land', borders='ne_10m_admin_0_boundary_lines_land', rivers=(), lakes=True, tol=0.6):
    m.parts.append(f'<rect width="{m.W}" height="{m.H}" fill="{SEA}"/>')
    m.parts.append(f'<path d="{poly_path(m, load(land), tol)}" fill="{LAND}" stroke="#9fb9c9" stroke-width="0.8" stroke-linejoin="round"/>')
    if lakes:
        lk = [f for f in load('ne_10m_lakes') if (f['properties'].get('scalerank') or 9) <= 6]
        m.parts.append(f'<path d="{poly_path(m, lk, tol, 6)}" fill="{SEA}" stroke="#9fb9c9" stroke-width="0.6"/>')
    if rivers:
        rv = [f for name in ('ne_10m_rivers_lake_centerlines', 'ne_10m_rivers_europe') for f in load(name)
              if (f['properties'].get('name') or '') in rivers]
        m.parts.append(f'<path d="{line_path(m, rv, tol)}" fill="none" stroke="{RIVER}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
    if borders:
        m.parts.append(f'<path d="{line_path(m, load(borders), tol)}" fill="none" stroke="{BORDER}" stroke-width="1" stroke-dasharray="4 3"/>')

def country(name, src='ne_50m_admin_0_countries'):
    return [f for f in load(src) if f['properties'].get('ADMIN') == name or f['properties'].get('NAME_DE') == name]

def text(m, lon, lat, s, dx=0, dy=0, anchor='middle', size=15, color=TXT, weight=400, italic=False, halo=True):
    x, y = m.P(lon, lat)
    h = ' stroke="#fff" stroke-width="3.5" stroke-linejoin="round" paint-order="stroke"' if halo else ''
    it = ' font-style="italic"' if italic else ''
    m.parts.append(f'<text x="{f1(x + dx)}" y="{f1(y + dy)}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{color}"{it}{h}>{s}</text>')

def sea(m, lon, lat, s, size=15): text(m, lon, lat, s, size=size, color='#4f7f9c', italic=True, halo=False)

def dot(m, lon, lat, r=4, fill='#8a97a2'):
    x, y = m.P(lon, lat); m.parts.append(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{r}" fill="{fill}" stroke="#fff" stroke-width="1.5"/>')

def target(m, lon, lat, label, dx=12, dy=5, anchor='start', size=19):
    x, y = m.P(lon, lat)
    m.parts.append(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="15" fill="{OR}" opacity=".25"/>'
                   f'<circle cx="{f1(x)}" cy="{f1(y)}" r="7" fill="{OR}" stroke="#fff" stroke-width="2.5"/>')
    if label: text(m, lon, lat, label, dx + (6 if anchor == 'start' else -6 if anchor == 'end' else 0), dy, anchor, size, OR_D, 750)

def save(m, fname, note=None):
    parts = list(m.parts)
    if note: parts.append(f'<text x="{m.W - 10}" y="{m.H - 10}" text-anchor="end" font-size="12" fill="{MUTED}">{note}</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {m.W} {m.H}" font-family="-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">'
           f'<defs><clipPath id="r"><rect width="{m.W}" height="{m.H}" rx="18"/></clipPath></defs><g clip-path="url(#r)">'
           + ''.join(parts) + '</g></svg>')
    with open(os.path.join(OUT, fname), 'w', encoding='utf-8') as f: f.write(svg)
    print(fname, m.W, 'x', m.H, round(len(svg) / 1024), 'KB')

# ================= Nordrange / Häfen =================
PORTS = {  # name: (lon, lat, Fluss/Zusatz, dx, dy, anchor)
    'Hamburg': (9.97, 53.54, 'Elbe', 12, 5, 'start'),
    'Cuxhaven': (8.70, 53.87, 'Elbmündung', 12, -4, 'start'),
    'Bremerhaven': (8.58, 53.55, 'Weser', 12, 14, 'start'),
    'Wilhelmshaven': (8.13, 53.52, 'Jadebusen', -12, 18, 'end'),
    'Emden': (7.20, 53.36, 'Ems', -12, 20, 'middle'),
    'Amsterdam': (4.90, 52.37, 'Nordseekanal', 12, 5, 'start'),
    'Rotterdam': (4.15, 51.95, 'Maas / Maasvlakte', -12, -8, 'end'),
    'Antwerpen': (4.40, 51.22, 'Schelde', 12, 5, 'start'),
    'Duisburg': (6.76, 51.43, 'Rhein + Ruhr', 12, 5, 'start'),
    'Le Havre': (0.11, 49.49, 'Seinemündung', -6, -16, 'middle'),
    'Rouen': (1.09, 49.44, 'Seine', 12, 5, 'start'),
    'Dover': (1.32, 51.12, 'Straße von Dover', -12, 18, 'end'),
    'Felixstowe': (1.33, 51.96, '', -12, -6, 'end'),
    'Southampton': (-1.40, 50.90, 'Solent', -2, -16, 'middle'),
}
NR_RIVERS = ('Elbe', 'Weser', 'Ems', 'Rhein', 'Rhine', 'Maas', 'Schelde', 'Seine', 'Thames', 'Ruhr')
def nr_map():
    m = Map(-2.2, 48.9, 11.4, 54.9)
    base(m, rivers=NR_RIVERS)
    sea(m, 3.6, 53.9, 'Nordsee', 20); sea(m, -0.8, 50.25, 'Ärmelkanal', 15)
    text(m, 9.6, 52.3, 'DEUTSCHLAND', size=13, color=MUTED, weight=600, halo=False)
    text(m, 5.75, 52.65, 'NL', size=13, color=MUTED, weight=600, halo=False)
    text(m, 4.7, 50.65, 'BELGIEN', size=13, color=MUTED, weight=600, halo=False)
    text(m, 2.7, 49.6, 'FRANKREICH', size=13, color=MUTED, weight=600, halo=False)
    text(m, -0.7, 52.2, 'ENGLAND', size=13, color=MUTED, weight=600, halo=False)
    return m

def port_maps():
    for name, (lon, lat, sub, dx, dy, anc) in PORTS.items():
        m = nr_map()
        for o, v in PORTS.items():
            if o != name: dot(m, v[0], v[1], 3.5)
        target(m, lon, lat, name, dx, dy, anc)
        if sub: text(m, lon, lat, sub, dx + (6 if anc == 'start' else -6 if anc == 'end' else 0), dy + 18, anc, 13, OR_D, 500)
        save(m, 'geo-' + name.lower().replace(' ', '-') + '.svg')
    # Nordrange: alle Häfen von Le Havre bis Hamburg
    m = nr_map()
    rng = ['Le Havre', 'Antwerpen', 'Rotterdam', 'Amsterdam', 'Bremerhaven', 'Hamburg']
    m.parts.append(f'<path d="{lonlat_path(m, [(0.11, 49.49), (1.6, 50.6), (3.2, 51.33), (4.15, 51.95), (4.6, 52.46), (7.0, 53.65), (8.58, 53.55), (9.97, 53.54)])}" fill="none" stroke="{OR}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity=".55"/>')
    for o, v in PORTS.items():
        if o in rng: target(m, v[0], v[1], o, v[3], v[4], v[5], 15)
        else: dot(m, v[0], v[1], 3.5)
    text(m, 3.3, 52.9, 'Nordrange', size=22, color=OR_D, weight=800)
    text(m, 3.3, 52.9, 'Le Havre – Hamburg', 0, 20, 'middle', 13, OR_D, 500)
    save(m, 'geo-nordrange.svg')

# ================= Elbmündung (Trichtermündung) =================
def elbe_funnel():
    m = Map(7.9, 53.35, 10.25, 54.15)
    base(m, rivers=('Elbe',))
    funnel = [(8.5, 53.99), (8.95, 53.93), (9.35, 53.8), (9.75, 53.6), (10.0, 53.53), (10.0, 53.5), (9.6, 53.53), (9.2, 53.72), (8.75, 53.82), (8.5, 53.84)]
    m.parts.insert(1, f'<path d="{lonlat_path(m, funnel, True)}" fill="{OR}" opacity=".45"/>')
    target(m, 9.97, 53.54, 'Hamburg', 0, -18, 'middle', 17); target(m, 8.70, 53.87, 'Cuxhaven', -8, -16, 'end', 17)
    text(m, 9.25, 53.86, 'wird zum Meer hin immer breiter', 0, -26, 'middle', 13, OR_D, 600)
    sea(m, 8.15, 54.05, 'Nordsee', 18); text(m, 9.0, 53.47, 'Elbe', size=14, color='#3f7fa6', italic=True, halo=True)
    save(m, 'geo-elbe-trichter.svg')

# ================= Deutschland =================
DE_RIVERS = ('Rhein', 'Rhine', 'Elbe', 'Donau', 'Danube', 'Main', 'Weser', 'Ems', 'Inn', 'Isar', 'Oder')
def de_map(highlight_de=False):
    m = Map(5.4, 47.1, 15.6, 55.15, W=640)
    base(m, borders='ne_10m_admin_0_boundary_lines_land')
    de = country('Germany')
    m.parts.append(f'<path d="{poly_path(m, de)}" fill="{LAND_HI if highlight_de else "#fbf8f1"}" stroke="#8d8370" stroke-width="1.4" stroke-linejoin="round"/>')
    rv = [f for name in ('ne_10m_rivers_lake_centerlines', 'ne_10m_rivers_europe') for f in load(name) if (f['properties'].get('name') or '') in DE_RIVERS]
    m.rivers = f'<path d="{line_path(m, rv)}" fill="none" stroke="{RIVER}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
    m.parts.append(m.rivers)
    return m, de

def zugspitze():
    m, _ = de_map()
    x, y = m.P(10.98, 47.42)
    m.parts.append(f'<path d="M{f1(x)},{f1(y - 16)}L{f1(x + 13)},{f1(y + 6)}L{f1(x - 13)},{f1(y + 6)}Z" fill="{OR}" stroke="#fff" stroke-width="2"/>')
    text(m, 10.98, 47.42, 'Zugspitze', 0, -24, 'middle', 19, OR_D, 750)
    text(m, 10.98, 47.42, '2.963 m · Bayerische Alpen', 0, 24, 'middle', 13, OR_D, 500)
    save(m, 'geo-zugspitze.svg')

def zones():
    m, de = de_map()
    clip = poly_path(m, de)
    m.parts.append(f'<defs><clipPath id="de"><path d="{clip}"/></clipPath></defs>')
    north = [(5.0, 50.75), (6.6, 50.7), (7.1, 50.7), (7.4, 51.3), (8.0, 51.55), (8.5, 51.9), (8.4, 52.15), (9.0, 52.25), (9.7, 52.2), (10.3, 52.0), (10.9, 51.9), (11.5, 51.6), (12.0, 51.25), (12.6, 51.1), (13.3, 51.1), (14.0, 51.1), (16.0, 51.0)]
    danube = [(16.0, 48.4), (13.85, 48.75), (13.5, 48.57), (13.0, 48.7), (12.1, 48.95), (11.8, 48.85), (10.9, 48.73), (10.0, 48.4), (9.3, 48.1), (8.9, 47.95), (8.6, 47.68), (8.0, 47.2)]
    alps = [(8.0, 47.0), (9.6, 47.52), (10.2, 47.6), (10.7, 47.6), (11.2, 47.66), (11.8, 47.68), (12.3, 47.7), (12.75, 47.78), (13.1, 47.73), (16.0, 47.6)]
    Z = [('#cfe3b0', north[::-1] + [(5.0, 56.0), (16.0, 56.0)]),
         ('#efd9a8', north + [(16.0, 48.4)] + danube[1:] + [(8.0, 47.2), (5.0, 47.2)]),
         ('#f2c98a', danube + [(8.0, 47.0)] + alps[1:] + [(16.0, 48.4)]),
         ('#e09f5c', alps + [(16.0, 46.5), (8.0, 46.5)])]
    m.parts.append('<g clip-path="url(#de)" opacity=".9">' + ''.join(f'<path d="{lonlat_path(m, p, True)}" fill="{c}"/>' for c, p in Z) + '</g>')
    m.parts.append(f'<path d="{clip}" fill="none" stroke="#8d8370" stroke-width="1.4"/>' + m.rivers)
    text(m, 10.2, 53.0, 'Norddeutsche Tiefebene', size=16, weight=750)
    text(m, 9.7, 50.3, 'Mittelgebirgszone', size=16, weight=750)
    text(m, 11.4, 48.2, 'Alpenvorland', size=15, weight=750)
    text(m, 11.2, 47.42, 'Alpen', 0, 16, 'middle', 14, '#7a3f0d', 800)
    save(m, 'geo-landschaftszonen.svg', 'vereinfacht')

NEIGH = {'Denmark': ('Dänemark', 9.6, 54.98), 'Poland': ('Polen', 15.3, 52.6), 'Czechia': ('Tschechien', 14.6, 49.8),
         'Austria': ('Österreich', 13.4, 47.45), 'Switzerland': ('Schweiz', 7.9, 47.25), 'France': ('Frankreich', 6.2, 48.4),
         'Luxembourg': ('Lux.', 6.1, 49.75), 'Belgium': ('Belgien', 5.75, 50.45), 'Netherlands': ('Niederlande', 6.45, 52.95)}
def neighbours():
    m, _ = de_map()
    for k, (de, lon, lat) in NEIGH.items():
        f = country(k) or [x for x in load('ne_50m_admin_0_countries') if x['properties'].get('NAME') == k]
        m.parts.append(f'<path d="{poly_path(m, f)}" fill="{OR}" opacity=".28" stroke="{OR_D}" stroke-width="1"/>')
    for i, (k, (de, lon, lat)) in enumerate(NEIGH.items(), 1):
        text(m, lon, lat, f'{i} {de}', size=14, color=OR_D, weight=750)
    text(m, 10.3, 51.1, 'DEUTSCHLAND', size=15, color=TXT, weight=800)
    save(m, 'geo-nachbarlaender.svg')

def transit():
    m, _ = de_map(True)
    arrows = [[(5.6, 52.3), (14.9, 52.4)], [(9.6, 54.9), (11.0, 47.6)], [(6.0, 49.6), (14.7, 51.0)], [(14.6, 53.2), (7.6, 47.8)]]
    m.parts.append(f'<defs><marker id="ah" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0L10,5L0,10Z" fill="{OR_D}"/></marker></defs>')
    for a in arrows:
        m.parts.append(f'<path d="{lonlat_path(m, a)}" stroke="{OR_D}" stroke-width="4" fill="none" stroke-linecap="round" marker-end="url(#ah)" opacity=".85"/>')
    text(m, 10.3, 50.6, 'Transitland', size=20, color=OR_D, weight=800)
    text(m, 10.3, 50.6, 'Mittellage in Europa', 0, 20, 'middle', 13, OR_D, 500)
    save(m, 'geo-transitland.svg')

def main_donau():
    m, _ = de_map()
    canal = [(10.89, 49.89), (11.0, 49.6), (11.05, 49.43), (11.19, 49.19), (11.47, 49.03), (11.59, 49.04), (11.88, 48.92)]
    m.parts.append(f'<path d="{lonlat_path(m, canal)}" stroke="{OR}" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    dot(m, 10.89, 49.89, 4, OR_D); dot(m, 11.88, 48.92, 4, OR_D)
    text(m, 10.89, 49.89, 'Bamberg (Main)', -10, -6, 'end', 13, OR_D, 600); text(m, 11.88, 48.92, 'Kelheim (Donau)', 10, 16, 'start', 13, OR_D, 600)
    text(m, 11.4, 49.45, 'Main-Donau-Kanal', 14, 0, 'start', 16, OR_D, 800)
    text(m, 8.4, 50.2, 'Main', size=13, color='#3f7fa6', italic=True); text(m, 13.0, 48.55, 'Donau', size=13, color='#3f7fa6', italic=True)
    text(m, 7.2, 51.9, 'Rhein', size=13, color='#3f7fa6', italic=True)
    save(m, 'geo-main-donau-kanal.svg')

def nok():
    m = Map(7.7, 53.45, 11.4, 55.0)
    base(m, rivers=('Elbe',))
    canal = [(9.14, 53.89), (9.27, 54.0), (9.29, 54.06), (9.40, 54.12), (9.52, 54.2), (9.62, 54.29), (9.72, 54.30), (9.86, 54.33), (10.0, 54.36), (10.15, 54.37)]
    m.parts.append(f'<path d="{lonlat_path(m, canal)}" stroke="{OR}" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    dot(m, 9.14, 53.89, 4, OR_D); dot(m, 10.15, 54.37, 4, OR_D)
    text(m, 9.14, 53.89, 'Brunsbüttel', -10, 16, 'end', 13, OR_D, 600); text(m, 10.15, 54.37, 'Kiel', 10, 5, 'start', 13, OR_D, 600)
    text(m, 9.55, 54.22, 'Nord-Ostsee-Kanal', 14, 22, 'start', 17, OR_D, 800)
    sea(m, 8.1, 54.6, 'Nordsee', 18); sea(m, 10.9, 54.75, 'Ostsee', 18); text(m, 9.7, 53.62, 'Elbe', size=13, color='#3f7fa6', italic=True)
    save(m, 'geo-nord-ostsee-kanal.svg')

# ================= Europa =================
def eu_map():
    m = Map(-12, 34, 66, 71)
    base(m, land='ne_50m_land', borders='ne_50m_admin_0_boundary_lines_land', rivers=('Ural',), tol=0.8)
    return m

URAL_MTS = [(66.0, 68.0), (65.0, 66.5), (60.5, 64.5), (59.3, 62.0), (59.5, 59.5), (59.2, 57.0), (58.8, 55.0), (58.5, 53.5), (58.8, 52.0)]
def ural():
    m = eu_map()
    rv = [f for f in load('ne_10m_rivers_lake_centerlines') if f['properties'].get('name') == 'Ural']
    m.parts.append(f'<path d="{line_path(m, rv)}" stroke="{OR}" stroke-width="4" fill="none" stroke-linecap="round"/>')
    m.parts.append(f'<path d="{lonlat_path(m, URAL_MTS)}" stroke="{OR_D}" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1 9"/>'
                   f'<path d="{lonlat_path(m, URAL_MTS)}" stroke="{OR}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    rest = [(51.5, 46.9), (49.5, 44.5), (47.5, 43.0), (44.0, 42.8), (41.0, 43.2), (37.5, 44.5), (33.0, 43.0), (29.0, 41.2), (26.4, 40.2), (25.0, 38.5)]
    m.parts.append(f'<path d="{lonlat_path(m, rest)}" stroke="{OR_D}" stroke-width="2" fill="none" stroke-dasharray="5 4" opacity=".7"/>')
    text(m, 60.5, 60.0, 'Uralgebirge', -12, 0, 'end', 17, OR_D, 800)
    text(m, 55.0, 50.2, 'Uralfluss', 0, 0, 'middle', 15, OR_D, 750)
    text(m, 43.0, 43.0, 'Kaukasus', 0, -10, 'middle', 12, MUTED, 600)
    sea(m, 50.8, 42.0, 'Kasp. Meer', 12); sea(m, 34.0, 43.4, 'Schwarzes Meer', 12)
    text(m, 25.0, 55.0, 'EUROPA', size=20, color=MUTED, weight=800, halo=False); text(m, 62.0, 57.5, 'ASIEN', 30, 0, 'start', 18, MUTED, 800, halo=False)
    save(m, 'geo-ural.svg')

def peninsulas():
    m = eu_map()
    for s, lon, lat, anc in [('Skandinavische Halbinsel', 15.5, 64.0, 'middle'), ('Iberische Halbinsel', -4.0, 40.0, 'middle'), ('Apenninhalbinsel', 13.5, 42.3, 'end'),
                        ('Balkanhalbinsel', 21.0, 43.6, 'start'), ('Jütland', 9.0, 56.0, 'end')]:
        text(m, lon, lat, s, 0, 0, anc, 16, OR_D, 800)
    text(m, 32.0, 52.0, 'stark gegliedert:', size=13, color=MUTED, weight=600, halo=False)
    text(m, 32.0, 52.0, 'viele Buchten und Halbinseln', 0, 16, 'middle', 13, MUTED, 600, halo=False)
    save(m, 'geo-europa.svg')

def gibraltar():
    m = Map(-7.0, 35.3, -4.2, 36.9)
    base(m)
    x0, y0 = m.P(-5.62, 36.0); x1, y1 = m.P(-5.62, 35.84)
    m.parts.append(f'<path d="M{f1(x0)},{f1(y0 + 6)}L{f1(x1)},{f1(y1 - 6)}" stroke="{OR}" stroke-width="5" stroke-linecap="round" marker-start="url(#a2)" marker-end="url(#a2)"/>'
                   f'<defs><marker id="a2" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M0,0L10,5L0,10Z" fill="{OR}"/></marker></defs>')
    text(m, -5.62, 35.93, '12 km', 12, 5, 'start', 15, OR_D, 750)
    text(m, -5.6, 35.95, 'Straße von Gibraltar', -110, 0, 'end', 19, OR_D, 800)
    sea(m, -6.6, 36.0, 'Atlantik', 17); sea(m, -4.6, 36.2, 'Mittelmeer', 17)
    text(m, -5.3, 36.6, 'SPANIEN · Europa', size=14, color=MUTED, weight=700, halo=False)
    text(m, -5.3, 35.45, 'MAROKKO · Afrika', size=14, color=MUTED, weight=700, halo=False)
    dot(m, -5.35, 36.14, 3.5); text(m, -5.35, 36.14, 'Gibraltar', 8, -6, 'start', 12, MUTED, 600)
    save(m, 'geo-gibraltar.svg')

def bosporus():
    m = Map(25.4, 39.7, 30.0, 41.75)
    base(m)
    for lon, lat, s, dx, dy, a in [(29.06, 41.13, 'Bosporus', 12, 0, 'start'), (26.45, 40.15, 'Dardanellen', -14, 6, 'end')]:
        x, y = m.P(lon, lat)
        m.parts.append(f'<ellipse cx="{f1(x)}" cy="{f1(y)}" rx="26" ry="34" fill="none" stroke="{OR}" stroke-width="4"/>')
        text(m, lon, lat, s, dx + (20 if a == 'start' else -20), dy, a, 18, OR_D, 800)
    sea(m, 28.0, 40.75, 'Marmarameer', 15); sea(m, 25.8, 40.35, 'Ägäis', 15); sea(m, 29.4, 41.55, 'Schwarzes Meer', 14)
    dot(m, 28.98, 41.01, 3.5); text(m, 28.98, 41.01, 'Istanbul', -8, 16, 'end', 12, MUTED, 600)
    text(m, 27.0, 41.45, 'EUROPA', size=14, color=MUTED, weight=800, halo=False); text(m, 29.2, 40.1, 'ASIEN (Vorderasien)', size=14, color=MUTED, weight=800, halo=False)
    save(m, 'geo-bosporus-dardanellen.svg')

os.makedirs(OUT, exist_ok=True)
port_maps(); elbe_funnel(); zugspitze(); zones(); neighbours(); transit(); main_donau(); nok(); ural(); peninsulas(); gibraltar(); bosporus()
