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
# ---------- seeds over the whole shell (left half), graded ----------
hub = env_point(np.array(0.), np.array(0.))
A = rng.uniform(-np.pi, 0, 500000); E = np.arcsin(rng.uniform(-1, 1, 500000))
ci, cj = cell(A, E); ok = inside[ci, cj]; A, E = A[ok], E[ok]
Ps = env_point(A, E); rd = rimdepth(Ps); ok = rd > 0.035; Ps, A, E, rd = Ps[ok], A[ok], E[ok], rd[ok]
phi = np.arccos(np.clip(Ps[:,1]/np.linalg.norm(Ps, axis=1), -1, 1))
side = np.exp(-((np.abs(A) - 1.75)/0.45)**2)*np.exp(-(E/0.55)**2)          # larger openings on the sides
def grade(rdv, phiv, sidev):
    return np.clip((rdv - 0.035)/0.09, 0, 1)*np.clip(0.30 + 0.70*np.exp(-(phiv/0.75)**2) + 0.55*sidev, 0, 1)
g = grade(rd, phi, side); size = 0.024 + 0.10*g
seeds = []; srad = []
for ang in (0, 60, 120, 180):
    t = math.radians(ang); seeds.append(hub + np.array([-math.sin(t), 0, math.cos(t)])*0.152); srad.append(0.15)
seeds.append(hub.copy()); srad.append(0.09)
for i in rng.permutation(len(Ps)):
    p = Ps[i]; s = size[i]
    if p[0] > -0.42*s or np.linalg.norm(p - hub) < 0.25: continue
    if all(np.linalg.norm(p - q) > 0.5*(s + qs) for q, qs in zip(seeds, srad)): seeds.append(p); srad.append(s)
S = np.array(seeds); S = np.concatenate([S, S[S[:,0] < -1e-6]*[-1,1,1]]); print('seeds', len(S))
from scipy.spatial import SphericalVoronoi
U = S/np.linalg.norm(S, axis=1, keepdims=True)
sv = SphericalVoronoi(U, radius=1.0, center=np.zeros(3)); sv.sort_vertices_of_regions()
edges = set()
for reg in sv.regions:
    for i in range(len(reg)):
        a_, b_ = reg[i], reg[(i+1) % len(reg)]; edges.add((min(a_, b_), max(a_, b_)))
VD = sv.vertices
def to_env(D, off=-0.011):
    r_, a_, e_ = sph(D); return D/np.maximum(r_, 1e-9)[:, None]*(rs_at(a_, e_) + off)[:, None]
def domain_ok(P):  # on the shell, not in front of the seam
    r_, a_, e_ = sph(P); i_, j_ = cell(a_, e_); return inside[i_, j_] & (rimdepth(P) > -0.003)
# drop edges fully outside; then remove dead ends that are not at the seam, repeatedly
VP = to_env(VD); vin = domain_ok(VP); vseam = rimdepth(VP) < 0.05
E = [e for e in edges if vin[e[0]] or vin[e[1]]]
while True:
    deg = np.zeros(len(VD), int)
    for i_, j_ in E: deg[i_] += 1; deg[j_] += 1
    dead = {k for k in range(len(VD)) if deg[k] == 1 and vin[k] and not vseam[k]}
    if not dead: break
    E = [e for e in E if e[0] not in dead and e[1] not in dead]
print('struts', len(E), 'of', len(edges))
pts = []; 
for i_, j_ in E:
    p, q = VD[i_], VD[j_]; ang = np.arccos(np.clip(p @ q, -1, 1)); n = max(2, int(ang*0.3/0.0012))
    t = np.linspace(0, 1, n)[:, None]
    sl = (np.sin((1-t)*ang)*p + np.sin(t*ang)*q)/max(np.sin(ang), 1e-9)
    pts.append(sl)
SP = to_env(np.concatenate(pts)); SP = SP[domain_ok(SP) | (rimdepth(SP) > -0.02)]
SN = SP/np.linalg.norm(SP, axis=1, keepdims=True)
deg = np.zeros(len(VD), int)
for i_, j_ in E: deg[i_] += 1; deg[j_] += 1
NP = VP[(deg >= 3) & vin]
def gfun(P):
    r_, a_, e_ = sph(P); ph = np.arccos(np.clip(P[:,1]/np.maximum(r_, 1e-9), -1, 1))
    sd = np.exp(-((np.abs(a_) - 1.75)/0.45)**2)*np.exp(-(e_/0.55)**2); return grade(rimdepth(P), ph, sd)
PL_DIR = np.array([0.0, 0.0, -1.0])
P0 = to_env(PL_DIR[None, :], -0.011)[0]; print('plate centre', P0.round(3))
RP = 0.070                      # plate radius: 140 mm across
boost = lambda P: 1 + 0.9*np.exp(-np.linalg.norm(P - P0, axis=1)/0.07)   # heavier struts around the plate
gS = gfun(SP); WS = (0.0036 + 0.045*(0.024 + 0.10*gS))*boost(SP); HS = np.maximum(0.0042, 0.0046 + 0.007*gS)
gN = gfun(NP); WN = 1.30*(0.0036 + 0.045*(0.024 + 0.10*gN))*boost(NP); HN = 1.15*np.maximum(0.0042, 0.0046 + 0.007*gN)
TP = cKDTree(SP); TN = cKDTree(NP)
# ---------- voxels of the left half near the envelope ----------
VX = 0.0019
lo = np.array([-0.45, -0.37, -0.53]); hi = np.array([0.0, 0.38, 0.53])
nx, ny, nz = (np.round((hi - lo)/VX).astype(int) + 1)
occ = np.zeros((nx, ny, nz), bool)
AA, EE = np.meshgrid(np.linspace(-np.pi, 0, 1700), np.linspace(-np.pi/2, np.pi/2, 1800), indexing='ij')
gi, gj = cell(AA, EE); m = wrapf(maximum_filter, inside, 9)[gi, gj]   # sample past the rim so the seam is never cut by the sampling edge
base = env_point(AA[m], EE[m]); dirs = base/np.linalg.norm(base, axis=1, keepdims=True)
for t in np.arange(-0.040, 0.016, VX*0.7):
    k = np.round((base + dirs*t - lo)/VX).astype(int); k = k[(k >= 0).all(1) & (k < [nx, ny, nz]).all(1)]; occ[k[:,0], k[:,1], k[:,2]] = True
occ = binary_dilation(occ, iterations=2)
_k0 = np.round((np.array([-0.085, P0[1]-0.085, P0[2]-0.050]) - lo)/VX).astype(int); _k1 = np.round((np.array([0.0, P0[1]+0.085, P0[2]+0.030]) - lo)/VX).astype(int)
_k0 = np.maximum(_k0, 0); occ[_k0[0]:_k1[0]+1, _k0[1]:_k1[1]+1, _k0[2]:_k1[2]+1] = True     # room for plate and boss
K = np.argwhere(occ); X = lo + K*VX; print('voxels', len(K), round(time.time()-t0))
inside_f = wrapf(gaussian_filter, inside.astype(float), 1.5)
def smin(a, b, k):
    h = np.clip(0.5 + 0.5*(b - a)/k, 0, 1); return b*(1-h) + a*h - k*h*(1-h)
def rbox(a1, a2, rr):
    a1 = a1 + rr; a2 = a2 + rr
    return np.sqrt(np.maximum(a1, 0)**2 + np.maximum(a2, 0)**2) + np.minimum(np.maximum(a1, a2), 0) - rr
def field(x):
    rX, aX, eX = sph(x); xi, xj = cell(aX, eX); dsurf = rX - rs_at(aX, eX)
    rdX = rimdepth(x)
    phiX = np.arccos(np.clip(x[:,1]/np.maximum(rX, 1e-6), -1, 1))
    sideX = np.exp(-((np.abs(aX) - 1.75)/0.45)**2)*np.exp(-(eX/0.55)**2)
    gX = grade(rdX, phiX, sideX)
    dd, ii = TP.query(x, k=6)
    best = np.full(len(x), 1.0)
    for k_ in range(6):
        v = x - SP[ii[:, k_]]; n_ = SN[ii[:, k_]]; vn = np.einsum('ij,ij->i', v, n_); vt = np.linalg.norm(v - vn[:, None]*n_, axis=1)
        w_ = WS[ii[:, k_]]; h_ = HS[ii[:, k_]]
        best = np.minimum(best, np.sqrt(vt**2 + (vn*w_/h_)**2) - w_)
    dn, jn = TN.query(x, k=1)
    vN = x - NP[jn]; nN = NP[jn]/np.linalg.norm(NP[jn], axis=1, keepdims=True); vnN = np.einsum('ij,ij->i', vN, nN)
    vtN = np.linalg.norm(vN - vnN[:, None]*nN, axis=1)
    f_node = np.sqrt(vtN**2 + (vnN*WN[jn]/HN[jn])**2) - WN[jn]
    f_lat = smin(best, f_node, 0.004)
    # rim lip: smooth band at the front edge, rounded on all sides; the grid grows into it
    f_lip = rbox(np.abs(rdX - 0.019) - 0.019, np.abs(dsurf + 0.011) - 0.0105, 0.0025)   # flat front land, small edge fillets
    fi_ = (aX + np.pi)/RES - 0.5; fj_ = (eX + np.pi/2)/RES - 0.5
    insS = map_coordinates(inside_f, [fi_, fj_], order=1, mode='nearest') > 0.5      # smooth mask, no stair steps
    f_lat = np.where(insS, f_lat, np.maximum(f_lat, 0.01))
    f = smin(f_lat, f_lip, 0.006)
    # solid load area: follows the shell curve, thicker in the middle, soft edge into the grid
    dP = np.linalg.norm(x - P0, axis=1)
    thick = 0.0085 + 0.0015*np.clip(1 - dP/RP, 0, 1)      # covers the struts, so the pad face stays smooth
    f_pad = rbox(dP - RP, np.abs(dsurf + 0.011) - thick, 0.004)
    f = smin(f, f_pad, 0.014)
    f = np.maximum(f, -rdX - 0.002)                                                      # clean cut in front of the seam

    return f
out = np.empty(len(K), np.float32); CH = 2_000_000
for s0 in range(0, len(K), CH):
    out[s0:s0+CH] = field(X[s0:s0+CH])
gaps = []
for i_, j_ in E:
    p, q = VD[i_], VD[j_]; ang = np.arccos(np.clip(p @ q, -1, 1)); t = np.linspace(0, 1, max(8, int(ang*0.45/0.001)))[:, None]
    P_ = to_env((np.sin((1-t)*ang)*p + np.sin(t*ang)*q)/max(np.sin(ang), 1e-9))
    P_ = P_[P_[:,0] <= 0.0005]; P_ = P_[domain_ok(P_)]
    if len(P_) == 0: continue
    P_[:,0] = np.minimum(P_[:,0], 0.0)
    fv = field(P_)
    if fv.max() > 0: gaps.append((P_[fv.argmax()].round(3), round(float(fv.max())*1000, 1)))
pt = np.array([[-0.0005, -0.001, 0.388]]); r_, a_, e_ = sph(pt)
print('probe el', e_, 'rs', rs_at(a_, e_), 'r', r_, 'inside', inside[cell(a_, e_)], 'rimdepth', rimdepth(pt), 'field', field(pt))
gaps = [g for g in gaps if g[1] > 2.0]
print('strut gaps', len(gaps)); [print('  gap at', g[0], 'depth mm', g[1]) for g in gaps[:20]]
vol = np.full((nx, ny, nz), 0.02, np.float32); vol[K[:,0], K[:,1], K[:,2]] = out
vol[-1] = vol[-2]
vol = gaussian_filter(vol, 0.8)
vs, fs, _, _ = marching_cubes(vol, 0.0, spacing=(VX, VX, VX)); vs += lo; del vol
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
nv = len(vs); e = np.concatenate([fs[:,[0,1]], fs[:,[1,2]]])
ncomp, labv = connected_components(coo_matrix((np.ones(len(e), np.int8), (e[:,0], e[:,1])), shape=(nv, nv)), directed=False)
cnt = np.bincount(labv); big = cnt.argmax(); keepv = labv == big
fk = fs[keepv[fs[:,0]]]; remap = -np.ones(nv, int); remap[keepv] = np.arange(keepv.sum()); vs, fs = vs[keepv], remap[fk]
print('pieces', ncomp, 'dropped verts', nv - keepv.sum(), 'kept tris', len(fs), round(time.time()-t0))
bpy.ops.wm.read_factory_settings(use_empty=True)
m2 = bpy.data.meshes.new('shell'); m2.from_pydata(vs.tolist(), [], fs.tolist()); m2.update()
o = bpy.data.objects.new('shell', m2); bpy.context.scene.collection.objects.link(o); bpy.context.view_layer.objects.active = o; o.select_set(True)
md = o.modifiers.new('s', 'LAPLACIANSMOOTH'); md.iterations = 3; md.lambda_factor = 0.4; md.use_volume_preserve = True; bpy.ops.object.modifier_apply(modifier='s')
md = o.modifiers.new('d', 'DECIMATE'); md.ratio = 0.4; bpy.ops.object.modifier_apply(modifier='d')
for v in m2.vertices:
    if abs(v.co.x) < VX*0.6: v.co.x = 0.0
md = o.modifiers.new('mir', 'MIRROR'); md.use_axis[0] = True; md.use_mirror_merge = True; md.merge_threshold = VX*0.3; bpy.ops.object.modifier_apply(modifier='mir')
for p in m2.polygons: p.use_smooth = True
print('faces', len(m2.polygons))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '.blend'); bpy.ops.export_scene.gltf(filepath=OUT + '.glb', export_format='GLB')
print('saved', round(time.time()-t0))
