# Version A2: one 30 mm sheet, 6 darts, full v3 size (no global inward shift), edge 2 mm behind the lip front on both faces,
# darts on the vertical centre line (top, bottom) and every 60 deg, pattern drawn with the shell top up, seen from the singer.
import sys as _s; _ARGS = _s.argv[_s.argv.index('--')+1:] if '--' in _s.argv else []
exec(open('/home/claude/scripts/v8_sheet_common.py').read())
import bpy, bmesh, json
from shapely.geometry import Polygon
from collections import defaultdict
OUT = '/home/claude/v8/sheetA3/'
_A3 = np.load(OUT + 'A3_surface.npz'); Rs = _A3['S']; _TH, _DE = _A3['TH'], _A3['DE']
def edgedepth(P): return rimdepth(P) - np.interp(np.arctan2(P[..., 2], np.abs(P[..., 0])), _TH, _DE)
ROUT = Rs; RMID = ROUT - T/2
# 2) edge: stop where either face comes within 2 mm of the lip front
NPS, NU = 240, 70
psis = np.linspace(0, 2*np.pi, NPS, endpoint=False); ph = np.linspace(0.05, 2.9, 1400)
PH, PS = np.meshgrid(ph, psis); D = dvec(PH, PS); PM = D*surf_r(RMID, D)[..., None]          # mid-surface, psi x phi
dphi = np.gradient(PM, ph, axis=1); dpsi = (np.roll(PM, -1, 0) - np.roll(PM, 1, 0))
NRM = np.cross(dpsi, dphi); NRM /= np.linalg.norm(NRM, axis=-1, keepdims=True)
NRM *= np.sign((NRM*D).sum(-1, keepdims=True))                                                   # point outward
rd = np.minimum(edgedepth(PM + NRM*T/2), edgedepth(PM - NRM*T/2))
raw = np.array([ph[np.where(r_ < 0)[0][0]] if (r_ < 0).any() else ph[-1] for r_ in rd])
p = raw.copy()
for it in range(3):
    p = np.convolve(np.r_[p[-4:], p, p[:4]], np.ones(9)/9, 'valid'); p = np.minimum(p, raw)
print('edge smoothing pulled back by max deg', round(float(np.degrees((raw - p).max())), 2))
pmax = p
us = np.linspace(0, 1, NU + 1)[1:]
c0 = dvec(np.array([0.0]), np.array([0.0])); verts = [c0[0]*surf_r(RMID, c0)[0]]
for u in us:
    D = dvec(u*pmax, psis); verts += list(D*surf_r(RMID, D)[:, None])
verts = np.array(verts)*SC
vid = lambda i, j: 1 + i*NPS + (j % NPS)
faces = [(0, vid(0, j), vid(0, j+1)) for j in range(NPS)]
for i in range(NU - 1):
    for j in range(NPS):
        faces += [(vid(i, j), vid(i+1, j), vid(i+1, j+1)), (vid(i, j), vid(i+1, j+1), vid(i, j+1))]
F = np.array(faces)
# which psi is up (+z) and right (+x)?
ang = np.degrees(np.arctan2(verts[1:NPS+1, 2], verts[1:NPS+1, 0]))
j_top = int(np.argmin(np.abs(((ang - 90) + 180) % 360 - 180)))
cols = [(j_top + k*NPS//6) % NPS for k in range(6)]
print('dart columns at front-view angles', [round(float(ang[j]), 1) for j in cols])
U0 = float(_ARGS[1]) if len(_ARGS) > 1 else 0.25
def unwrap(u0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new('A'); me.from_pydata(verts.tolist(), [], faces); me.update()
    o = bpy.data.objects.new('A', me); bpy.context.scene.collection.objects.link(o); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bm = bmesh.new(); bm.from_mesh(me); i0 = int(round(u0*NU)) - 1
    seam = {frozenset((vid(i, j), vid(i+1, j))) for j in cols for i in range(max(i0, 0), NU - 1)}
    for e in bm.edges:
        if frozenset((e.verts[0].index, e.verts[1].index)) in seam: e.seam = True
    bm.to_mesh(me); bm.free()
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.unwrap(method='MINIMUM_STRETCH', margin=0.0); bpy.ops.object.mode_set(mode='OBJECT')
    UVl = np.zeros(len(me.loops)*2); me.uv_layers.active.data.foreach_get('uv', UVl); U2 = UVl.reshape(-1, 3, 2)
    T3 = verts[F]; l3 = np.linalg.norm(T3 - np.roll(T3, -1, 1), axis=2).sum(); l2 = np.linalg.norm(U2 - np.roll(U2, -1, 1), axis=2).sum(); U2 = U2*l3/l2
    return U2, dict(stretch(U2), u0=u0)
def stretch(U2):
    T3 = verts[F]; e1 = T3[:,1] - T3[:,0]; e2 = T3[:,2] - T3[:,0]; nrm = np.cross(e1, e2); A3 = 0.5*np.linalg.norm(nrm, axis=1)
    b1 = e1/np.linalg.norm(e1, axis=1, keepdims=True); b2 = np.cross(nrm/np.linalg.norm(nrm, axis=1, keepdims=True), b1)
    X = np.stack([np.stack([(e1*b1).sum(1), (e1*b2).sum(1)], 1), np.stack([(e2*b1).sum(1), (e2*b2).sum(1)], 1)], 2)
    Y = np.stack([U2[:,1] - U2[:,0], U2[:,2] - U2[:,0]], 2); J = Y @ np.linalg.inv(X); sv = np.linalg.svd(J, compute_uv=False); det = np.linalg.det(J)
    def wq(v, q): o_ = np.argsort(v); c = np.cumsum(A3[o_]); return float(v[o_][np.searchsorted(c, q*c[-1])])
    return dict(p5=round(wq(sv[:,1], 0.05), 3), p95=round(wq(sv[:,0], 0.95), 3), mirrored=bool(np.median(det) < 0), flipped=int((det*np.sign(np.median(det)) <= 0).sum()))
U2, st = unwrap(U0); print('stretch', st)
# orient: seen from the singer (front), +x right, +z up
U2 = U2*1000  # mm
if st['mirrored']: U2[..., 0] *= -1
uvv = {}
for f in range(len(F)):
    for a in range(3): uvv.setdefault(F[f, a], []).append(U2[f, a])
cen = np.mean(uvv[0], 0)
def at(j, i=NU//2): return np.mean(uvv[vid(i, j)], 0)
jr = int(np.argmin(np.abs(ang))); jl = int(np.argmin(np.abs(np.abs(ang) - 180)))
# panel centres at +-30 deg from top are symmetric pairs; use top-bottom axis: mean of the two sides of the top dart
up = (at((j_top + NPS//12) % NPS) + at((j_top - NPS//12) % NPS))/2 - cen
rot = np.pi/2 - np.arctan2(up[1], up[0]); R = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
U2 = (U2 - cen) @ R.T
# make the flat layout exactly mirror-symmetric: average each corner with its mirror corner
i0s = int(round(U0*NU)) - 1; seamset = {(i, j) for j in cols for i in range(max(i0s, 0), NU)}
def vij(v): return (None, None) if v == 0 else ((v - 1)//NPS, (v - 1) % NPS)
def side(f, v):
    i, j = vij(v)
    if (i, j) not in seamset: return 0
    js = [vij(w)[1] for w in F[f] if w != v and w != 0]; d = ((np.mean([((x - j + NPS//2) % NPS) - NPS//2 for x in js])))
    return 1 if d > 0 else -1
key = {}; acc = defaultdict(list)
for f in range(len(F)):
    for a in range(3):
        v = F[f, a]; k = (v, side(f, v)); key[(f, a)] = k; acc[k].append(U2[f, a])
mean = {k: np.mean(v, 0) for k, v in acc.items()}
def mir(k):
    v, s_ = k
    if v == 0: return k
    i, j = vij(v); return (vid(i, (2*j_top - j) % NPS), -s_)
sym = {k: (mean[k] + mean[mir(k)]*[-1, 1])/2 for k in mean}
U2 = np.array([[sym[key[(f, a)]] for a in range(3)] for f in range(len(F))])
st = stretch(U2/1000); print('after symmetry, stretch', st)
# outline from boundary edges
from collections import defaultdict
ed = defaultdict(list)
for f in range(len(F)):
    for a in range(3):
        p_, q_ = tuple(np.round(U2[f, a], 3)), tuple(np.round(U2[f, (a+1) % 3], 3)); ed[tuple(sorted((p_, q_)))].append(f)
bnd = [k for k, v in ed.items() if len(v) == 1]; adj = defaultdict(list)
for a, b in bnd: adj[a].append(b); adj[b].append(a)
start = bnd[0][0]; loop = [start]; prev = None; cur = start
for _ in range(len(bnd) + 2):
    nx_ = [x for x in adj[cur] if x != prev]
    if not nx_: break
    prev, cur = cur, nx_[0]
    if cur == start: break
    loop.append(cur)
L = np.array(loop); poly = Polygon(L)
mirror = Polygon(L*[-1, 1]); asym = poly.symmetric_difference(mirror).area/poly.area
print('outline valid', poly.is_valid, 'size', (L.max(0) - L.min(0)).round(), 'mirror mismatch %', round(asym*100, 2))
np.savez(OUT + 'A3_mid.npz', V=verts, F=F)
json.dump(dict(stretch=st, j_top=j_top, cols=cols, U0=U0, NU=NU, NPS=NPS, outline=L.tolist(), size=(L.max(0) - L.min(0)).round().tolist()), open(OUT + 'A3_flat.json', 'w'))
# morph data for the animation: split vertices (vertex, side), 3D position (m) and flat position (mm, x right, y up as seen from the singer)
klist = sorted(sym.keys(), key=lambda k: (k[0], k[1])); kidx = {k: i for i, k in enumerate(klist)}
FM = np.array([[kidx[key[(f, a)]] for a in range(3)] for f in range(len(F))])
np.savez(OUT + 'A3_morph.npz', P3=np.array([verts[k[0]] for k in klist]), P2=np.array([sym[k] for k in klist])/1000, F=FM, ring=np.array([0 if k[0] == 0 else vij(k[0])[0] + 1 for k in klist]))
print('morph verts', len(klist))
