'''
Speed Rush — preview renders of a built car (EEVEE): a neutral studio, a few camera angles
and a contact sheet. render_views(S, path, views) -> path + '.png'.
Views: 'rear34', 'front34', 'side', 'rear', 'front', 'top', 'chase' (in-game angle).
'''
import bpy, math, os
import numpy as np
from mathutils import Vector


def _studio():
    sc = bpy.context.scene
    for ob in [o for o in bpy.data.objects if o.name in ('Cube', 'Light', 'Camera')]:
        bpy.data.objects.remove(ob)
    try:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        try:
            sc.render.engine = 'BLENDER_EEVEE'
        except TypeError:
            pass
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.get('lp_studio') or bpy.data.worlds.new('lp_studio')
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.42, 0.45, 0.5, 1.0)
    bg.inputs['Strength'].default_value = 0.9
    coll = bpy.data.collections.get('lp_studio')
    if coll is None:
        coll = bpy.data.collections.new('lp_studio')
        sc.collection.children.link(coll)
        me = bpy.data.meshes.new('lp_floor')
        me.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
        floor = bpy.data.objects.new('lp_floor', me)
        coll.objects.link(floor)
        m = bpy.data.materials.new('lp_floor')
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = (0.11, 0.11, 0.12, 1)
        b.inputs['Roughness'].default_value = 0.5
        me.materials.append(m)
        for name, loc, size, energy in (('lp_key', (4, -3, 6), 7, 1100), ('lp_fill', (-5, 4, 4), 6, 420), ('lp_top', (0, 2.5, 7), 5, 500)):
            ld = bpy.data.lights.new(name, 'AREA')
            ld.size, ld.energy = size, energy
            ob = bpy.data.objects.new(name, ld)
            ob.location = loc
            ob.rotation_euler = (Vector((0, 2.4, 0.4)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
            coll.objects.link(ob)
        cam = bpy.data.objects.new('lp_cam', bpy.data.cameras.new('lp_cam'))
        coll.objects.link(cam)
    sc.camera = bpy.data.objects['lp_cam']
    return sc


def _look(cam, loc, target, lens=50, ortho=None):
    cam.data.type = 'ORTHO' if ortho else 'PERSP'
    if ortho:
        cam.data.ortho_scale = ortho
    cam.data.lens = lens
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def render_views(S, path, views=('rear34', 'front34')):
    sc = _studio()
    for c in bpy.data.collections:                      # show only this car
        if c.name.startswith('car_'):
            c.hide_render = c.name != 'car_' + S['id']
    cam, L = bpy.data.objects['lp_cam'], S['L']
    shots = {
        'rear34': ((-4.4, -4.2, 2.3), (0, L * 0.45, 0.55), 52, None),
        'front34': ((4.6, L + 3.8, 1.9), (0, L * 0.55, 0.5), 52, None),
        'side': ((12, L / 2, 0.6), (0, L / 2, 0.6), 50, L * 1.15),
        'rear': ((0, -12, 0.65), (0, 0, 0.65), 50, 2.5),
        'front': ((0, L + 12, 0.65), (0, L, 0.65), 50, 2.5),
        'top': ((0, L / 2, 12), (0, L / 2 + 0.001, 0), 50, L * 1.15),
        'chase': ((0, -L * 1.9, L * 0.62), (0, L * 0.5, 0.35), 120, None),
    }
    files = []
    for v in views:
        loc, tgt, lens, ortho = shots[v]
        _look(cam, loc, tgt, lens, ortho)
        f = '%s_%s.png' % (path, v)
        sc.render.filepath = f
        bpy.ops.render.render(write_still=True)
        files.append(f)
    tiles = []
    for f in files:
        im = bpy.data.images.load(f, check_existing=False)
        a = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32)
        im.pixels.foreach_get(a)
        tiles.append(a.reshape(im.size[1], im.size[0], 4))
        bpy.data.images.remove(im)
        os.remove(f)
    sheet = np.concatenate(tiles, axis=1)               # one row, left to right
    out = bpy.data.images.new('lp_sheet', sheet.shape[1], sheet.shape[0], alpha=True)
    out.pixels.foreach_set(sheet.ravel())
    out.filepath_raw = path + '.png'
    out.file_format = 'PNG'
    out.save()
    bpy.data.images.remove(out)
    return path + '.png'
