# Windows packaging

Use Windows x64, Python 3.12 and requirements-build.txt. Run build_portable.bat
only when a new build is needed. It builds the GUI and worker with PyInstaller
and validates the Qt module policy. The two QA probe executables are not customer
payload files. finalize_portable.py writes notices and a SHA-256 manifest.

To compile a future Setup with Inno Setup:

```text
ISCC /DBundleDir=<absolute verified portable folder> /DReleaseDir=<release output folder> installer/RetailDataStudio.iss
```

Never use the source repository or a data directory as BundleDir: the installer
recursively includes its contents. Review the manifest, licensing supplement and
functional acceptance before distribution. Build outputs stay outside GitHub.

The accepted V2.5 Matplotlib Setup is retained in the existing sibling
RetailDataStudio-v2.5-Delivery directory. Its SHA-256 is:

```text
f24b87dbb696556b71d76179444840ffa66c10da92c49ac3f1e009c3eabb1e20
```

The Setup is unsigned. Rebuilding is not expected to reproduce its bytes.
Commercial redistribution remains on hold; see FINAL_LICENSE_STATUS.md.
The required source archives and notices accompany the customer package in
LICENSE_COMPLIANCE. The main workspace retains license provenance under the
ignored artifacts/license_closure_20261102 directory. Neither location is private
application project storage.
