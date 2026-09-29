# jetbrains-fcitx-caret-fix

[中文说明](README.md)

Author and maintainer: [yelianna1001@gmail.com](mailto:yelianna1001@gmail.com)

A narrowly scoped workaround for an old PyCharm/XIM issue on Linux: the Sogou candidate window stays in the IDE's lower-left corner instead of following the editor caret.

**Verified target only:** PyCharm Professional 2021.1.3 (`PY-211.7628.24`), bundled JBR `11.0.11+9-b1341.60-jcef`, Linux x86_64/X11, Fcitx 4 and a specific Sogou 4.2.1 plugin. Exact native-library hashes are enforced. PyCharm 2022/JBR 17, Wayland and Fcitx 5 are not supported by this release.

The Java agent reads `InputMethodRequests` caret geometry on the EDT every 100 ms. A small JNI bridge, under the AWT lock, converts screen coordinates to the XIM focus window and updates `XNSpotLocation`. The launcher supplies a Sogou-specific -50 px Y correction. It does not read typed text, synthesize keys, change focus, or replace the candidate-window renderer.

## Install a release

Download the release ZIP and adjacent `.sha256` file, verify the checksum and extract it. From the extracted directory:

```bash
bash install.sh --ide-dir /path/to/pycharm-2021.1.3 --check
bash install.sh --ide-dir /path/to/pycharm-2021.1.3
```

Save your work, fully exit and reopen PyCharm. The script does not restart it. A nonstandard plugin location can be supplied with `--sogou-plugin /path/to/fcitx-sogoupinyin.so`; the exact hash requirement remains.

The launcher selects the IDE's bundled JBR and disables Java UI scaling. **Default editor fonts and UI size may change**, even though your settings files are untouched. Record your font and scaling settings first; explicitly choosing the previous editor font can preserve its appearance. See [troubleshooting](docs/TROUBLESHOOTING.md).

```bash
bash diagnose.sh --ide-dir /path/to/pycharm-2021.1.3
bash uninstall.sh --ide-dir /path/to/pycharm-2021.1.3
```

Backups are kept inside the target IDE directory. Uninstall restores the original launcher and retains an archive. Modified launchers/backups are not overwritten automatically. No global Java configuration, input-method configuration, skins or startup services are changed.

## Build and test

Requirements: Bash, GNU utilities, GCC, X11 development headers/libraries, JDK 11+ and Python 3.8+ (standard library only). Dependencies are not installed automatically.

```bash
bash build.sh
python3 -B -m unittest discover -s tests -v
bash package.sh
```

Set `CARET_BUILD_JDK` and `CARET_PYTHON` to use specific installed tools. `payload/`, `SHA256SUMS`, `build/` and `dist/` are generated and ignored by Git. Installers in ready-made releases need neither Python nor a compiler. Build native release binaries on an OS compatible with the oldest target; CI on a newer Ubuntu does not prove compatibility with older glibc.

Installer tests use temporary mock IDEs and commands: they never load the JNI library into a desktop IDE. See [validation evidence](VALIDATION.md), [compatibility](docs/COMPATIBILITY.md), and [porting notes](docs/PORTING.md) before adapting another version. Do not bypass the private-ABI hash guards.

[MIT license](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md). This is an independent project, not an official JetBrains, Fcitx or Sogou product.
