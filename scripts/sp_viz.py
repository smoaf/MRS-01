# Renders for one package variant: numbered part maps (shell from the back, plate from the front), exploded view, joint close-up.
# usage: sp_viz.py -- <conn> <tag>
import bpy, json, sys, numpy as np, colorsys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
conn, tag = sys.argv[sys.argv.index('--') + 1:][:2]; MODE = (sys.argv[sys.argv.index('--') + 1:] + ['all'])[2]; B = '/home/claude/v8/split/build/'; OUT = B + f'{conn}/{tag}/'
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
def mat(n, c, r=0.6):
    m = bpy.data.materials.new(n); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = r; return m
objs = {}; meta = {}
for name in ('shell', 'plate'):
    J = json.load(open(OUT + f'{name}/parts.json')); meta[name] = J; objs[name] = []
    for k, r in enumerate(J['parts']):
        bpy.ops.wm.stl_import(filepath=OUT + f"{name}/{r['part']}.stl"); o = bpy.context.selected_objects[0]
        R = np.array(r['R']); off = np.array(r['off']); V = np.array([v.co[:] for v in o.data.vertices]); V = (V + off) @ R; o.data.vertices.foreach_set('co', (V/1000).ravel()); o.data.update()
        h = (k*0.618034) % 1.0; base = (0.62, 0.82) if name == 'shell' else (0.7, 0.9); o.data.materials.append(mat(r['part'], colorsys.hsv_to_rgb(h, *base)))
        o['cen'] = (V.mean(0)/1000).tolist(); o['label'] = r['part'].split('_')[1]; objs[name].append(o)
sc.view_settings.view_transform = 'Standard'; sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True; sc.render.resolution_x = 1200; sc.render.resolution_y = 1200
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.93, 0.93, 0.92, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.55
L = bpy.data.lights.new('k', 'SUN'); L.energy = 1.6; L.angle = 0.5; lo = bpy.data.objects.new('k', L); sc.collection.objects.link(lo)
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_start = 0.01
labels = {}
def shot(n, p, t=(0, 0, 0.03), lens=60, show=('shell', 'plate'), lab=None):
    for nm, lst in objs.items():
        for o in lst: o.hide_render = nm not in show
    cam.data.lens = lens; cam.location = Vector(p); cam.rotation_euler = (Vector(t) - Vector(p)).to_track_quat('-Z', 'Y').to_euler(); lo.rotation_euler = cam.rotation_euler; lo.rotation_euler.rotate_axis('X', 0.5); lo.rotation_euler.rotate_axis('Y', 0.4)
    bpy.context.view_layer.update(); sc.render.filepath = OUT + f'_r_{n}.png'; bpy.ops.render.render(write_still=True)
    if lab: labels[n] = [(o['label'], *[float(x) for x in world_to_camera_view(sc, cam, Vector(o['cen']) + o.location)][:2]) for o in objs[lab]]
if MODE in ('all', 'maps'):
    shot('shell_back', (1.5, 2.5, 0.7), lens=95, show=('shell',), lab='shell'); shot('shell_front', (-1.2, -2.8, 0.5), lens=95, show=('shell',), lab='shell')
    shot('plate_front', (-0.5, -3.0, 0.3), lens=105, show=('plate',), lab='plate')
    for lst in objs.values():
        for o in lst: c = Vector(o['cen']); o.location = Vector((c.x, c.y*0.6 + 0.05, c.z)).normalized()*0.16 if c.length > 1e-6 else Vector()
    for o in objs['plate']: o.location.y -= 0.55
    shot('exploded', (-2.4, -3.2, 1.0), t=(0, -0.25, 0.0), lens=80)
    for lst in objs.values():
        for o in lst: o.location = Vector()
# joint close-up on the shell: the first joint whose two parts are both there
J = meta['shell']; c = next(c for c in J['crossings'] if c['inradius'] < 6.5 and abs(c['c'][0]) > 60 and not c['triple'] and c['ext'][0] < 16)
pa, pb = objs['shell'][c['a']], objs['shell'][c['b']]; n = Vector(c['n']); cc = Vector(c['c'])/1000; wv = Vector(c['w']); uv = wv.cross(n)
pa.location = -n*0.012; pb.location = n*0.012
for nm, lst in objs.items():
    for o in lst: o.hide_render = o not in (pa, pb)
if conn == 'keys':
    import glob; from mathutils import Matrix
    bpy.ops.wm.stl_import(filepath=glob.glob(OUT + 'shell/shell_key_x*.stl')[0]); key = bpy.context.selected_objects[0]; key.data.materials.append(mat('key', (0.95, 0.55, 0.1)))
    Rw = 10.0; z0 = -(Rw - 0.4)/1000 - 0.022; nn, uu = n, wv.cross(n)
    key.scale = (1, 1, 1); key.matrix_world = Matrix(((nn.x, uu.x, wv.x, cc.x + wv.x*z0), (nn.y, uu.y, wv.y, cc.y + wv.y*z0), (nn.z, uu.z, wv.z, cc.z + wv.z*z0), (0, 0, 0, 1))) @ Matrix.Scale(0.001, 4)
    pa.location = -n*0.004; pb.location = n*0.004
view = (uv*0.5 - wv*0.8 + n*0.3).normalized() if conn == 'keys' else (uv*0.6 + wv*0.7 + n*0.3).normalized()
cam.data.lens = 70; cam.location = cc + view*0.3; cam.rotation_euler = (cc - cam.location).to_track_quat('-Z', 'Y').to_euler(); lo.rotation_euler = cam.rotation_euler; lo.rotation_euler.rotate_axis('X', 0.4)
sc.render.resolution_x = 1000; sc.render.resolution_y = 800; sc.render.filepath = OUT + '_r_joint.png'; bpy.ops.render.render(write_still=True)
if labels: json.dump(labels, open(OUT + '_labels.json', 'w'))
