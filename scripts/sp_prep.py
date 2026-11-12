# Split pipeline, step 0: clean, lighter base meshes (mm, shell frame: x right, y depth with front at -y, z up).
import bpy, bmesh, sys
OUT = '/home/claude/v8/split/'
for name, src, target in (('shell', '/home/claude/v8/insert2/shell_with_insert_pocket.stl', 520000), ('plate', '/home/claude/v8/plate/front_plate_v3.stl', 150000)):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.wm.stl_import(filepath=src); o = bpy.context.selected_objects[0]; bpy.context.view_layer.objects.active = o
    n0 = len(o.data.polygons)
    if n0 > target:
        m = o.modifiers.new('d', 'DECIMATE'); m.ratio = target/n0; bpy.ops.object.modifier_apply(modifier='d')
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    nm = sum(1 for e in bm.edges if not e.is_manifold); vol = bm.calc_volume(); bm.to_mesh(o.data); bm.free()
    print(name, 'faces', n0, '->', len(o.data.polygons), 'non-manifold edges', nm, 'volume cm3', round(vol/1000, 1))
    bpy.ops.wm.stl_export(filepath=OUT + f'base_{name}.stl', export_selected_objects=True)
