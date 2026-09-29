#!/usr/bin/env python3
"""Explicit release allowlist, integrity manifest, deterministic ZIP container.

Standard library only. No Git access, installation, network, or IDE operations.
ZIP bytes are stable for the same input files; compiler output may differ.
"""
import hashlib
import re
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    'README.md', 'README.en.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
    'VERSION', 'CHANGELOG.md', 'CONTRIBUTING.md', 'VALIDATION.md',
    '.gitignore', '.gitattributes', 'build.sh', 'package.sh', 'common.sh',
    'install.sh', 'uninstall.sh', 'diagnose.sh', 'patch-launcher.awk',
)
TREE_FILES = (
    'src/CaretAgent.java', 'src/caret_bridge.c', 'src/MANIFEST.MF',
    'tools/package_release.py', 'tests/test_installer.py', 'tests/test_agent_startup.py',
    'docs/COMPATIBILITY.md', 'docs/PORTING.md', 'docs/TROUBLESHOOTING.md',
    'docs/TESTING.md', 'docs/RELEASING.md',
    '.github/workflows/ci.yml', '.github/ISSUE_TEMPLATE/bug_report.yml',
    'payload/caret-agent.jar', 'payload/libcaret_bridge.so', 'payload/BUILD-INFO.txt',
)


def files():
    paths = sorted(ROOT_FILES + TREE_FILES)
    for name in paths:
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('Missing file or symlink in release: ' + name)
    return paths


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def manifest(paths):
    return ''.join(checksum((ROOT / p).read_bytes()) + '  ' + p + '\n'
                   for p in paths).encode('utf-8')


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('manifest', 'package'):
        raise ValueError('Usage: package_release.py manifest|package')
    paths = files()
    sums = manifest(paths)
    if sys.argv[1] == 'manifest':
        (ROOT / 'SHA256SUMS').write_bytes(sums)
        return
    if (ROOT / 'SHA256SUMS').read_bytes() != sums:
        raise ValueError('Files changed since build; rebuild before packaging')
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z0-9.]+)?', version):
        raise ValueError('Invalid VERSION')
    prefix = 'jetbrains-fcitx-caret-fix-' + version
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    target = out / (prefix + '-linux-x86_64.zip')
    with zipfile.ZipFile(str(target), 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in paths + ['SHA256SUMS']:
            item = zipfile.ZipInfo(prefix + '/' + name, (2026, 1, 1, 0, 0, 0))
            item.create_system = 3
            item.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if name.endswith('.sh') else 0o644
            item.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(item, (ROOT / name).read_bytes())
    (out / (target.name + '.sha256')).write_text(
        checksum(target.read_bytes()) + '  ' + target.name + '\n', encoding='utf-8')
    print('Created ' + str(target.relative_to(ROOT)))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(str(error))
