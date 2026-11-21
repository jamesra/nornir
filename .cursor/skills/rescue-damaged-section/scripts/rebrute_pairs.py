"""Re-run masked StosBrute for chosen section pairs only, through the AlignSections stage function.

usage: rebrute_pairs.py <volume> check [<mapped>:<control> ...]   list which FinalStosMap brute pairs are stale
       rebrute_pairs.py <volume> run <mapped>:<control> [...]      re-register only those pairs (StosBrute64, Blob)

AlignSections registers every stale pair of the block. After repairs that are not all final, only some pairs may be
redone (the rest would have to be redone again), so this calls block.StosBruteAll with a stos map holding just the
named pairs. Same arguments as TEMAlign.sh: -NumAdjacentSections 1 -Filters Blob -UseMasks -Downsample 64 -Channels
TEM (masks are always on), flip check on, automatic GPU workers. Nodes are saved the way the pipeline saves them.
Then run RefineSectionAlignment with -MappedSections for the same sections."""
import logging
import sys
from dataclasses import dataclass, field

import nornir_buildmanager.operations.block as block
from nornir_buildmanager.pipelinemanager import PipelineManager
from nornir_buildmanager.volumemanager import VolumeManager


@dataclass
class _Mapping:
    """Duck-typed stand-in for a MappingNode: one control section and its mapped sections."""
    Control: int
    Mapped: frozenset = field(default_factory=frozenset)


@dataclass
class _StosMap:
    """Duck-typed stand-in for a StosMapNode holding only the chosen mappings."""
    Mappings: list


def main() -> None:
    """Check or re-register the named pairs."""
    root, mode = sys.argv[1], sys.argv[2]
    pairs = [tuple(int(x) for x in p.split(":")) for p in sys.argv[3:]]
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("rebrute_pairs")
    vol = VolumeManager.Load(root)
    block_node = vol.find("Block")
    if mode == "check":
        final = block_node.GetStosMap("FinalStosMap")
        group = block_node.GetStosGroup("StosBrute64", 64)
        for m in final.Mappings:
            for mapped in sorted(m.Mapped):
                if pairs and (mapped, m.Control) not in pairs:
                    continue
                tasks = block._enumerate_brute_pair_tasks([_Mapping(m.Control, frozenset([mapped]))], block_node,
                                                          "TEM", "Blob", group, True, logger)
                stale = [t for t in tasks if t.needs_work]
                if stale or pairs:
                    print(f"{mapped}-{m.Control}: {'STALE' if stale else 'current'}")
        return
    by_control: dict[int, set[int]] = {}
    for mapped, control in pairs:
        by_control.setdefault(control, set()).add(mapped)
    stos_map = _StosMap([_Mapping(c, frozenset(m)) for c, m in sorted(by_control.items())])
    gen = block.StosBruteAll(Parameters={"Downsample": 64, "refine": "", "regularize": "", "NoFlipCheck": False},
                             stos_map_node=stos_map, block_node=block_node, ChannelsRegEx="TEM", FiltersRegEx="Blob",
                             Method=None, Logger=logger, GpuWorkers=0, OutputGroup="StosBrute64",
                             AngleSearchRange=None)
    PipelineManager._SaveNodes(gen)


if __name__ == "__main__":
    main()
