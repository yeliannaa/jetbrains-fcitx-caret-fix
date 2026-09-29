"""Installer integration tests in temporary trees; no real IDE/input method.

PATH mocks simulate only the external environment and known fixture hashes.
No production check is disabled. Integrity checks use the real sha256sum.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_SHA = shutil.which('sha256sum')
AWT_SHA = 'afcdea2f93d5b1550bff25a0f0a457db92f41b3f928078ee818aa39dc4e5f2a6'
PLUGIN_SHA = '95c1e5f378baf1ac19ee46ab67492a1b762bffb9c6dfdeb8db5f634181e6d024'
LAUNCHER = r'''#!/bin/sh
# Minimal authored test fixture, not a vendor launcher.
IDE_BIN_HOME=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
IDE_HOME=$(dirname "${IDE_BIN_HOME}")
JAVA_BIN="${PYCHARM_JDK:-$IDE_HOME/jbr}/bin/java"
VM_OPTIONS='-Xmx512m'
"$JAVA_BIN" \
  ${VM_OPTIONS} \
  -cp "$IDE_HOME/lib/fixture.jar" \
  fixture.Main "$@"
'''


def write(path, content, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    path.chmod(0o755 if executable else 0o644)


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mode & 0o777)
            for p in root.rglob('*') if p.is_file()}


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='caret-installer-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.package = self.base / 'package'
        shutil.copytree(ROOT, self.package, ignore=shutil.ignore_patterns(
            '.git', 'build', 'dist', '__pycache__', '*.pyc'))
        if not (self.package / 'payload/caret-agent.jar').is_file():
            self.fail('Run build.sh before the installer tests')
        self.ide = self.base / 'IDE 空格 \' " `literal` $(echo literal)'
        write(self.ide / 'bin/pycharm.sh', LAUNCHER, True)
        write(self.ide / 'build.txt', 'PY-211.7628.24\n')
        write(self.ide / 'jbr/lib/libawt_xawt.so', 'MOCK_AWT_VERIFIED\n')
        write(self.ide / 'jbr/release', 'JAVA_VERSION="11.0.11"\n')
        write(self.ide / 'jbr/bin/java', '#!/bin/sh\nprintf "%s\\n" "$@" > "$TEST_JAVA_ARGS"\n', True)
        self.plugin = self.base / 'plugins/fcitx-sogoupinyin.so'
        write(self.plugin, 'MOCK_SOGOU_VERIFIED\n')
        self.mocks = self.base / 'mock-bin'
        # An exact fixture byte sequence receives a fixture hash. Any altered
        # byte sequence, all manifests and all backups go to the real command.
        wrapper = '''#!{python}
import os, sys
from pathlib import Path
args = sys.argv[1:]
if len(args) == 2 and args[0] == '--':
    try:
        data = Path(args[1]).read_bytes()
    except OSError:
        data = b''
    hashes = {{b'MOCK_AWT_VERIFIED\\n': {awt!r}, b'MOCK_SOGOU_VERIFIED\\n': {plugin!r}}}
    if data in hashes:
        print(hashes[data] + '  ' + args[1])
        sys.exit(0)
os.execv({real!r}, [{real!r}] + args)
'''.format(python=sys.executable, awt=AWT_SHA, plugin=PLUGIN_SHA, real=REAL_SHA)
        write(self.mocks / 'sha256sum', wrapper, True)
        write(self.mocks / 'uname', '#!/bin/sh\ncase "$1" in -s) echo Linux;; -m) echo x86_64;; *) exit 1;; esac\n', True)
        write(self.mocks / 'fcitx', '#!/bin/sh\nexit 0\n', True)
        write(self.mocks / 'ldd', '#!/bin/sh\necho "libX11.so.6 => /mock/libX11.so.6 (0x1)"\n', True)
        self.env = os.environ.copy()
        self.env.update(PATH=str(self.mocks) + os.pathsep + os.environ['PATH'],
                        XDG_SESSION_TYPE='x11', TEST_JAVA_ARGS=str(self.base / 'java-args'),
                        PYTHONDONTWRITEBYTECODE='1', CARET_PYTHON=sys.executable)
        self.original = (self.ide / 'bin/pycharm.sh').read_bytes()
        self.before = snapshot(self.ide)

    def run_script(self, script='install.sh', extra=(), ok=True):
        result = subprocess.run(['bash', str(self.package / script), '--ide-dir', str(self.ide),
                                 '--sogou-plugin', str(self.plugin)] + list(extra),
                                env=self.env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def test_check_is_read_only(self):
        self.run_script(extra=['--check'])
        self.assertEqual(snapshot(self.ide), self.before)
        self.assertFalse((self.base / 'java-args').exists())

    def test_install_and_launcher_arguments(self):
        self.run_script()
        state = self.ide / '.pycharm-ime-fix'
        self.assertEqual((state / 'pycharm.sh.original').read_bytes(), self.original)
        self.assertEqual((self.ide / 'bin/pycharm.sh').stat().st_mode & 0o777, 0o755)
        self.assertFalse((self.base / 'java-args').exists(), 'Installer must not launch IDE')
        subprocess.run(['sh', str(self.ide / 'bin/pycharm.sh'), 'argument with spaces'],
                       env=self.env, check=True, timeout=10)
        args = (self.base / 'java-args').read_text().splitlines()
        self.assertIn('-javaagent:' + str(state / 'caret-agent.jar') + '=' + str(state / 'libcaret_bridge.so'), args)
        self.assertIn('-Dlocal.ime.yOffset=-50', args)
        self.assertIn('-Dsun.java2d.uiScale.enabled=false', args)
        self.assertEqual(args[-1], 'argument with spaces')

    def test_idempotence(self):
        self.run_script()
        installed = snapshot(self.ide)
        self.run_script()
        self.run_script(extra=['--check'])
        self.assertEqual(snapshot(self.ide), installed)

    def test_restore_byte_for_byte_and_reinstall(self):
        self.run_script()
        installed = snapshot(self.ide)
        self.run_script('uninstall.sh', ['--check'])
        self.assertEqual(snapshot(self.ide), installed)
        self.run_script('uninstall.sh')
        self.assertEqual((self.ide / 'bin/pycharm.sh').read_bytes(), self.original)
        self.assertEqual((self.ide / 'bin/pycharm.sh').stat().st_mode & 0o777, 0o755)
        self.assertEqual(len(list(self.ide.glob('.pycharm-ime-fix.removed-*'))), 1)
        restored = snapshot(self.ide)
        self.run_script('uninstall.sh')
        self.assertEqual(snapshot(self.ide), restored)
        self.run_script()

    def test_uninstall_after_environment_changes(self):
        self.run_script()
        self.env['XDG_SESSION_TYPE'] = 'wayland'
        write(self.ide / 'build.txt', 'new-version\n')
        write(self.ide / 'jbr/lib/libawt_xawt.so', 'new-jbr\n')
        self.plugin.unlink()
        self.run_script('uninstall.sh')
        self.assertEqual((self.ide / 'bin/pycharm.sh').read_bytes(), self.original)

    def test_relocated_ide_and_package(self):
        self.run_script()
        new_ide = self.base / 'relocated IDE'
        self.ide.rename(new_ide)
        self.ide = new_ide
        new_package = self.base / 'relocated package'
        self.package.rename(new_package)
        self.package = new_package
        self.run_script()
        subprocess.run(['sh', str(self.ide / 'bin/pycharm.sh')], env=self.env, check=True, timeout=10)
        self.assertIn(str(self.ide / '.pycharm-ime-fix/caret-agent.jar'), (self.base / 'java-args').read_text())
        self.run_script('uninstall.sh')

    def assert_rejected_without_writes(self, text):
        before = snapshot(self.ide)
        result = self.run_script(ok=False)
        self.assertIn(text, result.stdout)
        self.assertEqual(snapshot(self.ide), before)
        self.assertFalse((self.ide / '.pycharm-ime-fix.lock').exists())

    def test_wrong_build(self):
        write(self.ide / 'build.txt', 'PY-222.1\n')
        self.assert_rejected_without_writes('2021.1.3')

    def test_wrong_awt(self):
        write(self.ide / 'jbr/lib/libawt_xawt.so', 'wrong-jbr\n')
        self.assert_rejected_without_writes('JBR 原生库')

    def test_wrong_plugin(self):
        write(self.plugin, 'wrong-plugin\n')
        self.assert_rejected_without_writes('搜狗 Fcitx 插件')

    def test_missing_plugin(self):
        self.plugin.unlink()
        self.assert_rejected_without_writes('搜狗 Fcitx 插件')

    def test_wayland(self):
        self.env['XDG_SESSION_TYPE'] = 'wayland'
        self.assert_rejected_without_writes('X11')

    def test_wrong_arch(self):
        write(self.mocks / 'uname', '#!/bin/sh\ncase "$1" in -s) echo Linux;; *) echo aarch64;; esac\n', True)
        self.assert_rejected_without_writes('x86_64')

    def test_missing_native_dependency(self):
        write(self.mocks / 'ldd', '#!/bin/sh\necho "libX11.so.6 => not found"\n', True)
        self.assert_rejected_without_writes('native 库依赖缺失')

    def test_changed_anchor(self):
        write(self.ide / 'bin/pycharm.sh', LAUNCHER.replace('  ${VM_OPTIONS} \\', '  ${VM_OPTIONS:-} \\'), True)
        self.assert_rejected_without_writes('启动脚本结构不同')

    def test_duplicate_anchor(self):
        write(self.ide / 'bin/pycharm.sh', LAUNCHER + 'IDE_HOME=$(dirname "${IDE_BIN_HOME}")\n', True)
        self.assert_rejected_without_writes('启动脚本结构不同')

    def test_existing_manual_patch(self):
        write(self.ide / 'bin/pycharm.sh', LAUNCHER + '# local.ime.yOffset=-50\n', True)
        self.assert_rejected_without_writes('已有候选框补丁')

    def test_existing_lock(self):
        lock = self.ide / '.pycharm-ime-fix.lock'
        lock.mkdir()
        before = snapshot(self.ide)
        self.assertIn('锁已存在', self.run_script(ok=False).stdout)
        self.assertTrue(lock.is_dir())
        self.assertEqual(snapshot(self.ide), before)

    def test_launcher_changed_after_install(self):
        self.run_script()
        target = self.ide / 'bin/pycharm.sh'
        target.write_bytes(target.read_bytes() + b'# user edit\n')
        before = snapshot(self.ide)
        self.run_script(ok=False)
        self.run_script('uninstall.sh', ok=False)
        self.assertEqual(snapshot(self.ide), before)

    def test_backup_changed_after_install(self):
        self.run_script()
        write(self.ide / '.pycharm-ime-fix/pycharm.sh.original', '# changed\n')
        before = snapshot(self.ide)
        self.run_script('uninstall.sh', ok=False)
        self.assertEqual(snapshot(self.ide), before)

    def test_payload_tampering(self):
        with (self.package / 'payload/caret-agent.jar').open('ab') as stream:
            stream.write(b'tampered')
        self.assert_rejected_without_writes('安装包校验失败')

    def test_symlink_launcher(self):
        launcher = self.ide / 'bin/pycharm.sh'
        other = self.base / 'outside-launcher'
        launcher.rename(other)
        launcher.symlink_to(other)
        self.assert_rejected_without_writes('必须是普通文件')
        self.assertEqual(other.read_bytes(), self.original)

    def test_equals_path(self):
        moved = self.base / 'IDE=unsupported'
        self.ide.rename(moved)
        self.ide = moved
        self.assert_rejected_without_writes('等号或换行')

    def test_diagnostic_is_read_only_and_hides_normal_path(self):
        before = snapshot(self.ide)
        result = self.run_script('diagnose.sh')
        self.assertIn('PASS', result.stdout)
        self.assertNotIn(str(self.base), result.stdout)
        self.assertEqual(snapshot(self.ide), before)

    def test_package_roundtrip_and_repeatability(self):
        command = ['bash', str(self.package / 'package.sh')]
        subprocess.run(command, env=self.env, check=True, stdout=subprocess.PIPE, timeout=30)
        archive = next((self.package / 'dist').glob('*.zip'))
        first = archive.read_bytes()
        subprocess.run(command, env=self.env, check=True, stdout=subprocess.PIPE, timeout=30)
        self.assertEqual(first, archive.read_bytes())
        self.assertTrue(archive.with_suffix('.zip.sha256').read_text().startswith(hashlib.sha256(first).hexdigest()))
        extracted = self.base / 'extracted'
        with zipfile.ZipFile(str(archive)) as source:
            self.assertFalse(any('/build/' in n or '/dist/' in n or '/.git/' in n for n in source.namelist()))
            source.extractall(extracted)
        self.package = next(extracted.iterdir())
        self.run_script(extra=['--check'])
        self.run_script()
        self.run_script('uninstall.sh')

    def test_packaging_rejects_stale_manifest(self):
        with (self.package / 'README.md').open('a') as stream:
            stream.write('\nchanged\n')
        result = subprocess.run(['bash', str(self.package / 'package.sh')], env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rebuild', result.stdout)


if __name__ == '__main__':
    unittest.main()
