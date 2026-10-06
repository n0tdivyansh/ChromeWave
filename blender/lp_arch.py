'''
Chromewave — low-poly archetypes and detail kit (used with lowpoly.py)
======================================================================
make(d, kind, **o) turns a car's size and wheel positions into a lowpoly SPEC:
body and cabin curves come from the archetype (mid-engine, front-engine GT,
muscle notchback, rear-engine, rally hatch, prototype, beetle); the details come
from the kit below (lights, grilles, intakes, wings, exhausts, liveries).

d: dict(id, L, W, H, wh=dict(yf, yr, tf, tr, rf, rr, wf, wr, rimf, rimr), col=dict(paint, sec, stripe, caliper, rim))
Car space: meters, X right, Y forward (0 = tail), Z up.
'''
import math, random, zlib

# zsh/zd: shoulder and deck heights at (tail, rear axle, middle, front axle, nose); zb = ride height;
# fb/rb = hood/deck centre channel (< 0: fenders stand proud of the centre), bw = channel half-width;
# waist = side draw-in at the middle; nose/tail = width lost at the ends; hh = haunch over the wheels;
# xb = cabin inset from the side; xr = roof half-width;
# cab(r, f, L) = (back end, back of roof, front of roof, windshield base) along Y
KINDS = {
    'mid': dict(zsh=(0.70, 0.78, 0.64, 0.68, 0.43), zd=(0.80, 0.88, 0.84, 0.75, 0.47), zb=0.105, fb=-0.05, rb=0.0, bw=0.45,
                waist=0.06, nose=0.24, tail=0.06, hh=0.025, xb=0.20, xr=0.52, cab=lambda r, f, L: (r + 0.30, r + 1.05, f - 1.05, f - 0.45)),
    'gt': dict(zsh=(0.78, 0.84, 0.80, 0.78, 0.58), zd=(0.88, 0.95, 0.94, 0.86, 0.63), zb=0.115, fb=0.02, rb=0.0, bw=0.34,
               waist=0.03, nose=0.17, tail=0.08, hh=0.02, xb=0.17, xr=0.55, cab=lambda r, f, L: (r + 0.05, r + 0.80, f - 1.55, f - 0.95)),
    'notch': dict(zsh=(0.84, 0.86, 0.84, 0.84, 0.80), zd=(0.98, 0.99, 0.97, 0.95, 0.87), zb=0.16, fb=0.0, rb=0.0, bw=0.36,
                  waist=0.02, nose=0.06, tail=0.04, hh=0.01, xb=0.15, xr=0.62, cab=lambda r, f, L: (r + 0.50, r + 1.00, f - 1.60, f - 1.05)),
    'rear': dict(zsh=(0.70, 0.80, 0.74, 0.76, 0.50), zd=(0.78, 0.88, 0.88, 0.80, 0.53), zb=0.115, fb=-0.07, rb=-0.03, bw=0.48,
                 waist=0.04, nose=0.20, tail=0.10, hh=0.03, xb=0.18, xr=0.52, cab=lambda r, f, L: (0.45, r + 0.45, f - 1.35, f - 0.80)),
    'hatch': dict(zsh=(0.90, 0.95, 0.90, 0.86, 0.66), zd=(0.96, 1.0, 0.98, 0.90, 0.70), zb=0.19, fb=0.0, rb=0.0, bw=0.34,
                  waist=0.03, nose=0.10, tail=0.06, hh=0.04, xb=0.13, xr=0.62, cab=lambda r, f, L: (0.15, 0.75, f - 0.75, f - 0.05)),
    'lmp': dict(zsh=(0.76, 0.84, 0.60, 0.80, 0.34), zd=(0.84, 0.90, 0.64, 0.84, 0.36), zb=0.08, fb=-0.34, rb=-0.06, bw=0.38,
                waist=0.24, nose=0.18, tail=0.04, hh=0.0, xb=0.18, xr=0.32, cab=lambda r, f, L: (r + 0.85, r + 1.45, f - 1.30, f - 0.60)),
    'beetle': dict(zsh=(0.62, 0.78, 0.74, 0.80, 0.56), zd=(0.70, 0.84, 0.86, 0.86, 0.60), zb=0.15, fb=-0.10, rb=-0.08, bw=0.50,
                   waist=0.06, nose=0.22, tail=0.16, hh=0.04, xb=0.17, xr=0.45, dome=0.55,
                   cab=lambda r, f, L: (0.25, r + 0.55, f - 1.45, f - 0.70)),
}


def _curve(pts, x):
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * ((x - x0) / (x1 - x0) if x1 > x0 else 0.0)
    return pts[-1][1]


def _keys(pairs, L):
    '''Sorted keys clamped to [0, L]; of two keys closer than 5 cm the later value wins (the ends keep their Y).'''
    out = []
    for y, v in sorted((min(max(y, 0.0), L), v) for y, v in pairs):
        if out and y - out[-1][0] < 0.05:
            out[-1] = (out[-1][0] if out[-1][0] == 0.0 else y, v)
        else:
            out.append((y, v))
    return out


def _ease(a, b, t):
    return a + (b - a) * t


def dna(K, seed):
    '''Each car's own shape: a seeded variation of its archetype (heights, nose, tail, waist, haunches,
    roof width and curve, cabin position), so no two cars share a silhouette. Cars of one family
    (same `family` seed) keep the same shape on purpose.'''
    rng = random.Random(zlib.crc32(seed.encode()))
    j = lambda a: 1.0 + rng.uniform(-a, a)
    K['zsh'] = tuple(v * j(0.05) for v in K['zsh'])
    K['zd'] = tuple(v * j(0.04) for v in K['zd'])
    K['nose'] = max(0.04, K['nose'] + rng.uniform(-0.07, 0.07))
    K['tail'] = max(0.02, K['tail'] + rng.uniform(-0.03, 0.05))
    K['waist'] = max(0.0, K['waist'] + rng.uniform(-0.02, 0.04))
    K['hh'] = max(0.0, K['hh'] + rng.uniform(-0.012, 0.025))
    K['xr'] = K['xr'] + rng.uniform(-0.06, 0.05)
    K['dome'] = rng.uniform(0.65, 1.45)
    K['cab_shift'] = [rng.uniform(-0.14, 0.14) for _ in range(4)]
    return K


def make(d, kind, **o):
    K = dict(KINDS[kind])
    if o.get('dna', True):
        dna(K, o.get('family') or d['id'])
    K.update({k: v for k, v in o.items() if k in K})
    ts = o.get('tail_shape')                       # how the body ends, the first thing seen from the race camera
    if ts == 'kamm':                               # chopped: full width and height to a flat cut
        K['tail'] = 0.02
        K['zsh'] = (K['zsh'][1] * 0.99,) + tuple(K['zsh'][1:])
        K['zd'] = (K['zd'][1] * 0.99,) + tuple(K['zd'][1:])
    elif ts == 'taper':                            # boat tail: narrows and drops toward the end
        K['tail'] += 0.16
        K['zsh'] = (K['zsh'][0] * 0.85,) + tuple(K['zsh'][1:])
        K['zd'] = (K['zd'][0] * 0.84,) + tuple(K['zd'][1:])
    elif ts == 'drop':                             # fastback falling to a low tail
        K['zsh'] = (K['zsh'][0] * 0.92,) + tuple(K['zsh'][1:])
        K['zd'] = (K['zd'][0] * 0.88,) + tuple(K['zd'][1:])
    L, W, wh, col = d['L'], d['W'], d['wh'], d['col']
    r, f = wh['yr'], wh['yf']
    m = (r + f) / 2
    hw = o.get('hw', W / 2 - 0.005)
    hwr = max(hw, wh['tr'] / 2 + wh['wr'] / 2 + 0.015)
    hwf = max(hw - 0.01, wh['tf'] / 2 + wh['wf'] / 2 + 0.015)
    s = o.get('zscale', 1.0)                                   # stretches all heights (taller / lower cars)
    zsh, zd, zb = [v * s for v in K['zsh']], [v * s for v in K['zd']], K['zb']

    def five(v):
        a, b, c, e, n = v
        return _keys([(0.0, a * 0.93), (0.10, a), (r, b), (r + 0.55, _ease(b, c, 0.6)), (m, c), (f - 0.5, _ease(c, e, 0.6)), (f, e),
                      (L - 0.3, _ease(e, n, 0.6)), (L - 0.10, n + 0.01), (L, n * 0.95)], L)
    body = dict(
        zb=_keys([(0.0, zb + 0.12), (0.25, zb + 0.03), (r + 0.4, zb), (f - 0.3, zb), (L - 0.3, zb + 0.01), (L, zb + 0.05)], L),
        xw=_keys([(0.0, hw - K['tail'] - 0.07), (0.10, hw - K['tail']), (max(0.1, r - 0.35), hw - 0.02), (r, hwr), (r + 0.55, hw - 0.03),
                  (m, hw - K['waist']), (f - 0.5, hw - 0.03), (f, hwf), (L - 0.4, hw - K['nose'] * 0.4), (L - 0.1, hw - K['nose'] * 0.85),
                  (L, hw - K['nose'] - 0.03)], L),
        haunch=_keys([(0.0, 0.0), (max(0.05, r - 0.35), 0.005), (r, K['hh']), (r + 0.5, 0.0), (f - 0.4, 0.0), (f, K['hh'] * 0.6),
                      (min(L - 0.05, f + 0.4), 0.0), (L, 0.0)], L),
        zsh=five(zsh), zdeck=five(zd),
        bulge=_keys([(0.0, K['rb']), (r + 0.3, K['rb']), (r + 0.65, 0.0), (f - 0.95, 0.0), (f - 0.6, K['fb']), (L - 0.25, K['fb']),
                     (L, K['fb'] * 0.5)], L),
        bulge_w=K['bw'], deck_in=0.07, crown=0.015,
    )
    body.update(o.get('body', {}))
    knots = sorted({round(y, 3) for key in ('zb', 'xw', 'zsh', 'zdeck', 'bulge', 'haunch') for y, _ in body[key]} | {round(r, 3), round(f, 3)})
    st = []
    for y in knots:
        if not st or y - st[-1] > 0.07:
            st.append(y)
    st[-1] = L
    body['stations'] = st
    # cabin: domed slopes front and back, flat roof between, both ends hidden inside the body
    roof = o.get('roof', d['H'] - 0.02)
    yb0, yb1, yf1, yf0 = o.get('cab') or K['cab'](r, f, L)
    if not o.get('cab') and 'cab_shift' in K:                       # the car's own cabin position
        s0, s1, s2, s3 = K['cab_shift']
        yb0 = max(0.08, yb0 + s0)
        yb1 = max(yb0 + 0.25, yb1 + s1)
        yf1 = max(yb1 + 0.2, yf1 + s2)
        yf0 = min(f - 0.05, max(yf1 + 0.3, yf0 + s3))
    deck = lambda y: _curve(body['zdeck'], y)
    xwa = lambda y: _curve(body['xw'], y)
    dome = o.get('dome', K.get('dome', 1.0))
    pts = []                                              # (y, belt, roof)
    for y0, y1 in ((yb0, yb1), (yf0, yf1)):
        for t in (0.0, 0.35, 0.7):
            y = _ease(y0, y1, t)
            pts.append((y, deck(y) + 0.005, deck(y) + 0.01 + (roof - deck(y) - 0.01) * math.sin(t * math.pi / 2) ** dome))
    n = max(1, math.ceil((yf1 - yb1) / 0.45))
    for i in range(n + 1):
        y = _ease(yb1, yf1, i / n)
        pts.append((y, deck(y) + 0.005, roof + (0.01 if 0 < i < n else 0.0)))
    pts.append((yb0 - 0.07, deck(yb0) - 0.08, deck(yb0) - 0.08))
    pts.append((yf0 + 0.07, deck(yf0) - 0.08, deck(yf0) - 0.08))
    pts.sort()
    xr = K['xr']
    cabin = dict(
        stations=[p[0] for p in pts],
        belt=[(p[0], p[1]) for p in pts], roof=[(p[0], p[2]) for p in pts],
        xbelt=[(p[0], xwa(p[0]) - K['xb']) for p in pts],
        xroof=[(p[0], min(xr + (0.10 if p[0] <= yb0 or p[0] >= yf0 else 0.0), xwa(p[0]) - K['xb'] - 0.05)) for p in pts],
        crown=0.02, side_glass=(yb1 - 0.02, yf1 + 0.02), windshield=(yf1, yf0),
        rear_glass=(_ease(yb0, yb1, 0.25), yb1), rear_mat=o.get('rear_mat', 'glass'),
    )
    cabin.update(o.get('cabin', {}))
    Ra = max(wh['rf'], wh['rr']) + 0.045             # tight arches: the tyre fills the wheel well
    S = dict(
        id=d['id'], L=L, color=col['paint'], sec=col.get('sec', '#15171b'), stripe=o.get('stripe', col.get('stripe', '#f2f2f2')),
        stripes=o.get('stripes', False), lower=o.get('lower'), roof_mat=o.get('roof_mat'), mirrors=o.get('mirrors', True),
        doors=o.get('doors', True), plates=o.get('plates', True), trim=o.get('trim', 'black'), kind=kind, belt=round(sum(p[1] for p in pts) / len(pts), 4),
        wheels=dict(yf=f, yr=r, r=wh['rf'], dr=round(wh['rr'] - wh['rf'], 4), drim=round(wh['rimr'] - wh['rimf'], 4), wf=wh['wf'], wr=wh['wr'],
                    tf=wh['tf'], tr=wh['tr'], rim=wh['rimf'], style=o.get('rim', '5'), spokes=o.get('spokes', 5), sides=20,
                    caliper=col.get('caliper', '#c41a1a'), rim_color=col.get('rim', '#2a2c31'), cal_a=150),
        arches=dict(r=Ra, x_in=min(wh['tf'], wh['tr']) / 2 - max(wh['wf'], wh['wr']) / 2 - 0.07, sides=16),
        body=body, cabin=cabin,
        anchors=dict(yb0=yb0, yb1=yb1, yf1=yf1, yf0=yf0, roof=roof, Ra=Ra),
    )
    S['details'] = [kit_base] + list(o.get('details', ()))
    return S


# ------------------------------------------------------------------ detail kit
def B(c, key, y):
    return _curve(c['S']['body'][key], y)


def circle(cx, cy, rad, n=10):
    return [(cx + rad * math.cos(2 * math.pi * (i + 0.5) / n), cy + rad * math.sin(2 * math.pi * (i + 0.5) / n)) for i in range(n)]


def scale_poly(poly, k):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in poly]


def grow(poly, d):
    '''Pushes every corner d metres away from the centre (a surround for a lamp).'''
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out = []
    for x, y in poly:
        l = math.hypot(x - cx, y - cy) or 1.0
        out.append((x + (x - cx) / l * d, y + (y - cy) / l * d))
    return out


def kit_base(c):
    '''Every car: mirrors, door lines and a handle.'''
    S, mb, C = c['S'], c['mb'], c['S']['cabin']
    A, W = S['anchors'], S['wheels']
    cf, L = c['conform'], S['L']
    if S.get('mirrors', True):
        y = A['yf0'] - 0.22
        zb_, xb_ = _curve(C['belt'], y + 0.1), _curve(C['xbelt'], y + 0.1)
        for sx in (1, -1):
            mirror_part(mb, xb_, y, zb_, sx=sx)
    # wipers resting at the foot of the windshield
    yw = A['yf0'] - 0.09
    cf([(0.03, yw), (0.52, yw + 0.035), (0.52, yw + 0.047), (0.03, yw + 0.012)], 'top', 'black', off=0.006, sub=1)
    # chrome badges on the nose and the tail
    zn_b, zt_b = B(c, 'zsh', L - 0.1) - 0.03, B(c, 'zsh', 0.0) - 0.15
    cf(circle(0.0, zn_b, 0.032, 8), 'front', 'badge', off=0.012, mirror=False, wall=True, wall_mat='badge')
    cf(circle(0.0, zt_b, 0.032, 8), 'rear', 'badge', off=0.012, mirror=False, wall=True, wall_mat='badge')
    if S.get('plates', True):
        zt, zn = B(c, 'zb', 0.0), B(c, 'zb', L)
        cf([(-0.27, zt + 0.12), (0.27, zt + 0.12), (0.27, zt + 0.26), (-0.27, zt + 0.26)], 'rear', 'black', off=0.004, mirror=False)
        cf([(-0.25, zt + 0.13), (0.25, zt + 0.13), (0.25, zt + 0.25), (-0.25, zt + 0.25)], 'rear', 'plate', off=0.006, mirror=False)
        cf([(-0.24, zn + 0.05), (0.24, zn + 0.05), (0.24, zn + 0.15), (-0.24, zn + 0.15)], 'front', 'plate', off=0.008, mirror=False)
    if S.get('doors', True):
        y1 = W['yf'] - A['Ra'] - 0.08
        y0 = max(W['yr'] + A['Ra'] + 0.08, y1 - 1.25)
        zlo = B(c, 'zb', (y0 + y1) / 2) + 0.16
        ztop = _curve(C['belt'], (y0 + y1) / 2) - 0.03
        g = 0.0035
        cf = c['conform']
        cf([(y1 - g, zlo), (y1 + g, zlo), (y1 + g - 0.02, ztop), (y1 - g - 0.02, ztop)], 'side', 'gap', off=0.002, sub=1)
        cf([(y0 - g, zlo), (y0 + g, zlo), (y0 + g + 0.02, ztop), (y0 - g + 0.02, ztop)], 'side', 'gap', off=0.002, sub=1)
        cf([(y0, zlo - g), (y1, zlo - g), (y1, zlo + g), (y0, zlo + g)], 'side', 'gap', off=0.002, sub=1)
        cf([(y0 + 0.12, ztop - 0.10), (y0 + 0.28, ztop - 0.10), (y0 + 0.28, ztop - 0.085), (y0 + 0.12, ztop - 0.085)], 'side', 'black', off=0.004, sub=1)


def rear_lights(style='slim', z=None, panel=False, mat='tail'):
    def fn(c):
        c['S']['tail_style'] = style
        cf, xt = c['conform'], B(c, 'xw', 0.0)
        zl = z if z is not None else B(c, 'zsh', 0.0) - 0.05

        def lamp(p, off=0.004, mirror=True):          # lit element in a raised black housing, under a red lens
            cf(grow(p, 0.012), 'rear', 'black', off=off + 0.008, mirror=mirror, wall=True)
            cf(p, 'rear', mat, off=off + 0.009, mirror=mirror)
            cf(p, 'rear', 'lensred', off=off + 0.012, mirror=mirror)
        if panel:
            cf([(-xt * 0.93, zl - 0.06), (xt * 0.93, zl - 0.06), (xt * 0.93, zl + 0.05), (-xt * 0.93, zl + 0.05)], 'rear', 'black', off=0.002, mirror=False)
        if style == 'bar':
            lamp([(-xt * 0.9, zl - 0.022), (xt * 0.9, zl - 0.022), (xt * 0.9, zl + 0.018), (-xt * 0.9, zl + 0.018)], off=0.004, mirror=False)
        elif style == 'slim':
            lamp([(xt * 0.50, zl - 0.02), (xt * 0.94, zl - 0.005), (xt * 0.93, zl + 0.035), (xt * 0.53, zl + 0.022)], off=0.004)
        elif style == 'wide':
            lamp([(xt * 0.42, zl - 0.04), (xt * 0.94, zl - 0.04), (xt * 0.94, zl + 0.04), (xt * 0.42, zl + 0.04)], off=0.004)
            cf([(xt * 0.44, zl - 0.005), (xt * 0.92, zl - 0.005), (xt * 0.92, zl + 0.005), (xt * 0.44, zl + 0.005)], 'rear', 'black', off=0.018)
        elif style in ('round', 'round2', 'ring'):
            for x in ((0.76,) if style == 'round' else (0.64, 0.86)):
                lamp(circle(xt * x, zl, 0.06), off=0.004)
                if style == 'ring':
                    cf(circle(xt * x, zl, 0.032), 'rear', 'black', off=0.018)
        elif style == 'x':
            lamp([(xt * 0.55, zl - 0.05), (xt * 0.62, zl - 0.05), (xt * 0.92, zl + 0.04), (xt * 0.85, zl + 0.04)], off=0.004)
            lamp([(xt * 0.55, zl + 0.04), (xt * 0.62, zl + 0.04), (xt * 0.92, zl - 0.05), (xt * 0.85, zl - 0.05)], off=0.005)
        elif style == 'c':
            lamp([(xt * 0.60, zl - 0.05), (xt * 0.93, zl - 0.05), (xt * 0.93, zl - 0.02), (xt * 0.60, zl - 0.02)], off=0.004)
            lamp([(xt * 0.60, zl + 0.02), (xt * 0.93, zl + 0.02), (xt * 0.93, zl + 0.05), (xt * 0.60, zl + 0.05)], off=0.004)
            lamp([(xt * 0.90, zl - 0.05), (xt * 0.93, zl - 0.05), (xt * 0.93, zl + 0.05), (xt * 0.90, zl + 0.05)], off=0.0045)
        elif style == 'vbar':
            lamp([(xt * 0.86, zl - 0.12), (xt * 0.93, zl - 0.12), (xt * 0.93, zl + 0.05), (xt * 0.86, zl + 0.05)], off=0.004)
        elif style == 'dots':                     # three round lamps in a row
            for x in (0.58, 0.72, 0.86):
                lamp(circle(xt * x, zl, 0.034, 8))
        elif style == 'stack':                    # two thin stacked bars
            for dz in (0.024, -0.024):
                lamp([(xt * 0.50, zl + dz - 0.011), (xt * 0.93, zl + dz - 0.011), (xt * 0.93, zl + dz + 0.011), (xt * 0.50, zl + dz + 0.011)])
        elif style == 'arrow':                    # chevron pointing inward
            lamp([(xt * 0.52, zl), (xt * 0.78, zl + 0.055), (xt * 0.93, zl + 0.055), (xt * 0.70, zl), (xt * 0.93, zl - 0.055), (xt * 0.78, zl - 0.055)])
        elif style == 'hook':                     # L-shaped lamp wrapping the corner
            lamp([(xt * 0.55, zl - 0.022), (xt * 0.93, zl - 0.022), (xt * 0.93, zl + 0.06), (xt * 0.87, zl + 0.06), (xt * 0.87, zl + 0.012),
                  (xt * 0.55, zl + 0.012)])
        elif style == 'pill':                     # long rounded capsule
            lamp([(xt * 0.73 + 0.13 * math.cos(2 * math.pi * i / 14), zl + 0.03 * math.sin(2 * math.pi * i / 14)) for i in range(14)])
        elif style == 'quad':                     # 2 x 2 square lamps
            for x, dz in ((0.64, 0.032), (0.82, 0.032), (0.64, -0.032), (0.82, -0.032)):
                lamp([(xt * x - 0.04, zl + dz - 0.022), (xt * x + 0.04, zl + dz - 0.022), (xt * x + 0.04, zl + dz + 0.022), (xt * x - 0.04, zl + dz + 0.022)])
        elif style == 'halo':                     # square lamp with a dark centre
            lamp([(xt * 0.74 - 0.075, zl - 0.05), (xt * 0.74 + 0.075, zl - 0.05), (xt * 0.74 + 0.075, zl + 0.05), (xt * 0.74 - 0.075, zl + 0.05)])
            cf([(xt * 0.74 - 0.042, zl - 0.022), (xt * 0.74 + 0.042, zl - 0.022), (xt * 0.74 + 0.042, zl + 0.022), (xt * 0.74 - 0.042, zl + 0.022)],
               'rear', 'black', off=0.02)
        elif style == 'strip3':                   # three short strips in a row
            for x0, x1 in ((0.50, 0.62), (0.66, 0.78), (0.82, 0.94)):
                lamp([(xt * x0, zl - 0.014), (xt * x1, zl - 0.014), (xt * x1, zl + 0.014), (xt * x0, zl + 0.014)])
        elif style == 'split':                    # near full-width bar broken in the middle, with tall outer ends
            lamp([(xt * 0.16, zl - 0.012), (xt * 0.88, zl - 0.012), (xt * 0.88, zl - 0.06), (xt * 0.94, zl - 0.06), (xt * 0.94, zl + 0.05),
                  (xt * 0.88, zl + 0.05), (xt * 0.88, zl + 0.012), (xt * 0.16, zl + 0.012)])
        elif style == 'blade':                    # tall thin outer blade plus a short top bar
            lamp([(xt * 0.90, zl - 0.09), (xt * 0.945, zl - 0.09), (xt * 0.945, zl + 0.05), (xt * 0.90, zl + 0.05)])
            lamp([(xt * 0.56, zl + 0.034), (xt * 0.88, zl + 0.034), (xt * 0.88, zl + 0.05), (xt * 0.56, zl + 0.05)], off=0.0045)
    return fn


def front_lights(style='slim', z=None, xk=1.0, size=0.075):
    def fn(c):
        c['S']['front_style'] = style
        cf, L = c['conform'], c['L']
        xn = B(c, 'xw', L - 0.15) * xk
        zl = z if z is not None else B(c, 'zsh', L - 0.15) - 0.05
        if style == 'round2':
            for x in (0.60, 0.84):
                cf(circle(xn * x, zl, 0.07, 10), 'front', 'black', off=0.012, wall=True)
                cf(circle(xn * x, zl, 0.058, 10), 'front', 'head', off=0.013)
                cf(circle(xn * x, zl, 0.058, 10), 'front', 'lens', off=0.017)
            return
        if style == 'quad':
            for x in (0.62, 0.74, 0.86):
                cf(circle(xn * x, zl, 0.045, 8), 'front', 'black', off=0.012, wall=True)
                cf(circle(xn * x, zl, 0.035, 8), 'front', 'head', off=0.013)
                cf(circle(xn * x, zl, 0.035, 8), 'front', 'lens', off=0.017)
            return
        if style == 'blade':
            for x in (0.70, 0.78, 0.86):
                p = [(xn * x - 0.012, zl - 0.07), (xn * x + 0.012, zl - 0.07), (xn * x + 0.012, zl + 0.05), (xn * x - 0.012, zl + 0.05)]
                cf(grow(p, 0.008), 'front', 'black', off=0.012, wall=True)
                cf(p, 'front', 'drl', off=0.013)
                cf(p, 'front', 'lens', off=0.017)
            return
        poly = {
            'slim': [(0.58, -0.03), (0.93, -0.01), (0.92, 0.035), (0.62, 0.02)],
            'tear': [(0.55, -0.02), (0.92, 0.0), (0.93, 0.04), (0.66, 0.03), (0.60, -0.09), (0.56, -0.09)],
            'wide': [(0.52, -0.04), (0.92, -0.03), (0.92, 0.04), (0.55, 0.03)],
            'pop': [(0.55, -0.018), (0.92, -0.01), (0.92, 0.018), (0.56, 0.012)],
        }.get(style)
        poly = circle(xn * 0.74, zl, size, 12) if style == 'round' else [(xn * x, zl + dz) for x, dz in poly]
        cf(grow(poly, 0.012), 'front', 'black', off=0.012, wall=True)
        cf(poly, 'front', 'head', off=0.013)
        xs, lo = [p[0] for p in poly], min(p[1] for p in poly)
        cf([(min(xs) + 0.02, lo + 0.004), (max(xs) - 0.02, lo + 0.004), (max(xs) - 0.02, lo + 0.014), (min(xs) + 0.02, lo + 0.014)], 'front', 'drl', off=0.0145)
        cf(poly, 'front', 'lens', off=0.017)
    return fn


def grille(style='wide', mat='mesh', z0=None, z1=None, w=0.62, frame_mat='black'):
    def fn(c):
        c['S']['grille_style'] = style
        cf, L = c['conform'], c['L']
        xn = B(c, 'xw', L - 0.05)
        a = z0 if z0 is not None else B(c, 'zb', L) + 0.09
        b = z1 if z1 is not None else B(c, 'zsh', L) - 0.06

        def frame(p):
            cf(scale_poly(p, 1.08), 'front', frame_mat, off=0.002, mirror=False)
            cf(p, 'front', mat, off=0.004, mirror=False)
        if style == 'wide':
            frame([(-xn * w, a), (xn * w, a), (xn * w * 0.95, b), (-xn * w * 0.95, b)])
        elif style == 'mouth3':
            frame([(-xn * 0.32, a), (xn * 0.32, a), (xn * 0.30, a + 0.11), (-xn * 0.30, a + 0.11)])
            cf([(xn * 0.52, a), (xn * 0.86, a + 0.02), (xn * 0.84, a + 0.15), (xn * 0.55, a + 0.12)], 'front', mat, off=0.004)
        elif style == 'horseshoe':
            frame([(-0.16, a), (0.16, a), (0.2, (a + b) / 2), (0.14, b), (-0.14, b), (-0.2, (a + b) / 2)])
            cf([(xn * 0.45, a - 0.02), (xn * 0.85, a), (xn * 0.83, a + 0.12), (xn * 0.47, a + 0.10)], 'front', mat, off=0.004)
        elif style == 'hex':
            frame([(-xn * 0.36, a), (xn * 0.36, a), (xn * 0.46, (a + b) / 2), (xn * 0.36, b), (-xn * 0.36, b), (-xn * 0.46, (a + b) / 2)])
        elif style == 'low':
            frame([(-xn * w, a), (xn * w, a), (xn * w, a + 0.08), (-xn * w, a + 0.08)])
        elif style == 'lmp':
            cf([(-0.28, a), (0.28, a), (0.24, a + 0.07), (-0.24, a + 0.07)], 'front', mat, off=0.004, mirror=False)
    return fn


def splitter(mat='matte', depth=0.35, ext=0.05, wk=0.95):
    def fn(c):
        L = c['L']
        xn = B(c, 'xw', L - 0.1) * wk
        z = B(c, 'zb', L)
        c['mb'].box(-xn, xn, L - depth, L + ext, z - 0.035, z - 0.005, mat)
    return fn


def diffuser(fins=2, mat='matte'):
    def fn(c):
        mb = c['mb']
        xt = B(c, 'xw', 0.0) * 0.82
        z0, z1 = B(c, 'zb', 0.35), B(c, 'zb', 0.0) - 0.005
        top = max(z1, z0 + 0.06)
        mb.box(-xt, xt, -0.03, 0.40, z0 - 0.02, top, mat)
        for i in range(fins):
            x = xt * (0.25 + 0.6 * i / max(1, fins - 1))
            mb.box(x - 0.008, x + 0.008, -0.035, 0.30, z0 - 0.06, top, mat, mirror=True)
    return fn


def exhausts(style='dual', z=None, r=0.042):
    def fn(c):
        c['S']['exhaust_style'] = style
        xt = B(c, 'xw', 0.0)
        zz = z if z is not None else B(c, 'zb', 0.3) + 0.06
        tips = {'dual': [(xt * 0.62, True)], 'quad': [(xt * 0.56, True), (xt * 0.70, True)], 'center2': [(0.075, True)],
                'center1': [(0.0, False)], 'hex': [(0.10, True), (0.22, True), (0.34, True)], 'twin_high': [(0.16, True)]}[style]
        for x, mir in tips:
            c['mb'].tube_y(x, zz, r, -0.07, 0.3, 'exhaust', end_mat='hole', mirror=mir)
    return fn


def wing(style='wing', y0=0.02, chord=0.26, span=None, z=None, mat='wing_carbon', posts=0.34):
    def fn(c):
        c['S']['wing_style'] = style
        mb, S = c['mb'], c['S']
        xt = B(c, 'xw', 0.1)
        if style in ('duck', 'lip'):
            zt = B(c, 'zdeck', 0.0)
            k = 1.0 if style == 'duck' else 0.55
            mb.prism([(-0.015, zt + 0.055 * k), (0.28 * k, zt - 0.005), (0.0, zt - 0.03)], 'x', -xt * 0.86, xt * 0.86, 'wing_paint')
            return
        sp = span if span is not None else xt * 0.92
        deck = B(c, 'zdeck', y0 + chord * 0.5)
        zw = z if z is not None else deck + 0.25
        if style == 'roof':
            zw = z if z is not None else S['anchors']['roof'] + 0.02
        mb.prism([(y0, zw), (y0 + chord, zw + 0.04), (y0 + chord, zw + 0.058), (y0 - 0.005, zw + 0.022)], 'x', -sp, sp, mat)
        for sx in (1, -1):
            x = sx * sp
            mb.box(min(x, x + sx * 0.014), max(x, x + sx * 0.014), y0 - 0.04, y0 + chord + 0.03, zw - 0.09, zw + 0.11, mat)
        if style in ('wing', 'swan'):
            top = zw + (0.10 if style == 'swan' else 0.0)
            mb.box(posts - 0.01, posts + 0.01, y0 + chord * 0.35, y0 + chord * 0.65, deck - 0.03, top, 'wing_black', mirror=True)
    return fn


def side_intake(mat='black', k=1.0):
    def fn(c):
        W, Ra = c['S']['wheels'], c['S']['anchors']['Ra']
        y0 = W['yr'] + Ra + 0.06
        y1 = y0 + 0.55 * k
        zlo, zs = B(c, 'zb', y0) + 0.2, B(c, 'zsh', y1) - 0.08
        c['conform']([(y0, zlo + 0.05), (y1, zlo - 0.02), (y1, zs), (y0 + 0.12, (zlo + zs) / 2 + 0.03)], 'side', mat, off=0.004)
    return fn


def fender_vents(mat='black'):
    def fn(c):
        W, Ra = c['S']['wheels'], c['S']['anchors']['Ra']
        y1 = W['yf'] - Ra - 0.03
        z = B(c, 'zsh', W['yf']) - 0.12
        for i in range(3):
            yy = y1 - 0.06 * i
            c['conform']([(yy - 0.025, z - 0.1), (yy, z - 0.1), (yy + 0.03, z), (yy + 0.005, z)], 'side', mat, off=0.004, sub=1)
    return fn


def louvers(n=5, y0=0.25, y1=None, xw=0.42, mat='black'):
    def fn(c):
        b = y1 if y1 is not None else c['S']['anchors']['yb0'] - 0.05
        for i in range(n):
            y = y0 + (b - y0) * (i + 0.5) / n
            c['conform']([(0.05, y - 0.018), (xw, y - 0.018), (xw, y + 0.018), (0.05, y + 0.018)], 'top', mat, off=0.004, sub=1)
    return fn


def hood_vents(y=None, mat='black', w=0.16, x=0.30):
    def fn(c):
        yy = y if y is not None else c['S']['wheels']['yf'] + 0.1
        c['conform']([(x, yy - 0.12), (x + w, yy - 0.10), (x + w, yy + 0.12), (x + 0.02, yy + 0.10)], 'top', mat, off=0.004)
    return fn


def naca(mat='black'):
    def fn(c):
        f = c['S']['wheels']['yf']
        c['conform']([(0.18, f - 0.45), (0.30, f - 0.45), (0.26, f - 0.05), (0.22, f - 0.05)], 'top', mat, off=0.004)
    return fn


def roof_scoop(mat='black'):
    def fn(c):
        A, mb = c['S']['anchors'], c['mb']
        yc = (A['yb1'] + A['yf1']) / 2 - 0.1
        z = A['roof'] + 0.01
        mb.prism([(yc - 0.35, z - 0.03), (yc + 0.25, z - 0.03), (yc + 0.25, z + 0.12), (yc + 0.05, z + 0.12)], 'x', -0.16, 0.16, 'paint')
        mb.box(-0.13, 0.13, yc + 0.252, yc + 0.256, z, z + 0.10, mat)
    return fn


def fin(mat='paint'):
    def fn(c):
        A = c['S']['anchors']
        z, zt = A['roof'], B(c, 'zdeck', 0.05)
        c['mb'].prism([(A['yb1'], z), (0.05, zt + 0.10), (0.05, zt - 0.02), (A['yb1'] + 0.3, z - 0.1)], 'x', -0.008, 0.008, mat)
    return fn


def side_band(mat='sec', z0=None, h=0.07, y0=0.25, y1=None):
    def fn(c):
        L = c['L']
        b = y1 if y1 is not None else L - 0.35
        za = z0 if z0 is not None else B(c, 'zb', L / 2) + 0.2
        c['conform']([(y0, za), (b, za), (b, za + h), (y0, za + h)], 'side', mat, off=0.003, sub=2)
    return fn


def roundel(mat='c_f2f3f5', y=None, z=None, rad=0.17):
    def fn(c):
        W = c['S']['wheels']
        yy = y if y is not None else (W['yr'] + W['yf']) / 2 + 0.1
        zz = z if z is not None else B(c, 'zsh', yy) - 0.28
        c['conform'](circle(yy, zz, rad, 16), 'side', mat, off=0.003)
    return fn


def _deck(c, y):
    '''Height of the deck centre line at y.'''
    B_ = c['S']['body']
    return _curve(B_['zdeck'], y) + _curve(B_['bulge'], y) + B_['crown']


def buttresses(mat='paint'):
    '''Flying buttresses: fins running from the back of the roof down to the tail deck.'''
    def fn(c):
        A, C = c['S']['anchors'], c['S']['cabin']
        xr = _curve(C['xroof'], A['yb1'])
        y_end = max(0.15, A['yb0'] - 0.2)
        z0, z1 = A['roof'] - 0.02, _deck(c, y_end)
        for sx in (1, -1):
            xa, xb = sorted((sx * (xr + 0.01), sx * (xr + 0.06)))
            c['mb'].prism([(A['yb1'] + 0.04, z0), (y_end, z1 + 0.01), (y_end, z1 - 0.05), (A['yb1'] + 0.04, z0 - 0.07)], 'x', xa, xb, mat)
    return fn


def spine(mat='paint'):
    '''A raised ridge along the centre of the engine cover, from the tail up to the roof.'''
    def fn(c):
        A = c['S']['anchors']
        y0, y1 = 0.12, A['yb1']
        z0, top = _deck(c, y0), A['roof'] - 0.04
        c['mb'].prism([(y0, z0 + 0.05), (y1, top), (y1, top - 0.08), (y0, z0 - 0.02)], 'x', -0.035, 0.035, mat)
    return fn


def hump(mat='paint'):
    '''A raised engine bump with black slats on the rear deck.'''
    def fn(c):
        A, mb = c['S']['anchors'], c['mb']
        y0, y1 = 0.30, max(0.55, A['yb0'] - 0.02)
        z = max(_deck(c, y0), _deck(c, y1))
        mb.prism([(-0.30, z - 0.04), (0.30, z - 0.04), (0.26, z + 0.06), (-0.26, z + 0.06)], 'y', y0, y1, mat)
        n = 4
        for i in range(n):
            y = y0 + (y1 - y0) * (i + 0.5) / n
            mb.box(-0.22, 0.22, y - 0.018, y + 0.018, z + 0.055, z + 0.068, 'black')
    return fn


def blower():
    '''Supercharger through the hood (muscle cars).'''
    def fn(c):
        mb, f = c['mb'], c['S']['wheels']['yf']
        z = B(c, 'zdeck', f - 0.3)
        mb.box(-0.20, 0.20, f - 0.62, f - 0.08, z - 0.05, z + 0.12, 'chrome')
        mb.prism([(f - 0.55, z + 0.12), (f - 0.12, z + 0.12), (f - 0.12, z + 0.26), (f - 0.40, z + 0.24)], 'x', -0.16, 0.16, 'black')
    return fn
