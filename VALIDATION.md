# 验证记录

## 原补丁的真实桌面验证

环境：Ubuntu 18.04 x86_64 / X11，PyCharm Professional 2021.1.3 (`PY-211.7628.24`)，JBR `11.0.11+9-b1341.60-jcef`，Fcitx 4 / 搜狗 4.2.1。对应哈希见 [COMPATIBILITY](docs/COMPATIBILITY.md)。

原问题为候选框固定在 PyCharm 左下角；采用现有 Java/JNI 坐标更新及 -50 像素补偿后，使用者确认跟随与距离符合预期。过程中发现切换 JBR 会改变未明确设置的默认编辑字体，使用者手动选回原字体后确认解决。

这些是原环境的人工验证结果，不代表所有 IDE 组件、窗口管理器、缩放或多屏排列都已穷尽测试。

## 公开版整理的验证范围

公开版 Java/C 核心源文件保留原补丁内容。新工作集中在构建、打包、文档、诊断和安装器环境定位；不在正在使用的 IDE 中重新安装、重启或切换输入法。

2026-09-29 本地检查：

- Java/C 源码、agent manifest 和启动器注入模板与原迁移包逐字节一致。
- 使用 OpenJDK javac 17.0.7（`--release 11`）、GCC 7.5.0 在 Ubuntu 18.04 构建最终载荷：生成的 `CaretAgent.class` 和 `libcaret_bridge.so` 与原验证载荷逐字节一致。JAR 容器因打包时间戳不同而有不同哈希。
- 也使用 javac 11.0.19 成功构建；该编译器的 class 文件与旧载荷字节不同，不据此声称逐字节复现。
- 25 项模拟安装器测试通过，含 ZIP 解压、包校验、重复打包一致性、安装/卸载与拒绝覆盖场景。
- 在未匹配的系统 OpenJDK 11 和 17 中用 `-javaagent ... -version` 做无界面启动检查，均打印 `Unverified Java runtime; bridge not loaded`，未加载 JNI。
- Bash 脚本语法检查、发布文件隐私扫描通过。未包含用户配置、账号、项目日志、皮肤资源或原 IDE 启动器。

模拟测试不执行实际 JBR 私有 ABI，不能替代新增运行时组合的 GUI 验证。最终 ZIP 的 SHA-256 随包提供；上述编译器信息同时记录在 `payload/BUILD-INFO.txt`。

本目录的 CI 配置尚需首次推送后在 GitHub 运行；本地测试结果不等同于已经跑过云端 CI。
