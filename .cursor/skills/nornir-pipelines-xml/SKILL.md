---
name: nornir-pipelines-xml
description: >-
  How nornir-buildmanager's Pipelines.xml drives stages: Arguments, Iterate, Select, RequireMatch,
  RequireSetMembership, PythonCall, variables and saving. Read before adding or changing a pipeline, or before
  writing buildmanager Python that loops over sections, channels, filters, levels or stos transforms, so selection,
  skipping and saving stay in the XML and existing stages are reused.
---

# Pipelines.xml: let the XML select, Python do one node

The pipeline engine (`nornir_buildmanager/pipelinemanager.py`) already walks the volume, filters what to process,
skips what is missing and saves what changed. Python stages should do the work for **one node the XML handed
them**. Writing loops, level lists or "is this filter there" checks in Python duplicates the engine and drifts from
how every other stage behaves (James, 2026-11-10: "a pattern of you trying to write code for functions exposed
already via the pipelines").

## Before writing any Python

1. Find two or three pipelines in `nornir_buildmanager/config/Pipelines.xml` that do something similar
   (same node type, same kind of selection) and read them whole.
2. List what the XML elements below can already do for your job: which nodes to visit, which to skip, which
   arguments to pass.
3. Search `operations/*.py` for an existing stage that already does the per-node work (`tile.BuildImagePyramid`,
   `tile.AssembleTransform`, `general.MovePath`, `block.FixStosFilePaths`, `setters.*` ...).
4. Write Python only for the per-node work nothing exposes. A new pipeline argument is a new option: ask James
   first (rule: ask before adding options).

## Elements

| Element | What it does | Skip / failure behaviour |
|---------|--------------|---------------------------|
| `<Arguments><Argument flag dest default type help/>` | argparse options. `dest` becomes a kwarg for every `PythonCall` and a `#dest` variable. `type` names a parser in `nornir_shared.argparse_helpers` (`IntegerList` takes `1,3,5-7`); `action="store_true/false"` for flags. Omitted with no default -> `None` | - |
| `<Iterate VariableName XPath [Root] [Validate] [SortAttribute]>` | Runs its children once per node matching `XPath` under the current node (or under variable `Root`). Binds the node to `VariableName` | Each candidate is validated first (`CleanIfInvalid`): an invalid node is **deleted** and skipped. Use `Validate="False"` when you must see nodes that may be invalid (e.g. renaming what they reference) |
| `<Select VariableName XPath [Root]>` | Binds the first match to `VariableName` | No match -> the enclosing Iterate skips this iteration (PipelineSelectFailed). This is the "tries, node missing, skips" behaviour; no Python guard needed |
| `<RequireMatch Attribute RegEx [Root]>` | Regex on an attribute of the current node | No match -> skip this iteration |
| `<RequireSetMembership Attribute List [Root]>` | Attribute value must be in the list variable (e.g. `#Sections`, `#Levels`) | Not in list -> skip. List argument omitted (`None`) -> everything passes |
| `<PythonCall Function="module.func" [Module] attr="#var"...>` | Calls `nornir_buildmanager.operations.<module>.<func>`. kwargs = all Arguments + all bound variables + this element's attributes (`#name` substituted) + `Parameters` (`<Parameters><Entry Name Value/></Parameters>`) + `Logger`, `VolumeElement`, `VolumeNode` | Return or yield the nodes that changed; the engine saves each one's container. Return `None` when nothing changed. An exception stops the pipeline |

`#Name` in any attribute is replaced by the variable or argument `Name`, so XPaths can be built from arguments:
`XPath="Filter[@Name='#InputFilter']"`.

## Patterns

**Pick levels of an ImageSet or TilePyramid** (AdjustAssembledContrast):

```xml
<Select VariableName="FilterNode" XPath="Filter[@Name='#InputFilter']"/>
<Iterate VariableName="LevelNode" Root="FilterNode" XPath="ImageSet/Level">
    <RequireSetMembership Attribute="Downsample" List="#Levels"/>
    <PythonCall Function="tile.AutolevelAssembledImage" level_node="#LevelNode" .../>
</Iterate>
```

with `-Downsample` declared `type="IntegerList"` and no default. Python gets one level; it never parses level lists.

**Per-filter setup, then per-level work:** two `PythonCall`s in order, the first under the `Select`, the second
inside the level `Iterate` (PrepareAssembledContrastFilter / AutolevelAssembledImage). Do not loop levels inside the
setup call.

**Skip what is not there:** `Select` the node. If a section lacks the filter, that iteration is skipped.

**Pattern-matched filters:** `Iterate XPath="Filter"` + `RequireMatch Attribute="Name" RegEx="#FilterRegEx"`
(Assemble's `-Filters`, default `(?![M|m]ask)`).

**Sections:** `Iterate XPath="Block/Section"` + `RequireSetMembership Attribute="Number" List="#Sections"` at the top.

**Stos transforms without cleaning them first:** `Iterate Block -> StosGroup -> SectionMappings/Transform` with
`Validate="False"` (RepairStosAngles, RenameFilter's transform step).

**Coarser levels from a finer one:** `tile.BuildImagePyramid` (pipeline `BuildImagePyramids`) or
`BuildTilePyramids`; do not write another shrink loop.

## Python side

- Signature: the kwargs named in the `PythonCall` plus `**kwargs` (the engine passes everything). Name the
  parameter after the attribute (`level_node="#LevelNode"` -> `def f(level_node: LevelNode, ..., **kwargs)`).
- Reach parents with `node.FindParent('Filter')`, `FindParent('Channel')`, rather than passing them separately.
- Return/yield changed nodes so they are saved; yield a newly created parent (e.g. the channel after
  `GetOrCreateFilter`) before the child.
- Keep it idempotent: compare a stored checksum/attribute and return `None` when current, so reruns are cheap.

## Testing

Run the pipeline itself: build a small volume with `VolumeManager.Load(path, Create=True)`, add nodes,
`VolumeManager.Save`, then `nornir_buildmanager.build.Execute([path, '-debug', '<Pipeline>', ...args])` and reload.
Examples: `tests/operations/test_autolevel_assembled.py`, `tests/operations/test_rename_filter_stos.py`. A test that
calls the Python directly misses the XML's selection and skipping. After deleting attributes in a fixture, set
`node.AttributesChanged = True` or the save does not write them.
