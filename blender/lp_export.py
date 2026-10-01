'''
Speed Rush — car model export ("lp2" format)
============================================
Turns a car built by lowpoly.py into the game's model data (js/car-models.js) and the
2D-fallback data in js/data.js (side silhouette + rear panel description).

lp2 record: {meta, z}. z = base64(zlib(bytes)); bytes = the meshes in meta.meshes order,
each one laid out as planes (little endian, padded to 4 bytes):
    pos   3 x nv x uint16   position quantised to [qmin, qmax] (metres; X right, Y forward
                            with Y = 0 at the tail, Z up)
    nrm   3 x nv x int8     unit normal x 127
    pal   nv x uint8        index into meta.palette = [game material, sRGB colour]
    ao    nv x uint8        ambient occlusion (255 = open)
    idx   ni x uint16       triangle indices (uint32 when meta.meshes[i].idx32)
Meshes with mirror=true hold only the X >= 0 half; the game mirrors them.
Triangles wind counter-clockwise seen from outside.
'''
import bpy, bmesh, math, json, zlib, base64, os, struct
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# game materials (names match the table in js/car-gl.js); index = position in this list
GAME_MATS = ['paint', 'sec', 'stripe', 'plastic', 'gloss', 'chrome', 'metal', 'glass', 'lens', 'lensred', 'rubber', 'tail',
             'head', 'amber', 'emit', 'caliper', 'carbon', 'mesh', 'dark', 'rim', 'livery', 'wingc', 'wingp', 'wingk', 'wings', 'wingl']

# builder material -> (game material, fixed sRGB colour, or None when the game sets it per car)
BUILD_MATS = {
    'paint': ('paint', None), 'sec': ('sec', None), 'stripe': ('stripe', None), 'rim': ('rim', None), 'caliper': ('caliper', None),
    'black': ('gloss', '#0c0c0e'), 'matte': ('plastic', '#151517'), 'carbon': ('carbon', '#18191c'), 'glass': ('glass', '#0b0d11'),
    'chrome': ('chrome', '#e6e6e8'), 'rubber': ('rubber', '#1b1b1d'), 'tread': ('rubber', '#111113'), 'disc': ('metal', '#6c6c70'),
    'tail': ('tail', '#b3101a'), 'taildark': ('gloss', '#1c0305'), 'reverse': ('gloss', '#cfd0d4'), 'head': ('chrome', '#b9bdc6'),
    'drl': ('emit', '#eef4ff'), 'amber': ('amber', '#ff8a12'), 'mesh': ('mesh', '#0d0d0f'), 'exhaust': ('metal', '#aaa49e'),
    'hole': ('dark', '#000000'), 'well': ('dark', '#0b0b0c'), 'under': ('dark', '#0e0e0f'), 'plate': ('plastic', '#dcdcd4'),
    'badge': ('chrome', '#dcdce0'), 'lens': ('lens', '#ffffff'), 'lensred': ('lensred', '#c8101e'), 'gap': ('dark', '#050506'),
    'wing_carbon': ('wingc', '#18191c'), 'wing_paint': ('wingp', None), 'wing_black': ('wingk', '#0c0c0e'), 'wing_sec': ('wings', None),
}


def game_mat(name):
    if name in BUILD_MATS:
        return BUILD_MATS[name]
    if name.startswith('c_') and len(name) == 8:          # fixed-colour livery paint
        return ('livery', '#' + name[2:])
    return ('plastic', '#333333')


def _rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _interp(pts, y):
    if y <= pts[0][0]:
        return pts[0][1]
    for a, b in zip(pts, pts[1:]):
        if y <= b[0]:
            return a[1] + (b[1] - a[1]) * ((y - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0)
    return pts[-1][1]


# ------------------------------------------------------------------ occlusion
def fib_dirs(k):
    '''k directions spread evenly over the upper hemisphere (golden-angle spiral, cosine weighted).'''
    out, ga = [], math.pi * (3 - math.sqrt(5))
    for i in range(k):
        r = math.sqrt((i + 0.5) / k)
        t = i * ga
        out.append((r * math.cos(t), r * math.sin(t), math.sqrt(max(0.0, 1 - r * r))))
    return out


def occluder(obs):
    verts, polys = [], []
    for ob in obs:
        mw = ob.matrix_world
        b = len(verts)
        verts += [mw @ v.co for v in ob.data.vertices]
        polys += [[b + i for i in p.vertices] for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def occlusion(p, n, trees, dirs, reach, ground):
    a = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    t1 = n.cross(a).normalized()
    t2 = n.cross(t1)
    o = p + n * 0.003
    hit = 0
    for x, y, z in dirs:
        d = (t1 * x + t2 * y + n * z).normalized()
        if ground and d.z < -1e-4 and 0 < -o.z / d.z < reach:
            hit += 1
            continue
        if any(t.ray_cast(o, d, reach)[0] is not None for t in trees):
            hit += 1
    return 1.0 - hit / len(dirs)


def smooth_occlusion(verts, tris, passes=2):
    '''Averages occlusion over neighbouring positions (split normals share a position).'''
    key = [(round(v[0], 4), round(v[1], 4), round(v[2], 4)) for v in verts]
    acc = {}
    for i, k in enumerate(key):
        acc.setdefault(k, []).append(verts[i][7])
    val = {k: sum(a) / len(a) for k, a in acc.items()}
    nb = {k: set() for k in val}
    for t in tris:
        ks = [key[i] for i in t]
        for a in ks:
            nb[a].update(b for b in ks if b != a)
    for _ in range(passes):
        val = {k: (0.5 * val[k] + 0.5 * sum(val[j] for j in nb[k]) / len(nb[k])) if nb[k] else val[k] for k in val}
    return [v[:7] + (val[key[i]],) + v[8:] for i, v in enumerate(verts)]


# ------------------------------------------------------------------ mesh extraction
def extract(ob, trees, mirror=False, local=False, rays=40, reach=0.55, ground=True):
    '''Game vertices (x, y, z, nx, ny, nz, rgb, ao, mat index) and triangles of an object.'''
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    if not local:
        bm.transform(ob.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    if mirror:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new('lp_export_tmp')
    bm.to_mesh(me)
    bm.free()
    names = [m.name[3:] if m and m.name.startswith('tg_') else '' for m in ob.data.materials]
    dirs = fib_dirs(rays)
    cn, V = me.corner_normals, me.vertices
    verts, index, tris, ao_cache = [], {}, [], {}
    for poly in me.polygons:
        if len(poly.vertices) != 3:
            continue
        gm, col = game_mat(names[poly.material_index] if poly.material_index < len(names) else 'paint')
        rgb = _rgb(col) if col else (255, 255, 255)
        mi = GAME_MATS.index(gm)
        ids = []
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            p = V[vi].co
            n = Vector(cn[li].vector)
            if mirror and abs(p.x) < 1e-5:
                n.x = 0.0
            if n.length < 1e-6:
                n = Vector(poly.normal)
            n.normalize()
            nk = (round(n.x, 2), round(n.y, 2), round(n.z, 2))
            a = ao_cache.get((vi, nk))
            if a is None:
                a = ao_cache[(vi, nk)] = occlusion(p, n, trees, dirs, reach, ground)
            key = (vi, nk, mi, rgb)
            j = index.get(key)
            if j is None:
                j = index[key] = len(verts)
                verts.append((p.x, p.y, p.z, n.x, n.y, n.z, rgb, a, mi))
            ids.append(j)
        tris.append(ids)
    bpy.data.meshes.remove(me)
    return verts, tris


def pack(verts, tris, palette):
    '''One mesh -> (bytes, meta) in the lp2 layout.'''
    nv, ni = len(verts), len(tris) * 3
    qmin = [min(v[i] for v in verts) for i in range(3)]
    qmax = [max(v[i] for v in verts) for i in range(3)]
    qmax = [b if b - a > 1e-6 else a + 1e-3 for a, b in zip(qmin, qmax)]
    out = bytearray()
    for c in range(3):
        out += struct.pack('<%dH' % nv, *[int(round((v[c] - qmin[c]) / (qmax[c] - qmin[c]) * 65535)) for v in verts])
    for c in range(3):
        out += struct.pack('<%db' % nv, *[max(-127, min(127, int(round(v[3 + c] * 127)))) for v in verts])
    pal = []
    for v in verts:
        key = (GAME_MATS[v[8]], '#%02x%02x%02x' % v[6])
        if key not in palette:
            palette[key] = len(palette)
        pal.append(palette[key])
    if len(palette) > 255:
        raise ValueError('more than 255 palette entries')
    out += bytes(pal)
    out += bytes(max(0, min(255, int(round(v[7] * 255)))) for v in verts)
    idx32 = nv > 65535
    flat = [i for t in tris for i in t]
    out += struct.pack(('<%dI' if idx32 else '<%dH') % ni, *flat)
    while len(out) % 4:
        out.append(0)
    return bytes(out), dict(nv=nv, ni=ni, idx32=idx32, qmin=[round(x, 6) for x in qmin], qmax=[round(x, 6) for x in qmax])


def anchors(verts, tris, pred, cell=0.12, rmin=0.04, rmax=0.09):
    '''Glow / flame anchor points: centres of the matching triangles, gathered in a grid of
    `cell` metres across X-Z (so a long light bar gives several points).'''
    cells = {}
    for t in tris:
        c = [sum(verts[i][k] for i in t) / 3 for k in range(3)]
        if not pred(verts[t[0]][8], c):
            continue
        cells.setdefault((round(c[0] / cell), round(c[2] / cell)), []).append(c)
    out = []
    for pts in cells.values():
        cx, cy, cz = (sum(p[k] for p in pts) / len(pts) for k in range(3))
        r = max(max(abs(p[0] - cx), abs(p[2] - cz)) for p in pts) + 0.02
        out.append(([round(cx, 4), round(cy, 4), round(cz, 4)], round(min(max(r, rmin), rmax), 4)))
    return out


def export_car(S, out_dir, rays=40):
    '''Writes out_dir/<id>.json = {meta, z} for a car built by lowpoly.build_lowpoly.'''
    cid, L, W = S['id'], S['L'], S['wheels']
    body = bpy.data.objects[cid]
    wf, wr = bpy.data.objects[cid + '_wheel_f'], bpy.data.objects[cid + '_wheel_r']
    wl = [bpy.data.objects[cid + '_wl_f'], bpy.data.objects[cid + '_wl_r']]
    bv, bt = extract(body, [occluder([body]), occluder([wf, wr] + wl)], mirror=True, rays=rays)
    bv = smooth_occlusion(bv, bt)
    wtree = BVHTree.FromPolygons([v.co.copy() for v in wf.data.vertices], [list(p.vertices) for p in wf.data.polygons])
    wv, wt = extract(wf, [wtree], local=True, rays=12, reach=0.25, ground=False)
    palette = {}
    b1, m1 = pack(bv, bt, palette)
    b2, m2 = pack(wv, wt, palette)
    m1.update(name='body', mirror=True)
    m2.update(name='wheel', mirror=False)
    M = GAME_MATS.index
    raw = b1 + b2
    meta = dict(
        id=cid, fmt='lp2', L=L, W=round(2 * max(abs(v[0]) for v in bv), 4), H=round(max(v[2] for v in bv), 4), meshes=[m1, m2],
        wheels=dict(yf=W['yf'], yr=W['yr'], tf=W['tf'], tr=W['tr'], rf=W['r'], rr=W['r'] + W.get('dr', 0.0), wf=W['wf'], wr=W['wr'],
                    rimf=W['rim'], rimr=W['rim'] + W.get('drim', 0.0)),
        lights=anchors(bv, bt, lambda m, c: m in (M('tail'), M('lensred')) and c[1] < 0.45, cell=0.12),
        exhausts=anchors(bv, bt, lambda m, c: m == M('metal') and c[1] < 0.35 and c[2] < 0.8, cell=0.1, rmax=0.06),
        heads=anchors(bv, bt, lambda m, c: m == M('lens') and c[1] > L - 0.9, cell=0.2, rmax=0.14), belt=S['belt'],
        colors=dict(paint=S['color'], sec=S.get('sec', '#15171b'), stripe=S.get('stripe', '#f2f2f2'), caliper=W.get('caliper', '#c41a1a'),
                    rim=W.get('rim_color', '#2a2c31')),
        palette=[[k[0], k[1]] for k, _ in sorted(palette.items(), key=lambda kv: kv[1])],
        bytes=len(raw), source='lowpoly',
    )
    os.makedirs(out_dir, exist_ok=True)
    rec = dict(meta=meta, z=base64.b64encode(zlib.compress(raw, 9)).decode('ascii'))
    with open(os.path.join(out_dir, cid + '.json'), 'w') as f:
        json.dump(rec, f, separators=(',', ':'))
    return dict(id=cid, tris=(m1['ni'] + m2['ni']) // 3, kb=round(len(rec['z']) / 1024))


# ------------------------------------------------------------------ 2D fallback data (js/data.js)
def side_outline(S):
    '''`side` block for data.js: silhouette, wheels and details (x: 0 = nose, 1 = tail; y = height / L).'''
    cid, L, W = S['id'], S['L'], S['wheels']
    me = bpy.data.objects[cid].data
    names = [m.name[3:] if m else '' for m in me.materials]
    B = 64
    top, bot, wing = [None] * B, [None] * B, None
    for p in me.polygons:
        nm = names[p.material_index] if p.material_index < len(names) else ''
        for i in p.vertices:
            co = me.vertices[i].co
            if nm.startswith('wing_'):
                w = wing or [co.y, co.y, co.z, co.z, abs(co.x)]
                wing = [min(w[0], co.y), max(w[1], co.y), min(w[2], co.z), max(w[3], co.z), max(w[4], abs(co.x))]
                continue
            k = min(B - 1, max(0, int(co.y / L * B)))
            top[k] = co.z if top[k] is None else max(top[k], co.z)
            bot[k] = co.z if bot[k] is None else min(bot[k], co.z)
    for arr in (top, bot):
        for i in range(B):
            if arr[i] is None:
                arr[i] = next((arr[j] for j in list(range(i, B)) + list(range(i, -1, -1)) if arr[j] is not None), 0.5)
    X = lambda y: round(min(1.0, max(0.0, (L - y) / L)), 3)
    Z = lambda z: round(z / L, 3)
    yc = lambda i: (i + 0.5) / B * L
    body = [[0.012, Z(bot[-1] + 0.02)], [0.0, Z((bot[-1] + top[-1]) / 2)]]
    body += [[X(yc(i)), Z(top[i])] for i in range(B - 1, -1, -1) if i in (B - 1, 0) or i % 4 == 1]
    body += [[1.0, Z((bot[0] + top[0]) / 2)], [0.99, Z(bot[0] + 0.02)]]
    mid = [bot[i] for i in range(B) if W['yr'] + 0.5 < yc(i) < W['yf'] - 0.5]
    zf, zr, zl = top[B - 4], top[3], top[B // 2] * 0.62
    side = dict(
        body=body, wheels=[X(W['yf']), X(W['yr']), round(W['r'] / L, 4)], cl=round((min(mid) if mid else 0.12) / L + 0.02, 3),
        rim={'Y': 'Y', '10': '10', '6': '6'}.get(str(W.get('style', '5')), '5'), caliper=W.get('caliper', '#c41a1a'),
        hl=[[0.006, Z(zf * 0.78)], [0.07, Z(zf * 0.86)], [0.078, Z(zf * 0.8)], [0.014, Z(zf * 0.72)]],
        tl=[[0.978, Z(zr * 0.93)], [0.998, Z(zr * 0.91)], [0.999, Z(zr * 0.82)], [0.98, Z(zr * 0.84)]],
        line=[[0.06, Z(zl * 0.95)], [0.4, Z(zl)], [0.7, Z(zl * 1.02)]],
    )
    if wing:
        side['wing'] = dict(x=X((wing[0] + wing[1]) / 2), y=Z(wing[3]), len=round((wing[1] - wing[0]) / L, 3), th=0.012, post=0.9)
        if S.get('wing_style') == 'swan':
            side['wing']['swan'] = True
        if S.get('wing_style') in ('duck', 'lip'):
            side['wing']['flush'] = True
        if wing[4] > 0.88:
            side['wing']['big'] = True
    C = S['cabin']
    y0, y1 = C['side_glass']
    ys = [y0 + (y1 - y0) * k / 6 for k in range(7)]
    topz = lambda y: _interp(C['belt'], y) + (_interp(C['roof'], y) - _interp(C['belt'], y)) * 0.84
    side['glass'] = [[X(y), Z(topz(y))] for y in reversed(ys)] + [[X(y), Z(_interp(C['belt'], y) + 0.015)] for y in ys]
    side['mirror'] = [X(y1 + 0.09), Z(_interp(C['belt'], y1) + 0.03)]
    if S.get('stripes'):
        side['stripe'] = S.get('stripe', '#f2f2f2')
    return side


def rear_panel(S):
    '''`rear` block for data.js (the 2D fallback's rear view), derived from the design.'''
    B, A, C = S['body'], S['anchors'], S['cabin']
    wmax = max(v for _, v in B['xw'])
    H = max(A['roof'], 0.9)
    rear = dict(
        w=round(min(0.99, _interp(B['xw'], 0.0) / wmax), 3), h=round(min(0.8, _interp(B['zdeck'], 0.0) / H), 3),
        deck=round(_interp(B['zsh'], 0.0) / H * 0.62, 3),
        cabinB=round(min(0.85, _interp(C['xbelt'], A['yb1']) / wmax), 3), cabinT=round(min(0.7, _interp(C['xroof'], A['yb1']) / wmax), 3),
        hip=10, arch=6, fins=3, mesh=0, engine=0, badge=S.get('badge', 'crest'),
        lights={'slim': 'slim', 'bar': 'bar', 'wide': 'bar', 'vbar': 'bar', 'round': 'round2', 'round2': 'round2', 'ring': 'rings',
                'x': 'y', 'c': 'slimC', 'tri': 'tri'}.get(S.get('tail_style'), 'slim'),
        spoiler={'wing': 'wing', 'swan': 'swan', 'roof': 'wing', 'duck': 'lip', 'lip': 'lip'}.get(S.get('wing_style'), 'none'),
        exhaust={'dual': 'twin', 'quad': 'quad', 'center2': 'center2', 'center1': 'center1', 'hex': 'center4', 'twin_high': 'high2'}.get(
            S.get('exhaust_style'), 'twin'),
    )
    g, f = S.get('grille_style'), S.get('front_style')
    rear['front'] = 'horseshoe' if g == 'horseshoe' else 'hex' if g == 'hex' else 'round' if f in ('round', 'round2') else 'grille' if g == 'wide' else 'slim'
    if S.get('stripes'):
        rear['stripes'] = S.get('stripe', '#f2f2f2')
    return rear
