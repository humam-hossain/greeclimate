import argparse
import asyncio
import logging

from greeclimate.device import Device, DeviceInfo
from greeclimate.discovery import Discovery, Listener

logging.basicConfig(
    level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s"
)
_LOGGER = logging.getLogger(__name__)


class DiscoveryListener(Listener):
    def __init__(self, bind):
        """Initialize the event handler."""
        super().__init__()
        self.bind = bind

    """Class to handle incoming device discovery events."""

    async def device_found(self, device_info: DeviceInfo) -> None:
        """A new device was found on the network."""
        if self.bind:
            device = Device(device_info)
            await device.bind()
            await device.request_version()
            await device.update_state()
            _LOGGER.info(
                "Device firmware hid=%s in_hid=%s oeep_hid=%s ota_hid=%s bc=%s",
                device.hid,
                device.in_hid,
                device.oeep_hid,
                device.ota_hid,
                device.bc,
            )
            _LOGGER.info(
                "Device model_type=%s all_error=%s fault=%s outdoor_temp=%s "
                "light_sensor=%s uvc=%s app_timer=%s ai_save=%s anti_blow=%s elec=%s",
                device.model_type,
                device.all_error,
                device.fault_display,
                device.current_temperature_outdoor,
                device.light_sensor,
                device.uvc_control,
                device.app_timer,
                device.ai_energy_save_display,
                device.anti_direct_blow,
                device.elec_energy,
            )
            _LOGGER.info(
                "Device sleep_curve l1=%s h1=%s l2=%s h2=%s l3=%s h3=%s l4=%s h4=%s "
                "l5=%s h5=%s l6=%s h6=%s l7=%s h7=%s l8=%s h8=%s",
                device.sleep_curve_l1,
                device.sleep_curve_h1,
                device.sleep_curve_l2,
                device.sleep_curve_h2,
                device.sleep_curve_l3,
                device.sleep_curve_h3,
                device.sleep_curve_l4,
                device.sleep_curve_h4,
                device.sleep_curve_l5,
                device.sleep_curve_h5,
                device.sleep_curve_l6,
                device.sleep_curve_h6,
                device.sleep_curve_l7,
                device.sleep_curve_h7,
                device.sleep_curve_l8,
                device.sleep_curve_h8,
            )


async def run_discovery(bind=False):
    """Run the device discovery process."""
    _LOGGER.debug("Scanning network for Gree devices")

    discovery = Discovery()
    listener = DiscoveryListener(bind)
    discovery.add_listener(listener)

    await discovery.scan(wait_for=10)

    _LOGGER.info("Done discovering devices")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gree command line utility.")
    parser.add_argument("--discovery", default=False, action="store_true")
    parser.add_argument("--bind", default=False, action="store_true")
    args = parser.parse_args()

    if args.discovery:
        asyncio.run(run_discovery(args.bind))
