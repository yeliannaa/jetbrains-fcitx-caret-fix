# Exact anchors are checked before any installed file is changed.
{
    print
    if ($0 == "IDE_HOME=$(dirname \"${IDE_BIN_HOME}\")") {
        homes++
        print "# PYCHARM_IME_FIX_BEGIN v1"
        print "PYCHARM_IME_DIR=\"$IDE_HOME/.pycharm-ime-fix\""
        print "export PYCHARM_JDK=\"$IDE_HOME/jbr\""
        print "export GTK_IM_MODULE=fcitx"
        print "export QT_IM_MODULE=fcitx"
        print "export XMODIFIERS=@im=fcitx"
        print "# PYCHARM_IME_FIX_END v1"
    }
    if ($0 == "  ${VM_OPTIONS} \\") {
        options++
        print "  --add-opens=java.desktop/sun.awt.im=ALL-UNNAMED \\"
        print "  --add-exports=java.desktop/sun.awt=ALL-UNNAMED \\"
        print "  -Dsun.java2d.uiScale.enabled=false \\"
        print "  -Dlocal.ime.yOffset=-50 \\"
        print "  \"-javaagent:$PYCHARM_IME_DIR/caret-agent.jar=$PYCHARM_IME_DIR/libcaret_bridge.so\" \\"
    }
}
END { if (homes != 1 || options != 1) exit 1 }
