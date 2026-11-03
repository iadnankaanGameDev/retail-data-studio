> Historical record below. Superseded for the MPL candidate by FINALIZATION.md and FINAL_LICENSE_STATUS.md. Qt Charts is no longer shipped. Distribution remains blocked.

# Third-party notices and owner licensing decision
Reviewed 2026-10-31. This is an inventory and release checklist, not a license grant.
The source repository deliberately has no LICENSE file until the owner chooses.

| Component | Terms to review / action |
| --- | --- |
| Python | PSF license and bundled third-party notices; preserve notices |
| PySide6 / Shiboken / Qt | Community LGPLv3/GPLv3 or commercial terms; inspect each used module |
| Qt Charts (used in reports_view.py) | **GPLv3 or commercial**, not an assumed LGPL-only dependency |
| pandas, NumPy | BSD-style notices plus licenses of bundled components |
| python-dateutil | Dual Apache-2.0/BSD-3-Clause terms; preserve applicable notices |
| six | MIT notice |
| tzdata | Apache-2.0 package; upstream IANA data notices |
| pytest | MIT, development only |
| PyInstaller | GPL with bundling exception; inspect applicable bootloader exception |
| Inno Setup | Separate compiler license; preserve required notices, check current commercial terms |

The existing customer payload includes licenses/ and THIRD_PARTY_NOTICES.txt.
Their presence alone is not proof of full redistribution compliance. Check exact
wheel contents, transitive dependencies and bundled native libraries. Include
corresponding source/offers and replacement/relinking information where required;
do not impose terms that remove rights granted by relevant dependencies.

## Options for the owner (none selected)
1. GPLv3-compatible open-source distribution, with the complete corresponding
   source/build information and dependency obligations addressed.
2. Proprietary distribution with appropriate commercial Qt/Qt Charts rights;
   verify entitlement for this specific already-built package and development.
3. A future alternative chart implementation followed by a fresh license review.
   That is not performed here and does not clear the current installer.

MIT/BSD for owner-written files alone does not remove Qt Charts obligations.
Do not describe this repository or installer as commercially cleared until the
chosen route has been checked. No commercial license entitlement was provided.

Primary references:
- https://doc.qt.io/qt-6/qtcharts-index.html#licenses
- https://doc.qt.io/qtforpython-6/commercial/index.html
- https://www.qt.io/development/open-source-lgpl-obligations
- https://pyinstaller.org/en/stable/license.html
- https://jrsoftware.org/isinfo.php

No external retail dataset was copied. Example values are newly authored synthetic
fixtures. Screenshots show only that synthetic data, with local paths normalized.
