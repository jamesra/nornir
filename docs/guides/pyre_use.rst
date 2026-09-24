Using Pyre
==========

Pyre is the interactive registration tool. Install it with :doc:`../packages/pyre_install`, or run a developer build with :doc:`../development/pyre_development`.

Open a registration with **File → Open STOS**, or **File → New STOS** for a new pair. Open a mosaic with **File → Open Mosaic**.

Control points
--------------

These bindings apply to STOS registration views. Triangulation transforms can add and delete points. A refined grid cannot; convert or use a triangulation transform if you need to edit the mesh.

* Click to select a point.
* Shift+Click to add a point.
* Alt+Shift+Click to add a point and auto-align it.
* Drag a point to move it.
* Ctrl+drag to translate the mapped (source) image.
* Alt+Click to move the selected point to the cursor.
* Shift+right-click to delete a point (triangulation only).
* Right-drag to pan.

Alignment keys
--------------

* **Rigid:** Space runs a local brute-force refine (±5° at 1° steps) and keeps scale. Shift+Space also refines scale.
* **Mesh / RBF:** Space auto-aligns the selected control point. Shift+Space auto-aligns all points.
* **Grid:** Space auto-aligns the selected control point. Shift+Space runs one grid-refine pass (settings dialog, then a live preview). The Refine w/ Grid menu runs the chosen number of iterations as one job and updates the view after each pass. Several Shift+Space presses are not the same as that multi-pass job.

Navigation
----------

* WASD pans. Right-drag also pans.
* The mouse wheel zooms.
* Shift+scroll scales the transform about the cursor when the transform supports it.
* Ctrl+scroll rotates the mapped section when the transform supports it. Ctrl+Shift+scroll uses finer steps. On a rigid transform, rotation is in the Composite view.
* Page Up / Page Down changes magnification.
* **M** matches Source, Target, and Composite to the focused window's center and magnification.
* **L** shows or hides mesh lines.
* **F** flips the source (mapped) image.
* **Tab** toggles how the source image is drawn (registered versus the alternate display) on the shared transform. It applies to Source, Target, and Composite.
* Ctrl+Z undoes. Ctrl+X redoes.

Save with **File → Save STOS**.

If the window is blank, update the graphics driver. A developer build can try ``PYOPENGL_PLATFORM=software``. Session logs for the installer build are under ``%LOCALAPPDATA%\Nornir\Pyre\logs``.
