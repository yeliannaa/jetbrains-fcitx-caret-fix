#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/common.sh"
parse_args "$@"
verify_package
verify_environment
if [[ -e "$STATE_DIR" ]]; then
    verify_state
    say "已安装且校验正常，无需重复安装：$IDE_DIR"
    exit 0
fi
verify_clean_launcher
say "兼容检查通过：$IDE_DIR"
if ((CHECK_ONLY)); then
    say '仅检查：没有修改文件。安装后仍需保存工作并完全退出、重新打开 PyCharm。'
    exit 0
fi

lock_target
[[ ! -e "$STATE_DIR" ]] || fail '检查后补丁目录发生变化，请重新检查'
verify_clean_launcher
original_hash=$(hash_file "$LAUNCHER")
STAGE_DIR=$(mktemp -d "$IDE_DIR/.pycharm-ime-fix.stage.XXXXXX")
chmod 755 "$STAGE_DIR"
cp -p -- "$LAUNCHER" "$STAGE_DIR/pycharm.sh.original"
cp -- "$PACKAGE_DIR/payload/caret-agent.jar" "$PACKAGE_DIR/payload/libcaret_bridge.so" "$STAGE_DIR/"
chmod 644 "$STAGE_DIR/caret-agent.jar" "$STAGE_DIR/libcaret_bridge.so"
awk -f "$PACKAGE_DIR/patch-launcher.awk" "$LAUNCHER" > "$STAGE_DIR/pycharm.sh.patched"
chmod --reference="$LAUNCHER" "$STAGE_DIR/pycharm.sh.patched"
sh -n "$STAGE_DIR/pycharm.sh.patched"
printf '%s\n' "$PATCH_VERSION" > "$STAGE_DIR/VERSION"
date -Iseconds > "$STAGE_DIR/installed-at.txt"
(
    cd -- "$STAGE_DIR"
    sha256sum VERSION installed-at.txt caret-agent.jar libcaret_bridge.so pycharm.sh.original pycharm.sh.patched > SHA256SUMS
    sha256sum -c --status SHA256SUMS
)
LAUNCH_TEMP=$(mktemp "$IDE_DIR/bin/.pycharm-ime-launcher.XXXXXX")
cp -p -- "$STAGE_DIR/pycharm.sh.patched" "$LAUNCH_TEMP"
[[ $(hash_file "$LAUNCHER") == "$original_hash" ]] || fail '准备安装时启动脚本发生变化，已停止'
mv -T -- "$STAGE_DIR" "$STATE_DIR"
STAGE_DIR=''
STATE_CREATED=1
mv -fT -- "$LAUNCH_TEMP" "$LAUNCHER"
LAUNCH_TEMP=''
COMMITTED=1
verify_state
say "安装完成；备份：$STATE_DIR/pycharm.sh.original"
say '请保存工作，完全退出 PyCharm 后重新打开。当前进程未被关闭，皮肤和输入法自启未被修改。'
