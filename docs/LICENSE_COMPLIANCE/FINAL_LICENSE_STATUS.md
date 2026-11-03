# License closure decision â€” 2026-11-02

**Distribution remains on hold. Technical preparation advanced substantially;
not every legal or build-source condition has been verified.**

This review applies to Setup SHA-256
`f24b87dbb696556b71d76179444840ffa66c10da92c49ac3f1e009c3eabb1e20`.
The accepted Setup and application binaries were not modified or rebuilt.
The existing 104 tests and installer acceptance results were reused, not rerun.

## Completed technical work

- The 35 Qt/PySide/Shiboken-folder native files excluding Microsoft runtimes match
  official PyPI 6.12.0 Windows x64 wheel bytes. This includes the Mesa DLL and
  retained Qt plugins. The three upgrade-only OpenGL files also match.
- A further 75 native files from Matplotlib 3.11.2, Pillow 13.0.0, NumPy 2.5.4,
  pandas 3.0.6, contourpy 1.4.0 and kiwisolver 1.5.1 match official wheel bytes.
  Two of those files are Microsoft runtime copies bundled by NumPy/pandas.
- All 25 remaining Python/native dependency files match the official Python
  3.12.9 embeddable Windows x64 archive. Its official SPDX document identifies
  OpenSSL 3.0.15, SQLite 3.45.3.0, libffi 3.4.4 and embedded dependencies.
- All 12 Microsoft runtime copies have valid Microsoft Authenticode signatures.
  A publisher signature is provenance evidence, not a redistribution license.
- Complete official 6.12.0 pyside-setup, qtbase, qtsvg and qtimageformats source
  archives were downloaded and checked against their official SHA-256 files.
  LGPL/GPL texts, source-tree notices and attribution records were collected.
- Official wheel notice texts were retained with original relative paths.
  Existing Pillow/Matplotlib licenses already include many embedded-library
  notices (including FreeType/Qhull); prior generic "missing" statements should
  not be read as proof these notices were absent. OpenSSL 3.0.15's exact-tag
  license text was added separately.
- Replacement instructions and a source-delivery mechanism were prepared.
  No runtime manifest/signature lock or packaging condition requiring a code
  change was found. The three OpenGL leftovers do not require a new build.

## Remaining items and concrete closure steps

| Item | Evidence / limitation | Concrete action | Type |
| --- | --- | --- | --- |
| Exact corresponding build source | Published release archives and binary wheel identity are established; upstream patches, full build options and all embedded dependencies are not reproduced | Obtain the wheel producer's source/build manifest or verify archive-to-build configuration, patches and embedded dependency set; add any missing source/build materials | Technical evidence, then legal sufficiency |
| Native third-party completeness | File-by-file matrix and source attribution superset exist; a source-tree superset is not a binary-specific SBOM | Reconcile enabled Qt third-party features, Mesa/LLVM build attribution, Python SBOM notice coverage and remaining matrix gaps against upstream build records; retain exact required notices | Technical/compliance |
| Modified-library operation | External shared-library layout inspected; detailed instructions supplied, but no modified Qt build/run performed | Execute the documented compatible modified-library run and retain loaded-DLL hashes/results, or obtain equivalent reliable evidence for the actual combined work | Technical evidence for LGPL 4(d)(1) |
| Microsoft redistribution rights | 12 signed runtime DLLs; no entitlement documents were provided | Owner checks applicable Visual Studio/runtime license and REDIST terms and records the lawful redistribution basis for these copies | Owner/legal |
| Customer terms and delivery | Proposed rights clarification and local source supplement prepared; actual EULA/channel not reviewed or executed | Review actual terms; supply the source supplement with every binary delivery or establish a compliant equivalent source-access route | Owner/legal and delivery operation |
| GitHub publication | No owner-code LICENSE selected; no push performed | Owner selects a license only for code they control and confirms publication rights; keep third-party notices and source-access documentation | Owner/legal |

Exact corresponding source does not mean the DLL must be byte-for-byte
reproducibly rebuildable, but a version match alone does not prove there are no
relevant upstream patches or omitted build materials. Likewise, a particular
test ritual is not itself prescribed by LGPL; the required capability must
exist. The unperformed modified-library run is recorded as an evidence gap.

## Distribution decision

The unchanged Setup has passed technical acceptance, but **do not release it as
license-cleared**. The accompanying-source package is prepared locally; no
customer hosting or legal source offer was activated. No commercial Qt license
or application source-code license was assumed. A compliant shared-library LGPL
route can permit proprietary application code; this review does not decide the
owner's application license or certify compliance with every distribution fact.

Existing README and QUICK_START content is preserved. Customer documentation is
added as a separate LICENSE_COMPLIANCE supplement. Old packages and user projects
are unchanged. Source inventories are a reviewable superset: references to
unshipped components in upstream source notices do not mean those components
were added to the binary payload.

Primary references checked:
- https://www.qt.io/development/open-source-lgpl-obligations
- https://doc.qt.io/qt-6/licensing.html
- https://doc.qt.io/qt-6/qt-attribution-llvmpipe.html
- https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170
- Supplied LGPLv3 section 4 and GPLv3 section 6; SOURCE_MANIFEST.json.
