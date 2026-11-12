# Assemble the release packages: one folder + zip per connection type, both bed sizes inside.
import json, os, shutil, glob, csv, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
def punch(im): return ImageEnhance.Color(im.convert('RGB').point(lambda v: int(255*(v/255)**1.6))).enhance(1.35)
B = '/home/claude/v8/split/build/'; PK = '/home/claude/v8/split/packages/'; F = '/usr/share/fonts/opentype/inter/Inter-'
CONN = dict(pins=('block-pins', 'Printed block pins'), keys=('butterfly-keys', 'Butterfly keys'), lap=('overlap', 'Overlapping joints'))
BEDS = dict(b256=('bed-256', '256 × 256 × 256 mm (parts kept within 246 mm)'), b350=('bed-350x320', '350 × 320 × 325 mm (parts kept within 340 × 310 × 315 mm)'))
OBJ = dict(shell=('back-shell', 'Back shell'), plate=('front-plate', 'Front plate'))
def annotate(src, dst, labels, title):
    im = punch(Image.open(src)); d = ImageDraw.Draw(im); W, H = im.size; f = ImageFont.truetype(F + 'SemiBold.otf', 30); ft = ImageFont.truetype(F + 'SemiBold.otf', 34)
    for lab, x, y in labels:
        px, py = x*W, (1 - y)*H; d.ellipse((px - 24, py - 24, px + 24, py + 24), fill=(255, 255, 255), outline=(30, 30, 30), width=2); d.text((px, py), lab, font=f, fill=(20, 20, 20), anchor='mm')
    d.text((24, 18), title, font=ft, fill=(20, 20, 20)); im.save(dst)
for conn, (slug, cname) in CONN.items():
    root = PK + f'MRS-01_{slug}/'; shutil.rmtree(root, ignore_errors=True); os.makedirs(root + 'docs'); facts = {}
    for tag, (bdir, bname) in BEDS.items():
        src = B + f'{conn}/{tag}/'; rowsall = []; facts[tag] = {}
        for name, (odir, oname) in OBJ.items():
            J = json.load(open(src + f'{name}/parts.json')); dst = root + f'{bdir}/{odir}/'; os.makedirs(dst)
            for f_ in sorted(glob.glob(src + f'{name}/{name}_[0-9][0-9].stl')): shutil.copy(f_, dst + 'MRS-01_' + os.path.basename(f_))
            for f_ in glob.glob(src + f'{name}/{name}_key_x*.stl'): os.makedirs(root + f'{bdir}/keys/', exist_ok=True); shutil.copy(f_, root + f'{bdir}/keys/MRS-01_' + os.path.basename(f_))
            nb = {}; outer = {}
            for c in J['crossings']:
                nb.setdefault(c['a'], set()).add(c['b']); nb.setdefault(c['b'], set()).add(c['a'])
            for k, r in enumerate(J['parts']):
                rowsall.append([oname, 'MRS-01_' + r['part'] + '.stl', *[round(x) for x in r['size']], r['volume_cm3'], r['joints'], ' '.join(f"{name}_{j+1:02d}" for j in sorted(nb.get(k, []))),
                                ' '.join(f"{name}_{j+1:02d}" for j in sorted(nb.get(k, [])) if j > k) if conn == 'lap' else ''])
            S = np.array([r['seed'] for r in J['parts']]); mount = int(np.argmin(np.linalg.norm(S - [0, 0, -360], axis=1))) + 1 if name == 'shell' else None
            facts[tag][name] = dict(parts=len(J['parts']), joints=J['joints'], vol=round(sum(r['volume_cm3'] for r in J['parts'])), hmax=round(max(r['size'][2] for r in J['parts'])), check=J['check'], mount=mount,
                                    maxvol=max(r['volume_cm3'] for r in J['parts']))
        with open(root + f'{bdir}/parts.csv', 'w', newline='') as fh:
            w = csv.writer(fh); w.writerow(['object', 'file', 'size_x_mm', 'size_y_mm', 'height_mm', 'solid_volume_cm3', 'joints', 'neighbours', 'lies_outside_of' if conn == 'lap' else '']); w.writerows(rowsall)
        L = json.load(open(B + f'pins/{tag}/_labels.json'))
        annotate(B + f'pins/{tag}/_r_shell_back.png', root + f'docs/{bdir}_back-shell_from-behind.png', L['shell_back'], f'Back shell, seen from behind, {bname.split(" (")[0]} bed')
        annotate(B + f'pins/{tag}/_r_shell_front.png', root + f'docs/{bdir}_back-shell_from-front.png', L['shell_front'], f'Back shell, seen from the front, {bname.split(" (")[0]} bed')
        annotate(B + f'pins/{tag}/_r_plate_front.png', root + f'docs/{bdir}_front-plate.png', L['plate_front'], f'Front plate, seen from the front, {bname.split(" (")[0]} bed')
        punch(Image.open(B + f'pins/{tag}/_r_exploded.png')).save(root + f'docs/{bdir}_exploded.png')
    punch(Image.open(B + f'{conn}/b350/_r_joint.png')).save(root + 'docs/joint.png')
    os.makedirs(root + 'common/inlay'); os.makedirs(root + 'common/stand-mount')
    for f_ in ('sheet_A3_30mm_pattern_1to1.svg', 'sheet_A3_30mm_pattern_A0_tiles.pdf', 'sheet_A3_30mm_pattern_A4_tiles.pdf', 'inlay_A3_overview_sheet_v2.png'): shutil.copy('/home/claude/v8/sheetA3/' + f_, root + 'common/inlay/')
    shutil.copy('/home/claude/v8/insert2/insert_from_below_overview.png', root + 'common/stand-mount/')
    os.makedirs(root + 'full-model')
    shutil.copy('/home/claude/v8/split/base_shell.stl', root + 'full-model/MRS-01_back-shell_one-piece.stl'); shutil.copy('/home/claude/v8/split/base_plate.stl', root + 'full-model/MRS-01_front-plate_one-piece.stl')
    shutil.copy('/home/claude/v8/sheetA3/sheet_A3_30mm.stl', root + 'full-model/MRS-01_inlay_formed.stl')
    json.dump(facts, open(root + 'docs/facts.json', 'w'), indent=1)
print('folders ready')

# ---------- README per package ----------
HOW = dict(
 pins="""Every joint has a rectangular pin on one part and a matching socket on the other. On the back shell the pin is 8 × 6 mm and 9 mm long; on the front plate it is 8 × 3.2 mm and 8 mm long. Sockets are 0.15 mm larger on every side.

1. Dry-fit two neighbours first. If a pin is tight, sand the pin, not the socket.
2. Put glue on the flat joint faces and into the sockets, push the parts together, and hold or tape them until the glue sets.
3. The pin always sits on the lower-numbered part of a seam.""",
 keys="""The parts meet with flat faces. Every joint has a bow-tie shaped pocket that runs across the seam, half in each part. A separate printed key is pressed into the pocket and locks the two parts together.

1. Print the keys from `keys/`. The file name gives the number you need, for example `MRS-01_shell_key_x63.stl` means 63 keys. Print a few spares. Print them flat, as they are.
2. Hold two neighbours together and press a key into each pocket across the seam. On the back shell the pockets open toward the inside of the bowl. On the front plate they open toward the foam side.
3. The keys hold without glue for a test fit. For the final assembly, glue the joint faces and the keys.
4. Keys are 0.2 mm smaller than the pockets. If they are loose on your printer, scale the key up by 1 to 2 % in the slicer.""",
 lap="""At every joint the two parts overlap by 10 mm (9 mm on the front plate): one part has a tongue on the outside, the other a tongue on the inside. The step is 0.15 mm clear.

1. At a seam, the lower-numbered part normally lies on the outside. `parts.csv` lists this in the column `lies_outside_of`.
2. Build from the inside out: place the higher-numbered part first, then put the lower-numbered part on from outside.
3. Glue the overlapping faces. They give the largest glue area of the three connection types, but they do not lock sideways, so tape or clamp each seam until the glue sets.
4. Where three parts meet at one strut, the joint is a plain flat face without a step. Glue it as a butt joint.""")
def readme(conn, slug, cname, facts, root):
    L = [f'# MRS-01 Modular Recording Shell, printable parts: {cname.lower()}', '',
         'This package holds the back shell and the front plate of the MRS-01, split into parts for FDM printing. It comes in two versions for two printer sizes. All parts are already turned into their print orientation.',
         '', '**Status: nothing in this package has been printed or assembled yet.** The geometry is checked by computer only. Print two neighbouring parts and test the joint before you print the whole set.', '',
         '## Folders', '', '```', f'MRS-01_{slug}/', '├── README.md', '├── bed-256/            parts for a 256 × 256 × 256 mm printer',
         '│   ├── back-shell/     MRS-01_shell_01.stl ...', '│   ├── front-plate/    MRS-01_plate_01.stl ...'] + (['│   ├── keys/           the butterfly keys'] if conn == 'keys' else []) + [
         '│   └── parts.csv       size, volume, joints and neighbours of every part', '├── bed-350x320/        the same for a 350 × 320 × 325 mm printer', '├── full-model/         the unsplit back shell, front plate and formed inlay, in mm, in their assembled position', '├── common/',
         '│   ├── inlay/          cutting pattern for the 30 mm foam inlay', '│   └── stand-mount/    how the 3/8" threaded insert goes in', '└── docs/               part maps, exploded view, joint close-up', '```', '',
         '## Which version', '', '| Printer bed | Back shell | Front plate | Joints | Tallest part |', '|---|---|---|---|---|']
    for tag, (bdir, bname) in BEDS.items():
        f = facts[tag]; L.append(f"| {bname} | {f['shell']['parts']} parts | {f['plate']['parts']} parts | {f['shell']['joints']} + {f['plate']['joints']} | {max(f['shell']['hmax'], f['plate']['hmax'])} mm |")
    L += ['', 'The part maps in `docs/` show where every numbered part sits.', '',
          '## Printing', '',
          '- **Orientation:** every STL is already rotated and sits on the bed at z = 0. The orientation was chosen by a script for low height, so most struts lie along the layers, and for little overhang. It was not tuned by hand.',
          '- **Supports:** needed on all parts, because the lattice is curved in every direction. Tree supports are a reasonable start.',
          '- **Bed contact:** the parts touch the bed only at a few points. Use a brim.',
          '- **Material and settings:** these are suggestions, not tested values. PETG or ASA rather than PLA, because the whole weight hangs on the stand mount and PLA creeps. 4 walls and 30 to 40 % infill. 0.2 mm layers.',
          '- **Solid volume:** the back shell is about ' + str(facts['b350']['shell']['vol']) + ' cm³ and the front plate about ' + str(facts['b350']['plate']['vol']) + ' cm³ of solid model volume. Real filament use depends on walls, infill and supports.', '',
          '## The connection', '', HOW[conn], '', '![joint](docs/joint.png)', '',
          '## Assembly order', '',
          f"1. Start with the part that holds the stand mount: `MRS-01_shell_{facts['b256']['shell']['mount']:02d}` on the 256 bed, `MRS-01_shell_{facts['b350']['shell']['mount']:02d}` on the 350 × 320 bed.",
          '2. Melt the threaded insert into that part before you assemble anything (see below).',
          '3. Add its neighbours, then theirs, working up both sides to the top. `parts.csv` lists the neighbours of every part.',
          '4. Close the shell at the top last. Dry-fit the last three parts together before gluing.',
          '5. Assemble the front plate the same way, starting at the bottom centre.',
          '6. Cut and form the foam inlay (`common/inlay/`) and press it into the shell, with its edge tucked under the lip.',
          '7. Set the front plate onto the foam. Its flange lies on the front face of the lip with a gap of about 0.5 mm. Glue it there with a gap-filling glue if you want it fixed for good.', '',
          '## Stand mount', '',
          '- **Part:** one ruthex threaded insert 3/8"-16, 12.7 mm long, 12.6 mm outer diameter.',
          '- **Hole:** 11.9 mm wide and 13.7 mm deep, open to the flat seat on the underside of the mount part. Check the hole size against the ruthex data sheet; 11.9 mm is taken from the product page.',
          '- **How:** heat the insert with a soldering iron and press it in from below until it is flush with the seat.',
          '- **Limit:** the insert is held only by its melted-in grip. Do not lift the shield by its edge while it is on the stand.', '',
          '## Other things you need', '', '- Glue that suits your filament, for example a two-part epoxy.', '- 30 mm soft acoustic foam or felt, about 1230 × 1150 mm, for the inlay.', '- A mic stand with a 3/8" thread.', '', '## Full model', '', 'The folder `full-model/` holds the unsplit back shell (with the stand mount), the unsplit front plate and the formed inlay. All three are in millimetres and in the same position, so they line up when you load them together. The shell is 800 mm wide.', '',
          '## Checks that were run', '',
          '- Every part is a closed solid and fits its bed in the given orientation.',
          '- Neighbouring parts were tested against each other in the assembled position.']
    for tag, (bdir, bname) in BEDS.items():
        for name in ('shell', 'plate'):
            ck = facts[tag][name]['check']; n_bad = ck['seams_interfering']
            L.append(f"  - {bdir}, {OBJ[name][1].lower()}: {ck['seams']} seams, " + ('no interference.' if n_bad == 0 else f"{n_bad} seam(s) touch too tightly, by up to {ck['worst_penetration_mm']} mm: " + ', '.join(f"{name}_{a:02d}/{name}_{b:02d}" for a, b, *_ in ck['detail']) + '. Sand these joints lightly.'))
    L += ['', '## Known limits', '',
          '- Nothing has been printed, so fit, strength and the clearances are unproven.',
          '- The front plate has no clips, pins or magnets to the shell. It can be glued to the lip, which then closes the foam in for good.',
          '- There is no opening for a mic rod.',
          '- Where a cut runs through a thin strut, the strut was thickened into a knuckle of about 20 mm so the joint has enough material. On the front plate these are flat pads about 9 mm thick.',
          '- Mirrored parts are not always turned the same way on the bed.', '']
    open(root + 'README.md', 'w').write('\n'.join(L))
for conn, (slug, cname) in CONN.items():
    root = PK + f'MRS-01_{slug}/'; facts = json.load(open(root + 'docs/facts.json')); readme(conn, slug, cname, facts, root); os.remove(root + 'docs/facts.json')
    shutil.make_archive(PK + f'MRS-01_{slug}', 'zip', PK, f'MRS-01_{slug}'); print(slug, round(os.path.getsize(PK + f'MRS-01_{slug}.zip')/1e6, 1), 'MB')
