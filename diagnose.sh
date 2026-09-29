#!/usr/bin/env bash
# Read-only, intentionally limited report suitable for an issue after review.
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/common.sh"
parse_args "$@"
say "project=$(cat "$PACKAGE_DIR/VERSION")"
say "os=$(uname -s) arch=$(uname -m) session=${XDG_SESSION_TYPE:-unset}"
if [[ -r "$IDE_DIR/build.txt" ]]; then
    say "ide_build=$(head -c 80 "$IDE_DIR/build.txt" | tr '\n\r' '  ')"
fi
if [[ -r "$IDE_DIR/jbr/release" ]]; then
    grep -E '^(JAVA_VERSION|IMPLEMENTOR|JAVA_RUNTIME_VERSION)=' "$IDE_DIR/jbr/release" || true
fi
if [[ -r "$IDE_DIR/jbr/lib/libawt_xawt.so" ]]; then
    say "awt_sha256=$(hash_file "$IDE_DIR/jbr/lib/libawt_xawt.so")"
fi
plugin_paths=(/usr/lib/x86_64-linux-gnu/fcitx/fcitx-sogoupinyin.so /usr/lib/fcitx/fcitx-sogoupinyin.so)
if [[ -n "$SOGOU_PLUGIN" ]]; then plugin_paths=("$SOGOU_PLUGIN"); fi
for plugin in "${plugin_paths[@]}"; do
    if [[ -r "$plugin" ]]; then say "sogou_plugin_sha256=$(hash_file "$plugin")"; fi
done
if command -v fcitx >/dev/null; then say 'fcitx_command=present'; else say 'fcitx_command=missing'; fi
if [[ -d "$STATE_DIR" ]]; then say 'installer_state=present'; else say 'installer_state=absent'; fi
say 'compatibility_check:'
# Hide the install path in normal diagnostic output. Error text remains visible.
verify_package
verify_environment
if [[ -e "$STATE_DIR" ]]; then verify_state; else verify_clean_launcher; fi
say 'PASS (read-only; no GUI or live Java process was tested)'
