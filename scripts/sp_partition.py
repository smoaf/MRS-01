# Split pipeline, step 1: mirror-symmetric partition into parts that fit the bed, and the strut crossings on every seam.
# usage: sp_partition.py <shell|plate> <bed_x> <bed_y> <bed_z> <tag> [tries]
import sys, json, numpy as np, trimesh, warnings; warnings.filterwarnings('ignore')
from scipy.spatial import cKDTree
from shapely.geometry import Polygon
from shapely.ops import polylabel
name, bx, by, bz, tag = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]; TRIES = int(sys.argv[6]) if len(sys.argv) > 6 else 5
OUT = '/home/claude/v8/split/'; mesh = trimesh.load(OUT + f'base_{name}.stl'); MARG = float(sys.argv[7]) if len(sys.argv) > 7 else 14.0
rng = np.random.default_rng(1); P, _ = trimesh.sample.sample_surface(mesh, 40000, seed=1); P = np.asarray(P); PH = P[P[:, 0] >= 0]
# candidate print orientations: up directions x spin
def fib(n):
    i = np.arange(n) + 0.5; ph = np.arccos(1 - 2*i/n); th = np.pi*(1 + 5**0.5)*i; return np.c_[np.cos(th)*np.sin(ph), np.sin(th)*np.sin(ph), np.cos(ph)]
UPS = fib(150)
def frames(u):
    a = np.cross(u, [0, 0, 1] if abs(u[2]) < 0.9 else [1, 0, 0]); a /= np.linalg.norm(a); b = np.cross(u, a); return a, b
def fits(Q):
    for u in UPS:
        h = Q @ u
        if h.max() - h.min() + MARG > bz: continue
        a, b = frames(u); A, B = Q @ a, Q @ b
        for s in np.linspace(0, np.pi/2, 10, endpoint=False):
            X = A*np.cos(s) + B*np.sin(s); Y = -A*np.sin(s) + B*np.cos(s); ex, ey = X.max() - X.min() + MARG, Y.max() - Y.min() + MARG
            if (ex <= bx and ey <= by) or (ex <= by and ey <= bx): return True
    return False
FIXED = [0.0, 0.0, -360.0] if name == 'shell' else None          # one part is centred on the stand mount
def full(S): return np.r_[S, S[S[:, 0] > 0]*[-1, 1, 1]]
def kmeans(k, seed):
    r = np.random.default_rng(seed); S = [np.array(FIXED)] if FIXED is not None else [PH[r.integers(len(PH))]]
    for _ in range(k - 1):
        d = cKDTree(full(np.array(S))).query(PH)[0]; S.append(PH[np.argmax(d*(0.7 + 0.6*r.random(len(PH))))])
    S = np.array(S); 
    for it in range(25):
        d = cKDTree(full(S)).query(S, k=2)[0][:, 1]
        S[:, 0] = np.where(S[:, 0] < 0.33*np.median(d), 0.0, S[:, 0])
        lab = cKDTree(full(S)).query(PH)[1]
        for i in range(len(S)):
            m = lab == i
            if m.sum() < 3 or (FIXED is not None and i == 0): continue
            c = PH[m].mean(0); S[i] = [0.0, c[1], c[2]] if S[i, 0] == 0 else c
    return S
def partition(k, seed):
    S = kmeans(k, seed); FS = full(S); lab = cKDTree(FS).query(P)[1]
    return FS, lab, all(fits(P[lab == i][::3]) for i in range(len(FS)))
ORI = np.zeros(3)
def crossings(FS):
    T = cKDTree(FS); d, ix = T.query(P, k=2); near = (d[:, 1] - d[:, 0]) < 20; pairs = {}
    for a, b in ix[near]: pairs[(min(a, b), max(a, b))] = pairs.get((min(a, b), max(a, b)), 0) + 1
    out = []; bad = 0
    for (i, j), cnt in sorted(pairs.items()):
        if cnt < 6: continue
        n = FS[j] - FS[i]; n /= np.linalg.norm(n); m = (FS[i] + FS[j])/2
        sec = mesh.section(plane_origin=m, plane_normal=n)
        if sec is None: continue
        for loop in sec.discrete:
            if len(loop) < 4: continue
            dd, ii = T.query(loop, k=3); own = np.isin(ii[:, 0], [i, j]) & np.isin(ii[:, 1], [i, j])
            if own.mean() < 0.5: continue                                  # the loop belongs to another seam
            c0 = loop.mean(0); r = c0 - ORI; r -= n*(r @ n); r /= np.linalg.norm(r); t = np.cross(n, r)
            uv = np.c_[(loop - m) @ t, (loop - m) @ r]; poly = Polygon(uv).buffer(0)
            if poly.is_empty or poly.area < 4: continue
            if hasattr(poly, 'geoms'): poly = max(poly.geoms, key=lambda g: g.area)
            lab_ = polylabel(poly, tolerance=0.3); cu = np.array(lab_.coords[0]); inr = float(poly.exterior.distance(lab_))
            c = m + t*cu[0] + r*cu[1]; rr = c - ORI; rr -= n*(rr @ n); rr /= np.linalg.norm(rr)
            q = np.array(poly.exterior.coords) - cu; ev, evec = np.linalg.eigh(np.cov(q.T)); ext = [float(np.ptp(q @ evec[:, 1])), float(np.ptp(q @ evec[:, 0]))]
            w = t*evec[0, 0] + r*evec[1, 0]                                 # thin direction of the section
            if ext[0]/max(ext[1], 1e-6) < 1.4 or abs(w @ rr) > 0.5: w = rr if ext[0]/max(ext[1], 1e-6) < 1.4 else w*np.sign(w @ rr)
            w = w - n*(w @ n); w /= np.linalg.norm(w); u = np.cross(n, w)
            triple = bool(own.mean() < 0.999); long_ = ext[0] > 70
            bad += triple + long_ + (poly.area < 30)
            out.append(dict(i=int(i), j=int(j), c=c.tolist(), n=n.tolist(), u=u.tolist(), w=w.tolist(), area=float(poly.area), ext=ext, inradius=inr, triple=triple, long=bool(long_)))
    return out, bad
# smallest part count that fits, then the cleanest of a few layouts
k = max(2, int(np.ceil(0.5*mesh.bounding_box.volume**(1/3)/ (0.55*min(bx, by)))))
best = None
while best is None and k < 60:
    for seed in range(TRIES):
        FS, lab, ok = partition(k, seed)
        if not ok: continue
        if FIXED is not None:
            d_ = np.linalg.norm(FS - FIXED, axis=1); o_ = np.argsort(d_); clear = min((d_[j]**2 - d_[o_[0]]**2)/(2*np.linalg.norm(FS[j] - FS[o_[0]])) for j in o_[1:])
            if clear < 40: continue
        cr, bad = crossings(FS); score = bad + 0.02*len(cr); print(f'k_half {k} seed {seed}: parts {len(FS)}, crossings {len(cr)}, awkward {bad}', flush=True)
        if best is None or score < best[0]: best = (score, FS, cr, seed)
    k += 1
score, FS, cr, seed = best; lab = cKDTree(FS).query(P)[1]
print('chosen: parts', len(FS), 'crossings', len(cr), 'score', round(score, 2)); a_ = np.array([c['area'] for c in cr]); ir = np.array([c['inradius'] for c in cr]); print('section area mm2 min/med/max', a_.min().round(), np.median(a_).round(), a_.max().round(), ' inradius min/med/max', ir.min().round(1), np.median(ir).round(1), ir.max().round(1), ' per seam crossings', round(len(cr)/len({(c['i'], c['j']) for c in cr}), 1))
json.dump(dict(name=name, bed=[bx, by, bz], seeds=FS.tolist(), crossings=cr), open(OUT + f'partition_{name}_{tag}.json', 'w'))
