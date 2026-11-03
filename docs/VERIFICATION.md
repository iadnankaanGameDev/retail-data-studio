> Historical record below. Superseded for the MPL candidate by FINALIZATION.md and FINAL_LICENSE_STATUS.md. Qt Charts is no longer shipped. Distribution remains blocked.

# Publication preparation verification

Run on Windows, 2026-10-31, from the curated source copy.

| Check | Result |
| --- | --- |
| Full source suite including public example | 76 passed, 271.42 seconds |
| Public example with original development tree access blocked | 1 passed, 20.00 seconds |
| Published source launcher with original access blocked | Passed; Qt event loop started and exited normally |
| Dependency consistency in fallback runtime (pip check) | No broken requirements found |
| Sample | 6 transactions, 14 units, 174.25 estimated revenue |
| Reimport and restore | Zero new records on repeat; restored totals match, original unchanged |
| Screenshots | Real Qt widgets and ETL output using synthetic data; local path labels normalized |
| Ignore rules | 13 cases checked with Git's actual ignore engine |
| Original source modules | Byte-identical copies |
| Fresh dependency installation | **Incomplete: disk full (Errno 28)** |

## Environment limitation
A new virtual environment was created, but pip could not install the wheels due
to insufficient disk space. Tests instead used a separate QA interpreter with
read-only use of hard-linked installed dependency files. Application imports and
subprocess entrypoints came from this publication tree. A Python audit hook
blocked filesystem access to the original development tree during the sample and
launcher checks. This verifies source isolation, not a successful fresh package
installation. Repeat the documented pip installation and full tests on a machine
with enough free disk space before claiming clean-machine acceptance.

The installer was not rebuilt or installed during publication preparation. Its
copy matched the previously audited SHA-256:
800fcbb3b7b0c5fb595254b621036615f6172317980547319f062ed47f43db8e

Physical Windows display scaling, native file-dialog acceptance and the complete
uninstall/reinstall/reopen sequence remain manual checks. The PDF was rendered
and all four pages visually inspected. License selection remains pending; see
THIRD_PARTY_NOTICES.md. No GitHub repository, push or release was created.
