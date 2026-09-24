# Viking handoff: RC2 962 compressed under SliceToVolume1 (not Linear)

## Ask for the Viking agent

Repo: `D:\src\VikingLegacy-Maintenance` (open that workspace in Cursor).

**Symptom:** In Viking, with **SliceToVolume1** selected as the active StosGroup (not SliceToVolumeLinear1), section **962** looks strongly compressed relative to **961**. Pyre shows Grid16 `962-961_…stos` looking correct (magenta/green composite, regular mesh). Timestamps on the Viking package look fine.

**Nornir-side conclusion (already checked):** The zip is not stale; checksums for SliceToVolume1 match disk; Linear is a separate known-bad path. Something in **how Viking applies SliceToVolume1 GridTransform stos** (or tile→volume composition) likely differs from Pyre/Nornir assemble. Please dig the apply path in VikingLegacy and report where 962 could get an extra scale/squash that 961 does not.

---

## Volume / package paths (Windows ↔ Linux)

| Role | Path |
|------|------|
| VikingXML | `\\storage4\RC2\SliceToVolume.VikingXML` (or `D:`/mapped equivalent under `/storage4/RC2/…`) |
| Active group zip | `\\storage4\RC2\TEM\SliceToVolume1.zip` |
| On-disk stos | `\\storage4\RC2\TEM\SliceToVolume1\962-645_ctrl-TEM_Leveled_map-TEM_Leveled.stos` |
| Neighbor (OK) | `…\961-645_ctrl-TEM_Leveled_map-TEM_Leveled.stos` |
| Pyre-good pair (different product) | `\\storage4\RC2\TEM\Grid16\962-961_ctrl-TEM_Leveled_map-TEM_Leveled.stos` |
| Linear (do **not** confuse) | `TEM\SliceToVolumeLinear1.zip` — 962 Linear **is** crushed (`sx≈0.29`); user confirms UI is on **SliceToVolume1** |

VikingXML root: `Version="2" Name="RC2" path="http://rogue1.codepharm.net/RC2" DefaultSection="645"`.

Stos entries:

```xml
<StosGroup Name="SliceToVolume1" zip="TEM/SliceToVolume1.zip">
  <stos controlSection="645" mappedSection="961" path="961-645_ctrl-TEM_Leveled_map-TEM_Leveled.stos" pixelspacing="1" type="Grid"/>
  <stos controlSection="645" mappedSection="962" path="962-645_ctrl-TEM_Leveled_map-TEM_Leveled.stos" pixelspacing="1" type="Grid"/>
```

Per-section mosaics (both 961 and 962): `UseForVolume="true"` is on **`TEM/Grid_Cel128_….mosaic`** (mtime ~2015), **not** on `ChannelToVolume.mosaic` (2026-09-09). ChannelToVolume has `UseForVolume="false"`.

---

## Nornir verification already done (do not re-litigate as “stale zip”)

1. **Zip == disk** for both `961-645` and `962-645` members (bytes + `StosFile.LoadChecksum`).
2. Zip mtime **2026-09-10 22:07** > stos mtimes **06:21** → `_stos_group_zip_is_fresh` would treat as current.
3. Composition checksums:
   - Grid16 root `962-961` checksum `9da3b07d8be22d15d152ad5673e7546b`
   - SliceToVolume16 `962-645` `InputTransformChecksum` = that Grid16 checksum
   - SliceToVolume16 `ControlToVolumeTransformChecksum` = SliceToVolume16 `961-645`
   - SliceToVolume1 `962-645` checksum `7cb6708379e148fe79ff347b865354be` (scaled from STV16)
4. **Center local scale** (Nornir `Transform` of ±200 px at image center, ds1 size ≈ ds16×16):
   - STV1 **962:** `sy≈0.936`, `sx≈0.929` (geom≈0.933)
   - STV1 **961:** `sy≈0.976`, `sx≈0.916` (geom≈0.946)
   - Not a “962 crushed / 961 fine” split at center under Nornir math.
5. **Mapped control-point spill** (Grid16 root used as STV input): ~19% of SourcePoints outside 962 image; SourcePoint span ≈1.42× image. Pyre pairwise still looks good at tissue. Automatic Grid16 differs (`47dae369…`, Aug 20) and was **not** what STV used (root Aug 19).
6. Build log: `/storage4/RC2/log-20260910-181732.txt` (CreateVikingXML wrote SliceToVolume1.zip). Dashboard DB in the Nornir container had no retained runs.

---

## Hypotheses for Viking (investigate in priority order)

### H1 — GridTransform parsing / RBF vs grid-only
On-disk transform string begins with `GridTransform_double_2_2 vp …` (Nornir loads as `GridWithRBFFallback`).  
**Ask:** Does Viking apply only the grid CP lattice and ignore / mishandle fallback? Do out-of-bounds SourcePoints cause Viking’s warp to collapse scale for 962 more than 961?

### H2 — Tile mosaic × stos composition
Volume path uses **old Grid mosaic** (`UseForVolume=true`) then SliceToVolume stos to section **645**.  
**Ask:** Exact matrix order: `stos(mapped→645) ∘ mosaic(tiles→section)` vs inverse? Any place that assumes mosaic bounds == stos SourcePoint bounds? 962’s SourcePoints extend past the image; 961 less so — could bias a bounds-derived scale.

### H3 — `pixelspacing="1"` / coordinate units
Emitter sets `pixelspacing` from `StosGroup.Downsample` (=1 for SliceToVolume1).  
**Ask:** Does Viking ever multiply/divide tile or stos coords by pixelspacing or by section downsample again for only some sections?

### H4 — Client cache
**Ask:** Where does Viking cache zip members / parsed transforms? Force re-read of `962-645_…stos` from `SliceToVolume1.zip` and print checksum/CRC (`zip CRC 0x9c7fb2bd`, size 29843). Confirm UI “SliceToVolume1” binds that zip, not Linear.

### H5 — Control section 645 framing
Both map to **645**. If Viking sizes the volume from control geometry incorrectly per mapped section, 962’s wider extrapolated corner bbox (X span ~179k vs target ~116k) might get fitted/squashed into the 645 frame differently than 961.

---

## Concrete debug asks (Viking codebase)

Please locate and document:

1. Code that loads `StosGroup/@zip` and opens `stos/@path` members.
2. Code that builds the section→volume transform when a StosGroup is active.
3. How `GridTransform_double_2_2` is parsed (ITK-compatible? control/mapped point order YX vs XY?).
4. How `UseForVolume` mosaics combine with stos.
5. Any per-section scale derived from control-point bounding boxes (suspect for exploded SourcePoints).

**Repro measurement in Viking (or a small harness):**  
Map the four corners and center of section 962’s full-res image through the active volume transform; report output bbox size. Nornir STV1 962 center scale ≈0.93; if Viking reports ≪0.5 on an axis, the bug is in Viking’s apply path. Compare to 961 under the same group.

Optional Nornir cross-check (already available):  
`nornir_imageregistration.assemble.TransformStos` on the same `962-645` file — warped size should track control (645) footprint, not a crushed 962.

---

## What not to “fix” first

- Do not regenerate VikingXML solely for freshness — zip already matches SliceToVolume1 disk.
- Do not point at SliceToVolumeLinear1 unless the UI is wrong; Linear **does** crush 962, but user selected SliceToVolume1.
- Grid16 pairwise looking good in Pyre does **not** prove volume stos are applied correctly in Viking.

---

## Return format

Short answer: which hypothesis holds, with file/function names and whether Viking’s corner→volume scale for 962 matches Nornir (~0.93) or shows the squash. If H2/H5, propose the correct composition/bounds rule.
