package je.ef.digi2droid

import java.util.concurrent.atomic.AtomicBoolean

/**
 * JNI bridge to libgphoto2. The app is always linked against native prebuilts under
 * [third_party/libgphoto2-android] and [libdigi2droid_gphoto] from CMake.
 */
object GphotoNative {

    private val configured = AtomicBoolean(false)

    init {
        System.loadLibrary("digi2droid_gphoto")
    }

    fun configureOnce(nativeLibDir: String) {
        if (configured.compareAndSet(false, true)) {
            nativeConfigure(nativeLibDir)
        }
    }

    fun probeCamera(fd: Int): String? = nativeProbeCamera(fd)

    private external fun nativeConfigure(nativeLibDir: String)

    private external fun nativeProbeCamera(fd: Int): String?
}
