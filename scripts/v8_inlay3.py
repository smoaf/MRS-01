# Step 2e: the whole outer shell as ONE grid over the envelope of the mockup, with a procedural rim lip.
# Left half only, mirrored. Keeps the largest connected piece.
import bpy, bmesh, math, numpy as np, time, sys
from scipy.ndimage import (distance_transform_edt, median_filter, maximum_filter, binary_closing, gaussian_filter,
                           binary_fill_holes, binary_dilation)
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
t0 = time.time(); rng = np.random.default_rng(int(sys.argv[-1]) if sys.argv[-1].isdigit() else 11)
OUT = '/home/claude/v8/step2i'
bpy.ops.wm.open_mainfile(filepath='/home/claude/v8/step1c.blend')
me = bpy.data.objects['shell'].data
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
C = np.array([f.calc_center_median()[:] for f in bm.faces]); bm.free()
def sph(P):
    r = np.linalg.norm(P, axis=-1); az = np.arctan2(P[...,0], P[...,1]); el = np.arctan2(P[...,2], np.hypot(P[...,0], P[...,1])); return r, az, el
RES = 0.012; NA = int(2*np.pi/RES)+2; NE = int(np.pi/RES)+2
def cell(az, el): return np.clip(((az+np.pi)/RES).astype(int), 0, NA-1), np.clip(((el+np.pi/2)/RES).astype(int), 0, NE-1)
r, az, el = sph(C); ia, ie = cell(az, el)
rmax = np.zeros((NA, NE)); np.maximum.at(rmax, (ia, ie), r)
PW = 18
def wrapf(fn, a, *k, **kw):
    b = np.pad(a, ((PW, PW), (0, 0)), mode='wrap'); b = np.pad(b, ((0, 0), (PW, PW)), mode='edge')
    return fn(b, *k, **kw)[PW:-PW, PW:-PW]
# the shell is mirror-symmetric: fill each az column from its mirror (az -> -az), which also closes the az=+-pi seam
AZc = (np.arange(NA)+0.5)*RES - np.pi; mi = np.clip(((-AZc + np.pi)/RES).astype(int), 0, NA-1)
rmax = np.maximum(rmax, rmax[mi, :])
valid = rmax > 0.05
ELc = (np.arange(NE)+0.5)*RES - np.pi/2
for j in np.where(ELc < -1.05)[0]:
    row = rmax[:, j]; ok_ = row > 0.05
    if ok_.sum() > 0.3*NA:   # the shell exists in this ring: fill its gaps with the ring's interpolated values
        idx_ = np.arange(NA); rmax[:, j] = np.interp(idx_, idx_[ok_], row[ok_], period=NA)
valid = rmax > 0.05
ext = binary_fill_holes(wrapf(binary_closing, valid, iterations=9))
num = wrapf(gaussian_filter, np.where(valid, rmax, 0.0), 9); den = wrapf(gaussian_filter, valid.astype(float), 9)
rmax = np.where(valid | ~ext, rmax, num/np.maximum(den, 1e-6))
from scipy.ndimage import distance_transform_edt as _edt
_d, _ix = _edt(~ext, return_indices=True); rmax = np.where(ext, rmax, rmax[_ix[0], _ix[1]])
rs = wrapf(median_filter, wrapf(maximum_filter, rmax, 4), 11)
rs_s = wrapf(gaussian_filter, rs, 3.8)
from scipy.ndimage import map_coordinates
for j in np.where((ELc < -1.30) | (ELc > 1.47))[0]:   # the angle map pinches at both poles: make those caps rotationally smooth
    e0 = 1.30 if ELc[j] < 0 else 1.47; wgt = np.clip((np.abs(ELc[j]) - e0)/(1.50 - e0), 0, 1); rs_s[:, j] = (1 - wgt)*rs_s[:, j] + wgt*rs_s[:, j].mean()
def rs_at(a, e):   # bilinear lookup of the smooth envelope: no steps, no ridges
    fi = (np.asarray(a, float) + np.pi)/RES - 0.5; fj = (np.asarray(e, float) + np.pi/2)/RES - 0.5
    return map_coordinates(rs_s, [np.ravel(fi), np.ravel(fj)], order=1, mode='nearest').reshape(np.shape(fi))                                  # smooth turtle-shell envelope
inside = wrapf(binary_closing, ext, iterations=3)
for j in np.where(np.abs((np.arange(NE)+0.5)*RES - np.pi/2) > 1.20)[0]:   # poles: the shell is closed there
    inside[:, j] = True
# rim: front edge per angle (from the mirrored-left mockup)
thL = np.arctan2(C[:,2], np.abs(C[:,0])); bins = np.linspace(-np.pi/2, np.pi/2, 181)
idx = np.clip(np.digitize(thL, bins)-1, 0, 179); ymin = np.full(180, 1.0); np.minimum.at(ymin, idx, C[:,1])
ymin = median_filter(ymin, 9, mode='nearest'); ymin = gaussian_filter(ymin, 5, mode='nearest')   # smooth rim outline
bc_ = 0.5*(bins[:-1] + bins[1:])
def rimdepth(P):
    th = np.arctan2(P[...,2], np.abs(P[...,0])); return P[...,1] - np.interp(th, bc_, ymin)
def env_point(a, e):
    rr = rs_at(a, e)
    d = np.stack([np.cos(e)*np.sin(a), np.cos(e)*np.cos(a), np.sin(e)], -1); return d*rr[..., None]
# ================= one-piece inlay =================
import sys
FC = np.load('/home/claude/v8/fc.npz')['C']; SC = 0.800/(2*np.abs(FC[:,0]).max())
T   = float(sys.argv[-1])/1000/SC if sys.argv[-1].replace('.','').isdigit() else 0.036/SC   # inlay thickness
GAP = 0.025                      # outer face of the inlay sits just inside the struts (struts reach about 24 mm in)
FL  = 0.012/SC                   # flange thickness in front of the seam band
OUT = '/home/claude/v8/inlay/inlay_v3_%dmm' % round(T*SC*1000)
VX = 0.0022
lo = np.array([-0.45, -0.40, -0.53]); hi = np.array([0.0, 0.38, 0.53])
nx, ny, nz = (np.round((hi - lo)/VX).astype(int) + 1)
from scipy.ndimage import minimum_filter, distance_transform_edt as edt
# smooth surface S just inside the struts: lower envelope of the shell, smoothed, extended past the rim
r_ext = rs_s.copy(); _d, _ix = edt(~inside, return_indices=True); r_ext = np.where(inside, r_ext, r_ext[_ix[0], _ix[1]])
r_low = wrapf(gaussian_filter, wrapf(minimum_filter, r_ext, 9), 6)
print('smooth surface above shell surface by at most mm', round(float((r_low - r_ext)[inside].max())*1000, 1))
RS_IN = r_low - GAP - wrapf(gaussian_filter, np.maximum(r_low - r_ext, 0), 3)*1.3   # never closer than GAP to the shell
print('after correction, max above shell mm', round(float((RS_IN + GAP - r_ext)[inside].max())*1000, 1))
def rin_at(a, e):
    fi = (np.asarray(a) + np.pi)/RES - 0.5; fj = (np.asarray(e) + np.pi/2)/RES - 0.5
    return map_coordinates(RS_IN, [np.ravel(fi), np.ravel(fj)], order=1, mode='nearest').reshape(np.shape(fi))
G = np.stack(np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing='ij'), -1).reshape(-1, 3)
insideS = np.zeros(len(G), bool); rdv = np.zeros(len(G), np.float32); dsv = np.zeros(len(G), np.float32)
CH = 3_000_000
for s0 in range(0, len(G), CH):
    x = lo + G[s0:s0+CH]*VX; rX, aX, eX = sph(x)
    insideS[s0:s0+CH] = rX < rin_at(aX, eX); rdv[s0:s0+CH] = rimdepth(x); dsv[s0:s0+CH] = rX - rs_at(aX, eX)
insideS = insideS.reshape(nx, ny, nz); rdv = rdv.reshape(nx, ny, nz); dsv = dsv.reshape(nx, ny, nz)
insideS[-1] = insideS[-2]
mirror = lambda A: np.concatenate([A, A[-2::-1]], axis=0)       # use the full width so the distances are right at the centre line
dS = (edt(mirror(insideS)) - edt(~mirror(insideS)))*VX; dS = dS[:nx]  # >0 inside S: true distance to S
print('distance field done')
def rbox(a1, a2, rr):
    a1 = a1 + rr; a2 = a2 + rr
    return np.sqrt(np.maximum(a1, 0)**2 + np.maximum(a2, 0)**2) + np.minimum(np.maximum(a1, a2), 0) - rr
def smin(a, b, k):
    h = np.clip(0.5 + 0.5*(b - a)/k, 0, 1); return b*(1-h) + a*h - k*h*(1-h)
f_body = rbox(np.abs(dS - T/2) - T/2, -rdv + 0.002, 0.003)                           # ends 2 mm behind the lip front, inside the band                          # even thickness T behind the seam band
f_fl = rbox(np.abs(rdv + FL/2) - FL/2, np.maximum(-dS - GAP + 0.0005, dS - T - 0.002), 0.004)   # flange covers the band face
out = f_body.astype(np.float32)                                                   # no flange: the lip frames the inlay
vol = out
vol[-1] = vol[-2]
vol = gaussian_filter(vol, 0.9)
vol = np.concatenate([vol, vol[-2::-1]], axis=0)          # mirror the volume: one closed, symmetric piece
vol = np.pad(vol, 1, constant_values=0.02)
vs, fs, _, _ = marching_cubes(vol, 0.0, spacing=(VX, VX, VX)); vs += lo - VX
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
nv = len(vs); e = np.concatenate([fs[:,[0,1]], fs[:,[1,2]]])
nc_, lab = connected_components(coo_matrix((np.ones(len(e), np.int8), (e[:,0], e[:,1])), shape=(nv, nv)), directed=False)
big = np.bincount(lab).argmax(); kv = lab == big; fk = fs[kv[fs[:,0]]]; rm = -np.ones(nv, int); rm[kv] = np.arange(kv.sum()); vs, fs = vs[kv], rm[fk]
print('pieces', nc_, 'tris', len(fs))
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('inlay'); me.from_pydata((vs*SC).tolist(), [], fs.tolist()); me.update()
o = bpy.data.objects.new('inlay', me); bpy.context.scene.collection.objects.link(o); bpy.context.view_layer.objects.active = o; o.select_set(True)
md = o.modifiers.new('s', 'LAPLACIANSMOOTH'); md.iterations = 4; md.lambda_factor = 0.5; md.use_volume_preserve = True; bpy.ops.object.modifier_apply(modifier='s')
md = o.modifiers.new('d', 'DECIMATE'); md.ratio = 0.35; bpy.ops.object.modifier_apply(modifier='d')
for p in me.polygons: p.use_smooth = True
bm = bmesh.new(); bm.from_mesh(me); volm = bm.calc_volume(); area = sum(f.calc_area() for f in bm.faces); nm = sum(1 for ed in bm.edges if not ed.is_manifold); bm.free()
V = np.array([v.co[:] for v in me.vertices])
print('INLAY thickness mm', round(T*SC*1000), 'size mm', ((V.max(0)-V.min(0))*1000).round(), 'volume L', round(volm*1000, 2), 'surface m2', round(area, 3), 'nonmanifold', nm)
bpy.ops.wm.save_as_mainfile(filepath=OUT + '.blend')
bpy.ops.export_scene.gltf(filepath=OUT + '.glb', export_format='GLB')
bpy.ops.wm.stl_export(filepath=OUT + '.stl', export_selected_objects=True, global_scale=1000.0)
