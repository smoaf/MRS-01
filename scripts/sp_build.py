# Split pipeline, step 2: collars, cut into parts, connectors, print orientation, STL export.
# usage: sp_build.py -- <shell|plate> <tag> <pins|keys|lap>
import bpy, bmesh, sys, json, os, numpy as np, time
from mathutils import Vector, Matrix
name, tag, conn = sys.argv[sys.argv.index('--') + 1:][:3]; t0 = time.time()
OUT = '/home/claude/v8/split/'; D = json.load(open(OUT + f'partition_{name}_{tag}.json')); S = np.array(D['seeds']); CR = D['crossings']
for c in CR: c['a'], c['b'] = c['i'], c['j']; bed = D['bed']
DST = OUT + f'build/{conn}/{tag}/{name}/'; os.makedirs(DST, exist_ok=True)
PRM = dict(shell=dict(col=(18.0, 10.0, 10.0), col_if=7.0, pin=(9.0, 8.0, 6.0), key=(11.0, 9.0, 4.5, 6.0, -1), lap=(10.0, 13.0)),
           plate=dict(col=(16.0, 10.0, 4.5), col_if=9.0, pin=(8.0, 8.0, 3.2), key=(10.0, 8.0, 4.0, 4.0, +1), lap=(9.0, 13.0)))[name]
CL = 0.15
def frame(c): n, w = np.array(c['n']), np.array(c['w']); return np.array(c['c']), n, np.cross(w, n), w      # right-handed (n, u, w)
def mat(o, n, u, w): M = Matrix(((n[0], u[0], w[0], o[0]), (n[1], u[1], w[1], o[1]), (n[2], u[2], w[2], o[2]), (0, 0, 0, 1))); return M
def new_obj(nm, bm): me = bpy.data.meshes.new(nm); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(nm, me); bpy.context.scene.collection.objects.link(o); return o
def add_box(bm, c, n, u, w, lo, hi):
    g = bmesh.ops.create_cube(bm, size=1.0)['verts']; sz = np.array(hi) - np.array(lo); ce = (np.array(hi) + np.array(lo))/2
    bmesh.ops.scale(bm, vec=Vector(sz), verts=g); bmesh.ops.translate(bm, vec=Vector(ce), verts=g); bmesh.ops.transform(bm, matrix=mat(c, n, u, w), verts=g)
def add_prism(bm, c, n, u, w, poly, z0, z1):                    # poly in (n, u), extruded along w
    vb = [bm.verts.new((p[0], p[1], z0)) for p in poly]; vt = [bm.verts.new((p[0], p[1], z1)) for p in poly]; k = len(poly)
    bm.faces.new(vb[::-1]); bm.faces.new(vt)
    for a in range(k): bm.faces.new((vb[a], vb[(a+1) % k], vt[(a+1) % k], vt[a]))
    bmesh.ops.transform(bm, matrix=mat(c, n, u, w), verts=vb + vt)
def bowtie(L, We, Ww, g=0.0): return [(-L - g, -We/2 - g), (0, -Ww/2 - g), (L + g, -We/2 - g), (L + g, We/2 + g), (0, Ww/2 + g), (-L - g, We/2 + g)]
def boolean(a, b, op, keep=False):
    v0 = stats(a)[1]; vb = abs(stats(b)[1]); backup = a.data.copy(); cands = []
    for solver in ('MANIFOLD', 'EXACT'):
        a.data = backup.copy(); m = a.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.object = b; m.solver = solver
        bpy.context.view_layer.objects.active = a
        try: bpy.ops.object.modifier_apply(modifier='b')
        except Exception: a.modifiers.clear(); continue
        if a.modifiers: a.modifiers.clear(); continue
        nm, v1 = stats(a); vok = len(a.data.polygons) > 0 and ((op == 'UNION' and v0 - 1 <= v1 <= v0 + vb + 1) or (op == 'DIFFERENCE' and v0 - vb - 1 <= v1 <= v0 + 1) or (op == 'INTERSECT' and v1 <= min(v0, vb) + 1))
        cands.append((not vok, nm, solver, a.data.copy()))
        if vok and nm == 0: break
    if cands:
        cands.sort(key=lambda t: (t[0], t[1])); bad, nm, solver, me = cands[0]; a.data = me
        if bad or nm: print('   boolean', op, 'kept', solver, 'volume ok' if not bad else 'VOLUME OFF', 'non-manifold edges', nm, flush=True)
    else: a.data = backup; print('   boolean', op, 'FAILED, skipped', flush=True)
    if not keep: bpy.data.objects.remove(b)
def stats(o):
    bm = bmesh.new(); bm.from_mesh(o.data); nm = sum(1 for e in bm.edges if not e.is_manifold); vol = bm.calc_volume(); bm.free(); return nm, vol
bpy.ops.wm.read_factory_settings(use_empty=True)
# ---- base with collars (cached per object and bed) ----
cache = OUT + f'build/_base_{name}_{tag}.blend'
if os.path.exists(cache): bpy.ops.wm.open_mainfile(filepath=cache); base = bpy.data.objects['base']
else:
    bpy.ops.wm.stl_import(filepath=OUT + f'base_{name}.stl'); base = bpy.context.selected_objects[0]; base.name = 'base'
    todo = [c for c in CR if c['inradius'] < PRM['col_if']]; k = len(todo); nb = 0
    while todo:                                           # batches of collars that do not touch each other, so the fast solver can take them
        batch = []; rest = []
        for c in todo:
            (batch if all(np.linalg.norm(np.array(c['c']) - np.array(d['c'])) > 2.3*PRM['col'][0] for d in batch) else rest).append(c)
        bm = bmesh.new()
        for c in batch:
            o, n, u, w = frame(c); g = bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=1.0)['verts']
            bmesh.ops.scale(bm, vec=Vector(PRM['col']), verts=g); bmesh.ops.transform(bm, matrix=mat(o, n, u, w), verts=g)
        boolean(base, new_obj('collars', bm), 'UNION'); todo = rest; nb += 1
    print('collar batches', nb, flush=True)
    print('collars', k, 'base after union', stats(base), round(time.time() - t0), 's', flush=True); bpy.ops.wm.save_as_mainfile(filepath=cache)
# ---- cut into parts ----
from scipy.spatial import HalfspaceIntersection, ConvexHull
from mathutils.bvhtree import BVHTree
def cell_obj(i):
    hs = []
    for j in range(len(S)):
        if j == i: continue
        n = S[j] - S[i]; n /= np.linalg.norm(n); m = (S[i] + S[j])/2; hs.append([*n, -float(n @ m)])
    for k in range(3):
        for sg in (1, -1): e = np.zeros(3); e[k] = sg; hs.append([*e, -1500.0])
    V = HalfspaceIntersection(np.array(hs), S[i] + 1e-3).intersections; h = ConvexHull(V); bm = bmesh.new(); vs = [bm.verts.new(V[k]) for k in h.vertices]; idx = {k: a for a, k in enumerate(h.vertices)}
    cen = V[h.vertices].mean(0)
    for tri, eq in zip(h.simplices, h.equations):
        t = [idx[k] for k in tri]; nrm = np.cross(V[tri[1]] - V[tri[0]], V[tri[2]] - V[tri[0]])
        if nrm @ eq[:3] < 0: t = t[::-1]
        bm.faces.new([vs[k] for k in t])
    return new_obj('cell', bm)
def cut_part(i):
    p = base.copy(); p.data = base.data.copy(); p.name = f'part_{i:02d}'; bpy.context.scene.collection.objects.link(p); boolean(p, cell_obj(i), 'INTERSECT'); return p
def split_loose(o):
    bm = bmesh.new(); bm.from_mesh(o.data); seen = set(); comps = []
    for v in bm.verts:
        if v.index in seen: continue
        st = [v]; comp = [v.index]; seen.add(v.index)
        while st:
            x = st.pop()
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen: seen.add(y.index); st.append(y); comp.append(y.index)
        comps.append(comp)
    comps.sort(key=len, reverse=True); out = []
    for comp in comps[1:]:
        b2 = bm.copy(); keep = set(comp); bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.index not in keep], context='VERTS'); vol = b2.calc_volume(); out.append((new_obj('frag', b2), vol))
    if len(comps) > 1:
        keep = set(comps[0]); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context='VERTS'); bm.to_mesh(o.data)
    bm.free(); return out
def add_hull(bm, V):
    h = ConvexHull(V); vs = {k: bm.verts.new(V[k]) for k in h.vertices}
    for tri, eq in zip(h.simplices, h.equations):
        t = list(tri); nrm = np.cross(V[t[1]] - V[t[0]], V[t[2]] - V[t[0]])
        if nrm @ eq[:3] < 0: t = t[::-1]
        bm.faces.new([vs[k] for k in t])
def add_box_in_cell(bm, c, n, u, w, lo, hi, k, i):
    """box in the joint frame, cut back to the region that is nearer to part k than to any third part"""
    hs = []; ax = [n, u, w]
    for d in range(3):
        hs.append([*ax[d], -(float(ax[d] @ c) + hi[d])]); hs.append([*(-ax[d]), (float(ax[d] @ c) + lo[d])])
    for j in range(len(S)):
        if j in (k, i): continue
        m_ = S[j] - S[k]; ln = np.linalg.norm(m_); m_ /= ln
        if ln/2 - abs(float(m_ @ (c - S[k]))) > 60 and float(m_ @ (c - S[k])) < ln/2 - 60: continue          # far away plane
        hs.append([*m_, -float(m_ @ (S[j] + S[k])/2)])
    hs = np.array(hs); ctr = c + n*(lo[0] + hi[0])/2 + u*(lo[1] + hi[1])/2 + w*(lo[2] + hi[2])/2
    for pt in (ctr, c + n*np.sign(lo[0] + hi[0])*1.5 + w*np.sign(lo[2] + hi[2])*1.5):
        if (hs[:, :3] @ pt + hs[:, 3] < -1e-3).all():
            try: add_hull(bm, HalfspaceIntersection(hs, pt).intersections); return True
            except Exception: pass
    return False
def gain_loss(i):
    add = bmesh.new(); sub = bmesh.new(); gain = {}; na = ns = ng = 0
    for c in CR:
        if i not in (c['a'], c['b']): continue
        o, n, u, w = frame(c); first = i == c['a']
        if conn == 'pins':
            L, pu, pw = PRM['pin']
            if first: na += add_box_in_cell(add, o, n, u, w, (-2.0, -pu/2, -pw/2), (L, pu/2, pw/2), c['j'], c['i'])
            else: add_box(sub, o, n, u, w, (-0.5, -pu/2 - CL, -pw/2 - CL), (L + 0.8, pu/2 + CL, pw/2 + CL)); ns += 1
        elif conn == 'keys':
            L, We, Ww, hk, side = PRM['key']; Rw = PRM['col'][2] if c['inradius'] < PRM['col_if'] else c['inradius']
            z = sorted([side*(Rw + 4.0), side*(Rw - hk - 0.4)]); add_prism(sub, o, n, u, w, bowtie(L, We, Ww, CL), z[0], z[1]); ns += 1
        elif conn == 'lap':
            L, B = PRM['lap']
            if c.get('lap') is None: continue
            o, w = np.array(c['lap'][0]), np.array(c['lap'][1]); u = np.cross(w, n)
            k_, i_ = (c['j'], c['i']) if first else (c['i'], c['j']); gk = gain.setdefault(0, bmesh.new())       # the cells the joint was cut between
            if first: ng += add_box_in_cell(gk, o, n, u, w, (-0.5, -B, CL), (L, B, B), k_, i_); add_box(sub, o, n, u, w, (-L - CL, -B - CL, -B), (0.5, B + CL, 0.0)); ns += 1
            else: ng += add_box_in_cell(gk, o, n, u, w, (-L, -B, -B), (0.5, B, -CL), k_, i_); add_box(sub, o, n, u, w, (-0.5, -B - CL, 0.0), (L + CL, B + CL, B)); ns += 1
    return (add, na), (sub, ns), (gain, ng)
# candidate print orientations
def fib(k):
    a = np.arange(k) + 0.5; ph = np.arccos(1 - 2*a/k); th = np.pi*(1 + 5**0.5)*a; return np.c_[np.cos(th)*np.sin(ph), np.sin(th)*np.sin(ph), np.cos(ph)]
UPS = fib(400)
def orient(o, pins):
    me = o.data; V = np.array([v.co[:] for v in me.vertices]); me.calc_loop_triangles(); F = np.array([t.vertices[:] for t in me.loop_triangles]); T = V[F]
    N = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); A = np.linalg.norm(N, axis=1)/2; N /= np.maximum(2*A[:, None], 1e-12); Cn = T.mean(1); best = None
    for up in UPS:
        h = V @ up; H = h.max() - h.min()
        if H > bed[2]: continue
        a = np.cross(up, [0, 0, 1] if abs(up[2]) < 0.9 else [1, 0, 0]); a /= np.linalg.norm(a); b = np.cross(up, a); X0, Y0 = V @ a, V @ b; fit = None
        for s in np.linspace(0, np.pi, 24, endpoint=False):
            X = X0*np.cos(s) + Y0*np.sin(s); Y = -X0*np.sin(s) + Y0*np.cos(s)
            if np.ptp(X) <= bed[0] and np.ptp(Y) <= bed[1]: fit = s; break
        if fit is None: continue
        dn = -(N @ up); hc = Cn @ up - h.min(); contact = A[(dn > 0.985) & (hc < 0.6)].sum(); over = A[(dn > 0.77) & (hc >= 0.6)].sum()   # steeper than 50 deg from vertical
        pen = 60*np.mean([abs(np.dot(p, up)) for p in pins]) if pins else 0.0                                 # pins standing upright shear along the layers
        sc = H + 200.0*over/A.sum() - 0.02*contact + pen
        if best is None or sc < best[0]: best = (sc, up, a, b, fit, H, contact, over)
    if best is None: return None
    sc, up, a, b, s, H, contact, over = best; ax = a*np.cos(s) + b*np.sin(s); ay = -a*np.sin(s) + b*np.cos(s)
    R = np.array([ax, ay, up]); W = V @ R.T; off = np.array([(W[:, 0].max() + W[:, 0].min())/2 - bed[0]/2 - 5, (W[:, 1].max() + W[:, 1].min())/2 - bed[1]/2 - 5, W[:, 2].min()]); W -= off
    me.vertices.foreach_set('co', W.ravel()); me.update()
    return dict(R=R.tolist(), off=off.tolist(), up=up.round(4).tolist(), height=round(float(H), 1), contact_mm2=round(float(contact)), overhang_mm2=round(float(over)), size=[round(float(np.ptp(W[:, k])), 1) for k in range(3)])
rows = []; ASM = {}
PARTS = [cut_part(i) for i in range(len(S))]; print('cut', len(PARTS), 'cells', round(time.time() - t0), 's', flush=True)
moved = 0; dropped = 0.0
for i in range(len(S)):
    for fr, vol in split_loose(PARTS[i]):
        if vol < 300: dropped += vol; bpy.data.objects.remove(fr); continue
        bv = BVHTree.FromObject(fr, bpy.context.evaluated_depsgraph_get()); touch = [c for c in CR if i in (c['a'], c['b']) and bv.find_nearest(Vector(c['c']))[3] < 2.0]
        score = {}
        for c in touch: k = c['b'] if c['a'] == i else c['a']; score[k] = score.get(k, 0) + c['area']
        if not score: dropped += vol; bpy.data.objects.remove(fr); continue
        tgt = max(score, key=score.get)
        for c in touch:
            k = c['b'] if c['a'] == i else c['a']
            if k == tgt: c['a'] = c['b'] = -1                      # this joint is now inside one part
            elif c['a'] == i: c['a'] = tgt
            else: c['b'] = tgt
        V_ = np.array([v.co[:] for v in fr.data.vertices]); c_ = V_.mean(0); V_ = c_ + (V_ - c_)*(1 + 0.12/max(np.ptp(V_, axis=0).max(), 1.0)); fr.data.vertices.foreach_set('co', V_.ravel()); fr.data.update()   # grow by ~0.06 mm so it fuses
        boolean(PARTS[tgt], fr, 'UNION'); moved += 1
CR = [c for c in CR if c['a'] >= 0]; print('loose pieces moved to a neighbour', moved, 'slivers dropped cm3', round(dropped/1000, 2), 'joints', len(CR), flush=True)
RAW = {i: PARTS[i].data.copy() for i in range(len(S))}
if conn == 'lap':                                        # one consistent step per group of close joints; joints at three-part corners stay plain butt joints
    R2 = 2*PRM['lap'][1] + 6.0; acc = []
    for c in sorted(CR, key=lambda c: -c['area']):
        o, n, u, w = frame(c); c['lap'] = None
        if c['triple']: continue
        near = [d for d in acc if np.linalg.norm(np.array(d['lap'][0]) - o) < R2]
        if any({d['a'], d['b']} != {c['a'], c['b']} for d in near): continue
        if near:
            o0, w0 = np.array(near[0]['lap'][0]), np.array(near[0]['lap'][1]); w = w0 - n*float(w0 @ n); w /= np.linalg.norm(w); o = o - w*float((o - o0) @ w)
        c['lap'] = (o.tolist(), w.tolist()); acc.append(c)
    print('lap joints', len(acc), 'plain butt joints', len(CR) - len(acc), flush=True)
for i in range(len(S)):
    p = PARTS[i]; (add, na), (sub, ns), (gain, ng) = gain_loss(i)
    for k_, gk in gain.items():                         # tongues: only material that belonged to that neighbour
        if not len(gk.verts): gk.free(); continue
        src = base.copy(); src.data = base.data.copy(); bpy.context.scene.collection.objects.link(src); boolean(src, new_obj('g', gk), 'INTERSECT')
        if len(src.data.polygons): boolean(p, src, 'UNION')
        else: bpy.data.objects.remove(src)
    if na:                                               # pins: clipped to the solid, so none sticks out into the air
        src = base.copy(); src.data = base.data.copy(); bpy.context.scene.collection.objects.link(src); boolean(src, new_obj('a', add), 'INTERSECT'); boolean(p, src, 'UNION')
    else: add.free()
    if ns: boolean(p, new_obj('s', sub), 'DIFFERENCE')
    else: sub.free()
    # weld, then look for loose bits
    LIM = 3000 if conn == 'lap' else 300      # a detached tongue remnant is removed; that joint then has a shorter overlap
    fr = split_loose(p); big = [round(v/1000, 2) for o_, v in fr if v >= LIM]; small = sum(v for o_, v in fr if v < LIM)
    for o_, v in fr:
        if v >= LIM: boolean(p, o_, 'UNION')          # keep real pieces in the file, they are reported
        else: bpy.data.objects.remove(o_)
    comps = [0]*(1 + len(big)); nm, vol = stats(p)
    pins = [c['n'] for c in CR if conn == 'pins' and i in (c['a'], c['b'])]
    ASM[i] = p.data.copy()
    info = orient(p, pins)
    if info is None: print('   DOES NOT FIT THE BED:', i + 1, flush=True); info = dict(R=np.eye(3).tolist(), off=[0, 0, 0], up=[0, 0, 1], height=0, contact_mm2=0, overhang_mm2=0, size=[0, 0, 0], fits=False)
    bpy.ops.object.select_all(action='DESELECT'); p.select_set(True)
    bpy.ops.wm.stl_export(filepath=DST + f'{name}_{i+1:02d}.stl', export_selected_objects=True)
    rows.append(dict(part=f'{name}_{i+1:02d}', seed=S[i].round(1).tolist(), volume_cm3=round(vol/1000, 1), pieces=len(comps), loose_cm3=big, slivers_removed_mm3=round(small), nonmanifold=nm,
                     joints=sum(1 for c in CR if i in (c['a'], c['b'])), **info))
    print(rows[-1]['part'], 'vol', rows[-1]['volume_cm3'], 'loose', big, 'slivers', round(small), 'nm', nm, 'joints', rows[-1]['joints'], 'size', info['size'], 'contact', info['contact_mm2'], round(time.time() - t0), 's', flush=True)
    bpy.data.objects.remove(p)
if conn == 'keys':
    L, We, Ww, hk, side = PRM['key']; bm = bmesh.new(); add_prism(bm, np.zeros(3), np.array([1., 0, 0]), np.array([0, 1., 0]), np.array([0, 0, 1.]), bowtie(L, We, Ww, -0.05), 0.0, hk)
    k = new_obj('key', bm); bpy.ops.object.select_all(action='DESELECT'); k.select_set(True); bpy.ops.wm.stl_export(filepath=DST + f'{name}_key_x{len(CR)}.stl', export_selected_objects=True)
# assembly check on the clean in-memory parts: points just inside one part must not lie inside its neighbour
def inside_depth(bv, pts):
    out = np.zeros(len(pts))
    for k, p_ in enumerate(pts):
        loc, nr, ix, d = bv.find_nearest(Vector(p_))
        if loc is None or d < 0.05: continue
        par = 0
        for dv in (Vector((0.31, 0.22, 0.925)).normalized(), Vector((-0.61, 0.52, -0.6)).normalized()):
            o_ = Vector(p_); cnt = 0
            while True:
                h = bv.ray_cast(o_, dv, 3000.0)
                if h[0] is None: break
                cnt += 1; o_ = h[0] + dv*1e-3
            par += cnt % 2
        if par == 2: out[k] = d
    return out
OBJ = {}; BV = {}; dg = None
for i_, me_ in ASM.items(): OBJ[i_] = bpy.data.objects.new(f'asm{i_}', me_); bpy.context.scene.collection.objects.link(OBJ[i_])
dg = bpy.context.evaluated_depsgraph_get()
for i_ in OBJ: BV[i_] = BVHTree.FromObject(OBJ[i_], dg)
pairs = sorted({(min(c['a'], c['b']), max(c['a'], c['b'])) for c in CR}); ov = []
for a_, b_ in pairs:
    JC = np.array([c['c'] for c in CR if {c['a'], c['b']} == {a_, b_}]); worst = 0.0; npts = 0
    for x_, y_ in ((a_, b_), (b_, a_)):
        me_ = ASM[x_]; V_ = np.array([v.co[:] for v in me_.vertices]); N_ = np.array([v.normal[:] for v in me_.vertices])
        near = (np.linalg.norm(V_[:, None, :] - JC[None, :, :], axis=2).min(1) < 24.0); pts = (V_ - 0.12*N_)[near]
        if len(pts) > 1500: pts = pts[np.random.default_rng(0).choice(len(pts), 1500, replace=False)]
        d_ = inside_depth(BV[y_], pts); worst = max(worst, float(d_.max()) if len(d_) else 0.0); npts += int((d_ > 0).sum())
    ov.append((a_ + 1, b_ + 1, round(worst, 2), npts))
bad = [o for o in ov if o[2] > 0.15]
check = dict(seams=len(pairs), seams_interfering=len(bad), worst_penetration_mm=max([o[2] for o in ov] + [0]), detail=bad[:30])
print('assembly check', check, flush=True)
json.dump(dict(name=name, tag=tag, conn=conn, bed=bed, parts=rows, joints=len(CR), crossings=CR, check=check), open(DST + 'parts.json', 'w'), indent=1)
print('total volume cm3', round(sum(r['volume_cm3'] for r in rows), 1), 'parts', len(rows), 'with loose pieces', sum(r['pieces'] > 1 for r in rows), 'non-manifold parts', sum(r['nonmanifold'] > 0 for r in rows))
