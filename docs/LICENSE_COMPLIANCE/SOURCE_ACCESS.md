# Version-specific library source access

**Prepared source delivery supplement; not a blanket compliance certificate.**

For Retail Data Studio V2.5 MPL, ship the `LICENSE_COMPLIANCE` directory together
with the unchanged Setup. Its `sources` directory contains official upstream
6.12.0 source archives; `SOURCE_SHA256SUMS.txt` records their verified hashes.
PySide and Shiboken share the pyside-setup source archive. Qt Base supplies Core,
Gui, Widgets, Network, OpenGL and the upgrade-only OpenGLWidgets library; Qt SVG
and Qt Image Formats have separate archives. All archives are complete as
downloaded, including build files and notices, not stripped snippets.

Official version-specific acquisition locations:

- https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/
- https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/

Use the archive names and exact HTTPS URLs in `SOURCE_MANIFEST.json`. Re-download
only from the official index or its indicated mirror and compare SHA-256 against
the accompanying checksum record. Checksums establish correspondence to the
published archives, not a reproducible-build proof for the supplied DLLs.

The application Qt/PySide/Shiboken native files were compared byte-for-byte with
the matching official PyPI 6.12.0 Windows x64 wheels; see official-provenance.json.
The three old OpenGL files were compared separately. No application-side patches
to those native binaries were found. This does not recover upstream wheel build
patches/configuration or prove all embedded third-party source corresponds to
each object file. Those limitations are listed in LICENSE_CLOSURE.md.

## Delivery mechanism

Prefer providing these source archives with every customer delivery. Do not
distribute Setup alone while claiming the source supplement accompanied it.
For download-based distribution, publish the supplement alongside the binary
with equally accessible source access and clear directions, without an additional
source access charge. Review the chosen GPLv3 section 6 route for the actual
delivery channel. Verify the link and preserve the exact release snapshot.

No customer-accessible hosting was created in this task. No written offer with
an unapproved contact, duration, address or fulfillment promise was invented.
The supplied local archives implement preparation for accompanying source; they
do not establish that a particular future recipient has actually received it.

Keep LGPL/GPL texts, original source notices and replacement instructions with
the supplement. Additional native components (particularly Mesa/LLVM and
Microsoft runtimes) have distinct provenance/notice/rights questions; the Qt
source archives do not automatically fulfill obligations for unrelated code.
