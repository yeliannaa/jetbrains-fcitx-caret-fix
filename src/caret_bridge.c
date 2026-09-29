#include <jni.h>
#include <X11/Xlib.h>
#include <stdint.h>
#include <limits.h>
#include <string.h>
#include <dlfcn.h>

/* JBR commit 7bea9b450563: current_ic is the first member of X11InputMethodData.
 * The Java entry point verifies the complete native library SHA256 before load.
 * All calls run on the EDT with SunToolkit.awtLock held. No keystrokes/focus changes.
 */
JNIEXPORT jint JNICALL Java_local_ime_CaretAgent_update
    (JNIEnv *env, jclass clazz, jobject method, jint screen_x, jint screen_y) {
    (void)clazz;
    jclass base = (*env)->FindClass(env, "sun/awt/X11InputMethodBase");
    if (!base) return -1;
    jfieldID field = (*env)->GetFieldID(env, base, "pData", "J");
    (*env)->DeleteLocalRef(env, base);
    if (!field) return -2;
    void *data = (void *)(intptr_t)(*env)->GetLongField(env, method, field);
    if (!data) return 0;
    XIC ic = NULL;
    memcpy(&ic, data, sizeof(ic));
    if (!ic) return 0;
    Display *display = XDisplayOfIM(XIMOfIC(ic));
    if (!display) return -3;
    /* The XIM server need not support querying XNFocusWindow. JBR records it. */
    jclass impl = (*env)->GetObjectClass(env, method);
    jmethodID get_focus = (*env)->GetStaticMethodID(env, impl, "getXICFocus", "()J");
    if (!get_focus) { (*env)->DeleteLocalRef(env, impl); return -4; }
    Window focus = (Window)(*env)->CallStaticLongMethod(env, impl, get_focus);
    (*env)->DeleteLocalRef(env, impl);
    if ((*env)->ExceptionCheck(env) || !focus) return -4;
    int x = 0, y = 0;
    Window child = None;
    if (!XTranslateCoordinates(display, DefaultRootWindow(display), focus,
                               screen_x, screen_y, &x, &y, &child)) return -5;
    if (x < SHRT_MIN || x > SHRT_MAX || y < SHRT_MIN || y > SHRT_MAX) return -6;
    static XIC last_ic;
    static Window last_focus;
    static int last_x, last_y;
    if (ic == last_ic && focus == last_focus && x == last_x && y == last_y) return 1;
    XPoint point = {(short)x, (short)y};
    XVaNestedList attrs = XVaCreateNestedList(0, XNSpotLocation, &point, NULL);
    if (!attrs) return -7;
    char *error = XSetICValues(ic, XNPreeditAttributes, attrs, NULL);
    XFree(attrs);
    if (error) return -8;
    XFlush(display);
    last_ic = ic;
    last_focus = focus;
    last_x = x;
    last_y = y;
    return 2;
}
