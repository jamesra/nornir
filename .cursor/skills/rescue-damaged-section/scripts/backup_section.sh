#!/bin/bash
# Back up one section's channel before an install (dev container paths).
# usage: backup_section.sh <volume dir> <NNNN> [backup root]
#   e.g. backup_section.sh /storage4/RC2-mirror 0147
#   -> <backup root>/<UTC date>-section<NNNN>/TEM/<NNNN>/TEM  (default root /storage4/_nornir_work/backups/<volume name>)
# Copies the channel's top-level files, and for Raw8/Leveled/Mask/Blob their top-level files and Images/
# (not TilePyramid or Tileset), then compares every file's size with the source. Refuses to overwrite a backup.
set -e
V=$1; N=$2; ROOT=${3:-/storage4/_nornir_work/backups/$(basename "$V")}
SRC=$V/TEM/$N/TEM
B=$ROOT/$(date -u +%F)-section$N/TEM/$N/TEM
[ -d "$SRC" ] || { echo "no channel folder $SRC"; exit 1; }
[ -e "$B" ] && { echo "backup exists: $B"; exit 1; }
mkdir -p "$B"
find "$SRC" -maxdepth 1 -type f -exec cp -p {} "$B/" \;
for f in Raw8 Leveled Mask Blob; do
  [ -d "$SRC/$f" ] || continue
  mkdir -p "$B/$f"; find "$SRC/$f" -maxdepth 1 -type f -exec cp -p {} "$B/$f/" \;
  [ -d "$SRC/$f/Images" ] && cp -rp "$SRC/$f/Images" "$B/$f/"
done
bad=0
while IFS= read -r -d '' f; do r=${f#$B/}; [ "$(stat -c %s "$f")" = "$(stat -c %s "$SRC/$r")" ] || { echo "size mismatch $r"; bad=1; }; done < <(find "$B" -type f -print0)
echo "$B files=$(find "$B" -type f | wc -l) mismatches=$bad"
exit $bad
