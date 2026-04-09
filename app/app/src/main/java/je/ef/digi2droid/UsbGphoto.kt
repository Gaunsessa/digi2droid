package je.ef.digi2droid

import android.hardware.usb.UsbConstants
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbDeviceConnection
import android.hardware.usb.UsbInterface
import android.os.Build

/**
 * Android requires claiming USB interfaces before low-level access (libusb / libgphoto2) works.
 * This mirrors fixing "cannot claim device" on desktop by ensuring the app holds the interface.
 */
object UsbGphoto {

    /**
     * Claims interfaces needed for PTP/gphoto access. Returns the list of interfaces that were
     * claimed — caller must [UsbDeviceConnection.releaseInterface] for each, then [UsbDeviceConnection.close].
     */
    fun claimInterfacesForGphoto(connection: UsbDeviceConnection, device: UsbDevice): List<UsbInterface> {
        val claimed = mutableListOf<UsbInterface>()
        fun tryClaim(intf: UsbInterface) {
            if (claimInterface(connection, intf)) {
                claimed.add(intf)
            }
        }
        for (i in 0 until device.interfaceCount) {
            val intf = device.getInterface(i)
            if (likelyCameraDataInterface(intf)) {
                tryClaim(intf)
            }
        }
        if (claimed.isEmpty()) {
            for (i in 0 until device.interfaceCount) {
                tryClaim(device.getInterface(i))
            }
        }
        return claimed
    }

    fun releaseInterfaces(connection: UsbDeviceConnection, interfaces: List<UsbInterface>) {
        for (intf in interfaces.asReversed()) {
            try {
                connection.releaseInterface(intf)
            } catch (_: Exception) {
                // ignore
            }
        }
    }

    private fun likelyCameraDataInterface(intf: UsbInterface): Boolean {
        when (intf.interfaceClass) {
            UsbConstants.USB_CLASS_STILL_IMAGE -> return true
            UsbConstants.USB_CLASS_VENDOR_SPEC -> return true
        }
        for (j in 0 until intf.endpointCount) {
            val ep = intf.getEndpoint(j)
            if (ep.type == UsbConstants.USB_ENDPOINT_XFER_BULK ||
                ep.type == UsbConstants.USB_ENDPOINT_XFER_INT
            ) {
                return true
            }
        }
        return false
    }

    private fun claimInterface(connection: UsbDeviceConnection, intf: UsbInterface): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            connection.claimInterface(intf, true)
        } else {
            // Single-arg claimInterface is not in compileSdk 34 stubs; invoke at runtime on API 24–27.
            try {
                val m = UsbDeviceConnection::class.java.getMethod(
                    "claimInterface",
                    UsbInterface::class.java
                )
                m.invoke(connection, intf) as Boolean
            } catch (_: ReflectiveOperationException) {
                false
            }
        }
    }
}
