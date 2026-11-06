# TileGains I/O cost on RC1_Crush (2026-11-06): question for James

Evidence from Build2 RC RC1 (py-spy record --subprocesses, 60 s, pid 621, 343-section RC1_Crush run, NAS saturated at
~420 MB/s each way): raw samples at
https://storage2.connectomes.pitt.edu/claude-transfer/rc1-tilegains-perf/tilegains_pyspy_raw.txt

- 56% of non-idle samples: serial `os.path.exists` per tile per level (974 tiles x 9 levels, ~8.8k CIFS stats a section).
  Fixed (buildmanager aa207af): one `os.scandir` per level.
- 38%: `stamp_gain_png` reading and rewriting whole PNGs to change ~300 bytes of tEXt. ~5.5 GB in and 5.5 GB out per
  section (level 001 4.2 GB, 002 1.2 GB). Fixed for reruns (imageregistration e129ed7): the "already has this gain"
  check reads only the chunks before the first IDAT. A first stamp or a changed gain still rewrites each file once.
- Single process 109 s per section; three concurrent ~210 s each: bandwidth bound, not CPU.

## Open design question

Gains are stamped into every tile at every pyramid level (`nornir_crush` chunk: `gain`, `effective_step`,
`effective_offset`), so any reader of a tile gets the gain-corrected counts without looking anything else up. RC1's
alternative: keep gains only in `TileGains_<transform>.json` + `TileGainsChecksum` and have AssembleTiles (and any other
reader, e.g. Viking's tile pyramid reader) look the gain up. That turns ~11 GB of I/O per section (RC1 total ~3.7 TB)
into one small JSON write. Cost: every consumer of crushed tiles must know the lookup, and the tiles stop being
self-describing. Not started; needs your decision (it touches Viking and the plan's crush-chunk contract).

Also not done: per-section INFO progress for TileGains (RC1: the "overlaps ... gain p5-p95" line only appears at the
end of a multi-section run through a tee'd pipe, so monitoring a run is blind).
