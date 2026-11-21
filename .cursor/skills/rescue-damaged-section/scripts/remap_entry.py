"""Add or refresh one section in a batch annotation-remap folder (for VikingAU remap-to-tiles / remap-from-tiles).

usage: remap_entry.py <remap folder> <production volume dir> <installed volume dir> <section> "<note>"
  e.g. remap_entry.py /storage4/_nornir_work/RC2/annotation_transfer/RC2-remap-2026-11-19 /storage4/RC2 /storage4/RC2-mirror 147 "..."
Writes <folder>/<section>/Grid_old.mosaic (production Grid, copied once), Grid_new.mosaic (the Grid as installed,
always refreshed), MANIFEST.txt (CRLF, Windows paths, sha256 of both), and adds the section to the $Sections default
of <folder>/Run-DryRuns.ps1 if that script exists. Run after every install, so the dry runs use the real file."""
import hashlib
import os
import re
import shutil
import sys

GRID = "Grid_Cel128_Mes8_Mes8_Thr0.25_it10_sp4.mosaic"


def sha(path: str) -> str:
    """sha256 of a file."""
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def win(path: str) -> str:
    """Dev-container path to the workstation's Y: path."""
    return "Y:\\Volumes" + path.replace("/storage4", "", 1).replace("/", "\\")


def main() -> None:
    """Copy the mosaics, write the manifest, update the dry-run script."""
    folder, prod, inst, sec, note = sys.argv[1:6]
    n4 = "%04d" % int(sec)
    d = os.path.join(folder, str(int(sec)))
    os.makedirs(d, exist_ok=True)
    old, new = os.path.join(prod, "TEM", n4, "TEM", GRID), os.path.join(inst, "TEM", n4, "TEM", GRID)
    if not os.path.exists(os.path.join(d, "Grid_old.mosaic")):
        shutil.copy2(old, os.path.join(d, "Grid_old.mosaic"))
    shutil.copy2(new, os.path.join(d, "Grid_new.mosaic"))
    text = (f"Section {int(sec)} annotation remap. Copies; production unchanged.\n"
            f"Grid_old.mosaic = {win(old)} (production, before install)\n"
            f"Grid_new.mosaic = {win(new)} as installed (the real file, not a preview)\n  {note}\n\n"
            f"{sha(os.path.join(d, 'Grid_old.mosaic'))}  Grid_old.mosaic\n{sha(os.path.join(d, 'Grid_new.mosaic'))}  Grid_new.mosaic\n")
    open(os.path.join(d, "MANIFEST.txt"), "w", newline="\r\n").write(text)
    ps1 = os.path.join(folder, "Run-DryRuns.ps1")
    if os.path.exists(ps1):
        s = open(ps1, newline="").read()
        m = re.search(r"\$Sections = @\(([^)]*)\)", s)
        items = [x.strip().strip("'") for x in m.group(1).split(",")]
        if str(int(sec)) not in items:
            items.append(str(int(sec)))
            open(ps1, "w", newline="").write(s[:m.start(1)] + ", ".join(f"'{x}'" for x in items) + s[m.end(1):])
    print(d, sha(os.path.join(d, "Grid_new.mosaic"))[:16])


if __name__ == "__main__":
    main()
