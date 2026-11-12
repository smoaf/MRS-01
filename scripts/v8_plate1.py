# Front plate, step 1: plate surface (1 mm inside the foam's inner face) and the rib pattern on it.
import sys as _s; _ARGS = _s.argv[_s.argv.index('--')+1:] if '--' in _s.argv else []
_src = open('/home/claude/scripts/v8_sheetA3.py').read().split('\n'); _k = [i for i, l in enumerate(_src) if l.startswith('pmax = p')][0]
exec('\n'.join(_src[:_k+1]))                       # RMID, PM, NRM, ph, psis, pmax, rimdepth, SC, T, _TH, _DE ... (model units)
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
OUTP = '/home/claude/v8/plate/'; MM = 0.001/SC
SEED = int(_ARGS[0]) if _ARGS else 3
TP = 5.0*MM; CLR = 2.5*MM                          # plate thickness, gap to the foam
# plate mid-surface: foam mid-surface moved inward along its normal
Q = PM - NRM*(T/2 + CLR + TP/2); valid = ph[None, :] <= pmax[:, None]
rQ = np.linalg.norm(Q, axis=-1); phQ = np.arccos(np.clip(Q[..., 1]/rQ, -1, 1)); psQ = np.arctan2(Q[..., 2], Q[..., 0]) % (2*np.pi)
GP = np.arange(0.0, 3.0, 0.004); GS = np.linspace(0, 2*np.pi, 1440, endpoint=False); GPm, GSm = np.meshgrid(GP, GS, indexing='ij')
sub = np.zeros_like(valid); sub[:, ::2] = True; m = valid & sub
pts = np.c_[phQ[m], psQ[m]]; val = rQ[m]
pts = np.r_[pts, pts - [0, 2*np.pi], pts + [0, 2*np.pi]]; val = np.r_[val, val, val]
Rp = griddata(pts, val, (GPm, GSm), method='linear')
# edge of the foam on this surface, per psi; beyond it the plate runs straight forward (collar)
pe = np.array([phQ[j, valid[j]].max() for j in range(len(psis))]); re = np.array([rQ[j, valid[j]][np.argmax(phQ[j, valid[j]])] for j in range(len(psis))])
pse = np.array([psQ[j, valid[j]][np.argmax(phQ[j, valid[j]])] for j in range(len(psis))]); o = np.argsort(pse)
PE = np.interp(GS, pse[o], pe[o], period=2*np.pi); RHOE = np.interp(GS, pse[o], (re*np.sin(pe))[o], period=2*np.pi)
PE = wrapf(_gf, PE[None, :], 6)[0] - 0.006; RHOE = np.interp(GS, GS, RHOE)
kE = np.clip(np.searchsorted(GP, PE), 1, len(GP) - 1); RHOE = np.array([Rp[kE[j] - 1, j]*np.sin(GP[kE[j] - 1]) if np.isfinite(Rp[kE[j] - 1, j]) else RHOE[j] for j in range(len(GS))])
RHOE = wrapf(_gf, RHOE[None, :], 4)[0]
beyond = GPm > PE[None, :]
Rp = np.where(beyond | ~np.isfinite(Rp), RHOE[None, :]/np.maximum(np.sin(GPm), 0.05), Rp)
Rp[:13] = Rp[13:14].mean()                          # pole cap
Rp = _gf(np.c_[Rp[:, -20:], Rp, Rp[:, :20]], 1.5, mode='nearest')[:, 20:-20]
X = dvec(GPm, GSm)*Rp[..., None]                    # model units
U = np.clip(GPm/PE[None, :], 0, 1.3)
# surface slope factor for true thickness
dR = np.gradient(Rp, GP, axis=0)/Rp; COS = 1/np.sqrt(1 + dR**2)
# --- pattern: big cells in the middle, smaller toward the rim, mirror-symmetric ---
rng = np.random.default_rng(SEED)
def cell_r(u): return (0.250 - 0.125*np.clip(u, 0, 1)**1.3)/SC          # wanted seed spacing (m at 80 cm -> model)
dom = (U < 0.97) & (X[..., 0] >= 0)
area = Rp**2*np.sin(GPm); cand = np.argwhere(dom); pw = area[dom]/area[dom].sum()
seeds = []
for idx in rng.choice(len(cand), 6000, p=pw):
    i, j = cand[idx]; p = X[i, j].copy(); r = cell_r(U[i, j])
    if p[0] < 0.3*r: p[0] = 0.0
    elif p[0] < 0.55*r: continue
    if all(np.linalg.norm(p - q) > 0.5*(r + rq) for q, rq in seeds) and all(np.linalg.norm(p*[-1, 1, 1] - q) > 0.5*(r + rq) or p[0] == 0 for q, rq in seeds): seeds.append((p, r))
S0 = np.array([s for s, _ in seeds])
def full(S): return np.r_[S, S[S[:, 0] > 0]*[-1, 1, 1]]
Xd = X[U < 1.0]; Ad = area[U < 1.0]; tree_s = cKDTree(X.reshape(-1, 3))
for it in range(4):                                  # Lloyd relaxation, keeps the grading, evens out the cells
    S = full(S0); _, lab = cKDTree(S).query(Xd)
    for k in range(len(S0)):
        mk = lab == k
        if mk.sum() < 5: continue
        c = (Xd[mk]*Ad[mk, None]).sum(0)/Ad[mk].sum(); c = X.reshape(-1, 3)[tree_s.query(c)[1]]
        S0[k] = [0.0, c[1], c[2]] if S0[k, 0] == 0 else 0.5*(S0[k] + c)
        if S0[k, 0] == 0: S0[k] = X.reshape(-1, 3)[tree_s.query(S0[k])[1]]*[0, 1, 1]
S = full(S0); print('cells', len(S), '(', len(S0), 'on one side incl. centre line )')
d, _ = cKDTree(S).query(X.reshape(-1, 3), k=2); E = ((d[:, 1] - d[:, 0])/2).reshape(Rp.shape)       # distance to the nearest cell border
BL = 3.5; Wd = (0.022*cell_r(U) + 0.5*MM + 0.8*BL*1.68*MM*0.75)                                                                      # rib half-width: 6 mm at the rim to 9 mm in the middle
F = E - Wd
# solid rim band: the last 22 mm of the foam plus the collar
th = np.arctan2(X[..., 2], np.abs(X[..., 0])); sband = rimdepth(X) - (np.interp(th, _TH, _DE) + 16*MM)
k_ = 6*MM; hmix = np.clip(0.5 + 0.5*(sband - F)/k_, 0, 1); F = sband*(1 - hmix) + F*hmix - k_*hmix*(1 - hmix)     # smooth union
Fp = np.c_[F[:, -30:], F, F[:, :30]]; F = _gf(Fp, [BL, BL], mode='nearest')[:, 30:-30]                     # fillets at the junctions
solid = (F < 0) & (U <= 1.0); lat = U <= 1.0
print('open area inside the rim band: %.0f %%' % (100*(area[lat & ~solid & (sband > 0)].sum()/area[lat & (sband > 0)].sum())))
np.savez(OUTP + 'plate_surface.npz', Rp=Rp, F=F, COS=COS, GP=GP, GS=GS, PE=PE, RHOE=RHOE, S=S, TP=TP)
# preview, seen from the singer: unrolled around the back centre
fig, ax = plt.subplots(figsize=(9, 9)); arc = np.cumsum(np.r_[np.zeros((1, Rp.shape[1])), np.linalg.norm(np.diff(X, axis=0), axis=-1)], 0)*SC*1000
arc = np.where(U <= 1.02, arc, np.nan); xx = np.nan_to_num(arc*np.cos(GSm)); yy = np.nan_to_num(arc*np.sin(GSm)); lat = U <= 1.02; ax.contourf(xx, yy, np.where(lat, F, np.nan)*SC*1000, levels=[-1e3, 0], colors=['#d9d9d6']); ax.contour(xx, yy, np.where(lat, F, np.nan), levels=[0], colors='k', linewidths=0.6)
ax.set_xlim(-640, 640); ax.set_ylim(-640, 640); ax.set_aspect('equal'); ax.axis('off'); ax.set_title('Rib pattern, unrolled (rim stretched)'); fig.savefig(OUTP + 'pattern_seed%d.png' % SEED, dpi=70)
