# Built Plans

Archive of Cursor agent plans whose todos are **fully completed**. Active or in-progress plans remain in `.cursor/plans/` (workspace) or the Cursor plans directory.

Each linked plan file retains its original frontmatter, overview, and implementation notes for historical reference.

| Plan | Primary deliverables |
|------|---------------------|
| [autolevelpyramid_skip_logic_993d734e.plan.md](autolevelpyramid_skip_logic_993d734e.plan.md) | `AutoLevelPyramid` pipeline; skip/coarser-level fixes in `nornir_buildmanager/operations/tile.py` |
| [batched_gpu_refine_prototype_825fa89e.plan.md](batched_gpu_refine_prototype_825fa89e.plan.md) | Batched GPU vertex measurement prototype in `local_distortion_correction.py` |
| [console_pipeline_navigation_9766363b.plan.md](console_pipeline_navigation_9766363b.plan.md) | `nornir_shared/build_control.py`, MQTT Tab/Shift+Tab navigation, cooperative skip in `pipelinemanager.py` / `build.py` |
| [fix_copied_volume_timestamps_f2e96b2e.plan.md](fix_copied_volume_timestamps_f2e96b2e.plan.md) | `SyncValidationTimes` pipeline; `migration.SyncValidationTimes`; `tests/pipeline/test_sync_validation_times.py` |
| [gpu_1x_tile_streaming_42a5f74e.plan.md](gpu_1x_tile_streaming_42a5f74e.plan.md) | Per-tile streaming in `ConvertImagesInDictGpu` (`nornir_imageregistration/core/_core.py`) |
| [gpu_adjustcontrast_pipeline_ba198f94.plan.md](gpu_adjustcontrast_pipeline_ba198f94.plan.md) | `AdjustContrastGpu` pipeline; `ConvertImagesInDictGpu`; `scripts/bench_adjust_contrast.py` |
| [gpu_inverse_transform_for_refine_3ffdc4c6.plan.md](gpu_inverse_transform_for_refine_3ffdc4c6.plan.md) | GPU inverse transform path during mosaic grid refinement prewarp |
| [gpu_tile_pyramid_plan_7d3bc98a.plan.md](gpu_tile_pyramid_plan_7d3bc98a.plan.md) | GPU tile pyramid downsampling; merged contrast+pyramid tile pass |
| [mosaic_refine_grid_gpu_assessment_f32f0af3.plan.md](mosaic_refine_grid_gpu_assessment_f32f0af3.plan.md) | `scripts/microbench_mosaic_refine.py`; phase timers; [mosaic_refine_grid_gpu_assessment.md](../../nornir-imageregistration/docs/mosaic_refine_grid_gpu_assessment.md) |
| [per-tile_gpu_pyramid_pipeline_4c90b899.plan.md](per-tile_gpu_pyramid_pipeline_4c90b899.plan.md) | `ConvertImagesInDictGpuPyramid` per-tile streaming redesign |
| [pipeline_command_chaining_b922dc68.plan.md](pipeline_command_chaining_b922dc68.plan.md) | `nornir-build … --then …` chaining; `tests/pipeline/test_chain.py`; updated `TEMBuild.cmd` / `CMPBuild.cmd` |
| [pipelined_gpu_tile_conversion_49185090.plan.md](pipelined_gpu_tile_conversion_49185090.plan.md) | Three-stage producer-consumer GPU tile conversion pipeline |
| [pyramid_load_pipeline_fix_dbbbb0e4.plan.md](pyramid_load_pipeline_fix_dbbbb0e4.plan.md) | Streaming pyramid prefetch / NFS parallelism fixes |
| [streaming_memory_rule_f3259efc.plan.md](streaming_memory_rule_f3259efc.plan.md) | [.cursor/rules/Streaming-and-memory-bounded-processing.mdc](../rules/Streaming-and-memory-bounded-processing.mdc) |
| [pyre_windows_installer.plan.md](pyre_windows_installer.plan.md) | `nornir-pyre/packaging/windows/`; `.github/workflows/pyre-windows-release.yml`; `release/generate_pyre_windows_constraints.py`; `docs/packages/pyre_install.rst`; `docs/development/pyre_development.rst` |
| [pyre_empty_startup_05da5b09.plan.md](pyre_empty_startup_05da5b09.plan.md) | `pyre/state/__init__.py`, `pyre/stos_registration.py`, `pyre/launcher.py`; `tests/test_empty_startup.py` |
| [stos_explorer_delete_auto_b60fb47c.plan.md](stos_explorer_delete_auto_b60fb47c.plan.md) | `pyre/ui/windows/stosfilebrowser.py`; `tests/test_stos_file_browser_delete.py` |
| [stos_file_source_selector_e597a2eb.plan.md](stos_file_source_selector_e597a2eb.plan.md) | `pyre/stos_manual_paths.py`, `pyre/ui/widgets/stos_file_source_selector.py`, `pyre/settings/app.py`; `tests/test_stos_file_source_browser.py` |
| [warp_and_transfer_optimization_08b8512c.plan.md](warp_and_transfer_optimization_08b8512c.plan.md) | Prewarp GPU cost reduction (coverage warp elimination, validity mask derivation) |

## Plans still open (not archived)

- `fix_grid690_python_parity.plan.md` — Grid690 refine-grid C++ parity (Phase 0 checklist exists at `docs/refine-grid-cpp-parity-checklist.md`; parity work ongoing)
- Plans under the Cursor plans directory with pending todos (CIFS transport, dual-container debug, MQTT dashboard, network shares, equalize refine CPU/GPU, etc.)
