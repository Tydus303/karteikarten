"""Erzeugt die Tide-Skizzen (SVG) für den Geo-Stapel.
Aufruf: python3 -I tools/tide-skizzen.py img"""
import math, os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else 'img'
W, H = 820, 440
TXT, MUTED, OR, OR_D = '#22313d', '#6b7a86', '#f39a2b', '#b8681a'
SEA1, SEA2, SEA_L, LAND, MUD = '#7fb6d6', '#3f7fa6', '#cfe5f2', '#efe6d2', '#b9a27c'
SKY = '#f4f9fd'
RED = '#c8392b'

def f1(v): return ('%.1f' % v).rstrip('0').rstrip('.')
def t(x, y, s, size=15, color=TXT, weight=500, anchor='middle', italic=False, halo=False):
    it = ' font-style="italic"' if italic else ''
    h = ' stroke="#fff" stroke-width="4" stroke-linejoin="round" paint-order="stroke"' if halo else ''
    return f'<text x="{f1(x)}" y="{f1(y)}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{it}{h}>{s}</text>'
def line(x1, y1, x2, y2, color=TXT, w=2, dash='', arrow='', start=''):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    a = f' marker-end="url(#{arrow})"' if arrow else ''
    s = f' marker-start="url(#{start})"' if start else ''
    return f'<path d="M{f1(x1)},{f1(y1)}L{f1(x2)},{f1(y2)}" stroke="{color}" stroke-width="{w}" fill="none" stroke-linecap="round"{d}{a}{s}/>'
DEFS = ''.join(f'<marker id="{n}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse"><path d="M0,0L10,5L0,10Z" fill="{c}"/></marker>'
               for n, c in (('ao', OR), ('ad', OR_D), ('ab', SEA2), ('ak', TXT), ('ar', RED), ('am', MUTED)))
def save(name, body, h=H):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" font-family="-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">'
           f'<defs>{DEFS}<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SEA1}"/><stop offset="1" stop-color="{SEA2}"/></linearGradient>'
           f'<clipPath id="rc"><rect width="{W}" height="{h}" rx="18"/></clipPath></defs>'
           f'<g clip-path="url(#rc)"><rect width="{W}" height="{h}" fill="{SKY}"/>{body}</g></svg>')
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f: f.write(svg)
    print(name, round(len(svg) / 1024, 1), 'KB')

def ship(x, wl, L=150, draft=26, color='#4a5a68', label=''):
    """Schiff von der Seite: x = Bug links, wl = Wasserlinie (y)."""
    top = wl - 18
    hull = f'M{x},{top}L{x + L},{top}L{x + L - 14},{wl + draft}L{x + 22},{wl + draft}Z'
    sup = f'<rect x="{x + L - 46}" y="{top - 30}" width="30" height="30" fill="#e9eef2" stroke="{color}" stroke-width="1.5"/><rect x="{x + L - 50}" y="{top - 36}" width="38" height="7" fill="{color}"/>'
    s = f'<path d="{hull}" fill="{color}"/>{sup}'
    if label: s += t(x + L / 2, top - 44, label, 13, MUTED, 600)
    return s

# ---------------- Tidenkurve ----------------
X0, X1, MID, AMP = 80, 780, 215, 95
PER = 745  # Minuten
def tx(m): return X0 + (X1 - X0) * m / 1500
def ty(m): return MID + AMP * math.cos(2 * math.pi * m / PER)  # m=0: Niedrigwasser (unten)
def curve(m0, m1, step=6):
    pts = [(tx(m), ty(m)) for m in range(int(m0), int(m1) + 1, step)] + [(tx(m1), ty(m1))]
    return 'M' + 'L'.join(f'{f1(x)},{f1(y)}' for x, y in pts)
def tide_base(extra=''):
    b = f'<path d="{curve(0, 1500)}L{X1},400L{X0},400Z" fill="{SEA_L}"/>'
    b += line(X0, 400, X1 + 10, 400, MUTED, 1.5, arrow='am') + line(X0, 400, X0, 70, MUTED, 1.5, arrow='am')
    b += t(X1 + 5, 425, 'Zeit', 13, MUTED, 600, 'end') + t(X0 + 8, 76, 'Wasserstand', 13, MUTED, 600, 'start')
    b += f'<path d="{curve(0, 1500)}" fill="none" stroke="{SEA2}" stroke-width="3"/>'
    return b + extra
HWm, NWm = [372.5, 1117.5], [0, 745, 1490]

def tide_cards():
    # Tide: eine ganze Schwingung
    b = tide_base(f'<path d="{curve(0, 745)}" fill="none" stroke="{OR}" stroke-width="6"/>')
    b += line(tx(0), 60, tx(745), 60, OR_D, 2.5, arrow='ad', start='ad') + line(tx(0), 66, tx(0), 330, OR_D, 1, '4 4') + line(tx(745), 66, tx(745), 330, OR_D, 1, '4 4')
    b += t(tx(372), 48, '1 Tide = 12 h 25 min', 19, OR_D, 800)
    b += t(tx(186), 250, 'Flut', 15, TXT, 700, halo=True) + t(tx(560), 250, 'Ebbe', 15, TXT, 700, halo=True)
    b += t(tx(1120), 380, 'danach beginnt die nächste Tide', 13, MUTED, 500)
    save('tide-tide.svg', b)
    # Flut
    b = tide_base(''.join(f'<path d="{curve(a, a + 372.5)}" fill="none" stroke="{OR}" stroke-width="6"/>' for a in (0, 745)))
    b += line(tx(186) - 46, ty(186) + 40, tx(186) - 46, ty(186) - 50, OR_D, 4, arrow='ad')
    b += t(tx(186) - 56, ty(186) - 10, 'Flut', 22, OR_D, 800, 'end', halo=True) + t(tx(186) - 56, ty(186) + 12, 'Wasser steigt', 13, OR_D, 600, 'end', halo=True)
    b += t(tx(186) - 56, ty(186) + 28, '„läuft auf“', 13, OR_D, 600, 'end', halo=True)
    b += t(tx(0), ty(0) + 22, 'NW', 13, MUTED, 700) + t(tx(372.5), ty(372.5) - 12, 'HW', 13, MUTED, 700)
    save('tide-flut.svg', b)
    # Ebbe
    b = tide_base(''.join(f'<path d="{curve(a, a + 372.5)}" fill="none" stroke="{OR}" stroke-width="6"/>' for a in (372.5, 1117.5)))
    xm = tx(560) + 46
    b += line(xm, ty(560) - 50, xm, ty(560) + 40, OR_D, 4, arrow='ad')
    b += t(xm + 12, ty(560) - 10, 'Ebbe', 22, OR_D, 800, 'start', halo=True) + t(xm + 12, ty(560) + 12, 'Wasser fällt', 13, OR_D, 600, 'start', halo=True)
    b += t(xm + 12, ty(560) + 28, '„läuft ab“', 13, OR_D, 600, 'start', halo=True)
    b += t(tx(372.5), ty(372.5) - 12, 'HW', 13, MUTED, 700) + t(tx(745), ty(745) + 22, 'NW', 13, MUTED, 700)
    save('tide-ebbe.svg', b)
    # Hochwasser
    b = tide_base(line(X0, ty(372.5), X1, ty(372.5), OR_D, 2, '6 5'))
    for m in HWm: b += f'<circle cx="{f1(tx(m))}" cy="{f1(ty(m))}" r="9" fill="{OR}" stroke="#fff" stroke-width="3"/>'
    b += t(tx(745), ty(372.5) - 14, 'Hochwasser (HW) = höchster Wasserstand', 17, OR_D, 800, halo=True)
    save('tide-hochwasser.svg', b)
    # Niedrigwasser
    b = tide_base(line(X0, ty(0), X1, ty(0), OR_D, 2, '6 5'))
    for m in NWm: b += f'<circle cx="{f1(tx(m))}" cy="{f1(ty(m))}" r="9" fill="{OR}" stroke="#fff" stroke-width="3"/>'
    b += t(tx(372), ty(0) + 32, 'Niedrigwasser (NW) = niedrigster Wasserstand', 17, OR_D, 800, halo=True)
    save('tide-niedrigwasser.svg', b)
    # Tidenhub
    xa = tx(372.5)
    b = tide_base(line(X0, ty(0), X1, ty(0), MUTED, 1.5, '6 5') + line(X0, ty(372.5), X1, ty(372.5), MUTED, 1.5, '6 5'))
    b += line(xa, ty(372.5) + 4, xa, ty(0) - 4, OR_D, 4, arrow='ad', start='ad')
    b += t(xa + 14, MID + 2, 'Tidenhub', 22, OR_D, 800, 'start', halo=True) + t(xa + 14, MID + 22, 'Unterschied NW → HW', 13, OR_D, 600, 'start', halo=True)
    b += t(X1 - 6, ty(372.5) - 8, 'HW', 13, MUTED, 700, 'end') + t(X1 - 6, ty(0) + 18, 'NW', 13, MUTED, 700, 'end')
    b += f'<rect x="530" y="30" width="250" height="78" rx="10" fill="#fff" stroke="#dde5ec"/>'
    b += t(545, 54, 'Hamburg ≈ 3,63 m', 14, TXT, 700, 'start') + t(545, 76, 'Cuxhaven ≈ 2,88 m', 14, TXT, 600, 'start') + t(545, 98, 'offener Ozean ≈ 0,35 m', 14, MUTED, 600, 'start')
    save('tide-tidenhub.svg', b)

# ---------------- Strömung auf der Elbe ----------------
def elbe_river(arrows_right, title, sub):
    b = f'<rect x="0" y="0" width="{W}" height="{H}" fill="{LAND}"/>'
    river = 'M0,40 L120,60 C260,120 420,170 560,195 L820,205 L820,245 L560,255 C420,280 260,330 120,390 L0,410 Z'
    b += f'<path d="{river}" fill="{SEA_L}" stroke="#9fb9c9" stroke-width="1.5"/>'
    b += t(50, 230, 'Nordsee', 18, '#4f7f9c', 600, italic=True)
    b += f'<circle cx="150" cy="78" r="6" fill="{TXT}"/>' + t(160, 70, 'Cuxhaven', 14, TXT, 700, 'start')
    b += f'<circle cx="770" cy="200" r="6" fill="{TXT}"/>' + t(770, 188, 'Hamburg', 14, TXT, 700)
    for x, y in ((200, 225), (360, 225), (520, 225), (650, 225)):
        if arrows_right: b += line(x - 50, y, x + 50, y, OR, 7, arrow='ao')
        else: b += line(x + 50, y, x - 50, y, OR, 7, arrow='ao')
    b += t(410, 60, title, 24, OR_D, 800) + t(410, 86, sub, 15, OR_D, 600)
    return b
def stroeme():
    b = elbe_river(True, 'Flutstrom → elbaufwärts', 'bei Flut strömt das Wasser von der Nordsee nach Hamburg')
    b += t(410, 330, 'Schiff nach Hamburg fährt mit dem Strom:', 15, TXT, 600) + t(410, 352, 'schneller und spart Bunker (Treibstoff)', 15, TXT, 600)
    save('tide-flutstrom.svg', b)
    b = elbe_river(False, '← Ebbstrom: elbabwärts', 'bei Ebbe strömt das Wasser von Hamburg zur Nordsee')
    b += t(410, 330, 'Schiff Richtung Nordsee fährt mit dem Strom:', 15, TXT, 600) + t(410, 352, 'schneller und spart Bunker (Treibstoff)', 15, TXT, 600)
    save('tide-ebbstrom.svg', b)

# ---------------- Himmelskörper ----------------
def earth(cx, cy, r=62):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#5a9c5e"/>'
            f'<path d="M{cx - r * .55},{cy - r * .5} q{r * .4},{-r * .2} {r * .6},{r * .15} q{-r * .1},{r * .4} {-r * .45},{r * .3} z" fill="#7dbb72"/>'
            f'<path d="M{cx + r * .1},{cy + r * .2} q{r * .45},{-r * .1} {r * .55},{r * .35} q{-r * .3},{r * .3} {-r * .5},{r * .1} z" fill="#7dbb72"/>'
            + t(cx, cy + 5, 'Erde', 14, '#fff', 800))
def moon(cx, cy, r=24, label='Mond', dim=False):
    o = ' opacity=".45"' if dim else ''
    return f'<g{o}><circle cx="{cx}" cy="{cy}" r="{r}" fill="#d6d9dd" stroke="#9aa3ab" stroke-width="2"/><circle cx="{cx - r * .3}" cy="{cy - r * .2}" r="{r * .2}" fill="#bfc4ca"/>{t(cx, cy + r + 20, label, 14, TXT, 700)}</g>'
def sun(cx, cy, r=70):
    rays = ''.join(line(cx + (r + 8) * math.cos(a), cy + (r + 8) * math.sin(a), cx + (r + 24) * math.cos(a), cy + (r + 24) * math.sin(a), '#f2b01e', 4)
                   for a in [i * math.pi / 6 for i in range(12)])
    return rays + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#f9c846"/>' + t(max(cx, 0) + 12, cy + r + 46, 'Sonne', 16, '#7a5300', 800, 'start')
def bulge(cx, cy, rx, ry, rot=0, color=SEA1):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" transform="rotate({rot} {cx} {cy})" fill="{color}" opacity=".85"/>'

def himmel():
    # Zweiter Flutberg
    cx, cy = 330, 230
    b = bulge(cx, cy, 140, 88) + f'<path d="M{cx - 70},{cy - 76} A140,88 0 0 0 {cx - 70},{cy + 76}Z" fill="{OR}" opacity=".55"/>' + earth(cx, cy, 70) + moon(735, cy, 30)
    b += f'<path d="M{cx - 140},{cy} a140,88 0 0 1 70,-76 L{cx - 70},{cy + 76} a140,88 0 0 1 -70,-76z" fill="{OR}" opacity=".0"/>'
    b += line(cx + 145, cy, cx + 245, cy, OR_D, 5, arrow='ad') + t(cx + 195, cy - 14, 'stark', 13, OR_D, 700)
    b += line(cx - 20, cy - 100, cx + 50, cy - 100, OR_D, 4, arrow='ad') + t(cx + 15, cy - 112, 'mittel (Erde)', 13, OR_D, 700)
    b += line(cx - 145, cy, cx - 115, cy, OR_D, 3, arrow='ad') + t(cx - 128, cy - 14, 'schwach', 13, OR_D, 700, halo=True)
    b += t(cx - 155, cy + 72, '2. Flutberg', 15, OR_D, 800) + t(cx + 160, cy + 72, '1. Flutberg', 15, TXT, 700)
    b += t(410, 40, 'Anziehung des Mondes wird mit der Entfernung schwächer', 16, TXT, 700)
    b += t(410, 380, 'Mondseite: Wasser wird stärker angezogen als die Erde → Flutberg', 14, TXT, 500)
    b += t(410, 404, 'Rückseite: die Erde wird stärker angezogen als das Wasser – das Wasser „bleibt zurück“', 14, OR_D, 700)
    save('tide-zweiter-flutberg.svg', b)
    # Springtide
    cy = 215
    b = sun(-10, cy, 90) + line(80, cy, 790, cy, MUTED, 1.5, '6 6')
    b += bulge(450, cy, 135, 70) + earth(450, cy, 55) + moon(270, cy, 22, 'Neumond') + moon(720, cy, 22, 'Vollmond')
    b += t(450, 50, 'Springtide: Sonne, Mond und Erde in einer Linie', 19, OR_D, 800)
    b += t(450, 74, '(bei Neumond und Vollmond)', 14, OR_D, 600)
    b += t(450, 370, 'Kräfte von Sonne und Mond addieren sich', 15, TXT, 700)
    b += t(450, 394, '→ sehr hohes Hochwasser, sehr niedriges Niedrigwasser (großer Tidenhub)', 14, TXT, 500)
    save('tide-springtide.svg', b)
    # Nipptide
    cy = 230
    b = sun(-10, cy, 90) + line(80, cy, 450, cy, MUTED, 1.5, '6 6') + line(450, cy, 450, 70, MUTED, 1.5, '6 6')
    b += bulge(450, cy, 82, 100) + earth(450, cy, 55) + moon(450, 70, 22, '')
    b += t(484, 76, 'Halbmond', 14, TXT, 700, 'start')
    b += f'<path d="M450,{cy - 125} A125,125 0 0 0 325,{cy}" fill="none" stroke="{OR_D}" stroke-width="2"/>' + t(352, cy - 92, '90°', 15, OR_D, 800)
    b += t(660, 190, 'Nipptide:', 19, OR_D, 800) + t(660, 214, 'rechter Winkel', 15, OR_D, 600)
    b += t(450, 375, 'Sonne und Mond ziehen „über Kreuz“ – die Kräfte schwächen sich ab', 15, TXT, 700)
    b += t(450, 399, '→ Flut läuft kaum auf, kleiner Tidenhub', 14, TXT, 500)
    save('tide-nipptide.svg', b)
    # Sonne 45 %
    b = t(410, 50, 'Wirkung auf die Gezeiten', 19, TXT, 800)
    b += moon(110, 140, 30, '') + t(160, 146, 'Mond', 16, TXT, 700, 'start')
    b += f'<rect x="250" y="122" width="480" height="40" rx="8" fill="{SEA2}"/>' + t(740, 149, '100 %', 17, TXT, 800, 'start')
    b += f'<circle cx="110" cy="250" r="34" fill="#f9c846"/>' + t(160, 256, 'Sonne', 16, TXT, 700, 'start')
    b += f'<rect x="250" y="232" width="216" height="40" rx="8" fill="{OR}"/>' + t(476, 259, 'ca. 45 %', 17, OR_D, 800, 'start')
    b += t(410, 350, 'Die Sonne ist viel größer – aber fast 400-mal weiter weg als der Mond.', 15, TXT, 600)
    b += t(410, 374, 'Deshalb wirkt sie nur knapp halb so stark.', 15, TXT, 600)
    save('tide-sonne-45.svg', b)
    # 50 Minuten
    cx, cy = 260, 230
    b = earth(cx, cy, 70) + line(cx, cy, cx + 230, cy, MUTED, 1.5, '6 6')
    a = math.radians(-24)
    mx, my = cx + 230 * math.cos(a), cy + 230 * math.sin(a)
    b += line(cx, cy, mx, my, MUTED, 1.5, '6 6') + moon(cx + 230, cy, 24, 'Tag 1', True) + moon(mx, my, 24, 'Tag 2')
    b += f'<path d="M{cx + 120},{cy} A120,120 0 0 0 {f1(cx + 120 * math.cos(a))},{f1(cy + 120 * math.sin(a))}" fill="none" stroke="{OR_D}" stroke-width="3" marker-end="url(#ad)"/>'
    b += t(cx + 132, cy - 22, 'Mond wandert weiter', 13, OR_D, 700, 'start', halo=True)
    b += f'<path d="M{cx - 92},{cy - 30} A96,96 0 1 1 {cx - 92},{cy + 30}" fill="none" stroke="{MUTED}" stroke-width="2" marker-end="url(#am)"/>'
    b += t(cx - 105, cy + 4, 'Erde dreht', 12, MUTED, 600, 'end') + t(cx - 105, cy + 20, 'sich in 24 h', 12, MUTED, 600, 'end')
    b += f'<rect x="560" y="120" width="230" height="150" rx="12" fill="#fff" stroke="#dde5ec"/>'
    b += t(675, 152, 'Hochwasser', 15, MUTED, 700) + t(675, 186, 'Tag 1: 12:00', 18, TXT, 700) + t(675, 220, 'Tag 2: 12:50', 18, OR_D, 800)
    b += t(675, 252, 'jeden Tag ≈ 50 min später', 13, OR_D, 700)
    b += t(410, 40, 'Die Erde muss sich ein Stück weiter drehen, bis sie den Mond „einholt“', 15, TXT, 700)
    b += t(410, 410, 'Skizze übertrieben – in Wirklichkeit wandert der Mond ca. 12° pro Tag', 12, MUTED, 500)
    save('tide-50-minuten.svg', b)

# ---------------- Sturmflut ----------------
def sturmflut():
    g = 330  # Meeresboden/Grundlinie y
    def hy(m): return 380 - m * 44  # Höhe in m ü. NN → y
    b = f'<rect x="0" y="{hy(0)}" width="{W}" height="{H}" fill="{LAND}"/>'
    b += f'<path d="M0,{hy(6.45)} L560,{hy(6.45)} L560,{H} L0,{H}Z" fill="{SEA1}" opacity=".5"/>'
    b += f'<path d="M0,{hy(2.1)} L560,{hy(2.1)} L560,{H} L0,{H}Z" fill="{SEA2}" opacity=".55"/>'
    b += f'<path d="M520,{H} L600,{hy(7.4)} L660,{hy(7.4)} L760,{H} Z" fill="#8fae6b" stroke="#6d8a4f" stroke-width="2"/>'
    b += t(630, hy(7.4) - 10, 'Deich', 14, TXT, 700)
    for m, lbl, col, wgt in ((2.1, 'normales Hochwasser ≈ 2 m', SEA2, 600), (5.7, '1962: 5,70 m ü. NN (315 Tote)', RED, 700), (6.45, '1976: 6,45 m ü. NN (höchste)', RED, 800)):
        b += line(20, hy(m), 590, hy(m), col, 2.5 if m > 3 else 2, '' if m < 3 else '8 5')
        b += t(30, hy(m) - 8, lbl, 14, col, wgt, 'start', halo=True)
    for i, (x, y) in enumerate(((40, 38), (190, 38), (340, 38))):
        b += line(x, y, x + 80, y + 30, MUTED, 4, arrow='am')
    b += t(20, 24, 'Sturm aus Nordwest drückt Wasser in die Elbe', 15, TXT, 700, 'start')
    b += t(280, 405, 'Springtide + NW-Sturm = Sturmflut', 17, '#fff', 800)
    b += line(560, hy(2.1) - 4, 560, hy(6.45) + 4, OR_D, 3, arrow='ad')
    save('tide-sturmflut.svg', b)

# ---------------- Pegelturm ----------------
def pegel():
    b = f'<rect x="0" y="300" width="{W}" height="140" fill="url(#sea)"/>'
    b += f'<rect x="300" y="40" width="110" height="380" fill="#d9cdb6" stroke="#9a8a6c" stroke-width="2"/>'
    b += f'<path d="M290,40 L355,8 L420,40Z" fill="#7a4c3a"/>'
    b += f'<rect x="318" y="60" width="74" height="350" fill="#fff" stroke="#9a8a6c"/>'
    skn = 260
    for i, v in enumerate(range(40, -21, -10)):
        y = skn - v * 4.6
        col = TXT if v >= 0 else RED
        b += line(318, y, 340, y, col, 2) + t(372, y + 5, str(abs(v)), 16, col, 800)
        for k in range(1, 10):
            yy = y + k * 4.6 if v > -20 else None
            if yy and yy < 410: b += line(318, yy, 328, yy, col, 1)
    b += line(250, skn, 470, skn, OR_D, 2.5, '8 5') + t(480, skn + 5, 'Seekartennull (SKN) = 0', 15, OR_D, 800, 'start')
    b += t(480, 120, 'schwarze Zahlen = über SKN', 15, TXT, 700, 'start') + t(480, 340, 'rote Zahlen = unter SKN', 15, RED, 700, 'start')
    b += line(250, 300, 300, 300, '#fff', 3) + t(240, 326, 'aktueller', 13, '#fff', 700, 'end') + t(240, 342, 'Wasserstand', 13, '#fff', 700, 'end')
    b += t(150, 60, 'Pegelturm', 22, OR_D, 800) + t(150, 84, 'Landungsbrücken Hamburg', 13, MUTED, 600) + t(150, 104, 'Anzeige in Dezimetern', 13, MUTED, 600)
    save('tide-pegelturm.svg', b)

# ---------------- Tiefgang Elbe ----------------
def tiefgang():
    nw, hw, bottom = 150, 105, 345
    b = f'<rect x="0" y="{hw}" width="{W}" height="{H}" fill="{SEA_L}"/><rect x="0" y="{nw}" width="{W}" height="{H}" fill="{SEA1}" opacity=".55"/>'
    b += f'<rect x="0" y="{bottom}" width="{W}" height="{H}" fill="{MUD}"/>'
    b += t(808, bottom - 8, 'Grund der Fahrrinne', 12, '#2b4f66', 700, 'end')
    b += t(12, hw - 6, 'HW', 13, SEA2, 800, 'start') + t(12, nw - 6, 'NW', 13, SEA2, 800, 'start')
    for i, (lab, d, sub, wl, hi) in enumerate((('13,80 m', 138, 'immer (tideunabhängig)', nw, True), ('14,80 m', 148, 'tideabhängig auslaufend', hw, False), ('16,10 m', 161, 'tideabhängig einlaufend', hw, False))):
        x = 50 + i * 260
        b += ship(x, wl, 170, d * 1.15 - 18, '#4a5a68' if not hi else '#5b4a3a')
        keel = wl + d * 1.15 - 18
        b += line(x + 200, wl, x + 200, keel, OR_D if hi else TXT, 3, arrow='ad' if hi else 'ak', start='ad' if hi else 'ak')
        b += t(x + 85, bottom + 30, lab, 19, OR_D if hi else TXT, 800) + t(x + 85, bottom + 52, sub, 13, OR_D if hi else MUTED, 700)
    b += t(410, 30, 'Tiefgang auf der Elbe nach Hamburg', 17, TXT, 800)
    b += t(410, 52, 'einlaufend fährt das Schiff mit der Flutwelle → länger hohes Wasser', 13, MUTED, 600)
    save('tide-tiefgang-elbe.svg', b)

# ---------------- Hafentypen ----------------
def kai(x, top, bottom, w=60): return f'<rect x="{x}" y="{top}" width="{w}" height="{bottom - top}" fill="#b9b2a3" stroke="#8d8370" stroke-width="2"/>'
def haefen():
    # Tidehafen
    hw, nw = 170, 260
    b = f'<rect x="0" y="{hw}" width="680" height="{H}" fill="{SEA_L}"/><rect x="0" y="{nw}" width="680" height="{H}" fill="{SEA1}" opacity=".6"/>'
    b += f'<rect x="0" y="390" width="680" height="60" fill="{MUD}"/>' + kai(680, 110, H, 140)
    b += f'<g opacity=".45">{ship(440, hw, 220, 30)}</g>' + ship(440, nw, 220, 30)
    b += line(410, hw + 2, 410, nw - 2, OR_D, 3.5, arrow='ad', start='ad') + t(400, (hw + nw) / 2 + 5, 'Tidenhub', 14, OR_D, 800, 'end')
    b += t(20, hw - 8, 'Hochwasser', 13, SEA2, 800, 'start') + t(20, nw - 8, 'Niedrigwasser', 13, SEA2, 800, 'start')
    b += t(340, 40, 'Tidehafen: offen zum Meer', 20, OR_D, 800) + t(340, 64, 'Wasserstand steigt und fällt mit der Tide – Schiff schwimmt immer', 14, TXT, 600)
    b += t(750, 100, 'Kai', 14, TXT, 700) + t(340, 425, 'z. B. Hamburg, Rotterdam', 13, MUTED, 700)
    save('hafen-tidehafen.svg', b)
    # Fluthafen
    b = ''
    for i, (lab, wl, dry) in enumerate((('bei Flut', 200, False), ('bei Ebbe', 330, True))):
        ox = i * 410
        b += f'<rect x="{ox}" y="{wl}" width="410" height="{H}" fill="{SEA_L}"/><path d="M{ox},350 Q{ox + 205},330 {ox + 410},350 L{ox + 410},{H} L{ox},{H}Z" fill="{MUD}"/>'
        b += f'<g transform="translate({ox},0)">' + (ship(110, 322, 180, 22) if dry else ship(110, wl, 180, 22)) + '</g>'
        b += t(ox + 205, 110, lab, 18, TXT, 800) + t(ox + 205, 134, 'fällt trocken – Schiff liegt auf Grund' if dry else 'genug Wasser – Schiff schwimmt', 13, OR_D if dry else MUTED, 700)
    b += line(410, 90, 410, H, MUTED, 1.5, '5 5')
    b += t(410, 40, 'Fluthafen: nur bei Flut anzulaufen', 20, OR_D, 800) + t(410, 64, 'z. B. Husum, Büsum', 13, MUTED, 700)
    save('hafen-fluthafen.svg', b)
    # Reedehafen
    b = f'<rect x="0" y="210" width="{W}" height="{H}" fill="url(#sea)"/><path d="M640,210 L820,180 L820,{H} L700,{H} Z" fill="{LAND}"/>'
    b += f'<rect x="600" y="196" width="80" height="14" fill="#8d8370"/>' + t(720, 170, 'Insel / Hafen', 14, TXT, 700)
    b += ship(90, 210, 230, 30)
    b += f'<path d="M150,{210 + 4} Q130,300 110,370" stroke="{TXT}" stroke-width="2" fill="none" stroke-dasharray="3 3"/><path d="M100,365 l10,12 l10,-12" stroke="{TXT}" stroke-width="3" fill="none"/>'
    b += t(150, 395, 'Anker', 13, '#fff', 700)
    for x in (380, 500):
        b += f'<path d="M{x},208 L{x + 70},208 L{x + 62},222 L{x + 8},222 Z" fill="#6b5a45"/><rect x="{x + 12}" y="198" width="44" height="10" fill="{OR}"/>'
    b += line(460, 186, 570, 186, OR_D, 3, arrow='ad', start='ad') + t(515, 176, 'Schuten', 14, OR_D, 800)
    b += t(330, 60, 'Reedehafen', 22, OR_D, 800) + t(330, 86, 'Schiff liegt vor Anker auf der geschützten Reede,', 14, TXT, 600)
    b += t(330, 106, 'die Ladung wird mit kleinen Booten (Schuten) an Land gebracht', 14, TXT, 600) + t(330, 128, 'z. B. Helgoland', 13, MUTED, 700)
    save('hafen-reedehafen.svg', b)
    # Dockhafen
    b = f'<rect x="0" y="170" width="380" height="{H}" fill="{SEA_L}"/><rect x="0" y="270" width="380" height="{H}" fill="{SEA1}" opacity=".6"/>'
    b += f'<rect x="440" y="190" width="380" height="{H}" fill="{SEA1}" opacity=".8"/>'
    b += f'<rect x="0" y="390" width="{W}" height="60" fill="{MUD}"/>'
    b += f'<rect x="380" y="120" width="22" height="300" fill="#5d4b3b"/><rect x="418" y="120" width="22" height="300" fill="#5d4b3b"/>'
    b += t(410, 108, 'Schleuse', 14, TXT, 800)
    b += line(30, 170, 360, 170, SEA2, 2, '6 4') + line(30, 270, 360, 270, SEA2, 2, '6 4')
    b += line(60, 174, 60, 266, OR_D, 3, arrow='ad', start='ad') + t(70, 225, 'Tide: steigt und fällt', 14, OR_D, 700, 'start')
    b += t(190, 150, 'außen: Fluss / Meer', 15, TXT, 800)
    b += ship(530, 190, 220, 30) + t(630, 300, 'innen: gleichbleibender', 15, OR_D, 800) + t(630, 320, 'Wasserstand', 15, OR_D, 800)
    b += t(410, 40, 'Dockhafen (Schleusenhafen)', 20, OR_D, 800) + t(410, 64, 'z. B. Bremerhaven (Kaiserhäfen), Antwerpen', 13, MUTED, 700)
    save('hafen-dockhafen.svg', b)

os.makedirs(OUT, exist_ok=True)
tide_cards(); stroeme(); himmel(); sturmflut(); pegel(); tiefgang(); haefen()
