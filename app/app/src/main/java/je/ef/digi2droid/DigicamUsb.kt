package je.ef.digi2droid

import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager

/**
 * Enumerates all USB host devices. libgphoto2 (when available) is used to classify / describe
 * devices after the user grants [android.hardware.usb.UsbManager] access.
 */
object DigicamUsb {

    data class Entry(
        val device: UsbDevice,
        val vendorId: Int,
        val productId: Int,
        val usbSummary: String,
        /** libgphoto2 camera summary, status text, or null if not probed. */
        val libgphotoLine: String?,
    )

    fun listUsbDevices(usbManager: UsbManager): List<UsbDevice> {
        return usbManager.deviceList.values
            .sortedWith(compareBy({ it.manufacturerName ?: "" }, { it.productName ?: "" }, { it.deviceName }))
    }

    fun buildUsbSummary(d: UsbDevice): String {
        val parts = mutableListOf<String>()
        d.manufacturerName?.takeIf { it.isNotBlank() }?.let { parts.add(it) }
        d.productName?.takeIf { it.isNotBlank() }?.let { parts.add(it) }
        val title = parts.joinToString(" ").ifBlank { "USB device" }
        return "$title · ${hexId(d.vendorId)}:${hexId(d.productId)} · ${d.deviceName}"
    }

    private fun hexId(id: Int): String = "0x%04X".format(id and 0xffff)
}
