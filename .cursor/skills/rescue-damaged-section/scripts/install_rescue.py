"""Install a hand-rescued Translated and Grid mosaic as a section's locked production transforms.

Run after the Prune pipeline has produced the new Prune transform. Before anything is written, the new mosaics
are shifted rigidly so the section's centre tile (tile 0 when both mosaics have it) sits at the same
coordinates as in the mosaics being replaced. Annotations are stored in mosaic coordinates, so this keeps
them on the right tissue. The mosaic origin may therefore not be (0, 0).

Then it replaces the files behind the Translated_Prune and Grid transform nodes, re-points each node at its
input transform's current checksum, recomputes the node checksums, and locks both, the way TranslateTransform
and GridTransform leave them.

usage: install_rescue.py <volume root> <section> <translated.mosaic> <grid.mosaic>
           (--annotation-rescue-report PATH | --no-annotations)
           [--anchor-tile N] [--allow-negative-origin] [--no-anchor] [--dry-run]
           [--old-translated PATH] [--old-grid PATH]

POLICY (set by the user 2026-11-04): a repaired mosaic is not installed until the section's annotations have been
rescued, i.e. mapped from the old mosaic coordinates to the new (scripts/remap_mosaic_points.py), or the user has
confirmed the section has none. A real install therefore needs --annotation-rescue-report or --no-annotations.

--old-translated/--old-grid name the mosaics being replaced when they are no longer the files behind the nodes
(for example the backups, to see what the shift would have been). --no-anchor installs at the new coordinates.
Assemble keeps only the part of a mosaic at non-negative coordinates, so if the shift would put tiles below
(-64, -64) the script refuses unless --allow-negative-origin is given: the better fix is then to translate the
annotations from the old mosaic coordinates to the new.
"""
import argparse
import os
import shutil
import sys
import tempfile

import numpy as np

import nornir_imageregistration
import nornir_imageregistration.mosaic_tileset
from nornir_buildmanager.volumemanager import VolumeManager

NEGATIVE_ORIGIN_LIMIT_PX = 64.0  # the same limit Assemble warns at


def tile_centres(mosaic_path: str, image_dir: str) -> tuple[dict[int, np.ndarray], tuple[float, float]]:
    """Full-resolution (Y, X) centre of every tile's target-space bounding box, and the mosaic's (MinY, MinX)."""
    tileset = nornir_imageregistration.mosaic_tileset.CreateFromMosaic(
        nornir_imageregistration.Mosaic.LoadFromMosaicFile(mosaic_path), image_folder=image_dir,
        image_to_source_space_scale=4)
    centres = {}
    for tile_id, tile in tileset.items():
        box = tile.TargetSpaceBoundingBox
        centres[int(tile_id)] = np.array([(box.MinY + box.MaxY) / 2.0, (box.MinX + box.MaxX) / 2.0])
    bbox = tileset.TargetBoundingBox
    return centres, (float(bbox.MinY), float(bbox.MinX))


def shifted_copy(src: str, delta: np.ndarray, dst: str) -> None:
    """Write src with every tile's target space moved by delta (Y, X)."""
    mosaic = nornir_imageregistration.Mosaic.LoadFromMosaicFile(src)
    for transform in mosaic.ImageToTransform.values():
        transform.TranslateFixed(delta)
    mosaic.SaveToMosaicFile(dst)


def choose_anchor(requested: int | None, tables: list[dict[int, np.ndarray]]) -> int:
    """Tile 0 (or the requested tile) when every mosaic has it, else the common tile nearest the old centre."""
    common = set.intersection(*(set(t) for t in tables))
    if not common:
        raise SystemExit("The old and new mosaics share no tile to anchor on")
    wanted = 0 if requested is None else requested
    if wanted in common:
        return wanted
    if requested is not None:
        raise SystemExit(f"Tile {requested} is not in every mosaic being compared")
    old_centre = np.mean([c for c in tables[0].values()], axis=0)
    nearest = min(common, key=lambda t: float(np.linalg.norm(tables[0][t] - old_centre)))
    print(f"tile 0 is missing from a mosaic (pruned, or not placed); anchoring on tile {nearest}, nearest the old centre")
    return nearest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("section")
    parser.add_argument("translated")
    parser.add_argument("grid")
    parser.add_argument("--anchor-tile", type=int, default=None)
    parser.add_argument("--allow-negative-origin", action="store_true")
    parser.add_argument("--no-anchor", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--old-translated")
    parser.add_argument("--old-grid")
    parser.add_argument("--annotation-rescue-report", help="path to the report written by remap_mosaic_points.py for this section's annotations")
    parser.add_argument("--no-annotations", action="store_true", help="the user confirmed this section has no annotations to rescue")
    args = parser.parse_args()
    if not args.dry_run and not args.annotation_rescue_report and not args.no_annotations:
        raise SystemExit("Policy: annotations must be rescued before a repaired mosaic is installed. Pass "
                         "--annotation-rescue-report <report> once remap_mosaic_points.py has been run for this section, "
                         "or --no-annotations if the user has confirmed there are none.")
    if args.annotation_rescue_report and not os.path.exists(args.annotation_rescue_report):
        raise SystemExit(f"Annotation rescue report not found: {args.annotation_rescue_report}")

    vol = VolumeManager.Load(args.root)
    channel = vol.find(f"Block/Section[@Number='{args.section}']").find("Channel[@Name='TEM']")
    nodes = {name: channel.GetChildByAttrib("Transform", "Name", name) for name in ("Stage", "Prune", "Translated_Prune", "Grid")}
    for name, node in nodes.items():
        print(f"{name:18s} {node.Path:55s} locked={node.Locked} checksum={node.attrib.get('Checksum')}")
    prune, translated, grid = nodes["Prune"], nodes["Translated_Prune"], nodes["Grid"]
    old_translated = args.old_translated or translated.FullPath
    old_grid = args.old_grid or grid.FullPath
    image_dir = os.path.join(channel.FullPath, "Leveled", "TilePyramid", "004")

    # The new mosaics may only use tiles the Prune mosaic kept (a manual rule may have removed a few more).
    prune_tiles = set(nornir_imageregistration.MosaicFile.Load(prune.FullPath).ImageToTransformString)
    for label, src in (("translated", args.translated), ("grid", args.grid)):
        tiles = set(nornir_imageregistration.MosaicFile.Load(src).ImageToTransformString)
        extra = tiles - prune_tiles
        print(f"{label}: {len(tiles)} tiles, {len(extra)} not in the Prune mosaic, {len(prune_tiles - tiles)} Prune tiles left out")
        if extra:
            raise SystemExit(f"{label} uses tiles missing from the Prune mosaic: {sorted(extra)[:10]}")

    install_translated, install_grid = args.translated, args.grid
    temp_dir = tempfile.mkdtemp(prefix="rescue_anchor_")
    try:
        if not args.no_anchor:
            old_t, _ = tile_centres(old_translated, image_dir)
            old_g, _ = tile_centres(old_grid, image_dir)
            new_t, _ = tile_centres(args.translated, image_dir)
            new_g, _ = tile_centres(args.grid, image_dir)
            anchor = choose_anchor(args.anchor_tile, [old_t, old_g, new_t, new_g])
            delta_t = old_t[anchor] - new_t[anchor]
            delta_g = old_g[anchor] - new_g[anchor]
            print(f"anchor tile {anchor}: old Translated centre (Y, X) {old_t[anchor].round(1)}, new {new_t[anchor].round(1)} -> shift {delta_t.round(1)}")
            print(f"                 old Grid centre {old_g[anchor].round(1)}, new {new_g[anchor].round(1)} -> shift {delta_g.round(1)}")
            install_translated = os.path.join(temp_dir, os.path.basename(args.translated))
            install_grid = os.path.join(temp_dir, os.path.basename(args.grid))
            shifted_copy(args.translated, delta_t, install_translated)
            shifted_copy(args.grid, delta_g, install_grid)
            lowest = []
            for label, path in (("translated", install_translated), ("grid", install_grid)):
                centres, (min_y, min_x) = tile_centres(path, image_dir)
                print(f"{label} after the shift: origin (MinY, MinX) = ({min_y:.0f}, {min_x:.0f}); anchor centre {centres[anchor].round(1)}")
                lowest.append(min(min_y, min_x))
            if min(lowest) < -NEGATIVE_ORIGIN_LIMIT_PX and not args.allow_negative_origin:
                raise SystemExit(
                    "Refusing to install: the anchored mosaic extends below zero, and Assemble would keep only the part at "
                    "non-negative coordinates. Either pass --allow-negative-origin (accepting cropped assembled images), "
                    "install with --no-anchor, or translate the annotations from the old mosaic coordinates to the new.")
        if args.dry_run:
            return

        translated.Locked = False
        grid.Locked = False
        shutil.copy2(install_translated, translated.FullPath)
        shutil.copy2(install_grid, grid.FullPath)

        translated.SetTransform(prune)
        translated.ResetChecksum()
        # Attribute assignment on the node (not .attrib[...]) lets the volume manager mark it changed.
        translated.ManualOffsetsChecksum = nornir_imageregistration.settings.MosaicOffsetsChecksum([])
        translated.ManualOffsetsCount = "0"
        grid.SetTransform(translated)
        grid.ResetChecksum()
        grid.cmd = ("python:nornir_imageregistration.RefineGridMosaic(per half; cell_size=(128, 128), mesh_shape=(8, 8), "
                    "iterations=10, displacement_threshold=0.25, imageScale=0.25) on Leveled level 4; "
                    "hand-rescued, see .cursor/skills/rescue-damaged-section")
        translated.Locked = True
        grid.Locked = True
        channel.Save()
        print("installed; Translated_Prune checksum", translated.attrib["Checksum"], "Grid checksum", grid.attrib["Checksum"])
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
