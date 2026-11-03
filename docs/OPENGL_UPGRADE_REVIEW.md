# Upgrade-only OpenGL files — 2026-11-02

The old V2.5 upgrade retains these three files under `_internal/PySide6`:

| File | Role | Source / license route |
| --- | --- | --- |
| Qt6OpenGLWidgets.dll | Native QOpenGLWidget module | Qt Base 6.12.0; LGPLv3 route |
| QtOpenGL.pyd | Python binding for Qt OpenGL | pyside-setup 6.12.0; LGPLv3 route |
| QtOpenGLWidgets.pyd | Python binding for Qt OpenGL Widgets | pyside-setup 6.12.0; LGPLv3 route |

All three hashes match the official PySide6 Essentials 6.12.0 Windows x64 wheel.
Their hashes are recorded in upgrade-retained-native.json and the closure report.
The official Qt OpenGL documentation lists an LGPLv3 option; the corresponding
PySide wheel declares LGPLv3/GPL alternatives. No commercial license is assumed.

## Are they used or needed?

They are absent from the clean new package, which already passed acceptance.
Application-source searches and the frozen Python module inventory contain no
QtOpenGL/QtOpenGLWidgets imports. None of the new package's normal or delay-loaded
PE imports references these three names. Thus the current tested application
does not require them. This is static evidence plus existing clean-package
acceptance, not a new exhaustive trace of every possible runtime configuration.

Do not confuse these files with **Qt6OpenGL.dll**, which remains in the new
payload, or **opengl32sw.dll**, the separate Mesa software rasterizer. Neither
is one of the three upgrade-only leftovers.

## Distribution consequence

No GPL-only component or demonstrated runtime failure was identified in these
three files. They still need their applicable notices/source treatment while
present; lack of use does not erase obligations. The supplied Qt Base and
pyside-setup archives cover their upstream source modules. The same unresolved
exact upstream build/configuration issues apply as to the main Qt set.

No installer deletion rule was added, no old package was removed and no Setup
rebuild was made for these harmless-looking leftovers. Removing them is not
necessary to resolve a demonstrated license-family problem. General provenance,
source and customer-rights review remains applicable.

References:
- https://doc.qt.io/qt-6/qtopengl-index.html#licenses-and-trademarks
- https://pypi.org/project/PySide6-Essentials/6.12.0/
- official-provenance.json, upgrade-retained-native.json, package-audit.json.
