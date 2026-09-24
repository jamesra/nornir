CPU and GPU
===========

CPU paths in ``nornir_imageregistration`` do not need CuPy. GPU support is optional.

* Developer machines: ``pip install -e "nornir-imageregistration[gpu]" --no-deps`` for CuPy. The Windows Pyre installer does not include it.
* Pairwise distances on the GPU use the ``gpu_cuvs`` extra. Nearest-neighbor search stays on SciPy below 4096 points, because a brute-force GPU distance is slower than a 2D tree at typical mesh sizes. At 4096 points or more the index uses cuVS. ``NORNIR_CUVS_NN_MIN_POINTS`` changes that gate.
* cuVS wheels are Linux-only (``cuvs-cu13`` with CUDA 13 and ``cupy-cuda13x``). ``nornir:dev`` and ``nornir:cupy`` install that pair. Other platforms keep the SciPy nearest-neighbor path. The public API does not change.
* The host still needs a matching NVIDIA driver and GPU passthrough. Compute capability 7.5 or newer is required for the CUDA 13 images. See :doc:`../host_requirements`.

Copies between host memory and the device dominate many registration steps. Keep a chunk of work on one side until it is finished. A GPU timer that ignores transfer time is not a reason to move a stage.

Mosaic grid refine, as currently structured, can be slower on the GPU than on the CPU because of those copies. The measurement write-up, hardware, and how to reproduce it are in ``nornir-imageregistration/docs/mosaic_refine_grid_gpu_assessment.md`` inside a checkout. Read that note before changing the refine backend.

Where the algorithms live, beyond the generated API page: phase correlation, ``local_distortion_correction`` (grid refine), and ``blob_filter``.
