# Third-party references and dependencies

The project contains its Java agent, JNI bridge, scripts, tests and documentation. It does not bundle JetBrains IDEs/JBR, OpenJDK sources, Sogou binaries, Fcitx, fonts, skins or user configuration.

## JetBrains Runtime / OpenJDK

The native bridge relies on an internal JBR layout inspected at commit `7bea9b450563`: `X11InputMethodData.current_ic` is its first member. Reference:

- [JetBrains Runtime](https://github.com/JetBrains/JetBrainsRuntime)
- [awt_InputMethod.c at the referenced commit](https://github.com/JetBrains/JetBrainsRuntime/blob/7bea9b450563/src/java.desktop/unix/native/libawt_xawt/awt/awt_InputMethod.c)

That upstream source carries Oracle copyright and GPL version 2 with the Classpath exception. It is referenced, not included in this distribution. The project's MIT license does not relicense any upstream code or runtime. If a future port incorporates upstream source, its notices and applicable license obligations must be reviewed separately.

## X11, Fcitx and Sogou

The native bridge dynamically links the host X11 library and uses XIM interfaces. The host installation provides X11 under its own license. Fcitx and Sogou are external runtime dependencies, not redistributed here. Their licenses and trademarks remain with their respective owners.

- [Xlib documentation](https://www.x.org/releases/current/doc/libX11/libX11/libX11.html)
- [Fcitx cursor-following FAQ](https://fcitx-im.org/wiki/FAQ#Cursor_Following_problem)
- [Fcitx 4 source](https://github.com/fcitx/fcitx)

## Test and build materials

The mock launcher in the tests is a minimal fixture authored for this project. It is not a bundled copy of the vendor's launcher. GitHub Actions referenced by CI are used from their own repositories and licenses; they are not included in the release archive as vendored code.
