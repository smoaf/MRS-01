# Free space behind the lip: first shell hit along each radial ray, band (lip) depth per angle.
import sys
exec(open('/home/claude/scripts/v8_sheet_common.py').read())     # RS_IN, rimdepth, ymin, bc_, grid helpers (model units)
import bpy
from mathutils.bvhtree import BVHTree
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/home/claude/v8/step2i.blend')
sh = bpy.data.objects['shell']; print('shell matrix identity', [list(r) for r in sh.matrix_world])
dg = bpy.context.evaluated_depsgraph_get(); bvh = BVHTree.FromObject(sh, dg)
AZc = (np.arange(NA) + 0.5)*RES - np.pi; ELc = (np.arange(NE) + 0.5)*RES - np.pi/2
rhit = np.full((NA, NE), np.nan); hitP = np.full((NA, NE, 3), np.nan)
for i, a in enumerate(AZc):
    for j, e in enumerate(ELc):
        d = Vector((np.cos(e)*np.sin(a), np.cos(e)*np.cos(a), np.sin(e)))
        loc, nrm, idx, dist = bvh.ray_cast(Vector((0, 0, 0)), d, 2.0)
        if loc is not None: rhit[i, j] = dist; hitP[i, j] = loc[:]
print('rays done, hit fraction', np.isfinite(rhit).mean().round(3))
# band depth: rays along +y (backwards) at points in front of the band
thb = 0.5*(bins[:-1] + bins[1:]) if 'bins' in dir() else bc_
y_front = np.interp(thb, bc_, ymin); D_back = np.zeros(len(thb)); rho_in = np.zeros(len(thb)); rho_out = np.zeros(len(thb))
for k, th in enumerate(thb):
    best = 0; rin = None; rout = None
    for rho in np.linspace(0.20, 0.55, 351):
        x, z = rho*np.cos(th), rho*np.sin(th); o = Vector((x, y_front[k] - 0.05, z))
        loc, n_, i_, dist = bvh.ray_cast(o, Vector((0, 1, 0)), 0.5)
        if loc is None or loc.y - y_front[k] > 0.004: continue          # not the front face of the band
        rin = rho if rin is None else rin; rout = rho
        loc2, *_ = bvh.ray_cast(loc + Vector((0, 1e-4, 0)), Vector((0, 1, 0)), 0.5)
        if loc2 is not None: best = max(best, loc2.y - y_front[k])
    D_back[k] = best; rho_in[k] = rin or np.nan; rho_out[k] = rout or np.nan
print('band depth mm (model units*1000*SC) min/median/max', np.round(np.array([D_back.min(), np.median(D_back), D_back.max()])*1000*SC, 1))
np.savez('/home/claude/v8/sheetA3/lipspace.npz', rhit=rhit, hitP=hitP, thb=thb, D_back=D_back, rho_in=rho_in, rho_out=rho_out, y_front=y_front)
for k in range(0, len(thb), 15): print(f'theta {np.degrees(thb[k]):6.1f}  band {rho_in[k]*SC*1000:5.0f}-{rho_out[k]*SC*1000:5.0f} mm  depth {D_back[k]*SC*1000:5.1f} mm')
