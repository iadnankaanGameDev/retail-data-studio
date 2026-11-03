# QtAgg chart migration: distribution status

This is an engineering candidate, not commercial redistribution clearance. No
application source-code license has been selected. The existing V2.5 installer
and the separate publication/delivery folders are retained unchanged.

## Scope

Reports use Matplotlib FigureCanvasQTAgg with PySide6. The renderer accepts the
already-aggregated period frame; SQLite, ETL, filters, report totals and project
backup/restore are unchanged. Up to 18 periods use bars; longer series use a
line and a translucent area. Date tick positions can differ from Qt Charts.
The former vertical gradient is now a uniform light fill. Hover, metric changes,
zero baseline and the existing empty-state card are retained.

## Runtime dependency inventory

| Distribution | Tested version | License family / required notices |
| --- | --- | --- |
| PySide6 / Essentials / Addons / Shiboken | 6.12.0 | LGPLv3/GPL alternatives for bindings; each Qt module has its own terms |
| pandas | 3.0.6 | BSD-3-Clause and bundled notices |
| NumPy | 2.5.4 | BSD/0BSD/MIT/Zlib/CC0; OpenBLAS and GCC runtime exception notices |
| python-dateutil | 2.9.0.post0 | BSD / Apache-2.0 |
| six | 1.17.0 | MIT |
| tzdata | 2026.5 | Apache-2.0 plus IANA data notices |
| Matplotlib | 3.11.2 | PSF-based Matplotlib license; fonts and native libraries have additional notices |
| contourpy | 1.4.0 | BSD-3-Clause |
| cycler | 0.12.1 | BSD-style |
| fonttools | 4.68.0 | MIT |
| kiwisolver | 1.5.1 | BSD-style |
| Pillow | 13.0.0 | MIT-CMU; image-library notices |
| pyparsing | 3.3.3 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |

Build tools: PyInstaller 6.22.0 (GPL with bootloader exception), hooks-contrib,
altgraph/pefile/setuptools (MIT), pywin32-ctypes (BSD). pytest is test-only (MIT).
Inno Setup uses its separate permissive license. Using PyInstaller does not
waive the licensing obligations of the bundled libraries.

## Candidate native-library policy

Allowed Qt DLL families: Core, Gui, Widgets, Svg, Network, OpenGL, OpenGLWidgets.
These provide an LGPL route, subject to their complete conditions. Charts,
VirtualKeyboard, Graphs, QML, Quick and Pdf are excluded. The Python Addons wheel
may remain installed for build-time resolution; its presence does not authorize
shipping all of its modules. The spec prunes native plugins and validates both
ordinary and delay-loaded Qt PE imports, aborting on dangling Qt dependencies.

The finalizer audits the actual output again and writes NATIVE_INVENTORY.json.
The 2026-11-01 RC1 has now been collected and audited. Its native inventory is available; commercial clearance remains open.
The old V2.5 package still contains Qt Charts and Virtual Keyboard and must not
be relabeled as the migrated package.

A full binary inventory must also account for Python/SQLite, OpenSSL/libffi,
Microsoft VC runtimes, OpenBLAS/GCC runtime, image codecs, Qt's third-party code,
and Matplotlib's FreeType/fonts. A top-level Python license list is insufficient.
The finalizer copies available installed dependency license files, but this is
not proof that all upstream source/notice obligations have been met.

## LGPL documents and replacement rights

The verbatim LGPLv3 and incorporated GPLv3 texts are in docs/licenses/. Their
presence is for dependency compliance; it does not license this application GPL.
Sources for these standard license texts:

- https://raw.githubusercontent.com/qt/qtbase/v6.8.0/LICENSES/LGPL-3.0-only.txt
- https://raw.githubusercontent.com/qt/qtbase/v6.8.0/LICENSES/GPL-3.0-only.txt
- https://www.qt.io/development/open-source-lgpl-obligations
- https://matplotlib.org/stable/project/license.html

Before distribution, provide prominent Qt/PySide usage and copyright notices,
the applicable license texts, and an appropriate corresponding-library-source
delivery/access mechanism for the exact binaries and any patches. Record exact
source archives, hashes, build options and source availability duration; generic
links to a moving upstream branch are not a completed source offer.

The onedir layout keeps Qt DLLs and binding extensions external. Customers must
be permitted to replace them with interface-compatible modified versions. Do not
add a runtime hash/signature lock or an EULA that prohibits reverse engineering
for debugging LGPL-library modifications. Matching Qt, PySide, Shiboken, Python
ABI, architecture and plugin versions matter. Document replacement in a copy of
the installation, with no changes to project data, and supply installation
information where required. Static inspection is not proof of compliance:
actually running with a modified compatible Qt library remains untested.

## Open release obligations

1. Complete the candidate build and isolated EXE acceptance tests.
2. Review every retained native binary and its exact third-party notices/source.
3. Supply the version-specific library source/access package and replacement
   instructions; test the chosen shared-library mechanism.
4. Review customer contract/EULA terms and decide the application source license.
5. Recheck clean-machine installation, native dialogs and physical Windows DPI.

No claim is made that commercial distribution is fully cleared.

## Safe future build

Use a NEW directory with at least 2 GiB free space:

```powershell
.venv\Scripts\python.exe scripts/build_chart_candidate.py --output <new-absolute-directory> --iscc <ISCC.exe>
```

The helper refuses an existing target and does not modify the historical Setup.
It audits the actual binaries before finalization/installer compilation. A
successful build is not a substitute for the frozen EXE regression checks.

## RC1 actual inventory audit — 2026-11-01

The collected package contains Qt 6.12.0 Core, Gui, Widgets, Network, OpenGL and Svg DLLs, plus PySide6/Shiboken bindings. Charts, Virtual Keyboard, QML, Quick and PDF native files and frozen Python modules are absent. Normal and delay-loaded Qt PE dependencies resolve. The DLL/PYD inventory contains 145 entries. This is a component exclusion result, not complete legal clearance.

The installed PySide6/Essentials/Addons/Shiboken metadata declares LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only, but the wheel license-file entries only provide LicenseRef-Qt-Commercial.txt. That file does not grant a commercial license. The separately included LGPLv3/GPLv3 texts do not establish wheel provenance, complete notices, or source availability. Reconcile these metadata/notice gaps against exact upstream distribution sources before release.

Also audit opengl32sw.dll and Qt image codecs, OpenSSL 3.0.15, libffi, SQLite 3.45.3, Python 3.12.9, OpenBLAS, Microsoft runtime redistribution terms, Matplotlib FreeType and fonts. Available dependency notices have been collected; per-binary third-party mappings and exact corresponding Qt/PySide/Shiboken sources remain incomplete.

### Shared-library replacement procedure to validate

1. Close the application and make a separate copy of the complete program folder. Preserve the original program and all user data.
2. Build the exact Qt/PySide/Shiboken sources with compatible x64 architecture, Python 3.12 ABI, Qt interfaces, compiler runtime and plugin configuration; record patches and build instructions.
3. In the test copy, replace the matching libraries under _internal/PySide6 and _internal/shiboken6, including compatible plugins/bindings where needed. Do not replace only an incompatible member of the set.
4. Launch with an absolute, new RDS_DATA_HOME. Exercise the packaged worker, reports, export and backup/restore. The manifest is a QA inventory, not intended as a runtime hash lock.
5. Document and supply necessary installation information and source-access instructions. Verify customer terms permit library modification and reverse engineering for debugging those modifications.

No modified-library build/run has been performed in this verification. An external DLL layout alone does not prove LGPL section 4(d)(1) compliance. LGPL does not automatically require publishing proprietary application source when a compliant shared-library route is used.

References checked: https://www.qt.io/development/open-source-lgpl-obligations ; https://doc.qt.io/qt-6/licensing.html ; https://matplotlib.org/stable/project/license.html ; included LGPLv3 section 4.
