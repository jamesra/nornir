Using Pyre
==========

Pyre is the interactive registration tool. Install it with :doc:`../packages/pyre_install`, or run a developer build with :doc:`../development/pyre_development`.

Open a registration with **File → Open STOS File** (Ctrl+O). To register a new pair, open the images with **File → Open Source Image** and **File → Open Target Image**. **File → Open STOS Folder Browser** lists every ``.stos`` file in a folder. Save with **File → Save STOS File** (Ctrl+S).

The same mouse and keyboard reference is built into Pyre: **Help → Mouse and Keyboard Controls** (F1).

Menus
-----

* **File:** open STOS files, images, and masks; save the STOS file or the warped image.
* **Transform:** convert the transform type, flip the source image, reset the transform.
* **Registration:** rotation/translation estimates, rigid and grid refinement, removing points on masked areas, cancelling registration (Esc), the ROI inspector, and the registration defaults (**Transform Settings**).
* **View:** window layouts for multiple displays, showing or hiding the Source, Target, and Composite windows, restoring orientation, and image contrast.
* **Help:** the controls reference and this manual.

Control points
--------------

These bindings apply to the Source, Target, and Composite STOS windows.

On a control point:

* Click to select only that point. Shift+Click adds it to or removes it from the selection.
* Drag to move it. Shift+Drag starts a box selection instead.
* Alt+Shift+Click auto-aligns it.
* Shift+right-click deletes it.

On empty space:

* Click to clear the selection.
* Drag to box-select. Alt+Drag lasso-selects. Hold Shift as well to add to or remove from the selection.
* Shift+Click or middle-click adds a control point. Alt+Shift+Click adds one and auto-aligns it.
* Alt+Click moves the selected point to the cursor (exactly one point selected).
* Ctrl+Drag moves all control points together, translating the mapped (source) image (one or no point selected).

Delete or Backspace deletes the selected points.

By transform type:

* **Mesh and RBF:** every binding above. Deleting keeps at least three control points.
* **Grid:** points can be moved but not added or deleted; trying either offers to convert the transform to a mesh. Source points cannot be moved in the Source window; move them in the Target or Composite window.
* **Rigid:** there are no control points. Drag moves the mapped image in the Source or Composite window. Adding a point offers to convert the transform to a mesh.

Alignment keys
--------------

* **Rigid:** Space runs a local brute-force refine (±5° at 1° steps) and keeps scale. Shift+Space also refines scale. Both are also in the **Registration** menu.
* **Mesh / RBF:** Space auto-aligns the selected control points and the point under the cursor. Shift+Space auto-aligns all points.
* **Grid:** Space auto-aligns like Mesh. Shift+Space runs one grid-refine pass (settings dialog, then a live preview). **Registration → Refine w/ Grid** runs the chosen number of iterations as one job and updates the view after each pass. Several Shift+Space presses are not the same as that multi-pass job.
* **Esc** (or **Registration → Cancel Registration**, or the status-bar Cancel) cancels queued point alignments and any running refine or rotate job. Points already moved stay moved. While you are creating a point or dragging a selection box, Esc cancels that instead.

Navigation
----------

* WASD pans. Right-drag also pans.
* The mouse wheel zooms about the cursor. Page Up zooms out and Page Down zooms in.
* Shift+scroll scales the transform about the cursor when the transform supports it and no points are selected or queued.
* Ctrl+scroll rotates the mapped section when the transform supports it. Ctrl+Shift+scroll uses finer steps. On a rigid transform, rotation is in the Composite window only.
* **M** matches Source, Target, and Composite to the focused window's center and zoom.
* **L** shows or hides mesh lines in the focused window.
* **F** flips the source (mapped) image.
* Ctrl+Z undoes. Ctrl+X redoes.

If the window is blank, update the graphics driver. A developer build can try ``PYOPENGL_PLATFORM=software``. Session logs for the installer build are under ``%LOCALAPPDATA%\Nornir\Pyre\logs``.
