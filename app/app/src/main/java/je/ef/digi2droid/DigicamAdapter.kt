package je.ef.digi2droid

import android.hardware.usb.UsbDevice
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.view.isVisible
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import je.ef.digi2droid.databinding.ItemDigicamBinding

class DigicamAdapter(
    private val onDeviceClick: (UsbDevice) -> Unit,
) : ListAdapter<DigicamUsb.Entry, DigicamAdapter.VH>(
    object : DiffUtil.ItemCallback<DigicamUsb.Entry>() {
        override fun areItemsTheSame(
            a: DigicamUsb.Entry,
            b: DigicamUsb.Entry,
        ): Boolean = a.device.deviceName == b.device.deviceName

        override fun areContentsTheSame(
            a: DigicamUsb.Entry,
            b: DigicamUsb.Entry,
        ): Boolean = a == b
    },
) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val inflater = LayoutInflater.from(parent.context)
        val binding = ItemDigicamBinding.inflate(inflater, parent, false)
        return VH(binding, onDeviceClick)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        holder.bind(getItem(position))
    }

    class VH(
        private val binding: ItemDigicamBinding,
        private val onDeviceClick: (UsbDevice) -> Unit,
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(entry: DigicamUsb.Entry) {
            binding.title.text = entry.usbSummary
            binding.subtitle.text = binding.root.context.getString(
                R.string.digicam_item_subtitle,
                entry.device.deviceName,
            )
            val line = entry.libgphotoLine
            binding.gphoto.isVisible = line != null
            binding.gphoto.text = line.orEmpty()
            binding.root.setOnClickListener { onDeviceClick(entry.device) }
        }
    }
}
