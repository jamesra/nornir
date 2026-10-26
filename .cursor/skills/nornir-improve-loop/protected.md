# Protected areas (proposal only)

Never edit these. When a candidate lands here, write a proposal ([categories.md](categories.md), Proposals) and move on.

- **File formats read outside Nornir:**
  - `.stos` and `.mosaic` file formats (reader and writer code in `nornir-imageregistration`), and any serializer attribute, element, or column name in them;
  - the `Volume.VikingXML` export in `nornir-buildmanager/nornir_buildmanager/operations/vikingxml.py`, consumed by the Viking C# client;
  - the `Pipelines.xml` and `Importers.xsd` / `Volumes.xsd` schemas under `nornir-buildmanager/nornir_buildmanager/config` and `Schemas`;
  - the separate volume XML readers: `nornir-volumemodel` (`persistance/nornir_xml`) and `nornir-web` (`volume_import.py`).
- **`VolumeData.xml` itself:** changes only through the stages in [metadata-port.md](metadata-port.md). Until the user decides to retire XML, saved output stays byte-identical to what the current code writes.
- **Pyre's persisted user settings** (`nornir-pyre/pyre/settings.json` schema and keys): renaming or retyping a key is a format change; adding a defaulted key is not.
- **Secrets and deploy configuration:** `.env` and `*.run.env` files, anything under `D:\Docker`, mounted secrets and credentials in the container (`/run/secrets`, `/etc/nornir-net-mounts`, `*.cred`), deploy tokens, and `NORNIR_ORG_GITHUB_IO_DEPLOY_TOKEN`-style references beyond reading their names.
- **Edits the loop did not make:** if a file the candidate needs already has uncommitted changes, choose a different candidate. Untracked files in the launch git status (including `*.egg-info`, `logs/`, and `.cursor/` working notes) are the user's.
- **Steering:** anything matched by an `avoid:` line in `STEERING.md`.

Callers of these areas may change only if the protected code and its observable inputs and outputs stay exactly the same. Changing a numeric dtype or field type in a serialized, persisted, or wire type is a format change: write a proposal.
