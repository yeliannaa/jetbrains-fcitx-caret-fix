# 安装包与适配案例

本项目的定位方法和适配流程可以跨版本复用。预编译安装包则对应具体的 IDE、JBR 和输入法构建；两者分别记录如下。

## 已有案例

| 环境 | 结果与证据 | 使用方式 |
| --- | --- | --- |
| PyCharm Professional 2021.1.3 + JBR 11 | 本仓库参考实现，已完成原设备桌面验证及安装器自动测试 | 匹配下方具体构建时，可直接使用 v0.1.1 安装包 |
| PyCharm 2022 + JBR 17 | 作者反馈：让 AI 参考本迁移包，按实际设备环境适配后已跑通候选框跟随 | 复用 [PORTING.md](PORTING.md) 中的流程和提示词，为目标设备适配 |

2022 / JBR 17 案例目前记录了适配成功的反馈及所用提示词，尚未收录完整构建号、源码差异、库哈希和逐项测试结果。该适配的二进制未包含在 v0.1.1 附件中。

## v0.1.1 可直接安装的组合

| 项目 | v0.1.1 验证组合 |
| --- | --- |
| 系统 | Ubuntu 18.04 / Linux x86_64 / X11 |
| IDE | PyCharm Professional 2021.1.3，`PY-211.7628.24` |
| 运行时 | 随 IDE 提供的 JBR `11.0.11+9-b1341.60-jcef` |
| 输入框架 | Fcitx 4，`XMODIFIERS=@im=fcitx` |
| 输入法 | 搜狗 4.2.1，对应以下插件哈希 |
| AWT 坐标变换 | scaleX=1.0，scaleY=1.0 |
| 纵向补偿 | `local.ime.yOffset=-50` |

`jbr/lib/libawt_xawt.so` SHA-256：

```text
afcdea2f93d5b1550bff25a0f0a457db92f41b3f928078ee818aa39dc4e5f2a6
```

`fcitx-sogoupinyin.so` SHA-256：

```text
95c1e5f378baf1ac19ee46ab67492a1b762bffb9c6dfdeb8db5f634181e6d024
```

插件搜索位置：`/usr/lib/x86_64-linux-gnu/fcitx/fcitx-sogoupinyin.so`、`/usr/lib/fcitx/fcitx-sogoupinyin.so`，或显式 `--sogou-plugin` 路径。路径变化不放宽哈希要求。

安装器检查 OS、架构、会话类型、IDE 构建号、AWT 哈希、插件哈希和本补丁的动态链接依赖。Java agent 启动时再次检查 Java 11 与 AWT 哈希；运行时只处理 X11 XInputMethod，遇到未验证缩放会跳过更新。

这不是对所有环境行为的自动证明：安装检查不验证窗口管理器、实际活动输入法、其他 Java agents、远程桌面或每一种编辑组件。

## 需要单独适配的环境与安装条件

- PyCharm 2022 / JBR 17 已有上述适配成功反馈；其他 IDE 和 JBR 构建也可参考同一流程核对接口、修改并构建对应实现。
- Wayland、Fcitx 5、IBus、ARM64、Windows/macOS 尚无本项目的适配记录；应先确认实际输入链路，再选择相应实现，不能假定都使用当前 X11/XIM 接口。
- Java 非 1:1 坐标变换、混合 DPI 的通用换算。
- 安装路径含 `=`、换行；符号链接形式的 `bin/pycharm.sh`。
- 已有早期手动补丁或启动器结构变化：拒绝叠加补丁，需先人工核对。

正常 Unicode、空格、单引号、双引号和反引号路径由模拟安装器测试覆盖。其他 Linux 发行版即使通过检查，也需自行进行桌面回归后再报告验证结果。
