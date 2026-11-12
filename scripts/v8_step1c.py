import bpy, bmesh, math, numpy as np
BAND = 0.055      # depth behind the rim that comes from the left side
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='/home/claude/glb_in/model.glb')
src = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
bpy.context.view_layer.objects.active = src; src.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
V = np.zeros(len(src.data.vertices)*3); src.data.vertices.foreach_get('co', V); V = V.reshape(-1,3)
# rim front per angle around the depth axis, from the left side
th = np.arctan2(V[:,2], np.abs(V[:,0])); bins = np.linspace(-np.pi/2, np.pi/2, 181)
L = V[V[:,0] < 0]; thL = np.arctan2(L[:,2], -L[:,0]); idx = np.clip(np.digitize(thL, bins)-1, 0, 179)
ymin = np.full(180, 1.0)
np.minimum.at(ymin, idx, L[:,1])
ymin = np.convolve(np.pad(ymin, 3, mode='edge'), np.ones(7)/7, mode='valid')
def front_band(c):
    t = math.atan2(c.z, abs(c.x)); i = min(179, max(0, int((t + math.pi/2)/math.pi*180)))
    return c.y < ymin[i] + BAND
def half(keep_left):
    o = src.copy(); o.data = src.data.copy(); bpy.context.scene.collection.objects.link(o)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00005)
    g = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=g, plane_co=(0,0,0), plane_no=(1,0,0), clear_outer=keep_left, clear_inner=not keep_left)
    kill = [v for v in bm.verts if (front_band(v.co) != keep_left)]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    if not keep_left:
        for v in bm.verts: v.co.x = -v.co.x
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free(); return o
A = half(True); B = half(False)
bpy.data.objects.remove(src)
bpy.ops.object.select_all(action='DESELECT'); A.select_set(True); B.select_set(True); bpy.context.view_layer.objects.active = A
bpy.ops.object.join(); ob = A; ob.name = 'shell'
bm = bmesh.new(); bm.from_mesh(ob.data)
def kill(test):
    vs = [v for v in bm.verts if test(v.co)]; bmesh.ops.delete(bm, geom=vs, context='VERTS'); return len(vs)
print('removed',
  kill(lambda c: abs(c.x) < 0.035 and c.y > 0.25 and c.z < -0.21),          # rear pole
  kill(lambda c: abs(c.x) < 0.06 and -0.04 < c.y < 0.30 and c.z < -0.415),   # front pole, crossbar
  kill(lambda c: abs(c.x) < 0.06 and c.z < -0.33 and c.y > 0.12),            # collar remnants
  kill(lambda c: abs(c.x) < 0.125 and abs(c.z) < 0.15 and c.y > 0.262),      # mount ring only
  kill(lambda c: c.y > 0.205 and math.hypot(c.x, c.z) < 0.068),              # mount disc only, inner hub stays
  kill(lambda c: abs(c.x) < 0.17 and abs(c.z) > 0.15 and c.y > 0.256))       # spine end tabs and leg stubs
# remove everything that sticks out behind the smooth back surface (posts, tabs, legs)
from scipy.ndimage import median_filter
Pv = np.array([v.co[:] for v in bm.verts]); cs = 0.01
gx = np.clip(((Pv[:,0] + 0.3)/cs).astype(int), 0, 59); gz = np.clip(((Pv[:,2] + 0.55)/cs).astype(int), 0, 109)
top = np.full((60, 110), -1.0); np.maximum.at(top, (gx, gz), Pv[:,1])
surf_ = median_filter(top, size=9)
out = [v for v, a, b in zip(bm.verts, gx, gz) if v.co.y > 0.2 and v.co.y > surf_[a, b] + 0.008]
bmesh.ops.delete(bm, geom=out, context='VERTS'); print('stick-outs removed', len(out))
bm.to_mesh(ob.data); bm.free()
m = ob.modifiers.new('mir', 'MIRROR'); m.use_axis[0] = True; m.use_clip = True; m.use_mirror_merge = True; m.merge_threshold = 0.0006
bpy.ops.object.modifier_apply(modifier='mir')
# fuse everything into one clean solid
pass
bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
# round the outline across the centre line (top peak and bottom tip)
P = np.array([v.co[:] for v in bm.verts])
def outline(sign):
    xs = np.linspace(0, 0.14, 29); zz = []
    for x in xs:
        s = P[np.abs(np.abs(P[:,0]) - x) < 0.004]
        zz.append(s[:,2].max() if sign > 0 else s[:,2].min())
    return xs, np.array(zz)
for sign in (1, -1):
    xs, zz = outline(sign)
    fit = np.polyfit(xs[8:20]**2, zz[8:20], 1)          # smooth parabola from 0.04..0.10 m, extended to the centre
    target = np.polyval(fit, xs**2)
    delta = target - zz; delta[xs > 0.06] = 0
    for v in bm.verts:
        c = v.co
        if sign*c.z > 0.25:
            w = min(1.0, (sign*c.z - 0.25)/0.15)
            v.co.z += float(np.interp(abs(c.x), xs, delta))*w
    print('outline fix', sign, delta[:4])
# rod opening at the bottom, where the old front pole entered (larger than before)
R_ROD = 0.024
kill(lambda c: c.z < -0.25 and math.hypot(c.x, c.y - 0.0) < R_ROD)
bm.to_mesh(ob.data); bm.free()
for p in ob.data.polygons: p.use_smooth = True
print('faces', len(ob.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath='/home/claude/v8/step1c.blend')
bpy.ops.export_scene.gltf(filepath='/home/claude/v8/step1c.glb', export_format='GLB')
