"""Exercise the startup/class-loader regression in isolated, headless JVMs."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
package local.ime;
import java.awt.EventQueue;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Path;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import javax.swing.JCheckBox;
import javax.swing.UIManager;
public final class StartupHarness {
  static final CountDownLatch started = new CountDownLatch(1);
  static volatile boolean onEdt;
  static volatile ClassLoader callbackLoader;
  static void callback() {
    onEdt = EventQueue.isDispatchThread();
    callbackLoader = Thread.currentThread().getContextClassLoader();
    started.countDown();
  }
  static void require(boolean ok, String message) {
    if (!ok) throw new AssertionError(message);
  }
  static boolean hasEdt() {
    for (Thread t : Thread.getAllStackTraces().keySet())
      if (t.isAlive() && t.getClass().getName().equals("java.awt.EventDispatchThread")) return true;
    return false;
  }
  public static void main(String[] args) {
    try { run(args); System.out.println("PASS " + args[0]); System.exit(0); }
    catch (Throwable e) {e.printStackTrace(); System.exit(1);}
  }
  static void run(String[] args) throws Exception {
    String mode = args[0];
    if (mode.equals("idle")) {
      CaretAgent.startWhenIdeIsReady(StartupHarness::callback, 150);
      Thread.sleep(400);
      require(!hasEdt(), "startup created an EDT before the IDE");
      require(started.getCount() == 1, "callback ran without an IDE event thread");
      return;
    }
    if (mode.equals("system-loader")) {
      EventQueue.invokeAndWait(() -> {});
      CaretAgent.startWhenIdeIsReady(StartupHarness::callback, 150);
      Thread.sleep(400);
      require(started.getCount() == 1, "accepted the system loader as the IDE loader");
      EventQueue.invokeAndWait(() -> require(
          Thread.currentThread().getContextClassLoader() == ClassLoader.getSystemClassLoader(),
          "changed an existing EDT loader"));
      return;
    }
    if (mode.equals("deferred")) CaretAgent.startWhenIdeIsReady(StartupHarness::callback, 5000);
    Thread.sleep(400);
    require(!hasEdt(), "startup created an EDT before the IDE");
    ClassLoader ide = new URLClassLoader(new URL[]{Path.of(args[1]).toUri().toURL()},
                                         ClassLoader.getPlatformClassLoader());
    Thread.currentThread().setContextClassLoader(ide);
    EventQueue.invokeAndWait(() -> {
      require(Thread.currentThread().getContextClassLoader() == ide, "wrong initial EDT loader");
      UIManager.put("CheckBoxUI", "fixture.PrivateCheckBoxUI");
    });
    if (mode.equals("existing")) CaretAgent.startWhenIdeIsReady(StartupHarness::callback, 5000);
    if (mode.equals("premain")) Thread.sleep(800);
    else {
      require(started.await(5, TimeUnit.SECONDS), "callback did not start");
      require(onEdt && callbackLoader == ide, "callback did not use the IDE EDT/loader");
    }
    EventQueue.invokeAndWait(() -> {
      require(Thread.currentThread().getContextClassLoader() == ide, "EDT loader changed");
      JCheckBox box = new JCheckBox();
      require(box.getUI() != null, "checkbox UI delegate failed to load");
      require(box.getUI().getClass().getClassLoader() == ide, "UI resolved outside IDE loader");
      require(box.getPreferredSize().width > 0, "checkbox mouse hit width is zero");
    });
  }
}
'''
UI = r'''
package fixture;
import javax.swing.JComponent;
import javax.swing.plaf.ComponentUI;
import javax.swing.plaf.basic.BasicCheckBoxUI;
public final class PrivateCheckBoxUI extends BasicCheckBoxUI {
  public static ComponentUI createUI(JComponent c) {return new PrivateCheckBoxUI();}
}
'''


class AgentStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        jdk = os.environ.get('CARET_BUILD_JDK')
        cls.javac = str(Path(jdk) / 'bin/javac') if jdk else shutil.which('javac')
        cls.java = str(Path(jdk) / 'bin/java') if jdk else shutil.which('java')
        if not cls.javac or not cls.java:
            raise unittest.SkipTest('JDK 11+ is required')
        cls.temp = tempfile.TemporaryDirectory(prefix='caret-startup-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        (cls.base / 'classes').mkdir()
        (cls.base / 'private-ui').mkdir()
        (cls.base / 'StartupHarness.java').write_text(HARNESS)
        (cls.base / 'PrivateCheckBoxUI.java').write_text(UI)
        subprocess.run([cls.javac, '--release', '11', '-d', str(cls.base / 'classes'),
                        str(ROOT / 'src/CaretAgent.java'), str(cls.base / 'StartupHarness.java')],
                       check=True, capture_output=True, timeout=30)
        subprocess.run([cls.javac, '--release', '11', '-d', str(cls.base / 'private-ui'),
                        str(cls.base / 'PrivateCheckBoxUI.java')],
                       check=True, capture_output=True, timeout=30)

    def run_mode(self, mode):
        r = subprocess.run([self.java, '-Djava.awt.headless=true', '-cp',
                            str(self.base / 'classes'), 'local.ime.StartupHarness',
                            mode, str(self.base / 'private-ui')],
                           text=True, capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('PASS ' + mode, r.stdout)
        self.assertNotIn('no ComponentUI class', r.stderr)

    def test_waits_for_ide_and_preserves_checkbox_hit_width(self):
        self.run_mode('deferred')

    def test_already_running_ide_event_thread(self):
        self.run_mode('existing')

    def test_timeout_does_not_initialize_awt(self):
        self.run_mode('idle')

    def test_system_loader_is_not_changed_or_accepted(self):
        self.run_mode('system-loader')
