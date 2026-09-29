#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/common.sh"
parse_args "$@"
# Rollback deliberately does not require the old JBR, Sogou or X11 session.
# It must remain available after a runtime / input-method upgrade.
verify_package
if [[ ! -e "$STATE_DIR" ]]; then
    if grep -Eq 'caret-agent\.jar|local\.ime\.|PYCHARM_IME_FIX_BEGIN' "$LAUNCHER"; then
        fail '启动脚本含补丁但找不到本安装器的备份，不会猜测回退'
    fi
    say '未发现本安装器的补丁，无需卸载。'
    exit 0
fi
verify_state
if ((CHECK_ONLY)); then
    say "回退检查通过；未修改文件。备份：$STATE_DIR/pycharm.sh.original"
    exit 0
fi
lock_target
verify_state
original_hash=$(hash_file "$STATE_DIR/pycharm.sh.original")
LAUNCH_TEMP=$(mktemp "$IDE_DIR/bin/.pycharm-ime-restore.XXXXXX")
cp -p -- "$STATE_DIR/pycharm.sh.original" "$LAUNCH_TEMP"
sh -n "$LAUNCH_TEMP"
verify_state
mv -fT -- "$LAUNCH_TEMP" "$LAUNCHER"
LAUNCH_TEMP=''
COMMITTED=1
[[ $(hash_file "$LAUNCHER") == "$original_hash" ]] || fail '恢复后校验失败，请保留状态目录并检查'
archive="$STATE_DIR.removed-$(date +%Y%m%d-%H%M%S)-$$"
[[ ! -e "$archive" ]] || fail '归档路径已存在；启动脚本已恢复，备份保留在原状态目录'
mv -T -- "$STATE_DIR" "$archive"
say "已恢复原启动脚本。备份和补丁归档保留在：$archive"
say '请保存工作并完全退出、重新打开 PyCharm，完成回退。没有关闭当前进程。'
