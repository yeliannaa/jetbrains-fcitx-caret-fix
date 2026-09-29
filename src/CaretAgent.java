package local.ime;

import java.awt.*;
import java.awt.font.TextHitInfo;
import java.awt.im.InputMethodRequests;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.*;
import java.security.MessageDigest;
import javax.swing.Timer;

/** Per-process coordinate bridge for the exact bundled PyCharm 2021.1 JBR 11. */
public final class CaretAgent {
    private static final String AWT_HASH = "afcdea2f93d5b1550bff25a0f0a457db92f41b3f928078ee818aa39dc4e5f2a6";
    private static Field methodField;
    private static Method awtLock, awtUnlock;
    private static boolean failed;
    private static String lastTrace = "";
    private static final boolean TRACE = Boolean.getBoolean("local.ime.trace");
    // Sogou 4.2.1's XIM frontend substitutes 50px when Fcitx reports height 0.
    // Keep the generic bridge neutral; its Sogou-specific launcher supplies -50.
    private static final int Y_OFFSET = Integer.getInteger("local.ime.yOffset", 0);

    public static void premain(String options, Instrumentation instrumentation) {
        try {
            Path home = Paths.get(System.getProperty("java.home"));
            if (!"11".equals(System.getProperty("java.specification.version")) ||
                !AWT_HASH.equals(hash(home.resolve("lib/libawt_xawt.so")))) {
                throw new IllegalStateException("Unverified Java runtime; bridge not loaded");
            }
            if (!"@im=fcitx".equals(System.getenv("XMODIFIERS"))) {
                throw new IllegalStateException("Expected XMODIFIERS=@im=fcitx");
            }
            // premain runs before the IDE installs its own class loader. Creating
            // AWT here would give its EDT the system loader permanently: Swing
            // cannot resolve JetBrains UI delegates (e.g. JCheckBox width is 0).
            startWhenIdeIsReady(() -> initializeBridge(options), 180_000L);
        } catch (Exception | LinkageError error) {
            System.err.println("[caret-bridge] disabled: " + error);
        }
    }

    /** Wait without touching AWT; let the IDE create its event thread first. */
    static void startWhenIdeIsReady(Runnable initialize, long timeoutMillis) {
        Thread waiter = new Thread(() -> {
            long started = System.nanoTime();
            try {
                while ((System.nanoTime() - started) / 1_000_000L < timeoutMillis) {
                    for (Thread thread : Thread.getAllStackTraces().keySet()) {
                        if (!thread.isAlive() ||
                            !thread.getClass().getName().equals("java.awt.EventDispatchThread")) continue;
                        ClassLoader loader = thread.getContextClassLoader();
                        if (loader == null || loader == ClassLoader.getSystemClassLoader()) continue;
                        // Post from the IDE's thread group/AppContext, with its
                        // loader. Never replace an existing thread's loader.
                        Thread poster = new Thread(thread.getThreadGroup(),
                            () -> EventQueue.invokeLater(initialize), "caret-bridge-post");
                        poster.setContextClassLoader(loader);
                        poster.setDaemon(true);
                        poster.start();
                        return;
                    }
                    Thread.sleep(200);
                }
                System.err.println("[caret-bridge] IDE event thread not ready; disabled");
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
            } catch (Exception | LinkageError error) {
                System.err.println("[caret-bridge] startup disabled: " + error);
            }
        }, "caret-bridge-startup");
        waiter.setDaemon(true);
        waiter.start();
    }

    private static void initializeBridge(String options) {
        try {
            if (!Toolkit.getDefaultToolkit().getClass().getName().equals("sun.awt.X11.XToolkit")) {
                System.err.println("[caret-bridge] X11 toolkit required; disabled");
                return;
            }
            methodField = Class.forName("sun.awt.im.InputContext").getDeclaredField("inputMethod");
            methodField.setAccessible(true);
            Class<?> toolkit = Class.forName("sun.awt.SunToolkit");
            awtLock = toolkit.getMethod("awtLock");
            awtUnlock = toolkit.getMethod("awtUnlock");
            System.load(Paths.get(options).toAbsolutePath().toString());
            Timer timer = new Timer(100, event -> tick());
            timer.setCoalesce(true);
            timer.start();
            System.err.println("[caret-bridge] active; coordinate updates only");
        } catch (Exception | LinkageError error) {
            System.err.println("[caret-bridge] disabled: " + error);
        }
    }

    private static String hash(Path path) throws Exception {
        byte[] result = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path));
        StringBuilder out = new StringBuilder();
        for (byte value : result) out.append(String.format("%02x", value & 255));
        return out.toString();
    }

    private static void tick() {
        if (failed) return;
        try {
            Component client = KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner();
            if (client == null || !client.isShowing() || client.getInputContext() == null) return;
            InputMethodRequests requests = client.getInputMethodRequests();
            if (requests == null) return;
            Object inputMethod = methodField.get(client.getInputContext());
            if (inputMethod == null || !inputMethod.getClass().getName().equals("sun.awt.X11.XInputMethod")) return;
            Rectangle caret = requests.getTextLocation(TextHitInfo.leading(0));
            if (caret == null) return;
            // Existing PyCharm configuration disables UI scaling; refuse untested transforms.
            java.awt.geom.AffineTransform transform = client.getGraphicsConfiguration().getDefaultTransform();
            if (transform.getScaleX() != 1.0 || transform.getScaleY() != 1.0) return;
            int x = caret.x;
            int y = caret.y + Math.max(1, caret.height) + Y_OFFSET;
            int result;
            awtLock.invoke(null);
            try {
                result = update(inputMethod, x, y);
            } finally {
                awtUnlock.invoke(null);
            }
            if (TRACE) {
                String info = client.getClass().getName() + " " + x + "," + y + " result=" + result;
                if (!info.equals(lastTrace)) {
                    System.err.println("[caret-bridge] " + info);
                    lastTrace = info;
                }
            }
        } catch (IllegalComponentStateException ignored) {
            // The focused component may disappear while a popup closes.
        } catch (Exception | LinkageError error) {
            failed = true;
            System.err.println("[caret-bridge] disabled after error: " + error);
        }
    }

    private static native int update(Object inputMethod, int screenX, int screenY);
}
