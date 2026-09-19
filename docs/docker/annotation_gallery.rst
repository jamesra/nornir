Annotation overlay gallery
==========================

Slim HTTP + SPA for per-volume ``AnnotationCrops`` PNG + 1-bit mask review.
The **gallery image does not install Nornir** (no ``nornir-buildmanager``,
imageregistration, CuPy, or torch). Export, SAM2 scoring, and weekly refresh
run on ``nornir:prod`` / cursor-dev against the same registry.

Start::

  .\nornir-docker\start-annotation-gallery.ps1
  docker compose -f nornir-docker/compose.annotation-gallery.yaml up -d --build

Then open http://127.0.0.1:8090

Run env template: ``nornir-docker/example.annotation-gallery.run.env`` →
``<NORNIR_DOCKER_USER_ROOT>\Run\nornir-annotation-gallery\annotation-gallery.run.env``.

Registry
--------

``GALLERY_VOLUME_DIR`` (in-container ``/gallery-volumes``) is a folder of
**volume-root** links. The child **name** is the Identity volume name; the
child **target** is the volume root (``/storage4/RC2``), not ``AnnotationCrops``.
The gallery reads ``{name}/AnnotationCrops/``. Identity never stores filesystem
paths.

::

  ln -s /storage4/RC2 /gallery-volumes/RC2

Bind the registry **and** the storage root so those links resolve.
``GALLERY_VOLUME_DIR_HOST`` and ``GALLERY_STORAGE_HOST`` are compose bind sources.

Permissions
-----------

+------------------+---------------------------------------------+
| Identity         | Gallery                                     |
+==================+=============================================+
| Read             | Volume listed; GET catalog/crops/masks     |
+------------------+---------------------------------------------+
| Review           | Trash / restore; POST ignore/restore        |
+------------------+---------------------------------------------+
| Neither          | Volume omitted                              |
+------------------+---------------------------------------------+

``GALLERY_IDENTITY_MODE=stub`` (default) uses ``GALLERY_STUB_ROLE=read|review``.
``oidc`` talks to ``https://identity.codepharm.net:5001`` (auth) and
``https://identity.codepharm.net:6001`` (API). App mapping is Read vs Review
per volume; names are probed from Identity (``GALLERY_READ_PERMISSION`` /
``GALLERY_REVIEW_PERMISSION``).

Weekly export
-------------

Do **not** spawn ``nornir-build`` from a gallery HTTP request. Use
``nornir-docker/annotation-gallery/refresh-export.sh`` on ``nornir:prod`` cron
with the same registry.
