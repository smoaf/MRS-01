# Scripts

These scripts build the MRS-01 geometry. They are published so the process can be followed and reused. They are not yet a tool you can run as is: they were written for one machine and contain absolute paths, and some of them need input files that are not in this repository (the original mockup and intermediate Blender files).

## Requirements

- Python 3 with numpy, scipy, scikit-image, shapely, trimesh, matplotlib and Pillow.
- Blender as a Python module (`bpy`), used for booleans, unwrapping and rendering.

## What each script does

| Script | Step |
|---|---|
| `v8_step1c.py`, `v8_step2i.py` | Symmetric base mesh and the outer shell lattice |
| `v8_inlay3.py`, `v8_sheet_common.py` | Inner face of the shell and shared helpers for the inlay |
| `v8_lipspace.py`, `v8_lipfit.py` | Free space behind the lip, and the flared inlay edge |
| `v8_sheetA3.py`, `v8_sheetA3nets.py` | Inlay A3: one sheet with 6 darts, flat pattern, SVG and PDF tiles |
| `v8_plate1.py`, `v8_plate3.py` | Front plate: rib pattern, then the solid with its flange on the lip |
| `v8_insert2.py` | Stand mount for the 3/8"-16 heat-set insert |
| `sp_prep.py` | Clean base meshes for splitting |
| `sp_partition.py` | Mirror-symmetric split into parts that fit a given bed |
| `sp_build.py` | Cut the parts, add the connectors, choose the print orientation, check the seams |
| `sp_runall.sh` | Build every connection type for every bed |
| `sp_viz.py`, `sp_package.py` | Renders, part maps, READMEs and packages |

Run the split for one bed, for example:

```
python3 sp_partition.py shell 340 310 315 b350 5
python sp_build.py -- shell b350 pins
```
