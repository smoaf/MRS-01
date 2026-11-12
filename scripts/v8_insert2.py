# 3/8"-16 nut pocket in the load area of the shell: flat boss, through-hole, washer seat, hex pocket open to the inside.
import bpy, bmesh, numpy as np, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT = '/home/claude/v8/insert2/'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath='/home/claude/v8/package/vocal-shield-outer-shell-v8/01_one_piece/outer_shell_one_piece_80cm.stl'); sh = bpy.context.selected_objects[0]; sh.name = 'shell'
bvh = BVHTree.FromObject(sh, bpy.context.evaluated_depsgraph_get())
Y0 = 0.0; RB = 22.0
zb, zt = [], []
for a in np.linspace(0, 2*np.pi, 24, endpoint=False):
    for r in (0, 8, 16, RB):
        o = Vector((r*math.cos(a), Y0 + r*math.sin(a), -460)); h1 = bvh.ray_cast(o, Vector((0, 0, 1)), 200)
        if h1[0] is None: continue
        h2 = bvh.ray_cast(h1[0] + Vector((0, 0, 0.05)), Vector((0, 0, 1)), 200); zb.append(h1[0].z); zt.append(h2[0].z if h2[0] else np.nan)
zb, zt = np.array(zb), np.array(zt); print('plate under the boss: bottom', zb.min().round(1), zb.max().round(1), 'top', np.nanmin(zt).round(1), np.nanmax(zt).round(1))
Z0 = float(zb.min()) - 0.5                      # flat seat for the stand's shoulder
FLOOR, INS_L, INS_D, HOLE_D, STUD_HOLE, WELL_D = 3.0, 12.7, 12.6, 11.9, 10.5, 20.0      # ruthex 3/8"-16 x 12.7 mm: D1 12.6, D3 11.9, min. wall 6
ZTOP = max(float(np.nanmax(zt)), Z0 + FLOOR + INS_L + 1.0)
def cyl(name, r, z0, z1, n=96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=z1 - z0, location=(0, Y0, (z0 + z1)/2)); o = bpy.context.object; o.name = name; return o
def boolean(a, b, op):
    m = a.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.object = b; m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = a; bpy.ops.object.modifier_apply(modifier='b'); bpy.data.objects.remove(b)
boolean(sh, cyl('boss', RB, Z0, ZTOP - 0.5), 'UNION')
boolean(sh, cyl('ins', HOLE_D/2, Z0 - 5, Z0 + INS_L + 1.0), 'DIFFERENCE')                       # melt-in hole, open to the seat
boolean(sh, cyl('relief', STUD_HOLE/2, Z0 + INS_L + 0.9, Z0 + INS_L + 5.0), 'DIFFERENCE')        # blind relief for a longer stud and displaced plastic
print('seat z', round(Z0, 1), 'boss top z', round(ZTOP - 0.5, 1), 'solid above the hole', round(ZTOP - 0.5 - (Z0 + INS_L + 5.0), 1))
wz = Z0
n = cyl('nut_3_8', 11.7/2, wz, wz + INS_L, 48)   # drawn slightly thinner than the hole so it shows in cut views
bpy.ops.object.select_all(action='DESELECT'); sh.select_set(True); bpy.ops.wm.stl_export(filepath=OUT + 'shell_with_insert_pocket.stl', export_selected_objects=True)
np.save(OUT + 'nut_geom.npy', np.array([Y0, Z0, ZTOP, wz]))
bpy.ops.wm.save_as_mainfile(filepath=OUT + 'insert.blend')
