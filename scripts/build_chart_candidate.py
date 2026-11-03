"""Build only into a new candidate directory; never overwrite an older release."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from package_policy import audit_folder

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True,
                        help='New, non-existing candidate root; may be on another drive')
    parser.add_argument('--iscc', type=Path, help='Optional Inno Setup compiler')
    args = parser.parse_args()
    target = args.output.resolve()
    if target.exists():
        raise SystemExit('Refusing to reuse an existing candidate folder')
    ancestor = target.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    if shutil.disk_usage(ancestor).free < 2 * 1024**3:
        raise SystemExit('Build blocked: at least 2 GiB free space is required; no old files were deleted')
    target.mkdir(parents=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--distpath', str(target/'dist'),
                    '--workpath', str(target/'work'), str(ROOT/'RetailDataStudio.spec')],
                   cwd=ROOT, check=True)
    bundle = target/'dist/RetailDataStudio'
    natives = audit_folder(bundle)
    (target/'native-inventory.json').write_text(json.dumps(natives,indent=2))
    subprocess.run([sys.executable, str(ROOT/'scripts/finalize_portable.py'), '--target', str(bundle)],
                   cwd=ROOT, check=True)
    if args.iscc:
        subprocess.run([str(args.iscc), '/DBundleDir='+str(bundle),
                        '/DReleaseDir='+str(target/'installer'), str(ROOT/'installer/RetailDataStudio.iss')],
                       cwd=ROOT, check=True)
    print(f'Candidate built at {target}; EXE acceptance and license clearance still required.')


if __name__ == '__main__':
    main()
