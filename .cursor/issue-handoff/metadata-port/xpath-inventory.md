# Metadata port stage 0: XPath inventory

Inventory of every distinct XPath shape the build pipeline runs against the
volume metadata tree, captured for the XML-to-SQLite metadata port
(`.cursor/skills/nornir-improve-loop/metadata-port.md`, stage 0). Golden tests that
pin the result sets live in
`nornir-buildmanager/tests/test_volume_metadata_characterize.py`.

Captured 2026-10-07 against `nornir-buildmanager` `dev` @ `8fc56b3`. Re-run the
commands at the bottom before relying on the counts.

## How queries reach the tree

- Every query goes through `XElementWrapper.find` / `findall`, which override
  ElementTree's. Only the **first** `/`-separated step is link-aware: it is rewritten
  to `<Tag>_Link<predicates>` (`__ElementLinkNameFromXPath`), matching stubs are
  loaded and swapped in place (`_replace_links`, threaded for more than one), then the
  unlinked step is run with ElementTree and the remainder of the path recurses into
  each match. Deeper links therefore resolve one level at a time.
- A first-step predicate is evaluated against the **stub's** attributes. Stubs copy
  every attribute of the linked child at the parent's last save
  (`_save_link_element`), so they match as long as the parent was re-saved after the
  child changed; `_Save` does rewrite the parent when a linked child has
  `AttributesChanged`.
- `PipelineManager` substitutes `#Variable` tokens (`SubstituteStringVariables`)
  **before** the XPath is evaluated; values are pasted inside `'...'` with no escaping.
- `Iterate` goes through `resolve_iterate_candidates`
  (`pipelinemanager_iterate_filters.py`). With no `Require*` filters (or
  `use_legacy_iterate_fetch()`), it is plain `findall`. With section or transform
  membership filters it may do point lookups instead: `Section[@Number='n']`,
  `Transform[@<attr>='v']`.
- `Select` is `find` (first match), then validation of non-container results.
- `FindParent(tag)` / `FindFromParent(xpath)` walk the in-memory `Parent` chain and
  are not tree queries against stored data.

## Pipelines.xml (`nornir_buildmanager/config/Pipelines.xml`)

135 `Iterate` and 55 `Select` nodes; 33 of them set `Root=` to a variable bound by an
outer node, so the XPath is relative to that node. Counts are occurrences.

| Shape | Iterate | Select | Typical root |
|-------|--------:|-------:|--------------|
| `Block` | 19 | 9 | Volume |
| `Block/Section` | 26 | | Volume |
| `Block/Section/Channel` | 1 | | Volume |
| `Block/Section/Channel/Filter[@Name='#v']` | 3 | | Volume |
| `Block/StosGroup/SectionMappings/Transform` | 2 | | Volume |
| `Block/StosGroup[@Name='StosBrute64']/SectionMappings` | 1 | | Volume |
| `Block/StosGroup[@Name='#v']` | | 1 | Volume |
| `Block/StosMap[@Name='#v']` | 1 | | Volume |
| `Channel` | 26 | | Section |
| `Filter` | 18 | | Channel |
| `Filter[@Name='#v']` | | 5 | Channel |
| `Filter[@Name='#v']/TilePyramid` | | 1 | Channel |
| `TilePyramid` | 2 | 1 | Filter |
| `Tileset` | | 2 | Filter |
| `ImageSet` | | 2 | Filter |
| `ImageSet/Level`, `ImageSet/Level/Image` | 1, 1 | | Filter |
| `Histogram` | 1 | 1 | Filter |
| `Prune`, `Prune[@Overlap='#v']` | | 2, 1 | Filter |
| `Image`, `Data` | 1, 2 | | Histogram / Prune / Level |
| `Transform` | 5 | | Channel, SectionMappings |
| `Transform[@Name='#v']` (incl. `Translated_#v`) | | 11 | Channel |
| `TransformData` | 1 | | Channel |
| `StosGroup[@Name='#v#v']`, `StosGroup[@Name='#v']` | 3 | 9 | Block |
| `StosMap[@Name='#v']` | 1 | 8 | Block |
| `SectionMappings/Transform`, `SectionMappings/Transform[@Type='#v']` | 1, 1 | | StosGroup |
| `Mapping` | 3 | | StosMap |

Reporting `PythonCall` arguments: `RowXPath` `Section`, `SectionMappings`;
`ColumnXPaths` `Channel/Filter[@Name='#v']`, `Channel/TransformData`, `Channel/Notes`,
`Channel/Data`, `Channel/Filter[@Name='#v']/Histogram/Image`,
`Channel/Filter[@Name='#v']/Prune/Image`, `Image`, `Transform`, `Histogram/Image`.

## operations/ and volumemanager/ call sites

Literal or formatted XPaths passed to `find`/`findall` (excluding `str.find`):

- Tags only: `Block`, `Section`, `Channel`, `Filter`, `TilePyramid`, `Tileset`,
  `ImageSet`, `Histogram`, `Image`, `Data`, `Scale`, `Notes`, `Mapping`, `Transform`,
  `Level`, `StosGroup`, `StosMap`, `SectionMappings`, `AutoLevelHint`,
  `NonStosSectionNumbers`.
- Paths: `Section/Channel`, `Block/Section/Channel/Scale`, `Filter/TilePyramid/Level`
  (diagnostics.py).
- Predicates, formatted at run time:
  - `Section[@Number='%d']` (vikingxml.py, protected export; read only);
  - `Filter/TilePyramid/Level[@Downsample='%s']` (diagnostics.py);
  - `Image[@InputTransformChecksum='%s']` (block.py);
  - `SectionMappings[@MappedSectionNumber='%d']/Transform[@ControlSectionNumber='%d']`
    (block.py template, call site commented out);
  - `Mapping[@Control='%s']`, `StosGroup[@Name='%s']`, `*[@Path='%s']` (volumemanager);
  - `Transform[@<attr>='%s']` (iterate point lookups);
  - `GetChildByAttrib` / `GetChildrenByAttrib` / `UpdateOrAddChildByAttrib` build
    `Tag[@Attr='%g']` for numbers or `Tag[@Attr='%s']` for strings.
- Reporting `RecursiveReportGenerator` runs caller-supplied XPaths with `findall`.

## ElementTree limitations that shape the port

None of the inventoried patterns use XPath beyond ElementTree's subset:
`test_pipeline_xpaths_use_only_simple_steps` asserts every `Pipelines.xml` XPath is
`Tag` or `Tag[@Attr='value']` steps joined by `/`. Consequences:

- **No `and` / `or`.** Multi-criteria lookups are hand-written loops
  (`SectionMappingsNode.FindStosTransform` says so); `Require*` nodes filter
  candidates in Python after the fetch.
- **No `*_Link` wildcard.** A wildcard first step loads every child and filters link
  tags in Python.
- **String-only predicates.** `[@Downsample='1']` does not match `1.0`; numbers must be
  formatted exactly as saved (`%g` in `GetChildByAttrib`, `%d` in templates).
- **No escaping.** A substituted value containing `'` produces an invalid XPath. A
  value containing `/` is split by `__ElementLinkNameFromXPath` before ElementTree
  sees it.
- **Lazy resolution is part of the contract.** `find("Block/Section[@Number='2']")`
  loads only the matching section's file; a SQLite read path that materializes the
  whole tree changes memory and timing even if results match
  (`test_links_resolve_lazily_and_only_where_matched`).
- **Document order is observable.** `find` returns the first match and `Iterate`
  walks results in child order, so a backend must preserve child order. Today an
  attribute-only container save writes children in reverse of their loaded order
  (`test_attribute_only_save_reverses_child_order`): `sort()` sorts descending and
  `_Save` walks `list(self)[::-1]`, but the sort only runs when `ChildrenChanged`.
  On-disk order therefore flips on each such save. Even a sorting save only groups
  by tag (`SortKey` is the tag and the sort is stable), so same-tag siblings such as
  `Filter` or `Transform` are written in reverse of their in-memory order on every
  save (`test_parent_sort_leaves_attribute_only_children_unsorted`). Pinned, not
  fixed, because a fix changes saved bytes (decision `port-child-order-flip` in the
  loop ledger).

## Reproduce

```bash
cd nornir-buildmanager/nornir_buildmanager
python - <<'EOF'
from xml.etree import ElementTree as ET
from collections import Counter
c = Counter((e.tag, e.attrib['XPath']) for e in ET.parse('config/Pipelines.xml').iter() if 'XPath' in e.attrib)
for (tag, xp), n in sorted(c.items()): print(n, tag, xp)
EOF
rg -o --no-filename "\.(find|findall|iterfind)\((f?['\"][^'\"]*['\"])" -r '$1 $2' operations/ volumemanager/ | sort | uniq -c
```
