Annotation overlay gallery
==========================

Slim HTTP + SPA for per-volume ``AnnotationCrops`` review. The image does
**not** install Nornir. It lives in the SAM2 trainer repo
(``Sam2SegmentationTrainer/annotation-gallery``) and runs as a second service
on that project's Compose file, beside ``cursor-dev``.

The gallery and the trainer share ``SAM2_LOCAL_DATA_HOST`` mounted at
``/data-local``. ``GALLERY_VOLUME_DIR`` is ``SAM2_DATA_ROOT``
(``/data-local/current``). Children of that directory are volume roots
(``RC1``, ``RC2``, …); each contains ``AnnotationCrops``.

Start from the trainer repo (same ``docker/.env`` and net-mounts override as
the trainer)::

  docker compose -f docker/compose.cursor-dev.yaml up -d --build annotation-gallery

Pages:

* http://127.0.0.1:8080
* https://127.0.0.1:8443 when both PEM files are present

Host cert paths belong in ``D:\Docker\Run\sam2-dev\.env`` (``SSL_CERT_PATH``,
``SSL_KEY_PATH``). Compose mounts that directory at ``/certs``. If either PEM
is missing, HTTP on port 80 still starts and HTTPS stays off.

Trash and restore write ``ignore.json`` and move the mask between ``masks/``
and ``ignored/``. The trainer skips a sample whose raster is not in ``masks/``.

The trainer Compose service uses stub identity with the review role so
ignore/restore works on localhost. ``oidc`` still talks to Identity when
``GALLERY_IDENTITY_MODE=oidc``.

Weekly export
-------------

Do **not** spawn ``nornir-build`` from a gallery HTTP request. Use
``annotation-gallery/refresh-export.sh`` from the trainer repo on
``nornir:prod`` cron.
