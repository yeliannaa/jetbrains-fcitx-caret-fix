#!/usr/bin/env bash
# Build only this project's two payloads; never patch an IDE during a build.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
for tool in gcc realpath uname; do
    command -v "$tool" >/dev/null || { echo "Missing build tool: $tool" >&2; exit 1; }
done
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo 'Build target: Linux x86_64' >&2; exit 1; }
if [[ -n ${CARET_BUILD_JDK:-} ]]; then
    build_jdk=$(realpath -- "$CARET_BUILD_JDK")
else
    command -v javac >/dev/null || { echo 'Set CARET_BUILD_JDK to a JDK 11+ directory' >&2; exit 1; }
    build_jdk=$(dirname -- "$(dirname -- "$(realpath -- "$(command -v javac)")")")
fi
[[ -x "$build_jdk/bin/javac" && -x "$build_jdk/bin/jar" && -r "$build_jdk/include/jni.h" ]] || {
    echo 'JDK compiler, jar and JNI headers are required' >&2; exit 1;
}
build_python=${CARET_PYTHON:-python3}
command -v "$build_python" >/dev/null || { echo 'Python 3.8+ is required for build manifests' >&2; exit 1; }
mkdir -p build payload
stage=$(mktemp -d build/stage.XXXXXX)
trap 'rm -rf -- "$stage"' EXIT
mkdir "$stage/classes"
"$build_jdk/bin/javac" --release 11 -d "$stage/classes" src/CaretAgent.java
"$build_jdk/bin/jar" cfm "$stage/caret-agent.jar" src/MANIFEST.MF -C "$stage/classes" local
gcc -shared -fPIC -O2 -Wall -Wextra -Werror \
    -I"$build_jdk/include" -I"$build_jdk/include/linux" \
    src/caret_bridge.c -lX11 -ldl -o "$stage/libcaret_bridge.so"
{
    printf 'Project: jetbrains-fcitx-caret-fix %s\n' "$(cat VERSION)"
    "$build_jdk/bin/javac" -version 2>&1
    gcc -dumpfullversion -dumpversion
    printf 'Target: Linux x86_64; Java class release: 11\n'
} > "$stage/BUILD-INFO.txt"
install -m 644 "$stage/caret-agent.jar" "$stage/libcaret_bridge.so" "$stage/BUILD-INFO.txt" payload/
"$build_python" -B tools/package_release.py manifest
printf 'Built payload/ and refreshed SHA256SUMS. No IDE was modified.\n'
