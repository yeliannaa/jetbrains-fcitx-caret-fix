# 发布流程

仓库保存源文件；Releases 保存可直接安装的 ZIP 和 `.sha256`。`payload/`、`build/`、`dist/`、根 `SHA256SUMS` 已被 Git 忽略。首次上传时保留 `.github/`、`.gitignore` 等隐藏文件。

## 生成发布文件

1. 更新 `VERSION`、`CHANGELOG.md`、兼容表与验证记录。核对 MIT 署名和第三方说明。
2. 选择目标设备可用的构建系统和 JDK；面向旧 glibc 的包应在旧基线系统编译。只在新 Ubuntu CI 编译通过不够。
3. 运行构建、安装器测试和打包：

```bash
bash build.sh
python3 -B -m unittest discover -s tests -v
bash package.sh
cd dist
sha256sum -c *.sha256
```

4. 从 ZIP 解压一份，核对内层 `SHA256SUMS`；新运行时变更还需完成独立桌面验证。
5. 检查 ZIP 只含允许发布的文件；不应含本机日志、原启动脚本、用户配置或私有路径。
6. 在目标 GitHub 仓库发布对应版本，将 ZIP 和 `.sha256` 作为 Release assets 附件。仓库初始化、提交、推送和发布由维护者自行执行；这些脚本不访问 GitHub。

`tools/package_release.py` 使用显式文件列表，新增发布文件必须同步列表。包清单覆盖脚本、源码、文档和载荷；更改后需要重新构建。清单用于发现意外损坏，不是数字签名。

同一批输入文件产生相同 ZIP 字节。JAR 时间戳、JDK/GCC/链接器版本可能影响重新编译的二进制，暂不承诺跨工具链逐字节可复现。`payload/BUILD-INFO.txt` 记录实际编译器，Java 构建目标固定为 release 11。

当前 `common.sh` 的 `PATCH_VERSION` 是安装状态格式标识，独立于公开版本号。安装器尚未实现就地更新补丁：已有状态会校验后返回，不替换其载荷。更换版本时先用原发布包卸载再安装，并保留备份。
