"""Stumme Karten (zum Eintragen) für die Geo-Karten-Stapel.
Jede Karte besteht aus drei Ebenen mit gleicher viewBox:
  unten  = Meer (+ markiertes Meer)      → img/karte-<karte>-u-<id>.svg  bzw. img/karte-<karte>-meer.svg
  mitte  = Land, Flüsse, Grenzen         → img/karte-<karte>.svg (für alle Karten der Karte gleich)
  oben   = Markierung (Fluss, Hafen …)   → img/karte-<karte>-o-<id>.svg
Aufruf: python3 -I tools/stumme-karten.py <natural-earth-ordner> img"""
import importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('geo', os.path.join(HERE, 'geo-karten.py'))
geo = importlib.util.module_from_spec(spec); spec.loader.exec_module(geo)
Map, load, poly_path, line_path, lonlat_path, f1 = geo.Map, geo.load, geo.poly_path, geo.line_path, geo.lonlat_path, geo.f1
SEA, LAND, BORDER, RIVER, OR, OR_D = geo.SEA, geo.LAND, geo.BORDER, geo.RIVER, geo.OR, geo.OR_D
OUT = sys.argv[2]
CARDS = {}  # Kartenname → Liste (frage, antwort, beispiel, [ebenen])
QUIZ = {}   # Kartenname → Daten fürs Kartenquiz (Zielgeometrie in Bildpunkten)
GEOM = []   # Geometrie der gerade erzeugten Markierung(en)

def d_parts(d):
    out = []
    for sub in d.split('M')[1:]:
        closed = sub.endswith('Z'); sub = sub.rstrip('Z')
        pts = [tuple(float(v) for v in xy.split(',')) for xy in sub.split('L') if xy]
        out.append((closed, pts))
    return out
def reg_path(d, kind):
    for closed, pts in d_parts(d):
        if closed and len(pts) > 3:  # Ring am entferntesten Punkt teilen, sonst fällt er bei der Vereinfachung zusammen
            h = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
            pts = geo.dp(pts[:h + 1], 1.5)[:-1] + geo.dp(pts[h:] + [pts[0]], 1.5)[:-1]
        else: pts = geo.dp(pts, 1.5)
        if len(pts) >= 2: GEOM.append([kind, [[round(x, 1), round(y, 1)] for x, y in pts]])

def svg(m, body, name):
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {m.W} {m.H}">'
         f'<defs><clipPath id="r"><rect width="{m.W}" height="{m.H}" rx="18"/></clipPath></defs><g clip-path="url(#r)">{body}</g></svg>')
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f: f.write(s)
    return 'img/' + name

def slug(s):
    return ''.join(ch for ch in s.lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss').replace(' ', '-') if ch.isalnum() or ch == '-')

def rivers(names): return [f for n in ('ne_10m_rivers_lake_centerlines', 'ne_10m_rivers_europe') for f in load(n) if (f['properties'].get('name') or '') in names]
def marine(name): return [f for f in load('ne_10m_geography_marine_polys') if f['properties'].get('name') == name]
def belts():  # namenlose Fläche der Beltsee (Kieler Bucht, Großer/Kleiner Belt)
    def inbox(f):
        c = f['geometry']['coordinates']; pts = [p for poly in (c if f['geometry']['type'] == 'MultiPolygon' else [c]) for r in poly for p in r]
        return all(8.5 <= p[0] <= 12.8 and 53.8 <= p[1] <= 56.6 for p in pts)
    return [f for f in load('ne_10m_geography_marine_polys') if not f['properties'].get('name') and inbox(f)]
def region(*names): return [f for f in load('ne_10m_geography_regions_polys') if f['properties'].get('NAME') in names]

def ellipse(m, lon, lat, rx, ry, rot=0, fill=True):
    x, y = m.P(lon, lat)
    st = f'fill="{OR}" fill-opacity=".55" stroke="{OR_D}" stroke-width="2.5"' if fill else f'fill="none" stroke="{OR}" stroke-width="4"'
    GEOM.append(['ell', [round(x, 1), round(y, 1), rx, ry, rot]])
    return f'<ellipse cx="{f1(x)}" cy="{f1(y)}" rx="{rx}" ry="{ry}" transform="rotate({rot} {f1(x)} {f1(y)})" {st}/>'
def hi_poly(m, feats, tol=0.8, stroke=True):
    d = poly_path(m, feats, tol, 1); reg_path(d, 'poly')
    return f'<path d="{d}" fill="{OR}" fill-opacity=".6"' + (f' stroke="{OR_D}" stroke-width="1.5" stroke-linejoin="round"' if stroke else '') + '/>'
def hi_line(m, feats=None, pts=None, w=6):
    d = line_path(m, feats, 0.8) if feats else lonlat_path(m, pts)
    reg_path(d, 'line')
    return f'<path d="{d}" fill="none" stroke="{OR}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def hi_point(m, lon, lat):
    x, y = m.P(lon, lat)
    GEOM.append(['pt', [round(x, 1), round(y, 1)]])
    return f'<circle cx="{f1(x)}" cy="{f1(y)}" r="16" fill="{OR}" opacity=".3"/><circle cx="{f1(x)}" cy="{f1(y)}" r="8" fill="{OR}" stroke="#fff" stroke-width="3"/>'

def make(key, m, land, borders, river_names, dots, extra_base='', tol_km=50, scale_km=300):
    """Grundebenen einer Karte erzeugen; gibt eine Funktion zum Anlegen der Karten zurück."""
    sea = f'<rect width="{m.W}" height="{m.H}" fill="{SEA}"/>'
    u_plain = svg(m, sea, f'karte-{key}-meer.svg')
    lk = [f for f in load('ne_10m_lakes') if (f['properties'].get('scalerank') or 9) <= 5]
    body = (f'<path d="{poly_path(m, load(land), 0.7)}" fill="{LAND}" stroke="#9fb9c9" stroke-width="0.8" stroke-linejoin="round"/>'
            f'<path d="{poly_path(m, lk, 0.7, 6)}" fill="{SEA}" stroke="#9fb9c9" stroke-width="0.6"/>'
            f'<path d="{line_path(m, load(borders), 0.8)}" fill="none" stroke="{BORDER}" stroke-width="0.9" stroke-dasharray="4 3"/>'
            f'<path d="{line_path(m, rivers(river_names), 0.7)}" fill="none" stroke="{RIVER}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>'
            + extra_base
            + ''.join(f'<circle cx="{f1(m.P(*p)[0])}" cy="{f1(m.P(*p)[1])}" r="4" fill="#5d6b77" stroke="#fff" stroke-width="1.5"/>' for p in dots))
    base = svg(m, body, f'karte-{key}.svg')
    leer = svg(m, body.split('<circle')[0] if dots else body, f'karte-{key}-leer.svg') if dots else base
    CARDS[key] = []
    GEOM.clear()
    QUIZ[key] = {'w': m.W, 'h': m.H, 'kmPerPx': round(6371 / m.s, 4), 'tolKm': tol_km, 'scaleKm': scale_km, 'sea': u_plain, 'base': leer, 'items': []}
    KAT = {FL: 'Fluss', MEER: 'Meer / Meeresteil', GEB: 'Gebirge', HAFEN: 'Hafen', WEG: 'Wasserweg', KANAL: 'Kanal'}
    def card(frage, antwort, beispiel='', under=None, over=None):
        sid = slug(antwort.split(' (')[0])
        u = svg(m, sea + under, f'karte-{key}-u-{sid}.svg') if under else u_plain
        layers = [u, base] + ([svg(m, over, f'karte-{key}-o-{sid}.svg')] if over else [])
        CARDS[key].append([frage, antwort, beispiel, layers])
        QUIZ[key]['items'].append({'name': antwort, 'kat': KAT[frage], 'u': u, 'o': layers[2] if over else None, 'g': list(GEOM)})
        GEOM.clear()
    return card

KANAL = 'Welcher Kanal ist markiert?'
FL, MEER, GEB, HAFEN, WEG = 'Welcher Fluss ist markiert?', 'Welches Meer / welcher Meeresteil ist markiert?', 'Welches Gebirge ist markiert?', 'Welcher Hafen ist markiert?', 'Welcher Wasserweg ist markiert?'

# ===================== Europa =====================
def europa():
    m = Map(-14, 29, 62, 71)
    RV = {'Donau': ('Donau', 'Danube'), 'Elbe': ('Elbe',), 'Guadalquivir': ('Guadalquivir',), 'Loire': ('Loire',), 'Oder': ('Oder',), 'Rhein': ('Rhein', 'Rhine'), 'Seine': ('Seine',), 'Wolga': ('Volga',),
          # zusätzlich aus OneNote: Wasserwege der Nordrange und Topographie Deutschland
          'Schelde': ('Schelde',), 'Weser': ('Weser',), 'Ems': ('Ems',), 'Main': ('Main',)}
    card = make('europa', m, 'ne_50m_land', 'ne_50m_admin_0_boundary_lines_land', [n for v in RV.values() for n in v], [], tol_km=60, scale_km=300)
    ex = {'Donau': 'mündet ins Schwarze Meer', 'Elbe': 'mündet bei Cuxhaven in die Nordsee', 'Guadalquivir': 'Südspanien, mündet in den Atlantik (Sevilla)',
          'Loire': 'längster Fluss Frankreichs, mündet in die Biskaya', 'Oder': 'Grenze Deutschland–Polen, mündet in die Ostsee', 'Rhein': 'mündet bei Rotterdam in die Nordsee',
          'Seine': 'Paris, mündet bei Le Havre in den Ärmelkanal', 'Wolga': 'längster Fluss Europas, mündet ins Kaspische Meer',
          'Schelde': 'Antwerpen – Zufahrt über die Westerschelde (Nordrange)', 'Weser': 'Bremen / Bremerhaven (Nordrange)', 'Ems': 'Emden (Nordrange)',
          'Main': 'mündet bei Mainz in den Rhein (Topographie Deutschland)'}
    for k, names in RV.items(): card(FL, k, ex[k], over=hi_line(m, rivers(names), 5))
    MP = {'Ägäis': 'Aegean Sea', 'Ärmelkanal': 'English Channel', 'Biskaya': 'Bay of Biscay', 'Bosporus': 'Bosporus', 'Bottnischer Meerbusen': 'Gulf of Bothnia',
          'Dardanellen': 'Dardanelles', 'Europäisches Nordmeer (Nordmeer)': 'Norwegian Sea', 'Finnischer Meerbusen': 'Gulf of Finland', 'Kattegat': 'Kattegat', 'Marmarameer': 'Sea of Marmara',
          'Nordsee': 'North Sea', 'Ostsee': 'Baltic Sea', 'Schwarzes Meer': 'Black Sea', 'Skagerrak': 'Skagerrak', 'Straße von Gibraltar': 'Strait of Gibraltar'}
    small = {'Bosporus': (29.05, 41.15, 10, 18, 20), 'Dardanellen': (26.45, 40.2, 10, 18, -40), 'Straße von Gibraltar': (-5.6, 35.95, 16, 10, 0), 'Marmarameer': None, 'Kattegat': None, 'Skagerrak': None}
    for k, en in sorted(MP.items()):
        extra = {'Ostsee': ['Gulf of Riga', 'Mecklenburger Bucht', 'None', 'Øresund', 'Kaliningrad'], 'Nordsee': ['Waddenzee'], 'Schwarzes Meer': ['Sea of Azov'],
                 'Europäisches Nordmeer (Nordmeer)': ['Vestfjorden', 'Trondheimsfjorden']}.get(k, [])
        under = hi_poly(m, marine(en) + [f for n in extra if n != 'None' for f in marine(n)] + (belts() if 'None' in extra else []), stroke=False)
        over = ellipse(m, *small[k], fill=False) if small.get(k) else ''
        card(MEER, k, '', under=under, over=over or None)
    med = [f for n in ('Mediterranean Sea', 'Adriatic Sea', 'Aegean Sea', 'Ionian Sea', 'Tyrrhenian Sea', 'Ligurian Sea', 'Balearic Sea', 'Alboran Sea', 'Golfe du Lion', 'Gulf of Sidra', 'Sea of Crete', 'Gulf of Gabès') for f in marine(n)]
    card(MEER, 'Mittelmeer', 'mit Adria, Ägäis, Tyrrhenischem Meer …', under=hi_poly(m, med, stroke=False))
    card(MEER, 'Atlantik (Atlantischer Ozean)', '', under=hi_poly(m, marine('North Atlantic Ocean') + marine('Bay of Biscay') + marine('Irish Sea') + marine('Bristol Channel') + marine('Inner Seas'), stroke=False))
    card(MEER, 'Kaspisches Meer', 'größter See der Erde – Mündung der Wolga', under=hi_poly(m, marine('Caspian Sea'), stroke=False))
    card(MEER, 'Straße von Sizilien', 'zwischen Sizilien und Tunesien', over=ellipse(m, 11.6, 37.25, 22, 12, -30))
    # Gebirge
    sk = [(6.6, 59.0), (7.8, 60.8), (9.6, 62.2), (12.0, 63.4), (13.8, 65.0), (16.0, 67.0), (18.5, 68.6), (21.5, 69.6)]
    GB = {'Alpen': region('ALPS'), 'Atlas': region('ATLAS MOUNTAINS', 'HAUT ATLAS', 'Moyen Atlas', 'Anti Atlas', 'Atlas Tellien', 'ATLAS SAHARIEN'),
          'Karpaten': region('CARPATHIAN MOUNTAINS', 'Transylvanian Alps'), 'Kaukasus': region('CAUCASUS MTS.'), 'Pyrenäen': region('PYRENEES'), 'Ural': region('URAL MOUNTAINS')}
    gex = {'Alpen': 'höchstes Gebirge Europas', 'Atlas': 'Nordwestafrika (Marokko, Algerien)', 'Karpaten': 'Bogen um Ungarn/Rumänien', 'Kaukasus': 'zwischen Schwarzem und Kaspischem Meer',
           'Pyrenäen': 'Grenze Spanien–Frankreich', 'Ural': 'Grenze Europa–Asien', 'Skanden': 'Skandinavisches Gebirge, Norwegen/Schweden'}
    for k, feats in GB.items():
        assert feats, k
        card(GEB, k, gex[k], over=hi_poly(m, feats))
    reg_path(lonlat_path(m, sk), 'line')
    card(GEB, 'Skanden (Skandinavisches Gebirge)', 'Norwegen / Schweden', over=f'<path d="{lonlat_path(m, sk)}" fill="none" stroke="{OR}" stroke-opacity=".75" stroke-width="13" stroke-linecap="round" stroke-linejoin="round"/>')

# ===================== Nordrange =====================
NR_PORTS = {'Amsterdam': (4.90, 52.37), 'Antwerpen': (4.40, 51.22), 'Cuxhaven': (8.70, 53.87), 'Dover': (1.32, 51.12), 'Duisburg': (6.76, 51.43),
            'Emden': (7.20, 53.36), 'Felixstowe': (1.33, 51.96), 'Hamburg': (9.97, 53.54), 'Le Havre': (0.11, 49.49), 'Rotterdam': (4.15, 51.95), 'Rouen': (1.09, 49.44),
            'Southampton': (-1.40, 50.90), 'Wilhelmshaven': (8.13, 53.52), 'Zeebrügge': (3.20, 51.33)}
BREMEN, BREMERHAVEN = (8.80, 53.08), (8.58, 53.55)
def nordrange():
    m = Map(-2.2, 48.9, 11.4, 54.9)
    RV = ('Elbe', 'Weser', 'Ems', 'Rhein', 'Rhine', 'Maas', 'Schelde', 'Seine', 'Thames', 'Ruhr')
    nsk = [(4.58, 52.47), (4.70, 52.43), (4.82, 52.41), (4.90, 52.40)]
    nww = [(4.10, 51.98), (4.22, 51.94), (4.32, 51.91), (4.42, 51.90)]
    extra = (f'<path d="{lonlat_path(m, nsk)}" fill="none" stroke="{RIVER}" stroke-width="2"/>'
             f'<path d="{lonlat_path(m, nww)}" fill="none" stroke="{RIVER}" stroke-width="2"/>')
    card = make('nordrange', m, 'ne_10m_land', 'ne_10m_admin_0_boundary_lines_land', RV, list(NR_PORTS.values()) + [BREMEN, BREMERHAVEN], extra, tol_km=15, scale_km=60)
    pex = {'Amsterdam': 'am Nordseekanal', 'Antwerpen': 'an der Schelde', 'Cuxhaven': 'an der Elbmündung', 'Dover': 'Fährhafen an der Straße von Dover',
           'Duisburg': 'größter Binnenhafen, Rhein + Ruhr', 'Emden': 'an der Ems, Autoverladung', 'Felixstowe': 'größter britischer Containerhafen', 'Hamburg': 'an der Elbe',
           'Le Havre': 'an der Seinemündung', 'Rotterdam': 'Maas / Neuer Wasserweg', 'Rouen': 'an der Seine', 'Southampton': 'am Solent', 'Wilhelmshaven': 'am Jadebusen',
           'Zeebrügge': 'Belgien, gehört zu Port of Antwerp-Bruges'}
    for k, p in NR_PORTS.items(): card(HAFEN, k, pex[k], over=hi_point(m, *p))
    card(HAFEN, 'Bremische Häfen (Bremen / Bremerhaven)', 'an der Weser', over=hi_point(m, *BREMEN) + hi_point(m, *BREMERHAVEN))
    WY = {'Elbe': ('Elbe',), 'Ems': ('Ems',), 'Weser': ('Weser',), 'Rhein': ('Rhein', 'Rhine'), 'Seine': ('Seine',), 'Schelde': ('Schelde',)}
    for k, names in WY.items(): card(WEG, k, '', over=hi_line(m, rivers(names), 6))
    card(WEG, 'Jadebusen', 'Bucht bei Wilhelmshaven', over=ellipse(m, 8.20, 53.45, 13, 17))
    card(WEG, 'Nordseekanal', 'IJmuiden – Amsterdam', over=hi_line(m, pts=nsk, w=7))
    card(WEG, 'Neuer Wasserweg', 'Zufahrt von der Nordsee nach Rotterdam', over=hi_line(m, pts=nww, w=7))
    card(WEG, 'Nordsee', '', under=hi_poly(m, marine('North Sea') + marine('Waddenzee'), stroke=False))
    card(WEG, 'Ärmelkanal', '', under=hi_poly(m, marine('English Channel'), stroke=False))
    card(WEG, 'Straße von Dover', 'engste Stelle des Ärmelkanals', over=ellipse(m, 1.55, 51.0, 30, 16, -50))
    # Kartenquiz „Alle Häfen“: die 15 Nordrange-Häfen + London auf derselben Karte (nur Quiz, kein Karteikarten-Stapel)
    GEOM.clear(); lo = svg(m, hi_point(m, 0.05, 51.50), 'karte-nordrange-o-london.svg'); lg = list(GEOM); GEOM.clear()
    nr = QUIZ['nordrange']
    QUIZ['haefen'] = {**{k: v for k, v in nr.items() if k != 'items'}, 'items': [i for i in nr['items'] if i['kat'] == 'Hafen'] +
                      [{'name': 'London', 'kat': 'Hafen', 'u': nr['sea'], 'o': lo, 'g': lg}]}

# ===================== Traditionelle Seehäfen =====================
# ===================== Deutschland: Flüsse und Kanäle (Topographie Deutschland, Aufgabe 4) =====================
CANALS = {
    'Mittellandkanal': ([(7.62, 52.30), (7.98, 52.41), (8.40, 52.36), (8.92, 52.30), (9.30, 52.38), (9.73, 52.42), (10.23, 52.33), (10.53, 52.37),
                         (10.78, 52.43), (11.10, 52.38), (11.40, 52.29), (11.70, 52.23)], 'West-Ost-Verbindung vom Dortmund-Ems-Kanal bis zur Elbe bei Magdeburg'),
    'Elbe-Seitenkanal': ([(10.60, 52.43), (10.58, 52.62), (10.55, 52.80), (10.57, 52.96), (10.53, 53.15), (10.52, 53.29), (10.48, 53.37)],
                         'verbindet den Mittellandkanal mit der Elbe (Richtung Hamburg)'),
    'Nord-Ostsee-Kanal': ([(9.14, 53.89), (9.27, 54.0), (9.29, 54.06), (9.40, 54.12), (9.52, 54.2), (9.62, 54.29), (9.72, 54.30), (9.86, 54.33), (10.0, 54.36), (10.15, 54.37)],
                          'Brunsbüttel – Kiel, verbindet Nord- und Ostsee'),
    'Main-Donau-Kanal': ([(10.89, 49.89), (11.0, 49.6), (11.05, 49.43), (11.19, 49.19), (11.47, 49.03), (11.59, 49.04), (11.88, 48.92)],
                         'Bamberg – Kelheim, verbindet Main und Donau (Nordsee ↔ Schwarzes Meer)'),
}
def deutschland():
    m = Map(5.4, 47.1, 15.6, 55.15)
    RV = {'Donau': ('Donau', 'Danube'), 'Elbe': ('Elbe',), 'Ems': ('Ems',), 'Main': ('Main',), 'Oder': ('Oder',), 'Rhein': ('Rhein', 'Rhine'), 'Weser': ('Weser',)}
    extra = ''.join(f'<path d="{lonlat_path(m, pts)}" fill="none" stroke="{RIVER}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>' for pts, _ in CANALS.values())
    card = make('deutschland', m, 'ne_10m_land', 'ne_10m_admin_0_boundary_lines_land', [n for v in RV.values() for n in v], [], extra, tol_km=20, scale_km=80)
    ex = {'Donau': 'fließt nach Osten ins Schwarze Meer, Südgrenze der Mittelgebirgszone', 'Elbe': 'Hamburg, mündet bei Cuxhaven in die Nordsee',
          'Ems': 'Emden, mündet in die Nordsee', 'Main': 'Frankfurt, mündet bei Mainz in den Rhein', 'Oder': 'Grenze zu Polen, mündet in die Ostsee',
          'Rhein': 'Köln, Duisburg – wichtigste Binnenwasserstraße', 'Weser': 'Bremen / Bremerhaven, mündet in die Nordsee'}
    for k, names in RV.items(): card(FL, k, ex[k], over=hi_line(m, rivers(names), 6))
    for k, (pts, e) in CANALS.items(): card(KANAL, k, e, over=hi_line(m, pts=pts, w=7))

def traditionell():
    m = Map(-1.6, 50.5, 10.8, 54.4)
    P = {'London': (0.05, 51.50), 'Hamburg': (9.97, 53.54), 'Bremen': BREMEN, 'Rotterdam': (4.40, 51.91), 'Antwerpen': (4.40, 51.22)}
    card = make('traditionell', m, 'ne_10m_land', 'ne_10m_admin_0_boundary_lines_land', ('Elbe', 'Weser', 'Ems', 'Rhein', 'Rhine', 'Maas', 'Schelde', 'Thames'), list(P.values()), tol_km=15, scale_km=80)
    ex = {'London': 'an der Themse', 'Hamburg': 'an der Elbe', 'Bremen': 'an der Weser', 'Rotterdam': 'an der Maas', 'Antwerpen': 'an der Schelde'}
    for k, p in P.items(): card(HAFEN, k, ex[k], over=hi_point(m, *p))

def ctx_rings(m, f, tol=2.0):
    out = []
    for closed, pts in d_parts(poly_path(m, [f], tol, 8)):
        if len(pts) >= 3: out.append([[round(x, 1), round(y, 1)] for x, y in pts])
    return out
def add_context():
    """Länder und Meere, damit das Quiz sagen kann, was man stattdessen angetippt hat."""
    views = {'europa': (-14, 29, 62, 71), 'nordrange': (-2.2, 48.9, 11.4, 54.9), 'traditionell': (-1.6, 50.5, 10.8, 54.4), 'haefen': (-2.2, 48.9, 11.4, 54.9), 'deutschland': (5.4, 47.1, 15.6, 55.15)}
    def near(f, bb):
        c = f['geometry']['coordinates']; pts = [p for poly in (c if f['geometry']['type'] == 'MultiPolygon' else [c]) for r in poly for p in r]
        x0, y0, x1, y1 = min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)
        return x1 - x0 < 180 and x1 > bb[0] - 2 and x0 < bb[2] + 2 and y1 > bb[1] - 2 and y0 < bb[3] + 2
    for key, bb in views.items():
        m = Map(*bb)
        ctx = []
        for f in load('ne_50m_admin_0_countries'):
            if not near(f, bb): continue
            r = ctx_rings(m, f, 2.0 if key == 'europa' else 1.2)
            if r: ctx.append({'name': f['properties']['NAME_DE'], 'kat': 'Land', 'r': r})
        for f in load('ne_10m_geography_marine_polys'):
            nm = f['properties'].get('name_de') or f['properties'].get('name')
            if not nm or not near(f, bb): continue
            r = ctx_rings(m, f, 2.0 if key == 'europa' else 1.2)
            if r: ctx.append({'name': nm, 'kat': 'Meer', 'r': r})
        QUIZ[key]['ctx'] = ctx

os.makedirs(OUT, exist_ok=True)
europa(); nordrange(); traditionell(); deutschland(); add_context()
with open(os.path.join(HERE, 'stumme-karten.json'), 'w', encoding='utf-8') as f: json.dump(CARDS, f, ensure_ascii=False, indent=0)
with open(os.path.join(OUT, 'kartenquiz.json'), 'w', encoding='utf-8') as f: json.dump(QUIZ, f, ensure_ascii=False, separators=(',', ':'))
print('kartenquiz.json', round(os.path.getsize(os.path.join(OUT, 'kartenquiz.json')) / 1024), 'KB')
print({k: len(v) for k, v in CARDS.items()})
