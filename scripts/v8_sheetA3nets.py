import json, math, numpy as np
from shapely.geometry import Polygon
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
OUT = '/home/claude/v8/sheetA3/'
d = json.load(open(OUT + 'A3_flat.json')); L = np.array(d['outline']); L = L - Polygon(L).centroid.coords[0]*np.array([0, 1])
o = L*[1, -1]                      # page coordinates, y down; the shell top is at the top of the page
P = Polygon(o); size = (o.max(0) - o.min(0)).round()
# dart mouths: the 6 outline points nearest the centre are the dart tips
r = np.linalg.norm(o, axis=1); n = len(o)
tips = sorted({i for i in range(n) if r[i] == min(r[(i + k) % n] for k in range(-25, 26))}, key=lambda i: np.arctan2(o[i,1], o[i,0]))
info = dict(size_mm=size.tolist(), cut_length_m=round(P.length/1000, 2), area_m2=round(P.area/1e6, 3), darts=len(tips), stretch=d['stretch'])
print(info); json.dump(info, open(OUT + 'A3_pattern_info.json', 'w'), indent=1)
def draw(ax, fs=1.0):
    ax.plot(*np.vstack([o, o[:1]]).T, color='black', lw=1.0)
    for t in tips: ax.plot(*o[t], marker='o', ms=3*fs, color='#2f6f73')
    ax.plot([0, 0], [o[:,1].min() - 15, o[:,1].min() - 45], color='#2f6f73', lw=1.2); ax.text(0, o[:,1].min() - 50, 'TOP of the shell', ha='center', va='bottom', fontsize=10*fs, color='#2f6f73')
    ax.plot([-10, 10], [0, 0], color='#999', lw=0.6); ax.plot([0, 0], [-10, 10], color='#999', lw=0.6)
    ax.text(0, 40, 'Version A3, one piece, 30 mm\ncut the outline, then glue the 6 darts shut edge to edge\nseen from the singer side', ha='center', va='top', fontsize=9*fs)
fig, ax = plt.subplots(figsize=(9, 9.4)); draw(ax); ax.set_aspect('equal'); ax.invert_yaxis(); ax.axis('off')
ax.set_title(f'Version A3: flat sheet {int(size[0])} × {int(size[1])} mm', fontsize=13); fig.tight_layout(); fig.savefig(OUT + 'A3_pattern_preview.png', dpi=110)
mn = o.min(0) - [20, 80]; mx = o.max(0) + 20; W, H = mx - mn
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}mm" height="{H:.0f}mm" viewBox="{mn[0]:.1f} {mn[1]:.1f} {W:.1f} {H:.1f}">', f'<rect x="{mn[0]}" y="{mn[1]}" width="{W}" height="{H}" fill="white"/>',
       '<polygon points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in o) + '" fill="none" stroke="black" stroke-width="0.4"/>']
svg += [f'<circle cx="{o[t,0]:.1f}" cy="{o[t,1]:.1f}" r="2" fill="#2f6f73"/>' for t in tips]
svg.append(f'<line x1="0" y1="{o[:,1].min()-15:.1f}" x2="0" y2="{o[:,1].min()-45:.1f}" stroke="#2f6f73" stroke-width="0.6"/><text x="0" y="{o[:,1].min()-50:.1f}" font-size="14" font-family="Helvetica" text-anchor="middle" fill="#2f6f73">TOP of the shell</text>')
svg.append('<line x1="-10" y1="0" x2="10" y2="0" stroke="#999" stroke-width="0.3"/><line x1="0" y1="-10" x2="0" y2="10" stroke="#999" stroke-width="0.3"/>')
svg.append(f'<rect x="{mn[0]+5}" y="{mn[1]+5}" width="100" height="100" fill="none" stroke="black" stroke-width="0.3"/><text x="{mn[0]+8}" y="{mn[1]+60}" font-size="7" font-family="Helvetica">100 mm</text></svg>')
open(OUT + 'sheet_A3_30mm_pattern_1to1.svg', 'w').write('\n'.join(svg))
for nm, (pw, ph) in (('A0', (841, 1189)), ('A4', (210, 297))):
    mg = 10; tw, th = pw - 2*mg, ph - 2*mg; nx = math.ceil(W/tw); ny = math.ceil(H/th)
    with PdfPages(OUT + f'sheet_A3_30mm_pattern_{nm}_tiles.pdf') as pdf:
        for j in range(ny):
            for i in range(nx):
                fig = plt.figure(figsize=(pw/25.4, ph/25.4)); ax = fig.add_axes([mg/pw, mg/ph, tw/pw, th/ph]); draw(ax, 1.0 if nm == 'A0' else 0.6)
                if i == 0 and j == 0: ax.add_patch(plt.Rectangle((mn[0]+5, mn[1]+5), 100, 100, fill=False, lw=0.5)); ax.text(mn[0]+8, mn[1]+60, '100 mm check square', fontsize=6)
                ax.set_xlim(mn[0] + i*tw, mn[0] + (i+1)*tw); ax.set_ylim(mn[1] + (j+1)*th, mn[1] + j*th); ax.set_aspect('equal'); ax.axis('off')
                fig.text(0.5, 1 - 0.4*mg/ph, f'A3 pattern, {nm} tile row {j+1}/{ny}, column {i+1}/{nx}. Print at 100 %.', ha='center', fontsize=6); pdf.savefig(fig); plt.close(fig)
    print(nm, nx*ny, 'pages')
