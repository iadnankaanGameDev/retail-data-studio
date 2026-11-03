# Qt library replacement — Retail Data Studio V2.5 MPL

These instructions apply to the accepted 2026-11-01 onedir Windows x64 package.
They are technical instructions, not a claim that a modified Qt build has already
been tested. No application architecture or packaging changes were necessary.

## Findings

- Qt reports 6.12.0, x86_64, shared/dynamic, release, MSVC 2022. Python is 3.12.9;
  the official binding wheel tag is cp310-abi3-win_amd64. PySide6 and Shiboken are
  6.12.0. Do not mistake the stable-ABI tag for a requirement to use Python 3.10.
- DLLs/plugins and binding extensions are external under `_internal/PySide6`
  and `_internal/shiboken6`; PyInstaller does not bundle them into a single EXE.
- The build/finalizer manifest is an inventory. Source inspection found no
  application startup enforcement of its hashes, vendor signature lock or
  automatic repair that prevents replacing these library files. SHA-256 checks
  in project_backup.py protect project backups, not Qt libraries.
- Normal and delay-loaded PE imports were inspected. Application source and the
  frozen module inventory do not reference QtOpenGL or QtOpenGLWidgets Python
  modules. None of the new payload's PE imports require Qt6OpenGLWidgets.dll.
- LGPLv3 section 4(d)(1) requires operation with an interface-compatible modified
  library. Static inspection supports this route but does not prove every
  replacement will work. A patched-library run remains unperformed.

## Rebuild and replace in a separate copy

1. Close the application and its worker. Copy the complete installed program
   directory into a new folder such as `C:\RDS-Library-Test\program`. Keep the
   original installation, Setup and user projects intact. Save original hashes.
2. Use the supplied 6.12.0 source archives and SOURCE_ACCESS.md. Build shared
   release x64 Qt with a compatible MSVC toolchain/runtime. Preserve required
   Core, Gui, Widgets, Network, OpenGL, Svg, image-format and platform-plugin
   interfaces. Keep the existing exports and compatible build configuration;
   do not replace a release DLL with a debug DLL. Record the toolchain, CMake
   cache, patches and commands. The publisher's exact upstream wheel CMake cache
   has not been recovered; do not label these as a reproduced upstream build.
3. For changes to bindings, build PySide6 and Shiboken together from the supplied
   pyside-setup source against that Qt build, with Python 3.12 x64 and compatible
   stable ABI. Follow the official build instructions below. Rebuild dependent
   plugins/bindings when an internal/private ABI change requires it. Never mix
   Qt major versions or architectures. Exact 6.12.0 is the baseline; a later
   compatible version needs its own verification.
4. In the test copy only, replace the corresponding files under
   `_internal\PySide6` and `_internal\shiboken6`. Preserve plugin subfolders,
   including `plugins\platforms\qwindows.dll`. Do not copy an entire unreviewed
   Addons wheel: it would reintroduce unrelated modules and license obligations.
5. In PowerShell, select a NEW synthetic data directory and launch:

   ```powershell
   $env:RDS_DATA_HOME = 'C:\RDS-Library-Test\synthetic-data'
   & 'C:\RDS-Library-Test\program\RetailDataStudio.exe'
   ```

   Use synthetic examples only. Check CSV import, reports/CSV export, worker,
   backup/restore and reopen. Capture loaded-module paths and hashes to establish
   that the modified libraries, not system/original DLLs, were loaded. Record
   the modification, resulting library hashes, outputs and failures.
6. Do not run Setup over the test copy: reinstall/upgrade legitimately replaces
   installed files. Keep the replacement build and instructions separately.
   Remove the test-session variable with `Remove-Item Env:RDS_DATA_HOME` after
   closing the test app; never redirect production projects into this test.

No code signing key, activation secret or application rebuild is required by the
observed loader layout. Antivirus/organizational policy can impose independent
execution restrictions; those were not evaluated as product-imposed restrictions.

## Customer terms — owner/legal review required

Proposed clarification (not an executed EULA): "Nothing in the application terms
restricts rights granted by applicable third-party licenses, including modifying
LGPL-covered libraries and reverse engineering for debugging such modifications."

The owner must reconcile all actual customer terms and the distribution channel
with those rights. Whether Installation Information is legally required under
LGPLv3 4(e)/GPLv3 6 depends on the actual distribution facts; these technical
instructions do not independently settle that legal question.

References:
- https://doc.qt.io/qtforpython-6/building_from_source/index.html
- https://doc.qt.io/qt-6/windows-building.html
- https://www.qt.io/development/open-source-lgpl-obligations
- Supplied LGPL-3.0-only.txt section 4 and GPL-3.0-only.txt section 6.
