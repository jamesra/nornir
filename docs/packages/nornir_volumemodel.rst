nornir-volumemodel
==================

``nornir_volumemodel`` is a pure Python data model for a Nornir-registered electron-microscopy volume.  It describes the hierarchy of objects that make up a processed volume and supports serialization to/from Nornir's XML metadata format.

Object hierarchy
----------------

A volume is organized as a tree:

.. code-block:: text

    Volume
    └── Block (one or more)
        └── Section (one per physical slice / Z-level)
            └── Channel (e.g. "TEM", "Leveled")
                ├── Filter (image processing filter applied to the channel)
                │   └── TilePyramid → Level → Image tiles
                └── Transform (spatial registration transforms)

Key modules
-----------

``nornir_volumemodel.model.volume``
    ``Volume`` — top-level container; holds a list of ``Block`` objects. Inherits ``DirectoryResource`` and ``Named``.

``nornir_volumemodel.model.block``
    ``Block`` — groups sections and is the unit of batch processing.

``nornir_volumemodel.model.section``
    ``Section`` — represents one Z-slice. Holds channels and section-level transforms.

``nornir_volumemodel.model.channel``
    ``Channel`` — a named imaging channel within a section. Contains filters and a scale.

``nornir_volumemodel.model.scale``
    ``Scale`` — physical scale (units per pixel) on each axis.

``nornir_volumemodel.model.transform``
    ``Transform`` — a registration transform linking two coordinate spaces.

``nornir_volumemodel.persistance.nornir_xml``
    XML serialization/deserialization. Call ``nornir_volumemodel.Load_Xml(path)`` to load a volume from disk.

Usage
-----

Load a volume from XML::

    import nornir_volumemodel

    vol = nornir_volumemodel.Load_Xml('/path/to/volume.xml')
    for block in vol.Blocks:
        for section in block.Sections:
            print(section.Number, list(section.Channels))

**API reference:** :doc:`../api/nornir_volumemodel`
