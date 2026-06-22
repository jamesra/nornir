nornir-volumecontroller
=======================

``nornir_volumecontroller`` provides a high-level controller API for working with a registered Nornir volume. It sits above the data model (``nornir_volumemodel``) and the image-registration machinery (``nornir_imageregistration``), giving callers a single entry point to query bounds, enumerate channels, and retrieve registered image data from any region of a 3-D volume.

Key classes
-----------

``VolumeInterface``
    Abstract base class defining the contract for any volume controller: ``Bounds``, ``Channels``, and ``GetData``.

``Volume``
    Concrete controller that wraps a ``nornir_volumemodel`` volume model object. Lazily builds per-section transform maps and channel lists on first access.

``VolumeRegisteredChannel``
    Encapsulates a single channel + its channel-to-volume transform, exposing ``Scale`` and tile-pyramid path lookup.

``Scale``
    Thin wrapper around the volumemodel ``Scale`` object, providing X/Y/Z units-per-pixel as simple properties.

Usage
-----

Load a volume from an XML metadata file::

    import nornir_volumecontroller

    vol = nornir_volumecontroller.CreateVolumeController('/path/to/volume.xml')
    print(vol.Bounds)     # (minZ, minY, minX, maxZ, maxY, maxX)
    print(vol.Channels)   # set of channel names

Retrieve registered image data::

    region = [0, 0, 0, 10, 1024, 1024]  # (minZ, minY, minX, maxZ, maxY, maxX)
    images = vol.GetData(region, resolution=1.0, channel_names=None)
    # images is a dict of {section_number: ndarray}

**API reference:** :doc:`../api/nornir_volumecontroller`
