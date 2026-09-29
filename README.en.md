# PyCharm / JetBrains IME candidate window not following the cursor

`jetbrains-fcitx-caret-fix` · Linux / X11 / Fcitx / Sogou

[中文说明](README.md)

Author and maintainer: [yelianna1001@gmail.com](mailto:yelianna1001@gmail.com)

**Typical symptom:** on Ubuntu/Linux, the Chinese IME candidate popup stays in the bottom-left corner of PyCharm instead of following the text cursor (caret), while input works normally in other applications. This project documents the diagnosis and fix, with source and a workflow for adapting it to other versions.

A **reusable diagnostic and coordinate-update approach**, reference implementation and reversible installer for caret-following problems in JetBrains IDEs on Linux X11 with Fcitx/Sogou. It traces the path from editor caret geometry through coordinate conversion to input-method position updates when the candidate window remains in the IDE's lower-left corner.

**The approach can be ported across versions.** This repository provides a PyCharm 2021.1.3 + JBR 11 reference implementation. The maintainer also reports successfully adapting it to **PyCharm 2022 + JBR 17** by asking an AI coding assistant to use the migration package as a reference and adapt it to that machine.

Developers and AI coding assistants can reuse the source and workflow for similar problems in other environments. See the [adaptation records](docs/COMPATIBILITY.md) for the available evidence and ready-made package targets.

## Reuse on another version

Provide this repository or migration package together with these instructions, translated from the prompt used for the reported adaptation:

> Adapt Sogou candidate-window caret following for this machine's PyCharm 2022 + JBR 17, using this migration package as a reference. Inspect the actual running versions, input method and display environment, then reproduce the problem. Verify Java interfaces and native structures; modify and recompile the source if necessary, without bypassing version or hash checks. Re-evaluate whether the 50-pixel correction is needed, and test Chinese input, deletion, search fields, the terminal, multiple monitors and scaling. Validate in isolation before applying the change, keeping backups and rollback support.

Replace the target versions for another environment. The diagnostic approach, implementation structure, isolated validation and rollback workflow are reusable; interfaces, native layouts, coordinate transforms and offsets are checked for each target. See the [porting guide](docs/PORTING.md).

## Reference implementation

The Java agent reads `InputMethodRequests` caret geometry on the EDT every 100 ms. A small JNI bridge, under the AWT lock, converts screen coordinates to the XIM focus window and updates `XNSpotLocation`. The launcher supplies a Sogou-specific -50 px Y correction. It does not read typed text, synthesize keys, change focus, or replace the candidate-window renderer.

## Install the ready-made v0.1.1 package

v0.1.1 fixes Commit-list checkboxes ignoring mouse clicks while Space still works in affected environments. The agent now waits for the IDE to initialize its event thread. The original user confirmed mouse selection still works after fully restarting PyCharm. See the [changelog](CHANGELOG.md).

To upgrade from v0.1.0, uninstall with the old package, install the new one, then restart the IDE. Re-running the installer does not replace an existing payload.

This package targets PyCharm Professional 2021.1.3 (`PY-211.7628.24`), bundled JBR `11.0.11+9-b1341.60-jcef`, Linux x86_64/X11, Fcitx 4 and a specific Sogou 4.2.1 plugin. Exact native-library hashes are enforced. Use the adaptation workflow above to build for other environments.

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

Installer tests use temporary mock IDEs and commands: they never load the JNI library into a desktop IDE. See [validation evidence](VALIDATION.md), [adaptation records](docs/COMPATIBILITY.md), and [porting notes](docs/PORTING.md) for the workflow and target checks. Contributions with new adaptation results, code changes and validation records are welcome.

## Frequently asked questions

### Can I keep my current PyCharm version?

The original case kept PyCharm 2021.1.3 and used its bundled JBR, loading a Java agent and JNI bridge to update XIM candidate geometry. The maintainer also reports a successful PyCharm 2022/JBR 17 adaptation using the same workflow. See the [adaptation records](docs/COMPATIBILITY.md).

### How does this compare with JetBrainsRuntime-for-Linux-x64?

[RikudouPatrickstar/JetBrainsRuntime-for-Linux-x64](https://github.com/RikudouPatrickstar/JetBrainsRuntime-for-Linux-x64) addresses the related Fcitx caret-following problem by distributing patched JBR builds. Its documented installation replaces the IDE's JBR directory.

This project instead provides an agent/JNI reference implementation that reads editor caret geometry and updates the XIM position within the IDE process. Its installer selects the IDE's existing bundled JBR, adds launch parameters and preserves a rollback copy of the launcher. Selecting that JBR can still affect fonts or scaling if another JDK was previously used.

Both are approaches to the Linux IME positioning problem. Select and validate an implementation for the target runtime and input backend. For historical context, see [JetBrainsRuntime issue #32](https://github.com/JetBrains/JetBrainsRuntime/issues/32).

### How can an AI coding assistant adapt this to another environment?

Provide the repository or migration package with the prompt above. Have it inspect the actual environment, reproduce the issue, check interfaces and validate changes in isolation. Follow the [porting guide](docs/PORTING.md), then contribute the resulting versions, changes and validation evidence.

[MIT license](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md). This is an independent project, not an official JetBrains, Fcitx or Sogou product.
