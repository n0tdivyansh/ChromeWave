'''
Exports the Blender cars to the game's format.
==============================================
For each car it writes source/blender/out/<id>.json, then build_models()
merges them all into source/js/car-models.js (included by the game build).

Binary format, packed as an RGB PNG (deflate). For each mesh in
meta.meshes, in order (all as byte planes: low bytes first):
    pos   3 × nv × uint16  delta of the position quantized to [qmin, qmax]
                           (meters; X right, Y forward with Y = 0 at the
                           tail, Z up); accumulate modulo 65536
    nrm   2 × nv × int8    normal in octahedral encoding (x, y)
    pal   nv × uint8       index into meta.palette = [material, sRGB color]
    ao    nv × uint8       ambient occlusion (255 = unoccluded)
    idx   ni × uint16      high-water mark: index = hw - code; hw = max + 1
    (padded to a multiple of 4)
Triangles wind counterclockwise seen from outside.
Meshes with mirror=true store only the X >= 0 half; the game mirrors it.
'''
import bpy, bmesh, math, struct, json, zlib, base64, os, random
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# folder of this script (or $SPEEDRUSH_BLENDER when exec()'d inside Blender)
BASE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else (os.environ.get('SPEEDRUSH_BLENDER') or os.getcwd())
OUT = os.path.join(BASE, 'out')
JS = os.path.normpath(os.path.join(BASE, '..', 'js', 'car-models.js'))

# Game material table (the order is the index car-gl.js uses)
MATS = ['paint', 'sec', 'plastic', 'gloss', 'chrome', 'metal', 'glass', 'lens', 'rubber', 'tail',
        'head', 'amber', 'emit', 'caliper', 'carbon', 'mesh', 'dark', 'stripe', 'rim', 'lensred',
        'wingc', 'wingp', 'wingk', 'wings',          # wing parts (the game removes them if it breaks off)
        'livery', 'wingl']                           # fixed-color decoration paint (also on the wing)

# generator material -> (game material, sRGB color or None if the game sets it)
GEN_MAP = {
    'paint': ('paint', None), 'sec': ('sec', None), 'stripe': ('stripe', None),
    'black': ('gloss', '#0c0c0e'), 'matte': ('plastic', '#151517'), 'carbon': ('carbon', '#18191c'),
    'glass': ('glass', '#0b0d11'), 'chrome': ('chrome', '#e6e6e8'), 'rim': ('rim', None),
    'rubber': ('rubber', '#1b1b1d'), 'tread': ('rubber', '#111113'), 'caliper': ('caliper', None),
    'disc': ('metal', '#6c6c70'), 'tail': ('tail', '#b3101a'), 'taildark': ('gloss', '#1c0305'),
    'reverse': ('gloss', '#cfd0d4'), 'head': ('chrome', '#b9bdc6'), 'drl': ('emit', '#eef4ff'),
    'amber': ('amber', '#ff8a12'), 'mesh': ('mesh', '#0d0d0f'), 'louver': ('mesh', '#111115'),
    'exhaust': ('metal', '#aaa49e'), 'hole': ('dark', '#000000'), 'well': ('dark', '#0b0b0c'),
    'under': ('dark', '#0e0e0f'), 'plate': ('plastic', '#dcdcd4'), 'badge': ('chrome', '#dcdce0'),
    'interior': ('plastic', '#151517'), 'lens': ('lens', '#ffffff'), 'lensred': ('lensred', '#c8101e'),
    'gap': ('dark', '#050506'), 'darkchrome': ('metal', '#3c3e42'), 'led': ('tail', '#ff2433'),
    'seat': ('plastic', '#1d1b1b'), 'hidden': ('dark', '#000000'),
    'wing_carbon': ('wingc', '#18191c'), 'wing_paint': ('wingp', None), 'wing_black': ('wingk', '#0c0c0e'),
    'wing_matte': ('wingk', '#151517'), 'wing_sec': ('wings', None),
}


def gen_map(n):
    '''Generator material -> (game material, color). 'c_RRGGBB' = fixed-color decoration.'''
    if n in GEN_MAP:
        return GEN_MAP[n]
    if n.startswith('wing_c_') and len(n) == 13:
        return ('wingl', '#' + n[7:])
    if n.startswith('c_') and len(n) == 8:
        return ('livery', '#' + n[2:])
    return ('plastic', '#333333')


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hemisphere(n, k, seed=7):
    '''k directions with a cosine distribution around n.'''
    rnd = random.Random(seed)
    a = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    t1 = n.cross(a).normalized()
    t2 = n.cross(t1)
    out = []
    for i in range(k):
        u1 = (i + rnd.random()) / k
        u2 = rnd.random()
        r = math.sqrt(u1)
        th = 2 * math.pi * u2
        x, y = r * math.cos(th), r * math.sin(th)
        z = math.sqrt(max(0.0, 1 - u1))
        out.append((t1 * x + t2 * y + n * z).normalized())
    return out


def bvh_of(obs):
    verts, polys = [], []
    for ob in obs:
        mw = ob.matrix_world
        me = ob.data
        b = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        polys += [[b + i for i in p.vertices] for p in me.polygons]
    return BVHTree.FromPolygons(verts, polys)


def ambient(p, n, bvhs, k=20, dist=0.55, ground=True):
    o = p + n * 0.003
    hit = 0.0
    for d in hemisphere(n, k, seed=hash((round(p.x, 3), round(p.y, 3), round(p.z, 3))) & 0xffff):
        blocked = False
        if ground and d.z < -1e-4:
            t = -o.z / d.z
            if 0 < t < dist:
                blocked = True
        if not blocked:
            for b in bvhs:
                loc, _, _, t = b.ray_cast(o, d, dist)
                if loc is not None:
                    blocked = True
                    break
        if blocked:
            hit += 1
    return 1.0 - hit / k


def mesh_data(ob, bvhs, mirror, mat_of, color_of, local=False, ao_k=20, ao_dist=0.55, ground=True, dissolve=None, raw_names=False):
    '''Extracts the game-ready mesh (unique vertices per corner).'''
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    if not local:
        bm.transform(ob.matrix_world)
    if raw_names:
        names = [m.name if m else '_none' for m in ob.data.materials]
    else:
        names = [m.name[3:] if m and m.name.startswith('tg_') else (m.name if m else '') for m in ob.data.materials]
    if dissolve:
        # merges coplanar triangles in flat areas (not on the paint)
        faces = {f for f in bm.faces if f.material_index < len(names) and names[f.material_index] in dissolve}
        edges = [e for e in bm.edges if e.link_faces and all(ff in faces for ff in e.link_faces)]
        verts = [v for v in bm.verts if v.link_faces and all(ff in faces for ff in v.link_faces)]
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.5), verts=verts, edges=edges, delimit={'MATERIAL', 'SHARP'})
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    if mirror:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new('tg_export_tmp')
    bm.to_mesh(me)
    bm.free()
    for i, m in enumerate(ob.data.materials):
        me.materials.append(m)
    cn = me.corner_normals
    V = me.vertices
    uvd = me.uv_layers.active.data if me.uv_layers.active else None
    ao_cache = {}
    verts, index = [], {}
    tris = []
    for poly in me.polygons:
        if len(poly.vertices) != 3:
            continue
        mname = names[poly.material_index] if poly.material_index < len(names) else 'paint'
        gm = mat_of(mname)
        if gm is None:
            continue
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
            akey = (vi, nk)
            a = ao_cache.get(akey)
            if a is None:
                a = ambient(p, n, bvhs, ao_k, ao_dist, ground)
                ao_cache[akey] = a
            col = color_of(mname, p, uvd[li].uv) if (raw_names and uvd is not None) else color_of(mname, p)
            key = (vi, nk, gm, col)
            j = index.get(key)
            if j is None:
                j = len(verts)
                index[key] = j
                verts.append((p.x, p.y, p.z, n.x, n.y, n.z, col, a, MATS.index(gm)))
            ids.append(j)
        tris.append(ids)
    bpy.data.meshes.remove(me)
    return verts, tris


def octa(n):
    '''Normal -> 2 bytes (octahedral encoding).'''
    x, y, z = n
    s = abs(x) + abs(y) + abs(z) or 1.0
    x, y, z = x / s, y / s, z / s
    if z < 0:
        x, y = (1 - abs(y)) * (1 if x >= 0 else -1), (1 - abs(x)) * (1 if y >= 0 else -1)
    return (max(-127, min(127, int(round(x * 127)))) & 255, max(-127, min(127, int(round(y * 127)))) & 255)


def planes(vals, nbytes):
    '''Unsigned integers -> byte planes (all low bytes first).'''
    out = bytearray()
    for k in range(nbytes):
        out += bytes(((v >> (8 * k)) & 255) for v in vals)
    return out


def pack_mesh(verts, tris, palette):
    '''Mesh -> bytes. Order: vertices reordered by first use (better
    compression); delta int16 positions; octahedral normals; 1-byte palette
    (material + color); 1-byte occlusion; high-water-mark indices.'''
    order, remap = [], {}
    for t in tris:
        for i in t:
            if i not in remap:
                remap[i] = len(order)
                order.append(i)
    V = [verts[i] for i in order]
    T = [[remap[i] for i in t] for t in tris]
    nv, ni = len(V), len(T) * 3
    if nv > 65535:
        raise ValueError('mesh with more than 65535 vertices: %d' % nv)
    qmin = [min(v[i] for v in V) for i in range(3)]
    qmax = [max(v[i] for v in V) for i in range(3)]
    for i in range(3):
        if qmax[i] - qmin[i] < 1e-6:
            qmax[i] = qmin[i] + 1e-3
    b = bytearray()
    for c in range(3):
        prev = 0
        vals = []
        for v in V:
            q = int(round((v[c] - qmin[c]) / (qmax[c] - qmin[c]) * 65535))
            vals.append((q - prev) & 0xffff)
            prev = q
        b += planes(vals, 2)
    oc = [octa(v[3:6]) for v in V]
    b += bytes(o[0] for o in oc) + bytes(o[1] for o in oc)
    pal = []
    for v in V:
        key = (v[8],) + tuple(v[6])
        if key not in palette:
            palette[key] = len(palette)
        pal.append(palette[key])
    if len(palette) > 256:
        raise ValueError('paleta > 256 colores')
    b += bytes(pal)
    b += bytes(max(0, min(255, int(round(v[7] * 255)))) for v in V)
    hw = 0
    codes = []
    for t in T:
        for i in t:
            codes.append((hw - i) & 0xffff if hw - i < 65536 else 0xffff)
            if i >= hw:
                hw = i + 1
    b += planes(codes, 2)
    while len(b) % 4:
        b.append(0)
    return bytes(b), dict(nv=nv, ni=ni, qmin=[round(x, 6) for x in qmin], qmax=[round(x, 6) for x in qmax])


def png_bytes(data, width=1024):
    '''Packs arbitrary bytes into an 8-bit RGB PNG (no gamma or profile).'''
    n = len(data)
    px = (n + 2) // 3
    h = max(1, (px + width - 1) // width)
    raw = bytearray(data) + bytes(width * h * 3 - n)
    rows = bytearray()
    stride = width * 3
    for y in range(h):
        rows.append(1)                       # "Sub" filter: improves compression
        line = raw[y * stride:(y + 1) * stride]
        prev = [0, 0, 0]
        for x in range(0, stride):
            c = line[x]
            rows.append((c - (line[x - 3] if x >= 3 else 0)) & 255)
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', width, h, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(bytes(rows), 9)) + chunk(b'IEND', b'')


def clusters(verts, tris, pred, split=None):
    '''Connected groups of triangles matching pred(material, center) -> [(center, radius)].
    split: max width (m); wider groups (LED bars) are split into several points
    along X so the brake glow follows the bar.'''
    sel = [t for t in tris if pred(verts[t[0]][8], sum((Vector(verts[i][:3]) for i in t), Vector()) / 3)]
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for t in sel:
        for i in t[1:]:
            ra, rb = find(t[0]), find(i)
            if ra != rb:
                parent[ra] = rb
    groups = {}
    for t in sel:
        groups.setdefault(find(t[0]), set()).update(t)
    out = []
    for g in groups.values():
        pts = [Vector(verts[i][:3]) for i in g]
        lo = Vector([min(p[i] for p in pts) for i in range(3)])
        hi = Vector([max(p[i] for p in pts) for i in range(3)])
        c = (lo + hi) / 2
        dx, dz = hi.x - lo.x, hi.z - lo.z
        if split and dx > split:
            k = math.ceil(dx / split)
            for i in range(k):
                x = lo.x + (i + 0.5) * dx / k
                out.append(([round(x, 4), round(c.y, 4), round(c.z, 4)], round(max(dz / 2, 0.045), 4)))
            continue
        out.append(([round(c.x, 4), round(c.y, 4), round(c.z, 4)], round(max(dx, dz) / 2, 4)))
    return out


def merge_lights(items, cell=0.12, rmax=0.09):
    '''Merges nearby light groups (split LED strips, several lines close together) into
    ~12 cm cells: few glows per car even if the light is made of many parts.'''
    groups = {}
    for (c, r) in items:
        groups.setdefault((round(c[0] / cell), round(c[2] / cell)), []).append((c, r))
    out = []
    for g in groups.values():
        w = sum(max(r, 1e-3) for _, r in g)
        cx, cy, cz = (sum(c[i] * max(r, 1e-3) for c, r in g) / w for i in range(3))
        rad = max(max(r, math.hypot(c[0] - cx, c[2] - cz) + r * 0.5) for c, r in g)
        out.append(([round(cx, 4), round(cy, 4), round(cz, 4)], round(min(rad, rmax), 4)))
    return out


def export_procedural(G, ao_k=20):
    '''Exports a car built with carlib (G = namespace containing SPEC).'''
    S = G['SPEC']
    cid = S['id']
    body = bpy.data.objects[cid]
    wf = bpy.data.objects[cid + '_wheel_f']
    wr = bpy.data.objects[cid + '_wheel_r']
    wl = [bpy.data.objects[cid + '_wl_f'], bpy.data.objects[cid + '_wl_r']]
    occl = [bvh_of([body]), bvh_of([wf, wr] + wl)]

    def mat_of(n):
        return gen_map(n)[0]

    def color_of(n, p):
        c = gen_map(n)[1]
        return hexrgb(c) if c else (255, 255, 255)
    flat = {'mesh', 'black', 'matte', 'carbon', 'under', 'louver', 'glass', 'lens', 'lensred', 'taildark', 'hole', 'well', 'led', 'drl', 'amber', 'head', 'darkchrome', 'gap', 'plate'}
    bv, bt = mesh_data(body, occl, True, mat_of, color_of, ao_k=ao_k, dissolve=flat)
    # wheel: only the front one (the game scales it for the rear); its own occlusion
    wocc = [BVHTree.FromPolygons([v.co.copy() for v in wf.data.vertices], [list(p.vertices) for p in wf.data.polygons])]
    wv, wt = mesh_data(wf, wocc, False, mat_of, color_of, local=True, ao_k=12, ao_dist=0.25, ground=False)
    palette = {}
    b1, m1 = pack_mesh(bv, bt, palette)
    b2, m2 = pack_mesh(wv, wt, palette)
    m1.update(name='body', mirror=True)
    m2.update(name='wheel', mirror=False)
    W = S['wheels']
    L = S['L']
    tail_ids = {MATS.index('tail'), MATS.index('lensred')}
    lights = merge_lights(clusters(bv, bt, lambda m, c: m in tail_ids and c.y < 0.45, split=0.16))
    exh = [c for c in clusters(bv, bt, lambda m, c: m == MATS.index('metal') and c.y < 0.35 and c.z < 0.8)]
    heads = [c for c in clusters(bv, bt, lambda m, c: m == MATS.index('lens') and c.y > L - 0.9)]
    zmax = max(v[2] for v in bv)
    xmax = max(abs(v[0]) for v in bv)
    meta = dict(
        id=cid, L=L, W=round(2 * xmax, 4), H=round(zmax, 4), meshes=[m1, m2],
        wheels=dict(yf=W['yf'], yr=W['yr'], tf=W['tf'], tr=W['tr'], rf=W['r'], rr=W['r'] + W.get('dr', 0.0), wf=W['wf'], wr=W['wr'],
                    rimf=W['rim'], rimr=W['rim'] + W.get('drim', 0.0)),
        lights=lights, exhausts=exh, heads=heads,
        belt=round(sum(p[1] for p in S['cabin']['belt']) / len(S['cabin']['belt']), 4),
        colors=dict(paint=S['color'], sec=S.get('sec', '#15171b'), stripe=S.get('stripe', '#f2f2f2'), caliper=W.get('caliper', '#c41a1a'),
                    rim=W.get('rim_color', '#b9bdc4')),
        source='procedural',
        palette=[[k[0], '#%02x%02x%02x' % k[1:]] for k, _ in sorted(palette.items(), key=lambda kv: kv[1])],
    )
    return write_car(cid, meta, b1 + b2)


def write_car(cid, meta, data):
    os.makedirs(OUT, exist_ok=True)
    png = png_bytes(data)
    meta['bytes'] = len(data)
    rec = dict(meta=meta, png='data:image/png;base64,' + base64.b64encode(png).decode('ascii'))
    with open(os.path.join(OUT, cid + '.json'), 'w') as f:
        json.dump(rec, f, separators=(',', ':'))
    return dict(id=cid, raw=len(data), png=len(png), tris=sum(m['ni'] for m in meta['meshes']) // 3, verts=sum(m['nv'] for m in meta['meshes']))


def build_models():
    '''Merges out/*.json into source/js/car-models.js.'''
    recs = {}
    for fn in sorted(os.listdir(OUT)):
        if fn.endswith('.json'):
            with open(os.path.join(OUT, fn)) as f:
                recs[fn[:-5]] = json.load(f)
    js = ["'use strict';", '/* 3D car models built in Blender (source/blender). Generated by export_game.py: do not edit. */',
          'window.TG = window.TG || {};', 'TG.CarModels = {', '  mats: ' + json.dumps(MATS) + ',', '  cars: {']
    for cid, r in recs.items():
        js.append('    ' + json.dumps(cid) + ': {meta: ' + json.dumps(r['meta'], separators=(',', ':')) + ', png: ' + json.dumps(r['png']) + '},')
    js += ['  },', '};', '']
    with open(JS, 'w') as f:
        f.write('\n'.join(js))
    return dict(cars=list(recs), kb=round(os.path.getsize(JS) / 1024))


# ------------------------------------------------------------------ 2D silhouette for data.js
RIM2D = {'5': '5', '6': '6', '10': '10', 'Y': 'Y', 'aero': 'aero', 'turbine': 'turbine', 'jesko': 'aero', 'mesh': '10', 'wire': '10',
         'dish': 'aero', 'star': '5', 'rally': '6'}
SWAN = {'gt3rs', 'gt3r992', 'f296gt3', 'beetle', 'jesko'}


def side_data(G):
    '''Side silhouette (x: 0 = nose, 1 = tail; y = height) for data.js side{}, taken from the model:
    used by Car3D (fallback car without WebGL) and for the GL cars' shadows.'''
    S = G['SPEC']
    cid, L, W = S['id'], S['L'], S['wheels']
    ob = bpy.data.objects[cid]
    me = ob.data
    names = [m.name[3:] if m else '' for m in me.materials]
    B = 64
    top, bot = [-1.0] * B, [9.0] * B
    wing = None
    for p in me.polygons:
        nm = names[p.material_index]
        vs = [me.vertices[i].co for i in p.vertices]
        if nm.startswith('wing_'):
            for co in vs:
                if wing is None:
                    wing = [co.y, co.y, co.z, co.z, abs(co.x)]
                wing = [min(wing[0], co.y), max(wing[1], co.y), min(wing[2], co.z), max(wing[3], co.z), max(wing[4], abs(co.x))]
            continue
        if nm == 'hidden':
            continue
        for co in vs:
            i = min(B - 1, max(0, int(co.y / L * B)))
            top[i] = max(top[i], co.z)
            bot[i] = min(bot[i], co.z)
    for arr, bad in ((top, -1.0), (bot, 9.0)):
        for i in range(B):
            if arr[i] == bad:
                j = next((k for k in range(i, B) if arr[k] != bad), None)
                k2 = next((k for k in range(i, -1, -1) if arr[k] != bad), None)
                arr[i] = arr[j] if j is not None else arr[k2]
    X = lambda y: round(min(1.0, max(0.0, (L - y) / L)), 3)
    Z = lambda z: round(z / L, 3)
    yc = lambda i: (i + 0.5) / B * L
    # outline: under the nose, nose, roof front to back, tail and under the tail
    body = [[0.012, Z(bot[B - 1] + 0.02)], [0.0, Z((bot[B - 1] + top[B - 1]) / 2)]]
    for i in range(B - 1, -1, -1):
        if i in (B - 1, 0) or i % 4 == 1:
            body.append([X(yc(i)), Z(top[i])])
    body += [[1.0, Z((bot[0] + top[0]) / 2)], [0.99, Z(bot[0] + 0.02)]]
    mid = [bot[i] for i in range(B) if W['yr'] + 0.5 < yc(i) < W['yf'] - 0.5]
    cl = round((min(mid) if mid else 0.12) / L + 0.02, 3)
    out = dict(body=body, wheels=[X(W['yf']), X(W['yr']), round(W['r'] / L, 4)], cl=cl,
               rim=RIM2D.get(W['style'], '5'), caliper=W.get('caliper', '#c41a1a'))
    # side glass from the cabin curves
    C = S['cabin']
    zs = C['zones']
    ws = next((a for (a, b, m, pm) in zs if m == 'glass' and b >= 9), None)
    if ws is not None and C.get('side_mat') != 'hidden':
        edge, belt = G['Curve'](C['edge']), G['Curve'](C['belt'])
        ya, yb = C['y0'] + (ws - C['y0']) * 0.3, ws + (C['y1'] - ws) * 0.35
        ys = [ya + (yb - ya) * k / 6 for k in range(7)]
        out['glass'] = [[X(y), Z(edge(y) - 0.03)] for y in reversed(ys)] + [[X(y), Z(belt(y) + 0.03)] for y in ys]
        out['mirror'] = [X(yb) + 0.02, Z(belt(yb) + 0.02)]
    zf, zr = top[B - 4], top[3]
    out['hl'] = [[0.006, Z(zf * 0.78)], [0.07, Z(zf * 0.86)], [0.078, Z(zf * 0.8)], [0.014, Z(zf * 0.72)]]
    out['tl'] = [[0.978, Z(zr * 0.93)], [0.998, Z(zr * 0.91)], [0.999, Z(zr * 0.82)], [0.98, Z(zr * 0.84)]]
    zl = (top[B // 2] * 0.62)
    out['line'] = [[0.06, Z(zl * 0.95)], [0.4, Z(zl)], [0.7, Z(zl * 1.02)]]
    if wing:
        w = dict(x=X((wing[0] + wing[1]) / 2), y=Z(wing[3]), len=round((wing[1] - wing[0]) / L, 3), th=0.012, post=0.9)
        if cid in SWAN:
            w['swan'] = True
        if wing[4] > 0.88:
            w['big'] = True
        out['wing'] = w
    os.makedirs(os.path.join(OUT, 'side'), exist_ok=True)
    with open(os.path.join(OUT, 'side', cid + '.json'), 'w') as f:
        json.dump(out, f)
    return out
