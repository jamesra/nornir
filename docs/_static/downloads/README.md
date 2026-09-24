# Pyre Windows installer (docs static asset)

Keep the latest ``Pyre-<version>-Setup.exe`` here for **local** Sphinx builds
(Git LFS; see repo-root ``.gitattributes``).

**GitHub Pages cannot host this file** (over the 100 MiB git limit). End-user
downloads use the GitHub Releases **latest** asset:

https://github.com/jamesra/nornir/releases/latest/download/Pyre-Setup.exe

Versioned history: ``pyre-<version>`` releases with ``Pyre-<version>-Setup.exe``.

Publish / refresh (after building the installer)::

    python release/sync_pyre_user_changelog.py --write-docs
    .\release\publish_pyre_windows_release.ps1

Or push tag ``pyre-<version>`` / run workflow **Pyre Windows Release**.
