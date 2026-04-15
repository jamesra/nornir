nornir-web
==========

``nornir-web`` is a Python 3 web service (Django) that serves arbitrary registered image regions from a Nornir volume to HTTP clients.

.. note::

   The service is functional but was never optimized for production throughput. It is included in the repository for reference and future development.

Architecture
------------

- **One service per volume.** The service imports or updates the volume model at startup, building a spatial index (SQL database) that maps volume-space regions to registered tiles.
- **Arbitrary region requests.** Clients send HTTP requests for any (minZ, minY, minX, maxZ, maxY, maxX) bounding box in volume space. The service assembles the response image from registered, non-overlapping tiles.
- **Tile cache.** Registered tiles are stored on disk. Stale or missing tiles are computed on demand (GPU step) and cached. The intention was to pre-build the full-volume tile cache during idle periods.

Known limitations
-----------------

- Volume import/update at startup was slow, primarily due to XML-based metadata (SQL + spatial DB would be faster).
- Python's GIL was a bottleneck when handling large numbers of concurrent tile requests.
- Long-running registration jobs need versioning or locking to avoid serving stale tiles.

Django components
-----------------

The Django project contains standard boilerplate: ``settings.py``, ``urls.py``, ``wsgi.py``, and ``manage.py``. There is no meaningful public Python API beyond the Django admin and views.

.. seealso::

   :doc:`nornir_volumecontroller` — the controller layer that nornir-web uses to query volume data.
