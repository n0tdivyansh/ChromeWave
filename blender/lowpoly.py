'''
Chromewave — low-poly car builder (Blender 4.2+ / 5.x)
======================================================
Crisp, faceted cars in the retro-arcade style. A car is:
  · a body loft: closed rings of cross-section points, station by station
    along the car, end caps and boolean wheel arches;
  · a greenhouse loft (glass, pillars, roof) sitting on the deck;
  · details as real geometry (lights, grille, vents, stripes, exhausts),
    never painted onto the vertices;
  · a low-poly wheel (tyre, spoked rim, brake disc, caliper).
Every face is flat-shaded, so the game gets one normal per face.

Car space: meters. X right, Y forward (Y = 0 at the tail, Y = L at the nose),
Z up (ground at Z = 0). Exported by lp_export.py (the game's lp2 model format).
'''
import bpy, bmesh, math
from mathutils import Vector
from mathutils import geometry as mgeo
from mathutils.bvhtree import BVHTree

# preview material: (sRGB, metallic, roughness, coat, emission sRGB or None, strength, alpha)
LP_MAT = {
    'paint': ('#1766d6', 0.0, 0.3, 1.0, None, 0, 1), 'sec': ('#15171b', 0.0, 0.3, 1.0, None, 0, 1),
    'stripe': ('#f2f2f2', 0.0, 0.3, 1.0, None, 0, 1), 'black': ('#0c0c0e', 0.0, 0.2, 0.7, None, 0, 1),
    'matte': ('#151517', 0.0, 0.65, 0.0, None, 0, 1), 'carbon': ('#18191c', 0.2, 0.3, 1.0, None, 0, 1),
    'glass': ('#0b0d11', 0.0, 0.04, 1.0, None, 0, 1), 'chrome': ('#e6e6e8', 1.0, 0.06, 0.0, None, 0, 1),
    'rim': ('#2a2c31', 1.0, 0.25, 0.3, None, 0, 1), 'rubber': ('#1b1b1d', 0.0, 0.85, 0.0, None, 0, 1),
    'tread': ('#111113', 0.0, 0.95, 0.0, None, 0, 1), 'caliper': ('#c41a1a', 0.0, 0.35, 0.6, None, 0, 1),
    'disc': ('#6c6c70', 1.0, 0.45, 0.0, None, 0, 1), 'tail': ('#b3101a', 0.0, 0.08, 1.0, '#ff0a14', 3.0, 1),
    'reverse': ('#cfd0d4', 0.0, 0.08, 1.0, None, 0, 1), 'head': ('#b9bdc6', 1.0, 0.12, 1.0, None, 0, 1),
    'drl': ('#eef4ff', 0.0, 0.2, 1.0, '#eef4ff', 4.0, 1), 'amber': ('#ff8a12', 0.0, 0.1, 1.0, '#ff7300', 0.4, 1),
    'mesh': ('#0d0d0f', 0.3, 0.45, 0.0, None, 0, 1), 'exhaust': ('#aaa49e', 1.0, 0.22, 0.0, None, 0, 1),
    'hole': ('#000000', 0.0, 1.0, 0.0, None, 0, 1), 'well': ('#0b0b0c', 0.0, 0.9, 0.0, None, 0, 1),
    'under': ('#0e0e0f', 0.0, 0.8, 0.0, None, 0, 1), 'plate': ('#dcdcd4', 0.0, 0.4, 0.0, None, 0, 1),
    'badge': ('#dcdce0', 1.0, 0.08, 0.0, None, 0, 1), 'lens': ('#ffffff', 0.0, 0.02, 1.0, None, 0, 0.2),
    'gap': ('#050506', 0.0, 0.9, 0.0, None, 0, 1), 'lensred': ('#c8101e', 0.0, 0.02, 1.0, None, 0, 0.55), 'taildark': ('#1c0305', 0.0, 0.08, 1.0, None, 0, 1),
    'wing_carbon': ('#18191c', 0.2, 0.3, 1.0, None, 0, 1), 'wing_paint': ('#1766d6', 0.0, 0.3, 1.0, None, 0, 1),
    'wing_black': ('#0c0c0e', 0.0, 0.2, 0.7, None, 0, 1), 'wing_sec': ('#15171b', 0.0, 0.3, 1.0, None, 0, 1),
}


def _lin(h):
    h = h.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def lp_mat(name, color=None):
    '''Blender material for previews (the game material comes from lp_export.BUILD_MATS).'''
    m = bpy.data.materials.get('tg_' + name) or bpy.data.materials.new('tg_' + name)
    m.use_nodes = True
    if name.startswith('c_'):        # fixed-colour livery paint ('c_RRGGBB')
        c, metal, rough, coat, em, strength, alpha = ('#' + name[2:], 0.0, 0.32, 1.0, None, 0, 1)
    else:
        c, metal, rough, coat, em, strength, alpha = LP_MAT[name]
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    base = _lin(color or c)
    b.inputs['Base Color'].default_value = (*base, 1.0)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    if 'Coat Weight' in b.inputs:
        b.inputs['Coat Weight'].default_value = coat
        b.inputs['Coat Roughness'].default_value = 0.03
    if em:
        b.inputs['Emission Color'].default_value = (*_lin(em), 1.0)
        b.inputs['Emission Strength'].default_value = strength
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    m.diffuse_color = (*base, 1.0)
    return m


def lin(pts, x):
    '''Piecewise-linear curve through (x, y) keys.'''
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * ((x - x0) / (x1 - x0) if x1 > x0 else 0.0)
    return pts[-1][1]


# ------------------------------------------------------------------ mesh builder
class LP:
    '''bmesh with one material per face; every face flat-shaded.'''

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def mi(self, name):
        if name not in self.mats:
            self.mats.append(name)
        return self.mats.index(name)

    def face(self, pts, mat, out=None):
        '''Face from points or BMVerts; out (Vector) = side the normal must face.'''
        vs = [p if isinstance(p, bmesh.types.BMVert) else self.bm.verts.new(p) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self.mi(mat)
        f.smooth = False
        if out is not None:
            f.normal_update()
            if f.normal.dot(out) < 0:
                f.normal_flip()
        return f

    def solid(self, faces, mat, mats=None):
        '''Convex solid from a list of faces (point lists): normals point away from its center.'''
        allp = [Vector(p) for fc in faces for p in fc]
        c = sum(allp, Vector()) / len(allp)
        for i, fc in enumerate(faces):
            fc = [Vector(p) for p in fc]
            fcen = sum(fc, Vector()) / len(fc)
            self.face(fc, (mats[i] if mats and mats[i] else mat), out=fcen - c)

    def prism(self, poly, axis, a0, a1, mat, mirror=False, cap_mat=None, side_mat=None):
        '''Extrudes a 2D polygon along an axis ('x': poly in (y, z); 'y': (x, z); 'z': (x, y)).'''
        def P(u, v, a):
            return {'x': (a, u, v), 'y': (u, a, v), 'z': (u, v, a)}[axis]
        for sx in ((1, -1) if mirror else (1,)):
            pl = [(u * sx, v) if axis != 'x' else (u, v) for u, v in poly]
            bot = [P(u, v, a0) for u, v in pl]
            top = [P(u, v, a1) for u, v in pl]
            n = len(pl)
            faces = [bot, top] + [[bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]] for i in range(n)]
            mats = [cap_mat, cap_mat] + [side_mat] * n
            self.solid(faces, mat, mats)

    def box(self, x0, x1, y0, y1, z0, z1, mat, mirror=False):
        self.prism([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], 'y', y0, y1, mat, mirror=mirror)

    def tube_y(self, x, z, r, y0, y1, mat, end_mat=None, n=12, mirror=False):
        '''Cylinder along Y (exhaust tips); end_mat on the y0 end cap.'''
        for sx in ((1, -1) if mirror else (1,)):
            ring = [(x * sx + r * math.cos(2 * math.pi * i / n), z + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
            self.prism(ring, 'y', y0, y1, mat)
            if end_mat:
                self.face([(x * sx + r * 0.72 * math.cos(2 * math.pi * i / n), y0 - 0.002, z + r * 0.72 * math.sin(2 * math.pi * i / n)) for i in range(n)],
                          end_mat, out=Vector((0, -1, 0)))

    def to_object(self, name, coll, recalc=False):
        if recalc:
            bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for n in self.mats:
            me.materials.append(bpy.data.materials.get('tg_' + n) or lp_mat(n))
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        return ob


# ------------------------------------------------------------------ lofts
def loft(mb, stations, profile, mat_of, caps=True, creases=None, cap_crease=0.0):
    '''Loft: profile(y) -> half cross-section from the bottom centre (x = 0)
    out and up to the top centre (x = 0); mirrored into a full ring.
    mat_of(k, y) = material of half-segment k between two stations.'''
    rings = []
    for y in stations:
        half = profile(y)
        full = half + [(-x, z) for x, z in half[-2:0:-1]]
        rings.append([mb.bm.verts.new((x, y, z)) for x, z in full])
    n = len(profile(stations[0]))
    m = 2 * n - 2
    for i in range(len(stations) - 1):
        ym = (stations[i] + stations[i + 1]) / 2
        a, b = rings[i], rings[i + 1]
        for j in range(m):
            k = j if j < n - 1 else 2 * n - 3 - j
            mb.face([a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]], mat_of(k, ym))
    if caps:
        # end caps as quad strips bridging each profile point to its mirror (no n-gon pole to pinch)
        for r_, key, y in ((rings[0], 'cap0', stations[0]), (rings[-1], 'cap1', stations[-1])):
            mir = lambda k: r_[(2 * n - 2 - k) % m]
            for k in range(n - 1):
                vs = []
                for v in (r_[k], r_[k + 1], mir(k + 1), mir(k)):
                    if v not in vs:
                        vs.append(v)
                if len(vs) >= 3:
                    mb.face(vs, mat_of(key, y))
    cl = mb.bm.edges.layers.float.get('crease_edge') or mb.bm.edges.layers.float.new('crease_edge')
    for j in range(m):
        k = j if j < n else 2 * n - 2 - j                 # half-profile point index of ring vertex j
        c = (creases or {}).get(k, 0.0)
        if c:
            for i in range(len(stations) - 1):
                e = mb.bm.edges.get([rings[i][j], rings[i + 1][j]])
                if e:
                    e[cl] = c
    if cap_crease:
        for r_ in (rings[0], rings[-1]):
            for j in range(m):
                e = mb.bm.edges.get([r_[j], r_[(j + 1) % m]])
                if e:
                    e[cl] = cap_crease
    return rings


def body_profile(S):
    B = S['body']

    def prof(y):
        f = lambda k: lin(B[k], y)
        zb, xw, zsh, zd, hb = f('zb'), f('xw'), f('zsh'), f('zdeck'), f('bulge')
        zd = max(zd, zsh + 0.02)
        hs = zsh - zb
        xd = xw - B['deck_in']
        xbw, cr = min(max(B['bulge_w'], 0.3), xd - 0.06), B['crown']
        top = zd + hb
        return [
            (0.0, zb),                               # 0 underside centre
            (xw - 0.13, zb),                         # 1 underside edge
            (xw - 0.025, zb + min(0.07, hs * 0.12)), # 2 rocker chamfer
            (xw, zb + min(0.2, hs * 0.32)),          # 3 lower side
            (xw + f('haunch'), zb + hs * 0.52),      # 4 widest (haunches over the wheels)
            (xw - 0.004, zsh - min(0.05, hs * 0.12)),  # 5 upper side  (heights scale with the side: never fold)
            (xw - 0.018, zsh),                       # 6 shoulder crease
            (xd, zd - 0.012),                        # 7 deck edge
            (xbw + 0.03, zd),                        # 8 power bulge foot
            (xbw, top),                              # 9 bulge edge
            (0.25, top + cr * 0.55),                 # 10 stripe outer edge
            (0.04, top + cr),                        # 11 stripe inner edge
            (0.0, top + cr),                         # 12 top centre
        ]
    return prof


def body_mat(S):
    stripes, lower = S.get('stripes', True), S.get('lower')

    def mat(k, y):
        if k in ('cap0', 'cap1'):
            return 'paint'
        if k == 0:
            return 'under'
        if k == 1:
            return 'sec'                         # side skirt: accent colour (detailing shop)
        if lower and k in (2, 3):
            return lower
        if k == 10 and stripes:
            return 'stripe'
        return 'paint'
    return mat


def cabin_profile(S):
    C = S['cabin']

    def prof(y):
        f = lambda k: lin(C[k], y)
        zb, zr, xb, xr, cr = f('belt'), f('roof'), f('xbelt'), f('xroof'), C['crown']
        h = max(zr - zb, 0.0)
        return [
            (xb, zb - 0.08),                          # 0 base (inside the body)
            (xb, zb),                                 # 1 belt
            (xb - 0.025, zb + min(0.015, h * 0.1)),   # 2 glass bottom (window trim in between)
            (xr + (xb - xr) * 0.14, zb + h * 0.84),   # 3 glass top
            (xr, zr),                                 # 4 roof edge
            (0.25, zr + cr * 0.6),                    # 5 stripe outer edge
            (0.04, zr + cr),                          # 6 stripe inner edge
            (0.0, zr + cr),                           # 7 roof centre
        ]
    return prof


def cabin_mat(S):
    C = S['cabin']
    inside = lambda y, z: z[0] < y < z[1]
    stripes, roof = S.get('stripes', True), S.get('roof_mat')

    def mat(k, y):
        win, ws, rg = inside(y, C['side_glass']), inside(y, C['windshield']), inside(y, C['rear_glass'])
        if ws:                                   # windshield: one clean pane, gloss-black A-pillar beside it
            return 'glass' if k >= 3 else ('black' if k in (1, 2) else 'paint')
        if rg:                                   # rear glass: one clean pane, painted C-pillar below it
            return C.get('rear_mat', 'glass') if k >= 3 else ('paint' if k == 2 else 'paint')
        if k == 2 and win:
            return 'glass'
        if k in (1, 3) and win:
            return S.get('trim', 'black')           # window surround: gloss black, or chrome on luxury cars
        if k == 5 and stripes:
            return 'stripe'
        if roof and k >= 4:
            return roof
        return 'paint'
    return mat


# ------------------------------------------------------------------ helpers on the built body
def apply_boolean(ob, cutter):
    mod = ob.modifiers.new('arches', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.material_mode = 'TRANSFER'
    mod.object = cutter
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    if len(me.polygons) < len(old.polygons) * 0.6:
        raise RuntimeError('%s: the arch boolean removed the body (%d -> %d faces); check the profile' % (ob.name, len(old.polygons), len(me.polygons)))
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    for p in me.polygons:
        p.use_smooth = False


def subdivide(ob, levels):
    '''Catmull-Clark on the loft cage. Material borders (paint / glass / trim) and open borders
    are fully creased so they stay crisp; the loft's own creases shape the character lines.'''
    if levels <= 0:
        return
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    cl = bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
    for e in bm.edges:
        fs = e.link_faces
        if len(fs) != 2 or fs[0].material_index != fs[1].material_index:
            e[cl] = 1.0
    bm.to_mesh(ob.data)
    bm.free()
    mod = ob.modifiers.new('subd', 'SUBSURF')
    mod.levels = mod.render_levels = levels
    mod.use_creases = True
    mod.boundary_smooth = 'PRESERVE_CORNERS'
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def arch_cutter(S, coll):
    W, A = S['wheels'], S['arches']
    mb = LP()
    n = A.get('sides', 16)
    for y, zc in ((W['yf'], W['r']), (W['yr'], W['r'] + W.get('dr', 0.0))):
        R = A['r']
        circ = [(y + R * math.cos(2 * math.pi * (i + 0.5) / n), zc + R * math.sin(2 * math.pi * (i + 0.5) / n)) for i in range(n)]
        for sx in (1, -1):
            mb.prism(circ, 'x', sx * A['x_in'], sx * 1.4, 'well')
    return mb.to_object(S['id'] + '_cutter', coll)


class Surface:
    '''Ray-casts onto the built car so details sit exactly on its faces.'''

    def __init__(self, obs):
        verts, polys = [], []
        for ob in obs:
            mw = ob.matrix_world
            b = len(verts)
            verts += [mw @ v.co for v in ob.data.vertices]
            polys += [[b + i for i in p.vertices] for p in ob.data.polygons]
        self.bvh = BVHTree.FromPolygons(verts, polys)

    def hit(self, o, d):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(o), Vector(d), 20.0)
        return loc, nrm


# plane -> ray (origin, direction); 'side' uses (y, z), 'top' (x, y), 'rear'/'front' (x, z)
def _ray(plane, u, v, L, sx=1):
    if plane == 'side':
        return (sx * 4.0, u, v), (-sx, 0, 0)
    if plane == 'top':
        return (u, v, 4.0), (0, 0, -1)
    if plane == 'rear':
        return (u, -4.0, v), (0, 1, 0)
    return (u, L + 4.0, v), (0, -1, 0)


def conform(mb, surf, poly, plane, mat, L, off=0.003, sub=2, mirror=True, wall=False, wall_mat='black'):
    '''Flat 2D polygon laid onto the car surface (exact straight edges, then
    subdivided and projected): stripes, vents, door lines, scoops. wall=True also
    closes the sides from the surface up to the patch (a raised bezel / housing).'''
    tris = mgeo.tessellate_polygon([[Vector((u, v, 0.0)) for u, v in poly]])
    for sx in ((1, -1) if mirror else (1,)):
        cache = {}
        if wall:
            ring = []
            for i in range(len(poly)):
                (u0, v0), (u1, v1) = poly[i], poly[(i + 1) % len(poly)]
                steps = max(1, math.ceil(math.hypot(u1 - u0, v1 - v0) / 0.03))
                for s_ in range(steps):
                    u, v = u0 + (u1 - u0) * s_ / steps, v0 + (v1 - v0) * s_ / steps
                    o, d = _ray(plane, u * sx if plane != 'side' else u, v, L, sx)
                    loc, _ = surf.hit(o, d)
                    ring.append(None if loc is None else (loc - Vector(d) * 0.0005, loc - Vector(d) * off))
            ok = [p for p in ring if p]
            if ok:
                cen = sum((p[1] for p in ok), Vector()) / len(ok)
                for a, b in zip(ring, ring[1:] + ring[:1]):
                    if a and b:
                        mb.face([a[0], b[0], b[1], a[1]], wall_mat, out=(a[1] + b[1]) / 2 - cen)

        def P(u, v):
            key = (round(u, 5), round(v, 5))
            if key not in cache:
                uu = u * sx if plane != 'side' else u
                o, d = _ray(plane, uu, v, L, sx)
                loc, nrm = surf.hit(o, d)
                cache[key] = None if loc is None else (mb.bm.verts.new(loc - Vector(d) * off), -Vector(d))
            return cache[key]
        k = 2 ** sub
        for t in tris:
            A, B, C = [Vector(poly[i]) for i in t]
            grid = {}
            for i in range(k + 1):
                for j in range(k + 1 - i):
                    p = A + (B - A) * (i / k) + (C - A) * (j / k)
                    grid[(i, j)] = P(p.x, p.y)
            for i in range(k):
                for j in range(k - i):
                    tris2 = [((i, j), (i + 1, j), (i, j + 1))]
                    if i + j + 2 <= k:
                        tris2.append(((i + 1, j), (i + 1, j + 1), (i, j + 1)))
                    for tri in tris2:
                        vs = [grid.get(q) for q in tri]
                        if any(v is None for v in vs):
                            continue
                        mb.face([v[0] for v in vs], mat, out=vs[0][1])


# ------------------------------------------------------------------ wheel
def lp_wheel(W, name, coll, rear=False):
    '''Wheel centred at the origin, axle on X, outer face toward +X.'''
    R = W['r'] + (W.get('dr', 0.0) if rear else 0.0)
    w = W['wr'] if rear else W['wf']
    rr = W['rim'] + (W.get('drim', 0.0) if rear else 0.0)
    n = max(W.get('sides', 20), 32)
    h = w / 2
    mb = LP()

    def rot(ax, rad, a):
        return (ax, rad * math.cos(a), rad * math.sin(a))

    def revolve(profile, mats, closed=False, inward=False):
        rows = [[mb.bm.verts.new(rot(p[0], p[1], 2 * math.pi * i / n)) for p in profile] for i in range(n)]
        m = len(profile)
        cx = sum(p[0] for p in profile) / m
        cr = sum(p[1] for p in profile) / m
        for i in range(n):
            a, b = rows[i], rows[(i + 1) % n]
            am = 2 * math.pi * (i + 0.5) / n
            for k in range(m if closed else m - 1):
                k1 = (k + 1) % m
                if inward:
                    dx, dr = 0.0, -1.0
                else:
                    dx = (profile[k][0] + profile[k1][0]) / 2 - cx
                    dr = (profile[k][1] + profile[k1][1]) / 2 - cr
                mb.face([a[k], a[k1], b[k1], b[k]], mats[k], out=Vector((dx, dr * math.cos(am), dr * math.sin(am))))

    def disc(ax, r0, r1, mat, facing=1):
        if r0 <= 0:
            mb.face([rot(ax, r1, 2 * math.pi * i / n) for i in range(n)], mat, out=Vector((facing, 0, 0)))
            return
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            mb.face([rot(ax, r0, a0), rot(ax, r0, a1), rot(ax, r1, a1), rot(ax, r1, a0)], mat, out=Vector((facing, 0, 0)))

    # tyre: closed section, flat tread with chamfered shoulders
    sw = R - rr                                    # sidewall height (low-profile tyres on big rims)
    m_ = (rr + R) / 2
    tyre = [(h - 0.012, rr + sw * 0.12), (h, rr + sw * 0.35), (h + 0.006, m_), (h, R - sw * 0.38), (h - 0.018, R - sw * 0.1), (h - 0.045, R),
            (-h + 0.045, R), (-h + 0.018, R - sw * 0.1), (-h, R - sw * 0.38), (-h - 0.006, m_), (-h, rr + sw * 0.35), (-h + 0.012, rr + sw * 0.12)]
    revolve(tyre, ['rubber'] * 5 + ['tread'] + ['rubber'] * 6, closed=True)
    # rim: barrel (seen through the spokes), outer lip, dark back plate
    revolve([(-h + 0.02, rr), (h - 0.03, rr)], ['rim'], inward=True)
    disc(h - 0.012, rr - 0.03, rr + 0.012, 'rim')
    revolve([(h - 0.03, rr - 0.03), (h - 0.012, rr - 0.03)], ['rim'], inward=True)
    disc(-h + 0.03, 0.0, rr, 'well')
    # brake disc
    disc(h - 0.085, 0.07, rr - 0.045, 'disc')
    # spokes by rim style: '5'/'6' classic, '10' thin, 'Y' split pairs; tapered with a raised ridge
    style, ns = str(W.get('style', '5')), W.get('spokes', 5)
    r0, r1 = 0.07, rr - 0.028
    X = lambda x: Vector((x, 0, 0))
    if style == 'Y':
        arms = [(2 * math.pi * s_ / 5 + math.pi / 2, d) for s_ in range(5) for d in (-0.16, 0.16)]
        w0, w1 = 0.014, 0.022
    elif style in ('10', 'mesh', 'turbine', 'dish', 'wire'):
        arms = [(2 * math.pi * s_ / 10 + math.pi / 2, 0.0) for s_ in range(10)]
        w0, w1 = 0.015, 0.022
    else:
        arms = [(2 * math.pi * s_ / ns + math.pi / 2, 0.0) for s_ in range(ns)]
        w0, w1 = (0.028, 0.042) if ns <= 6 else (0.016, 0.024)
    xf0, xf1, xb = h - 0.022, h - 0.014, h - 0.06
    for a0, da in arms:
        a1 = a0 + da
        rv0, rv1 = Vector((0, math.cos(a0), math.sin(a0))), Vector((0, math.cos(a1), math.sin(a1)))
        t0, t1 = Vector((0, -math.sin(a0), math.cos(a0))), Vector((0, -math.sin(a1), math.cos(a1)))
        f = [rv0 * r0 - t0 * w0 + X(xf0), rv1 * r1 - t1 * w1 + X(xf1), rv1 * r1 + t1 * w1 + X(xf1), rv0 * r0 + t0 * w0 + X(xf0)]
        g0, g1 = rv0 * r0 + X(xf0 + 0.008), rv1 * r1 + X(xf1 + 0.005)
        tm = (t0 + t1).normalized()
        mb.face([f[0], f[1], g1, g0], 'rim', out=X(1) - tm * 0.5)
        mb.face([g0, g1, f[2], f[3]], 'rim', out=X(1) + tm * 0.5)
        for side, (p, q) in ((-1, (0, 1)), (1, (3, 2))):
            pb, qb = f[p].copy(), f[q].copy()
            pb.x = qb.x = xb
            mb.face([f[p], f[q], qb, pb], 'rim', out=tm * side)
    # lug nuts
    for i in range(5):
        a = 2 * math.pi * i / 5 + math.pi / 5
        cy, cz = 0.052 * math.cos(a), 0.052 * math.sin(a)
        mb.solid([[(x_, cy + dy, cz + dz) for dy, dz in ((-0.009, -0.009), (0.009, -0.009), (0.009, 0.009), (-0.009, 0.009))] for x_ in (h - 0.02, h - 0.008)] +
                 [[(x0_, cy + p_[0], cz + p_[1]), (x0_, cy + q_[0], cz + q_[1]), (x1_, cy + q_[0], cz + q_[1]), (x1_, cy + p_[0], cz + p_[1])]
                  for x0_, x1_ in ((h - 0.02, h - 0.008),)
                  for p_, q_ in zip(((-0.009, -0.009), (0.009, -0.009), (0.009, 0.009), (-0.009, 0.009)), ((0.009, -0.009), (0.009, 0.009), (-0.009, 0.009), (-0.009, -0.009)))],
                 'chrome')
    # hub and centre cap
    revolve([(h - 0.06, 0.075), (h - 0.018, 0.075)], ['rim'])
    disc(h - 0.018, 0.035, 0.075, 'rim')
    disc(h - 0.006, 0.0, 0.03, 'chrome')
    # caliper (stays still in the game): a block over the disc
    ca = math.radians(W.get('cal_a', 150))
    rc = rr - 0.075
    cal = [rot(h - 0.085 + dx, rc + dr, ca + dt) for dx in (-0.03, 0.02) for (dr, dt) in ((-0.04, -0.09), (0.035, -0.09), (0.035, 0.09), (-0.04, 0.09))]
    q = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
    mb.solid([[cal[i] for i in fc] for fc in q], 'caliper')
    return mb.to_object(name, coll)


# ------------------------------------------------------------------ car
def mirror_part(mb, xb, y, z, mat='sec', sx=1):
    '''Door mirror at the belt line: a tapered housing (accent colour) on a black stalk,
    mirror glass facing back. xb = belt edge, y = rear face of the housing.'''
    n = 12

    def ring(yy, k, dx):
        return [(sx * (xb + 0.115 + dx + 0.075 * k * math.cos(2 * math.pi * i / n)), yy, z + 0.055 + 0.04 * k * math.sin(2 * math.pi * i / n)) for i in range(n)]
    back, mid, front = ring(y, 1.0, 0.0), ring(y + 0.05, 0.95, -0.004), ring(y + 0.11, 0.55, -0.02)
    faces = [back, front] + [[r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]] for r0, r1 in ((back, mid), (mid, front)) for i in range(n)]
    mb.solid(faces, mat)
    cx, cz = sx * (xb + 0.115), z + 0.055
    mb.face([(cx + (p[0] - cx) * 0.86, y - 0.002, cz + (p[2] - cz) * 0.86) for p in back], 'chrome', out=Vector((0, -1, 0)))
    xs = sorted((sx * (xb - 0.02), sx * (xb + 0.06)))
    mb.box(xs[0], xs[1], y + 0.03, y + 0.07, z - 0.005, z + 0.03, 'black')


def shade(ob, angle):
    '''Smooth panels, hard creases: edges sharper than `angle` (degrees) or on open borders stay sharp.'''
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    lim = math.radians(angle)
    for e in bm.edges:
        e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(0.0) <= lim
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(ob.data)
    bm.free()


def arch_lips(S, mb, surf):
    '''A raised fender lip around every wheel arch, with an inner wall down into the well.'''
    W, A = S['wheels'], S['arches']
    mat = S.get('lip_mat', 'paint')
    zb = lambda y: lin(S['body']['zb'], y)
    for yc, zc in ((W['yf'], W['r']), (W['yr'], W['r'] + W.get('dr', 0.0))):
        Ro, Ri = A['r'] + 0.05, A['r'] + 0.002
        ts = [-0.4 + (math.pi + 0.8) * i / 28 for i in range(29)]
        for sx in (1, -1):
            ring = []
            for t in ts:
                ct, st = math.cos(t), math.sin(t)
                yo, zo = yc + Ro * ct, zc + Ro * st
                if zo < zb(yo) + 0.03:
                    ring.append(None)
                    continue
                loc, _ = surf.hit((sx * 4.0, yo, zo), (-sx, 0, 0))
                if loc is None:
                    ring.append(None)
                    continue
                xo = loc.x
                yi, zi = yc + Ri * ct, zc + Ri * st
                ring.append(((xo, yo, zo), (xo + sx * 0.022, yi, zi), (xo - sx * 0.06, yi, zi), Vector((0, ct, st))))
            for p, q in zip(ring, ring[1:]):
                if p is None or q is None:
                    continue
                rad = (p[3] + q[3]).normalized()
                mb.face([p[0], q[0], q[1], p[1]], mat, out=Vector((sx, 0, 0)) + rad * 0.6)
                mb.face([p[1], q[1], q[2], p[2]], mat, out=-rad)


def shut_lines(S, conform):
    '''Hood and trunk / engine-cover gaps on the top surfaces.'''
    if S.get('kind') == 'lmp':
        return
    L, C = S['L'], S['cabin']
    xw = lambda y: lin(S['body']['xw'], y)
    g = 0.0035

    def outline(y0, y1, inset):
        if y1 - y0 < 0.3:
            return
        a, b = xw(y0) - inset, xw(y1) - inset - 0.04
        for poly in ([(-a, y0 - g), (a, y0 - g), (a, y0 + g), (-a, y0 + g)], [(-b, y1 - g), (b, y1 - g), (b, y1 + g), (-b, y1 + g)]):
            conform(poly, 'top', 'gap', off=0.0025, sub=1, mirror=False)
        conform([(a - g, y0), (a + g, y0), (b + g, y1), (b - g, y1)], 'top', 'gap', off=0.0025, sub=2)
    outline(C['stations'][-2] + 0.06, L - 0.22, 0.13)       # hood / front lid
    outline(0.12, C['stations'][1] - 0.05, 0.15)            # trunk / engine cover


def lp_clear(name):
    coll = bpy.data.collections.get(name)
    if coll:
        for ob in list(coll.objects):
            bpy.data.objects.remove(ob)
    else:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def lp_join(obs, name):
    obs = [o for o in obs if o]
    with bpy.context.temp_override(active_object=obs[0], selected_editable_objects=obs, selected_objects=obs):
        bpy.ops.object.join()
    obs[0].name = obs[0].data.name = name
    return obs[0]


def build_lowpoly(S):
    '''Builds the car in collection car_<id>: objects <id>, <id>_wheel_f/_r, <id>_wl_f/_r.'''
    cid, L, W = S['id'], S['L'], S['wheels']
    coll = lp_clear('car_' + cid)
    for n in LP_MAT:
        lp_mat(n)
    lp_mat('paint', S['color'])
    lp_mat('wing_paint', S['color'])
    lp_mat('sec', S.get('sec', '#15171b'))
    lp_mat('wing_sec', S.get('sec', '#15171b'))
    lp_mat('stripe', S.get('stripe', '#f2f2f2'))
    lp_mat('caliper', W.get('caliper', '#c41a1a'))
    lp_mat('rim', W.get('rim_color', '#2a2c31'))
    # 1) body + arches
    mb = LP()
    # creases: underside edge, shoulder, deck edge, bulge edge; softened tail and nose borders
    loft(mb, S['body']['stations'], body_profile(S), body_mat(S), creases={1: 1.0, 6: 1.0, 7: 0.6, 9: 0.75}, cap_crease=0.85)
    body = mb.to_object(cid + '_body', coll, recalc=True)
    subdivide(body, S.get('subd', 2))
    cutter = arch_cutter(S, coll)
    apply_boolean(body, cutter)
    bpy.data.objects.remove(cutter)
    # 2) greenhouse
    mb = LP()
    loft(mb, S['cabin']['stations'], cabin_profile(S), cabin_mat(S), caps=False, creases={1: 1.0, 4: 0.3})
    cab = mb.to_object(cid + '_cabin', coll, recalc=True)
    subdivide(cab, S.get('subd', 2))
    # 3) details (solid parts, and parts laid onto the surface)
    surf = Surface([body, cab])
    mb = LP()
    ctx = dict(S=S, L=L, mb=mb, surf=surf, conform=lambda poly, plane, mat, **k: conform(mb, surf, poly, plane, mat, L, **k))
    for fn in S.get('details', ()):
        fn(ctx)
    if S.get('finish', True):
        arch_lips(S, mb, Surface([body]))
        shut_lines(S, ctx['conform'])
    det = mb.to_object(cid + '_details', coll) if mb.bm.faces else None
    car = lp_join([body, cab, det], cid)
    shade(car, S.get('smooth_angle', 32))
    # 4) wheels (front and rear; mirrored instances for the occlusion bake and previews)
    wf = lp_wheel(W, cid + '_wheel_f', coll)
    wr = lp_wheel(W, cid + '_wheel_r', coll, rear=True)
    wf.location = (W['tf'] / 2, W['yf'], W['r'])
    wr.location = (W['tr'] / 2, W['yr'], W['r'] + W.get('dr', 0.0))
    shade(wf, 40)
    shade(wr, 40)
    for src, nm in ((wf, '_wl_f'), (wr, '_wl_r')):
        inst = bpy.data.objects.new(cid + nm, src.data)
        inst.location = (-src.location.x, src.location.y, src.location.z)
        inst.scale = (-1, 1, 1)
        coll.objects.link(inst)
    return car
