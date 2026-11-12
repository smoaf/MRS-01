# Front plate, step 2: solid from the surface + pattern (voxel SDF, mirrored), STL and GLB.
import numpy as np, sys, bpy
from scipy.ndimage import map_coordinates as mc
from skimage.measure import marching_cubes
exec(open('/home/claude/scripts/v8_sheet_common.py').read())           # rimdepth, SC (model units)
OUTP = '/home/claude/v8/plate/'; d = np.load(OUTP + 'plate_surface.npz'); A3 = np.load('/home/claude/v8/sheetA3/A3_surface.npz')
Rp, F, COS, GP, GS, TP = d['Rp'], d['F'], d['COS'], d['GP'], d['GS'], float(d['TP']); MM = 0.001/SC
pad = lambda A: np.c_[A[:, -2:], A, A[:, :2]]
Rp_, F_, C_ = pad(Rp), pad(F), pad(COS); dP = GP[1] - GP[0]; dS_ = GS[1] - GS[0]
TF = 4.0*MM; FO = 0.5*MM; OVL = 16*MM; RR = 1.5*MM; VX = 1.4*MM
# real front face of the shell's lip, as a height map y(x, z): the flange lies on it with a 0.2 mm glue gap
from mathutils import Vector as _V
from mathutils.bvhtree import BVHTree as _BT
from scipy.ndimage import distance_transform_edt as _edt, gaussian_filter as _g2
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.wm.stl_import(filepath='/home/claude/v8/split/base_shell.stl'); _sh = bpy.context.selected_objects[0]
_bv = _BT.FromObject(_sh, bpy.context.evaluated_depsgraph_get()); GX = np.arange(0, 451, 1.0); GZ = np.arange(-460, 461, 1.0); YF = np.full((len(GX), len(GZ)), np.nan)
for a, x_ in enumerate(GX):
    for b, z_ in enumerate(GZ):
        h = _bv.ray_cast(_V((x_, -400, z_)), _V((0, 1, 0)), 260.0)
        if h[0] is not None: YF[a, b] = h[0].y
# keep only the lip: front hits close to the local front of the shell
_idx = _edt(np.isnan(YF), return_distances=False, return_indices=True); YFn = YF[tuple(_idx)]
from scipy.ndimage import minimum_filter as _mnf
lipmask = np.isfinite(YF) & (YF < _mnf(YFn, 61) + 14.0); _idx = _edt(~lipmask, return_distances=False, return_indices=True); YF = _g2(_g2(YF[tuple(_idx)], 2.5), 1.5)/1000/SC
def yfront(x, Z): return mc(YF, [np.full(Z.shape, abs(x)*SC*1000), Z*SC*1000 + 460], order=1, mode='nearest')
xs = np.arange(-2*VX, 0.40/SC, VX); ys = np.arange(-0.265/SC, 0.215/SC, VX); zs = np.arange(-0.43/SC, 0.43/SC, VX)
print('grid', len(xs), len(ys), len(zs)); SD = np.empty((len(xs), len(ys), len(zs)), np.float32)
Y, Z = np.meshgrid(ys, zs, indexing='ij')
def rbox(a, b, r): return np.hypot(np.maximum(a + r, 0), np.maximum(b + r, 0)) + np.minimum(np.maximum(a + r, b + r), 0) - r
for i, x in enumerate(xs):
    P = np.stack([np.full_like(Y, x), Y, Z], -1); r = np.linalg.norm(P, axis=-1)
    phi = np.arccos(np.clip(Y/r, -1, 1)); psi = np.arctan2(Z, x) % (2*np.pi); co = [phi/dP, psi/dS_ + 2]
    rp = mc(Rp_, co, order=1, mode='nearest'); f = mc(F_, co, order=1, mode='nearest'); c = mc(C_, co, order=1, mode='nearest')
    h = (r - rp)*c; rd = Y - yfront(x, Z); th = np.arctan2(Z, np.abs(x)); rho = np.hypot(x, Z)
    lat = np.maximum(rbox(f, np.abs(h) - TP/2, RR), -(rd + FO + TF))
    fl = rbox(np.abs(rd + FO + TF/2) - TF/2, np.maximum(-(h + TP/2), rho - (np.interp(th, A3['TH'], A3['RIN']) + OVL)), RR)
    SD[i] = np.minimum(lat, fl)
    SD[i][r < 0.05] = 1.0
full = np.concatenate([SD[:1:-1][:-1] if False else SD[:2:-1], SD[2:]], 0) if False else np.concatenate([SD[3:][::-1], SD[2:]], 0)   # mirror about x = 0 (index 2)
v, f, n, _ = marching_cubes(full, 0.0, spacing=(VX, VX, VX))
v = v + [-(len(xs) - 3)*VX, ys[0], zs[0]]; v = v*SC*1000                                                    # real mm
print('verts', len(v), 'faces', len(f), 'bounds', v.min(0).round(), v.max(0).round())
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('plate'); me.from_pydata(v.tolist(), [], f.tolist()); me.update(); o = bpy.data.objects.new('front_plate', me); bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.objects.active = o; o.select_set(True)
# keep the largest connected piece only, report loose bits
import bmesh; bm = bmesh.new(); bm.from_mesh(me); seen = set(); comps = []
for vv in bm.verts:
    if vv.index in seen: continue
    st = [vv]; comp = []; seen.add(vv.index)
    while st:
        u = st.pop(); comp.append(u)
        for e in u.link_edges:
            w = e.other_vert(u)
            if w.index not in seen: seen.add(w.index); st.append(w)
    comps.append(comp)
comps.sort(key=len, reverse=True); print('connected pieces', len(comps), [len(c) for c in comps[:5]])
for c in comps[1:]: bmesh.ops.delete(bm, geom=c, context='VERTS')
vol = bm.calc_volume(); bm.to_mesh(me); bm.free(); print('volume cm3', round(vol/1000, 1))
m = o.modifiers.new('d', 'DECIMATE'); m.ratio = 0.35; bpy.ops.object.modifier_apply(modifier='d')
tag = 'v3'
bpy.ops.wm.stl_export(filepath=OUTP + f'front_plate_{tag}.stl', export_selected_objects=True)
bpy.ops.wm.save_as_mainfile(filepath=OUTP + f'front_plate_{tag}.blend')
