#!/usr/bin/env bash
# Shared by install.sh / uninstall.sh. No Python or compiler is required.
set -euo pipefail
umask 022

PACKAGE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PATCH_VERSION='pycharm-2021.1.3-fcitx-ime-v1'
AWT_SHA='afcdea2f93d5b1550bff25a0f0a457db92f41b3f928078ee818aa39dc4e5f2a6'
SOGOU_SHA='95c1e5f378baf1ac19ee46ab67492a1b762bffb9c6dfdeb8db5f634181e6d024'
IDE_DIR=''
SOGOU_PLUGIN=''
CHECK_ONLY=0
LOCK_DIR=''
STAGE_DIR=''
LAUNCH_TEMP=''
STATE_CREATED=0
COMMITTED=0

fail() { printf '错误：%s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }
hash_file() { sha256sum -- "$1" | awk '{print $1}'; }

usage() {
    printf '用法：bash %s [--ide-dir /路径/pycharm-2021.1.3] [--check]\n' "${0##*/}"
    say '--check 只检查，不写文件、不启动或重启软件。'
    say '--sogou-plugin /路径/fcitx-sogoupinyin.so 指定插件位置；仍要求完整 SHA-256 匹配。'
    say '不指定目录时，只查找 ~/software/pycharm-2021.1.3、~/pycharm-2021.1.3 和 /opt/pycharm-2021.1.3。'
}

parse_args() {
    while (($#)); do
        case "$1" in
            --ide-dir) (($# >= 2)) || fail '--ide-dir 缺少路径'; IDE_DIR=$2; shift 2 ;;
            --sogou-plugin) (($# >= 2)) || fail '--sogou-plugin 缺少路径'; [[ -n "$2" ]] || fail '插件路径不能为空'; SOGOU_PLUGIN=$2; shift 2 ;;
            --check) CHECK_ONLY=1; shift ;;
            -h|--help) usage; exit 0 ;;
            *) fail "未知参数：$1；使用 --help 查看用法" ;;
        esac
    done
    local tool candidate resolved
    for tool in realpath sha256sum awk grep mktemp cp mv chmod stat uname date; do
        command -v "$tool" >/dev/null || fail "缺少系统命令：$tool；脚本不会自动安装依赖"
    done
    if [[ -z "$IDE_DIR" ]]; then
        local -a candidates=()
        for candidate in "$HOME/software/pycharm-2021.1.3" "$HOME/pycharm-2021.1.3" /opt/pycharm-2021.1.3; do
            [[ -f "$candidate/bin/pycharm.sh" ]] || continue
            resolved=$(realpath -- "$candidate")
            [[ " ${candidates[*]-} " == *" $resolved "* ]] || candidates+=("$resolved")
        done
        ((${#candidates[@]} == 1)) || fail '无法唯一定位 PyCharm，请用 --ide-dir 指定安装目录'
        IDE_DIR=${candidates[0]}
    fi
    [[ -d "$IDE_DIR" ]] || fail "目录不存在：$IDE_DIR"
    IDE_DIR=$(realpath -- "$IDE_DIR")
    # Java's -javaagent syntax uses '=' as the jar/options separator.
    [[ "$IDE_DIR" != *'='* && "$IDE_DIR" != *$'\n'* && "$IDE_DIR" != *$'\r'* ]] || fail '安装路径不能包含等号或换行'
    LAUNCHER="$IDE_DIR/bin/pycharm.sh"
    STATE_DIR="$IDE_DIR/.pycharm-ime-fix"
    [[ -f "$LAUNCHER" && ! -L "$LAUNCHER" ]] || fail 'bin/pycharm.sh 必须是普通文件'
}

verify_package() {
    [[ -r "$PACKAGE_DIR/SHA256SUMS" ]] || fail '缺少包校验清单，请重新解压完整安装包'
    (cd -- "$PACKAGE_DIR" && sha256sum -c --status SHA256SUMS) || fail '安装包校验失败，请重新复制完整安装包'
}

verify_environment() {
    [[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || fail '仅支持 Linux x86_64'
    [[ -r "$IDE_DIR/build.txt" && $(cat -- "$IDE_DIR/build.txt") == PY-211.7628.24 ]] || fail '只验证了 PyCharm Professional 2021.1.3（PY-211.7628.24），当前版本不匹配'
    [[ -x "$IDE_DIR/jbr/bin/java" && -r "$IDE_DIR/jbr/lib/libawt_xawt.so" ]] || fail '缺少该版本自带的 JBR，请勿改用任意系统 JDK'
    [[ $(hash_file "$IDE_DIR/jbr/lib/libawt_xawt.so") == "$AWT_SHA" ]] || fail 'JBR 原生库校验不匹配；为避免不兼容，未安装'
    [[ ${XDG_SESSION_TYPE:-} == x11 ]] || fail '请在目标设备的 X11 桌面终端执行（当前不是已确认的 X11 会话）'
    command -v fcitx >/dev/null || fail '未找到 Fcitx 4；本包不安装或切换输入法'
    local candidate matched=0 dependencies
    local -a plugin_candidates=(/usr/lib/x86_64-linux-gnu/fcitx/fcitx-sogoupinyin.so /usr/lib/fcitx/fcitx-sogoupinyin.so)
    if [[ -n "$SOGOU_PLUGIN" ]]; then plugin_candidates=("$SOGOU_PLUGIN"); fi
    for candidate in "${plugin_candidates[@]}"; do
        [[ -r "$candidate" ]] || continue
        if [[ $(hash_file "$candidate") == "$SOGOU_SHA" ]]; then
            matched=1
            break
        fi
    done
    ((matched)) || fail '搜狗 Fcitx 插件与验证版本不匹配；不能直接套用 50 像素补偿'
    command -v ldd >/dev/null || fail '缺少 ldd，无法检查 native 库依赖'
    dependencies=$(LC_ALL=C ldd "$PACKAGE_DIR/payload/libcaret_bridge.so" 2>&1) || fail '无法解析 native 库依赖'
    [[ "$dependencies" != *'not found'* ]] || fail "native 库依赖缺失：$dependencies"
}

verify_state() {
    [[ -d "$STATE_DIR" && ! -L "$STATE_DIR" ]] || fail '补丁状态目录缺失或异常'
    [[ -f "$STATE_DIR/VERSION" && $(cat -- "$STATE_DIR/VERSION") == "$PATCH_VERSION" ]] || fail '状态目录不是本版本安装器创建的，停止覆盖'
    (cd -- "$STATE_DIR" && sha256sum -c --status SHA256SUMS) || fail '备份或补丁文件发生变化，停止自动操作'
    [[ $(hash_file "$LAUNCHER") == $(hash_file "$STATE_DIR/pycharm.sh.patched") ]] || fail '安装后启动脚本又被修改，停止覆盖；请人工比较备份'
}

verify_clean_launcher() {
    if grep -Eq 'caret-agent\.jar|local\.ime\.|PYCHARM_IME_FIX_BEGIN' "$LAUNCHER"; then
        fail '启动脚本已有候选框补丁。此设备无需重复套用；如需迁移旧补丁，请先恢复其原始启动脚本'
    fi
    [[ $(grep -Fxc 'IDE_HOME=$(dirname "${IDE_BIN_HOME}")' "$LAUNCHER") == 1 ]] || fail '启动脚本结构不同，无法定位 IDE_HOME，未修改'
    [[ $(grep -Fxc '  ${VM_OPTIONS} \' "$LAUNCHER") == 1 ]] || fail '启动脚本结构不同，无法定位 JVM 参数，未修改'
    [[ $(grep -Fxc '"$JAVA_BIN" \' "$LAUNCHER") == 1 ]] || fail '启动脚本结构不同，无法定位 Java 启动入口，未修改'
    sh -n "$LAUNCHER" || fail '原启动脚本语法异常'
}

cleanup() {
    [[ -z "$LAUNCH_TEMP" || ! -e "$LAUNCH_TEMP" ]] || rm -f -- "$LAUNCH_TEMP"
    [[ -z "$STAGE_DIR" || ! -d "$STAGE_DIR" ]] || rm -rf -- "$STAGE_DIR"
    # Only a newly created, uncommitted state may be removed on failure.
    if ((STATE_CREATED && ! COMMITTED)); then
        if [[ -f "$STATE_DIR/pycharm.sh.patched" && $(hash_file "$LAUNCHER") == $(hash_file "$STATE_DIR/pycharm.sh.patched") ]]; then
            : # Launcher was already replaced; retain its recovery data.
        else
            rm -rf -- "$STATE_DIR"
        fi
    fi
    [[ -z "$LOCK_DIR" ]] || rmdir -- "$LOCK_DIR" 2>/dev/null || true
}

lock_target() {
    [[ -w "$IDE_DIR" && -w "$IDE_DIR/bin" ]] || fail "安装目录不可写：$IDE_DIR；请使用有权限的账号处理该安装目录"
    local requested="$IDE_DIR/.pycharm-ime-fix.lock"
    mkdir -- "$requested" 2>/dev/null || fail "安装/卸载锁已存在：$requested；确认没有其他安装进程后再处理"
    LOCK_DIR=$requested
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
}
