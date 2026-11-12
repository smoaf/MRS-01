# shared: smooth inner surface of the shell (RS_IN), rim, and helpers in a (phi, psi) frame around the depth axis
import sys
sys.argv = [sys.argv[0], '--', '30']
_src = open('/home/claude/scripts/v8_inlay3.py').read().split('\n')
exec('\n'.join(_src[:79]))          # defines RS_IN (outer face of the inlay), rin_at, rimdepth, SC, T, GAP, wrapf, ...
from scipy.ndimage import gaussian_filter as _gf, map_coordinates as _mc
def dvec(phi, psi):
    return np.stack([np.sin(phi)*np.cos(psi), np.cos(phi), np.sin(phi)*np.sin(psi)], -1)
def to_ae(D):
    return np.arctan2(D[...,0], D[...,1]), np.arctan2(D[...,2], np.hypot(D[...,0], D[...,1]))
def surf_r(R, D):
    a, e = to_ae(D); fi = (a + np.pi)/RES - 0.5; fj = (e + np.pi/2)/RES - 0.5
    return _mc(R, [np.ravel(fi), np.ravel(fj)], order=1, mode='nearest').reshape(np.shape(fi))
def simplified(sigma, allow=0.002):
    """heavily smoothed outer face, shifted in so it never comes closer to the shell than RS_IN (+allow)"""
    Rs = wrapf(_gf, RS_IN, sigma)
    over = np.maximum(Rs - RS_IN, 0)[inside]
    shift = max(0.0, float(np.percentile(over, 99.8)) - allow)
    return Rs - shift, shift
def rim_phi(Rmid, psis, stop=0.002):
    """phi where the mid-surface reaches 2 mm behind the lip front, per psi"""
    ph = np.linspace(0.05, 2.9, 1400); out = []
    for ps in psis:
        D = dvec(ph, np.full_like(ph, ps)); P = D*surf_r(Rmid, D)[:, None]; rd = rimdepth(P)
        k = np.where(rd < stop)[0]; out.append(ph[k[0]] if len(k) else ph[-1])
    return np.array(out)
