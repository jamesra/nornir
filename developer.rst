Developer Notes
---------------

Versioning
==========

requirements-v*.txt files live in nornir-pyre. Nornir requirements should refer to a specific tag on a specific branch,
created as follows:

::

   git tag dev-v1.5.2 dev -m "Version 1.5.2"
   git push origin dev-v1.5.2