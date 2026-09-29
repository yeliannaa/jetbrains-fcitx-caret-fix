# PyCharm / JetBrains 输入法候选框不跟随光标修复

项目：`jetbrains-fcitx-caret-fix` · Linux / X11 / Fcitx / 搜狗输入法

[English](README.en.md) · [安装包与适配案例](docs/COMPATIBILITY.md) · [复用思路与适配流程](docs/PORTING.md)

作者与维护者：[yelianna1001@gmail.com](mailto:yelianna1001@gmail.com)

**典型现象：在 Ubuntu / Linux 上，搜狗或 Fcitx 中文输入法的候选框固定在 PyCharm 窗口左下角，不随编辑光标移动，而其他软件输入正常。** 本项目记录了这一问题的定位和修复，并提供可供其他版本适配的源码与流程。

为 JetBrains IDE 在 Linux X11 + Fcitx / 搜狗环境下的候选框跟随问题，提供**可复用的排查与坐标修正思路、参考源码和可回滚安装器**。当候选框固定在 IDE 左下角、无法跟随编辑光标时，沿“编辑器光标位置 → 坐标转换 → 输入法位置更新”这条链路定位并修复问题。

**这套思路可以迁移到其他版本。** 本仓库提供 PyCharm 2021.1.3 + JBR 11 的参考实现；作者还已反馈，让 AI 参照本迁移包按本机环境适配，成功跑通了 **PyCharm 2022 + JBR 17**。

遇到类似问题，可以让开发者或 AI 参考源码和下面的流程，为实际设备建立对应实现。已有案例与安装包版本见[适配记录](docs/COMPATIBILITY.md)。

## 在其他设备或版本上复用

把迁移包或本仓库交给 AI，附上这段已用于上述适配的提示词：

> 请参考此迁移包，为本机 PyCharm 2022 + JBR 17 适配搜狗候选框跟随。先读取实际运行版本、输入法和显示环境，复现问题；核对 Java 接口及原生结构，必要时修改源码并重新编译，不得直接绕过版本或哈希校验。重新验证 50 像素补偿是否需要，并测试中文输入、删除、搜索框、终端、跨屏和缩放。先隔离验证，确认效果后再应用，保留备份与回退功能。

其他版本可替换提示词中的目标版本。定位链路、实现结构、隔离验证和回退流程都可以复用；Java 接口、原生结构、坐标缩放和补偿量则按目标环境核对。完整说明见 [PORTING.md](docs/PORTING.md)。

## 效果与原理

修复前：移动编辑光标后，搜狗候选框仍停留在窗口左下角。

修复后：候选框跟随编辑位置。PyCharm 2021.1.3 的参考实现还补偿了该搜狗 XIM 插件额外增加的 50 像素纵向距离；适配时重新测量补偿量。

```mermaid
flowchart LR
    A[编辑器 InputMethodRequests] -->|光标矩形| B[Java agent / EDT 每 100ms]
    B -->|持有 AWT 锁| C[JNI / 转换为焦点窗口坐标]
    C -->|XNSpotLocation| D[XIM → Fcitx → 搜狗候选框]
```

代码只更新候选位置，不读取输入内容，不模拟按键、不转移焦点、不修改皮肤或合成器。透明皮肤应继续由输入法原有窗口绘制；它并不是通用的黑框修复工具。

## 直接安装 v0.1.0

下列要求用于直接安装这个版本的预编译包。其他环境可沿用上面的思路重新适配。

- Linux x86_64，X11，会话中的输入法为 Fcitx 4 + 验证过的搜狗插件。
- PyCharm Professional **2021.1.3 / PY-211.7628.24**，自带 **JBR 11.0.11+9-b1341.60-jcef**；还会检查完整原生库 SHA-256。
- 安装器会让这个 PyCharm 使用其自带 JBR，设置进程内 Fcitx 环境，并传入 `-Dsun.java2d.uiScale.enabled=false`。**切换 JDK 可能改变默认字体，禁用 Java UI 缩放也可能改变显示大小。** 请先记录 Editor → Font 的字体、字号及显示设置，参阅[排查说明](docs/TROUBLESHOOTING.md)。
- 所有修补均限指定 IDE 安装目录；不更改用户字体配置、全局 Java、搜狗皮肤或输入法自启。需要对该目录有写权限。

### 下载与安装

从项目 Releases 下载 `jetbrains-fcitx-caret-fix-0.1.0-linux-x86_64.zip` 及同名 `.sha256` 文件，在下载目录校验、解压，然后进入解压目录执行：

```bash
sha256sum -c jetbrains-fcitx-caret-fix-0.1.0-linux-x86_64.zip.sha256
unzip jetbrains-fcitx-caret-fix-0.1.0-linux-x86_64.zip
cd jetbrains-fcitx-caret-fix-0.1.0
bash install.sh --ide-dir /path/to/pycharm-2021.1.3 --check
bash install.sh --ide-dir /path/to/pycharm-2021.1.3
```

随后保存工作，完全退出并重新打开 PyCharm。安装器不会主动关闭或启动软件。候选框的可见边缘与光标之间仍可能有皮肤透明边距。

脚本默认检查两个常见的搜狗插件位置；特殊安装目录可增加 `--sogou-plugin /path/to/fcitx-sogoupinyin.so`，完整哈希校验仍然生效。它不是跳过兼容检查的开关。

检查、卸载：

```bash
bash diagnose.sh --ide-dir /path/to/pycharm-2021.1.3
bash uninstall.sh --ide-dir /path/to/pycharm-2021.1.3 --check
bash uninstall.sh --ide-dir /path/to/pycharm-2021.1.3
```

卸载恢复原启动脚本并保留备份归档，不依赖当前仍是旧版 JBR / 搜狗 / X11。安装后若启动脚本被另行修改，会拒绝覆盖，需人工比较。安装状态位于 IDE 下的 `.pycharm-ime-fix/`；不要删除其中的原文件备份。已有早期手动补丁的设备无需重装本包。

## 从源码构建

依赖：Bash、GNU coreutils、awk、grep、GCC、libX11 开发头文件和库、JDK 11+（推荐 JDK 11）、Python 3.8+ 标准库。脚本不会自动安装依赖。发布包的安装和卸载无需 Python 或编译器。

```bash
# 可选：指定编译 JDK 和已存在的 Python 环境
export CARET_BUILD_JDK=/path/to/jdk-11
export CARET_PYTHON=/path/to/python3
bash build.sh
"$CARET_PYTHON" -B -m unittest discover -s tests -v
bash package.sh
```

若 PATH 已有这些工具，可不设置上述两个变量，用 `python3` 执行测试。构建生成 `payload/` 和 `SHA256SUMS`；打包产物在 `dist/`。源码仓库不提交编译产物，GitHub 自动生成的源码 ZIP 需要先构建。

新系统构建的 `.so` 可能要求更高的 glibc。给旧设备发布时应在相应旧系统构建并实测；GitHub CI 产物不自动视为 Ubuntu 18.04 可用。详见[测试](docs/TESTING.md)与[发布](docs/RELEASING.md)。

## 适配与反馈

### 不想升级 PyCharm，可以尝试这个方案吗？

可以参考这里的做法，在现有 IDE 上核对输入法链路并适配。原案例保留 PyCharm 2021.1.3，使用其自带 JBR，通过 Java agent 与 JNI 更新 XIM 候选位置。已有按同一思路适配 PyCharm 2022 + JBR 17 的反馈，参见[适配案例](docs/COMPATIBILITY.md)。

### 与 JetBrainsRuntime-for-Linux-x64 有什么区别？

[RikudouPatrickstar/JetBrainsRuntime-for-Linux-x64](https://github.com/RikudouPatrickstar/JetBrainsRuntime-for-Linux-x64) 也针对 Linux 下 Fcitx 候选框不跟随光标的问题，提供打过补丁的 JBR 编译产物。两种实现处理的是相关问题，修改的位置不同：

| 路线 | 实现与使用方式 |
| --- | --- |
| 打补丁并构建 JBR | 使用该项目提供的运行时，按其文档替换 IDE 的 JBR 目录 |
| 本项目的 agent / JNI 参考实现 | 在 IDE 进程中读取编辑光标坐标并更新 XIM 位置，通过启动参数加载桥接库，提供安装备份与回退 |

本项目的安装器会选用 IDE 已带的 JBR，并调整启动参数；原先使用其他 JDK 的设备仍应核对字体和缩放。选择路线时，可按目标 JBR 的可用实现、输入法后端和验证结果判断。相关的历史问题可见 [JetBrainsRuntime #32](https://github.com/JetBrains/JetBrainsRuntime/issues/32)。

### 让 AI 适配其他版本，从哪里开始？

将本仓库链接或迁移包与上面的完整提示词一起提供，让它先读取设备环境、复现问题，再核对接口并隔离验证。具体步骤见 [PORTING.md](docs/PORTING.md)。

### 提交适配结果

遇到相似问题可参照 [PORTING.md](docs/PORTING.md) 定位坐标链路、核对目标接口并建立对应实现。欢迎补充新的适配案例、源码差异和验证结果，帮助更多设备复用。

提交 issue 时附 IDE 完整构建号、实际运行 JBR、桌面会话、输入法版本及 `diagnose.sh` 输出；只上传与问题相关的日志片段。请参考[贡献指南](CONTRIBUTING.md)。

原创代码和文档采用 [MIT](LICENSE)。依赖和参考项目的归属见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)；本项目不是 JetBrains、Fcitx 或搜狗的官方产品。
