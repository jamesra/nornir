"""Re-run translate on the isolated copy of a section and report how the layout was assembled.

usage: retranslate.py <tag> [input mosaic, default Prune_Thr10.0.mosaic] [json settings overrides]
Writes Translated_<tag>.mosaic and Translated_<tag>_TranslateReport.json beside the section's mosaics.

Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy (<copy>/TEM/<section>/TEM). See ../SKILL.md."""
import json
import os
import sys

import nornir_imageregistration
import nornir_imageregistration.mosaic_tileset
from nornir_imageregistration.settings import TranslateSettings, LoadMosaicOffsets

SECTION = os.environ["RESCUE_SECTION_DIR"]
DOWNSAMPLE = 4
def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else "retranslate"
    input_mosaic = os.path.join(SECTION, sys.argv[2] if len(sys.argv) > 2 else "Prune_Thr10.0.mosaic")
    out_mosaic = os.path.join(SECTION, f"Translated_{tag}.mosaic")
    out_report = os.path.join(SECTION, f"Translated_{tag}_TranslateReport.json")

    settings_path = os.path.join(SECTION, "Translated_Prune_Settings.json")  # only some sections have one (1240 does; 11, 22, 75 do not)
    if os.path.exists(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            kw = json.load(f)
    else:  # the values 1240 used: min_overlap 0.02, 500 relax iterations, tension cutoff 0.5
        kw = {"min_overlap": 0.02, "max_relax_iterations": 500, "max_relax_tension_cutoff": 0.5}
    kw.pop("known_offsets", None)
    overrides = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    kw.update(overrides)
    settings = TranslateSettings(**kw)
    offsets_path = os.path.join(SECTION, "Translated_Prune_ManualOffsets.csv")
    settings.known_offsets = LoadMosaicOffsets(offsets_path) if os.path.exists(offsets_path) else {}
    print("settings", kw, "known_offsets", len(settings.known_offsets))

    image_dir = os.path.join(SECTION, "Leveled", "TilePyramid", "%03d" % DOWNSAMPLE)
    mfile = nornir_imageregistration.MosaicFile.Load(input_mosaic)
    invalid = mfile.RemoveInvalidMosaicImages(image_dir)
    print("invalid tiles removed:", invalid)
    tmp = os.path.join(SECTION, "Temp_" + os.path.basename(input_mosaic))
    mfile.Save(tmp)
    try:
        mosaic = nornir_imageregistration.Mosaic.LoadFromMosaicFile(tmp)
    finally:
        os.remove(tmp)
    tileset = nornir_imageregistration.mosaic_tileset.CreateFromMosaic(
        mosaic, image_folder=image_dir, image_to_source_space_scale=DOWNSAMPLE)
    report = nornir_imageregistration.TranslateReport()
    result = tileset.ArrangeTilesWithTranslate(settings, report=report)
    result.SaveMosaic(out_mosaic)
    report.save(out_report)
    print("saved", out_mosaic)
    print("tiles", report.tile_count, "passes", report.passes, "groups", [len(g) for g in report.groups])
    print("failed pairs", len(report.failed_pairs), "median ncc", report.median_ncc)
    print("matched groups", [len(g) for g in report.matched_groups])
    print("needs_review", report.needs_review)
    for r in report.review_reasons:
        print(" -", r)


if __name__ == "__main__":
    main()
