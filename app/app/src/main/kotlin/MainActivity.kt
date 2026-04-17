package je.ef.digi2droid

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.os.Build
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import androidx.recyclerview.widget.LinearLayoutManager
import je.ef.digi2droid.databinding.ActivityMainBinding
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val adapter = DigicamAdapter { device -> requestUsbPermission(device) }
    private val executor = Executors.newSingleThreadExecutor()

    private val usbPermissionReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action != ACTION_USB_PERMISSION) return
            refreshList()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter

        binding.fabRefresh.setOnClickListener { refreshList() }

        val filter = IntentFilter(ACTION_USB_PERMISSION)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(usbPermissionReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            registerReceiver(usbPermissionReceiver, filter)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        unregisterReceiverSafe(usbPermissionReceiver)
        executor.shutdownNow()
    }

    override fun onResume() {
        super.onResume()
        refreshList()
    }

    private fun unregisterReceiverSafe(receiver: BroadcastReceiver) {
        try {
            unregisterReceiver(receiver)
        } catch (_: IllegalArgumentException) {
            // not registered
        }
    }

    private fun requestUsbPermission(device: UsbDevice) {
        val usbManager = getSystemService(Context.USB_SERVICE) as UsbManager
        if (usbManager.hasPermission(device)) {
            return
        }
        val pi = PendingIntent.getBroadcast(
            this,
            0,
            Intent(ACTION_USB_PERMISSION),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        usbManager.requestPermission(device, pi)
    }

    private fun refreshList() {
        val usbManager = getSystemService(Context.USB_SERVICE) as UsbManager
        val devices = DigicamUsb.listUsbDevices(usbManager)
        if (devices.isEmpty()) {
            adapter.submitList(emptyList())
            binding.empty.isVisible = true
            binding.recycler.isVisible = false
            return
        }
        binding.empty.isVisible = false
        binding.recycler.isVisible = true

        GphotoNative.configureOnce(applicationInfo.nativeLibraryDir)

        val pending = devices.map { d ->
            val gphoto = when {
                !usbManager.hasPermission(d) -> getString(R.string.gphoto_need_permission)
                else -> getString(R.string.gphoto_probing)
            }
            DigicamUsb.Entry(
                device = d,
                vendorId = d.vendorId,
                productId = d.productId,
                usbSummary = DigicamUsb.buildUsbSummary(d),
                libgphotoLine = gphoto,
            )
        }
        adapter.submitList(pending)

        executor.execute {
            val rows = devices.map { d ->
                val base = DigicamUsb.Entry(
                    device = d,
                    vendorId = d.vendorId,
                    productId = d.productId,
                    usbSummary = DigicamUsb.buildUsbSummary(d),
                    libgphotoLine = null,
                )
                if (!usbManager.hasPermission(d)) {
                    return@map base.copy(libgphotoLine = getString(R.string.gphoto_need_permission))
                }
                val conn = usbManager.openDevice(d)
                if (conn == null) {
                    return@map base.copy(libgphotoLine = getString(R.string.gphoto_open_failed))
                }
                val claimed = UsbGphoto.claimInterfacesForGphoto(conn, d)
                try {
                    if (claimed.isEmpty()) {
                        return@map base.copy(libgphotoLine = getString(R.string.usb_claim_failed))
                    }
                    val summary = GphotoNative.probeCamera(conn.fileDescriptor)
                    base.copy(libgphotoLine = summary ?: getString(R.string.gphoto_null))
                } catch (e: Exception) {
                    base.copy(libgphotoLine = e.message ?: getString(R.string.gphoto_error))
                } finally {
                    UsbGphoto.releaseInterfaces(conn, claimed)
                    conn.close()
                }
            }
            runOnUiThread { adapter.submitList(rows) }
        }
    }

    companion object {
        const val ACTION_USB_PERMISSION = "je.ef.digi2droid.USB_PERMISSION"
    }
}
