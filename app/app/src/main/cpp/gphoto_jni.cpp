#include <android/log.h>
#include <jni.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <gphoto2/gphoto2.h>
#include <gphoto2/gphoto2-port.h>
#include <gphoto2/gphoto2-result.h>

#define LOG_TAG "digi2droid_gphoto"

static void log_cb(GPLogLevel /*level*/, const char *domain, const char *str, void * /*data*/) {
    __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, "%s: %s", domain ? domain : "gphoto", str ? str : "");
}

extern "C" JNIEXPORT void JNICALL
Java_je_ef_digi2droid_GphotoNative_nativeConfigure(JNIEnv *env, jclass /*clazz*/, jstring jLibDir) {
    const char *lib = env->GetStringUTFChars(jLibDir, nullptr);
    if (!lib) {
        return;
    }
    setenv("CAMLIBS", lib, 1);
    setenv("IOLIBS", lib, 1);
    setenv("CAMLIBS_PREFIX", "libgphoto2_camlib_", 1);
    setenv("IOLIBS_PREFIX", "libgphoto2_port_iolib_", 1);
    env->ReleaseStringUTFChars(jLibDir, lib);
    gp_log_add_func(GP_LOG_DEBUG, log_cb, nullptr);
}

extern "C" JNIEXPORT jstring JNICALL
Java_je_ef_digi2droid_GphotoNative_nativeProbeCamera(JNIEnv *env, jclass /*clazz*/, jint fd) {
    if (fd < 0) {
        return env->NewStringUTF("invalid file descriptor");
    }

    int r = gp_port_usb_set_sys_device(static_cast<int>(fd));
    if (r != GP_OK) {
        char buf[256];
        std::snprintf(buf, sizeof(buf), "gp_port_usb_set_sys_device: %s", gp_result_as_string(r));
        return env->NewStringUTF(buf);
    }

    GPContext *ctx = gp_context_new();
    if (!ctx) {
        return env->NewStringUTF("gp_context_new failed");
    }

    Camera *cam = nullptr;
    r = gp_camera_new(&cam);
    if (r != GP_OK || !cam) {
        gp_context_unref(ctx);
        char buf[256];
        std::snprintf(buf, sizeof(buf), "gp_camera_new: %s", gp_result_as_string(r));
        return env->NewStringUTF(buf);
    }

    r = gp_camera_init(cam, ctx);
    if (r != GP_OK) {
        gp_camera_free(cam);
        gp_context_unref(ctx);
        char buf[256];
        std::snprintf(buf, sizeof(buf), "gp_camera_init: %s", gp_result_as_string(r));
        return env->NewStringUTF(buf);
    }

    CameraText text;
    std::memset(&text, 0, sizeof(text));
    r = gp_camera_get_summary(cam, &text, ctx);
    gp_camera_exit(cam, ctx);
    gp_camera_free(cam);
    gp_context_unref(ctx);

    if (r != GP_OK) {
        char buf[256];
        std::snprintf(buf, sizeof(buf), "gp_camera_get_summary: %s", gp_result_as_string(r));
        return env->NewStringUTF(buf);
    }

    return env->NewStringUTF(text.text);
}
