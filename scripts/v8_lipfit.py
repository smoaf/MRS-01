# A3 outer face: A2 surface, flared outward in the last few cm so the edge tucks behind the lip band.
import sys as _s; _ARGS = _s.argv[_s.argv.index('--')+1:] if '--' in _s.argv else []
exec(open('/home/claude/scripts/v8_sheet_common.py').read())
import bpy
from mathutils.bvhtree import BVHTree
from mathutils import Vector
from scipy.ndimage import minimum_filter as _minf
MM = 0.001/SC                                   # 1 real mm in model units
OV = float(_ARGS[0]) if _ARGS else 10.0         # wanted overlap behind the band, mm
CL = 2.0                                        # clearance to shell material, mm
# A2 surface (same as v8_sheetA2.py, sigma 6)
Rs = wrapf(_gf, RS_IN, 6.0)
for it in range(12):
    over = np.maximum(Rs - RS_IN, 0); Rs = Rs - wrapf(_gf, over, 2.0)*1.6
bpy.ops.wm.open_mainfile(filepath='/home/claude/v8/step2i.blend'); sh = bpy.data.objects['shell']
bvh = BVHTree.FromObject(sh, bpy.context.evaluated_depsgraph_get())
# band per front-view angle th (x>=0 half, mirrored): inner edge radius and back face depth
TH = np.radians(np.arange(-90, 90.01, 1.0)); yfr = np.interp(TH, bc_, ymin); RIN = np.full(len(TH), np.nan); DB = np.full(len(TH), np.nan)
for k, th in enumerate(TH):
    hits = []
    for rho in np.arange(0.20, 0.55, 0.0015):
        o = Vector((rho*np.cos(th), yfr[k] - 0.05, rho*np.sin(th))); loc, n_, i_, d_ = bvh.ray_cast(o, Vector((0, 1, 0)), 0.5)
        if loc is None or loc.y - yfr[k] > 0.004: continue
        loc2, *_ = bvh.ray_cast(loc + Vector((0, 1e-4, 0)), Vector((0, 1, 0)), 0.5)
        hits.append((rho, (loc2.y - yfr[k]) if loc2 is not None else np.nan))
    if hits:
        RIN[k] = hits[0][0]; near = [d for r, d in hits if abs(r - hits[0][0] - OV*MM) <= 3*MM and np.isfinite(d)]; DB[k] = min(np.median(near), 25*MM) if near else np.nan
ok = np.isfinite(RIN) & np.isfinite(DB)
RIN = np.interp(TH, TH[ok], RIN[ok]); DB = np.interp(TH, TH[ok], DB[ok])
from scipy.ndimage import median_filter as _medf
RIN = _gf(_medf(RIN, 5, mode='nearest'), 1.5, mode='nearest'); DB = _gf(_medf(DB, 5, mode='nearest'), 1.5, mode='nearest')
DE = DB + 2*MM                                   # the inlay edge sits 2 mm behind the band's back face
for k in range(0, len(TH), 15): print(f'th {np.degrees(TH[k]):5.0f}: band inner {RIN[k]/MM:5.0f} mm, band depth {DB[k]/MM:5.1f} mm')
# shell material along each radial ray, band hits excluded
L = np.load('/home/claude/v8/sheetA3/lipspace.npz'); rhit = L['rhit']; hp = L['hitP']
thh = np.arctan2(hp[..., 2], np.abs(hp[..., 0])); rdh = rimdepth(np.nan_to_num(hp))
isband = np.isfinite(rhit) & (rdh < np.interp(thh, TH, DB) + 1*MM)
rmat = np.where(np.isfinite(rhit) & ~isband, rhit, 9.0)
rlim = wrapf(_minf, rmat, 5) - CL*MM                                 # outer face may not pass this
# grid geometry
AZ, EL = np.meshgrid((np.arange(NA) + 0.5)*RES - np.pi, (np.arange(NE) + 0.5)*RES - np.pi/2, indexing='ij')
DIR = np.stack([np.cos(EL)*np.sin(AZ), np.cos(EL)*np.cos(AZ), np.sin(EL)], -1); dxz = np.hypot(DIR[..., 0], DIR[..., 2])
S = Rs.copy(); dS = np.zeros_like(S)
for it in range(6):
    P = DIR*S[..., None]; th = np.arctan2(P[..., 2], np.abs(P[..., 0])); rho = np.hypot(P[..., 0], P[..., 2]); rd = rimdepth(P)
    de = np.interp(th, TH, DE); rt = np.interp(th, TH, RIN) + OV*MM
    w = 1 - np.clip((rd - de - 10*MM)/(80*MM), 0, 1); w = w*w*(3 - 2*w)
    w = w*inside
    need = np.minimum(np.maximum(rt - rho, 0)/np.maximum(dxz, 0.3), 60*MM)*w
    dS = np.maximum(dS, need); dS = wrapf(_gf, dS, 1.5)
    S = Rs + np.minimum(dS, np.maximum(rlim - Rs, 0))
    S = np.minimum(S, wrapf(_gf, S, 1.0) + 0.5*MM)                       # remove sharp clamp steps
print('flare: max outward mm', round(float((S - Rs).max()/MM), 1), ' cells limited by struts', int(((Rs + dS > rlim) & (dS > 1*MM)).sum()))
# smooth the flare: no streaks, still clear of the struts (a final small overshoot is soaked up by the soft foam)
Lf = S - Rs; cap = np.maximum(rlim - Rs, 0)
for it in range(5):
    Lf = wrapf(_gf, Lf, 2.0); Lf = np.minimum(Lf, cap + 2.5*MM)
Lf = wrapf(_gf, Lf, 1.2); S = Rs + np.maximum(Lf, 0)
S = 0.5*(S + S[mi, :])                                                   # keep mirror symmetry
np.savez('/home/claude/v8/sheetA3/A3_surface.npz', S=S, TH=TH, DE=DE, RIN=RIN, DB=DB, OV=OV)
