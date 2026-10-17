import asyncio
import enum
import logging
import re
import typing
from asyncio import AbstractEventLoop
from enum import IntEnum, unique
from typing import Union, Optional, Any

from greeclimate.cipher import CipherV1, CipherV2
from greeclimate.deviceinfo import DeviceInfo
from greeclimate.exceptions import DeviceNotBoundError, DeviceTimeoutError
from greeclimate.network import DeviceProtocol2
from greeclimate.taskable import Taskable


class Props(enum.Enum):
    POWER = "Pow"
    MODE = "Mod"

    # Dehumidifier fields
    HUM_SET = "Dwet"
    HUM_SENSOR = "DwatSen"
    CLEAN_FILTER = "Dfltr"
    WATER_FULL = "DwatFul"
    DEHUMIDIFIER_MODE = "Dmod"

    TEMP_SET = "SetTem"
    TEMP_SENSOR = "TemSen"
    TEMP_UNIT = "TemUn"
    TEMP_BIT = "TemRec"
    FAN_SPEED = "WdSpd"
    FRESH_AIR = "Air"
    XFAN = "Blo"
    ANION = "Health"
    SLEEP = "SwhSlp"
    SLEEP_MODE = "SlpMod"
    LIGHT = "Lig"
    SWING_HORIZ = "SwingLfRig"
    SWING_VERT = "SwUpDn"
    QUIET = "Quiet"
    TURBO = "Tur"
    STEADY_HEAT = "StHt"
    POWER_SAVE = "SvSt"
    UNKNOWN_HEATCOOLTYPE = "HeatCoolType"

    # Newer properties observed in recent app ↔ device traffic.
    # Older properties above are retained for compatibility with older units.
    # Sleep-curve fields (Slp1L*/Slp1H*) observed live as L=160/H=0 defaults.
    LIGHT_SENSOR = "LigSen"
    UVC_CONTROL = "UvcControl"
    ALL_ERROR = "AllErr"
    APP_TIMER = "AppTimer"
    AI_ENERGY_SAVE_DISPLAY = "AIEnSaveDis"
    MODEL_TYPE = "ModelType"
    TEMP_SENSOR_OUTDOOR = "TemsSenOut"
    FAULT_DISPLAY = "FaultDisplay"
    ANTI_DIRECT_BLOW = "AntiDirectBlow"
    ELEC_ENERGY = "ElcEn"
    SLEEP_CURVE_L1 = "Slp1L1"
    SLEEP_CURVE_H1 = "Slp1H1"
    SLEEP_CURVE_L2 = "Slp1L2"
    SLEEP_CURVE_H2 = "Slp1H2"
    SLEEP_CURVE_L3 = "Slp1L3"
    SLEEP_CURVE_H3 = "Slp1H3"
    SLEEP_CURVE_L4 = "Slp1L4"
    SLEEP_CURVE_H4 = "Slp1H4"
    SLEEP_CURVE_L5 = "Slp1L5"
    SLEEP_CURVE_H5 = "Slp1H5"
    SLEEP_CURVE_L6 = "Slp1L6"
    SLEEP_CURVE_H6 = "Slp1H6"
    SLEEP_CURVE_L7 = "Slp1L7"
    SLEEP_CURVE_H7 = "Slp1H7"
    SLEEP_CURVE_L8 = "Slp1L8"
    SLEEP_CURVE_H8 = "Slp1H8"


@unique
class TemperatureUnits(IntEnum):
    C = 0
    F = 1


@unique
class Mode(IntEnum):
    Auto = 0
    Cool = 1
    Dry = 2
    Fan = 3
    Heat = 4


@unique
class FanSpeed(IntEnum):
    Auto = 0
    Low = 1
    MediumLow = 2
    Medium = 3
    MediumHigh = 4
    High = 5


@unique
class HorizontalSwing(IntEnum):
    Default = 0
    FullSwing = 1
    Left = 2
    LeftCenter = 3
    Center = 4
    RightCenter = 5
    Right = 6


@unique
class VerticalSwing(IntEnum):
    Default = 0
    FullSwing = 1
    FixedUpper = 2
    FixedUpperMiddle = 3
    FixedMiddle = 4
    FixedLowerMiddle = 5
    FixedLower = 6
    SwingUpper = 7
    SwingUpperMiddle = 8
    SwingMiddle = 9
    SwingLowerMiddle = 10
    SwingLower = 11


class DehumidifierMode(IntEnum):
    Default = 0
    AnionOnly = 9


def generate_temperature_record(temp_f):
    temSet = round((temp_f - 32.0) * 5.0 / 9.0)
    temRec = (int)((((temp_f - 32.0) * 5.0 / 9.0) - temSet) > 0)
    return {"f": temp_f, "temSet": temSet, "temRec": temRec}


TEMP_MIN = 8
TEMP_MAX = 30
TEMP_OFFSET = 40
TEMP_MIN_F = 46
TEMP_MAX_F = 86
TEMP_MIN_TABLE = -60
TEMP_MAX_TABLE = 60
TEMP_MIN_TABLE_F = -76
TEMP_MAX_TABLE_F = 140
TEMP_TABLE = [generate_temperature_record(x) for x in range(TEMP_MIN_TABLE_F, TEMP_MAX_TABLE_F + 1)]
HUMIDITY_MIN = 30
HUMIDITY_MAX = 80


def sensor_raw_to_celsius_str(raw) -> str:
    """Dual display for TemSen/TemsSenOut raws: `70 (30 C)`.

    Single fork-owned raw-to-C formula feeding the CLI display path;
    TemUn is read as a note only and never switches this display (D-06).
    Assumes the non-v4 offset encoding (raw = °C + TEMP_OFFSET); v4
    plain-°C raws pass through the getters unconverted and should not
    use this helper.
    """
    return f"{raw} ({raw - TEMP_OFFSET} C)"


class Device(DeviceProtocol2, Taskable):
    """Class representing a physical device, it's state and properties.

    Devices must be bound, either by discovering their presence, or supplying a persistent
    device key which is then used for communication (and encryption) with the unit. See the
    `bind` function for more details on how to do this.

    Once a device is bound occasionally call `update_state` to request and update state from
    the HVAC, as it is possible that it changes state from other sources.

    Attributes:
        power: A boolean indicating if the unit is on or off
        mode: An int indicating operating mode, see `Mode` enum for possible values
        target_temperature: The target temperature, ignore if in Auto, Fan or Steady Heat mode
        temperature_units: An int indicating unit of measurement, see `TemperatureUnits` enum for possible values
        current_temperature: The current temperature
        fan_speed: An int indicating fan speed, see `FanSpeed` enum for possible values
        fresh_air: A boolean indicating if fresh air valve is open, if present
        xfan: A boolean to enable the fan to dry the coil, only used for cool and dry modes
        anion: A boolean to enable the ozone generator, if present
        sleep: A boolean to enable sleep mode, which adjusts temperature over time
        light: A boolean to enable the light on the unit, if present
        horizontal_swing: An int to control the horizontal blade position, see `HorizontalSwing` enum for possible values
        vertical_swing: An int to control the vertical blade position, see `VerticalSwing` enum for possible values
        quiet: A boolean to enable quiet operation
        turbo: A boolean to enable turbo operation (heat or cool faster initially)
        steady_heat: When enabled unit will maintain a target temperature of 8 degrees C
        power_save: A boolen to enable power save operation
        light_sensor: A boolean to enable the ambient light sensor, if present
        uvc_control: A boolean to enable UVC sterilization, if present
        all_error: Device error bitmask/status reported by the unit
        app_timer: App-managed timer value reported by the unit
        ai_energy_save_display: A boolean for the AI energy-save display feature, if present
        model_type: Device model type identifier reported by the unit
        current_temperature_outdoor: Outdoor temperature reported by the unit, if present
        fault_display: Fault display code/status reported by the unit
        anti_direct_blow: A boolean to enable anti-direct-blow, if present
        elec_energy: Electric energy related value reported by the unit
        target_humidity: An int to set the target relative humidity
        current_humidity: The current relative humidity
        clean_filter: A bool to indicate the filter needs cleaning
        water_full: A bool to indicate the water tank is full
        hid: Indoor unit firmware identifier string
        in_hid: Additional indoor firmware identifier, if present
        oeep_hid: Outdoor/EEP firmware identifier, if present
        ota_hid: OTA firmware identifier, if present
        bc: Device barcode / code string, if present
    """

    # Identity/firmware string cols requested by the app separately from normal HVAC props.
    # Kept off Props so update_state stays focused on operational state.
    IDENTITY_COLS = ("hid", "InHid", "OEEPHid", "OTAHid", "bc")

    def __init__(self, device_info: DeviceInfo, timeout: int = 120, bind_timeout: int = 10, loop: AbstractEventLoop = None):
        """Initialize the device object

        Args:
            device_info (DeviceInfo): Information about the physical device
            timeout (int): Timeout for device communication
            bind_timeout (int): Timeout for binding to the device, keep this short to prevent delays determining the
                                correct device cipher to use
            loop (AbstractEventLoop): The event loop to run the device operations on
        """
        DeviceProtocol2.__init__(self, timeout)
        Taskable.__init__(self, loop)
        self._logger = logging.getLogger(__name__)
        self.device_info: DeviceInfo = device_info

        self._bind_timeout = bind_timeout

        """ Device properties """
        self.hid = None
        self.in_hid = None
        self.oeep_hid = None
        self.ota_hid = None
        self.bc = None
        self.version = None
        self.check_version = True
        self._properties = {}
        self._dirty = []
        self._buzzer = True

        self._valid_state: asyncio.Event = asyncio.Event()
        self._valid_state.clear()

    async def bind(
        self,
        key: str = None,
        cipher: Union[CipherV1, CipherV2, None] = None,
    ):
        """Run the binding procedure.

        Binding is a finicky procedure, and happens in 1 of 2 ways:
            1 - Without the key, binding must pass the device info structure immediately following
                the search devices procedure. There is only a small window to complete registration.
            2 - With a key, binding is implicit and no further action is required

            Both approaches result in a device_key which is used as like a persistent session id.

        Args:
            cipher (CipherV1 | CipherV2): The cipher type to use for encryption, if None will attempt to detect the correct one
            key (str): The device key, when provided binding is a NOOP, if None binding will
                       attempt to negotiate the key with the device. cipher must be provided.

        Raises:
            DeviceNotBoundError: If binding was unsuccessful and no key returned
            DeviceTimeoutError: The device didn't respond
        """

        if key:
            if not cipher:
                raise ValueError("cipher must be provided when key is provided")
            else:
                cipher.key = key
                self.device_cipher = cipher
                return

        if not self.device_info:
            raise DeviceNotBoundError

        if self._transport is None:
            self._transport, _ = await self._loop.create_datagram_endpoint(
                lambda: self, remote_addr=(self.device_info.ip, self.device_info.port)
            )

        self._logger.info("Starting device binding to %s", str(self.device_info))

        try:
            if cipher is not None:
                await self.__bind_internal(cipher)
            else:
                """ Try binding with CipherV1 first, if that fails try CipherV2"""
                try:
                    self._logger.info("Attempting to bind to device using CipherV1")
                    await self.__bind_internal(CipherV1())
                except asyncio.TimeoutError:
                    self._logger.info("Attempting to bind to device using CipherV2")
                    await self.__bind_internal(CipherV2())

        except asyncio.TimeoutError:
            raise DeviceTimeoutError

        if not self.device_cipher:
            raise DeviceNotBoundError
        else:
            self._logger.info("Bound to device using key %s", self.device_cipher.key)

    async def __bind_internal(self, cipher: Union[CipherV1, CipherV2]):
        """Internal binding procedure, do not call directly"""
        await self.send(self.create_bind_message(self.device_info), cipher=cipher)
        task = self._loop.create_task(self.ready.wait())
        await asyncio.wait_for(task, timeout=self._bind_timeout)

    def handle_device_bound(self, key: str) -> None:
        """Handle the device bound message from the device"""
        DeviceProtocol2.handle_device_bound(self, key)
        self.device_cipher.key = key
        self._loop.create_task(self.update_state())

    async def request_version(self) -> None:
        """Request firmware / identity fields from the device.

        Requests the same identity cols the app queries (`hid`, `InHid`, `OEEPHid`,
        `OTAHid`, `bc`). `hid` is still used to derive `version` when possible.
        """
        if not self.device_cipher:
            await self.bind()

        try:
            await self.send(
                self.create_status_message(self.device_info, *self.IDENTITY_COLS)
            )

        except asyncio.TimeoutError:
            raise DeviceTimeoutError

    async def update_state(self):
        """Update the internal state of the device structure of the physical device, 0 for no wait
        """
        if not self.device_cipher:
            await self.bind()

        self._logger.debug("Updating device properties for (%s)", str(self.device_info))

        props = [x.value for x in Props]
        if not self.hid:
            props.append("hid")

        try:
            await self.send(self.create_status_message(self.device_info, *props))

        except asyncio.TimeoutError:
            raise DeviceTimeoutError

    def handle_state_update(self, **kwargs) -> None:
        """Handle incoming state and identity information from the device."""

        # Ex: hid = 362001000762+U-CS532AE(LT)V3.31.bin
        if "hid" in kwargs:
            self.hid = kwargs.pop("hid")
            if isinstance(self.hid, str):
                match = re.search(r"(?<=V)([\d.]+)\.bin$", self.hid)
                self.version = match and match.group(1)
            self._logger.info(f"Device version is {self.version}, hid {self.hid}")

        # Identity keep-last rule: cols absent from a reply (e.g. the empty
        # OTAHid probe) leave the previous values in place; only present keys update.
        if "InHid" in kwargs:
            self.in_hid = kwargs.pop("InHid")
        if "OEEPHid" in kwargs:
            self.oeep_hid = kwargs.pop("OEEPHid")
        if "OTAHid" in kwargs:
            self.ota_hid = kwargs.pop("OTAHid")
        if "bc" in kwargs:
            self.bc = kwargs.pop("bc")

        self._properties.update(kwargs)

        if self.check_version and Props.TEMP_SENSOR.value in kwargs:
            self.check_version = False
            temp = self.get_property(Props.TEMP_SENSOR)
            self._logger.debug(f"Checking for temperature offset, reported temp {temp}")
            # Wrong-type sensor values must never crash version detection; the
            # converted getters already yield None for them, so skip the check.
            if isinstance(temp, (int, float)) and temp and temp < TEMP_OFFSET:
                self.version = "4.0"
                self._logger.info(f"Device version changed to {self.version}, hid {self.hid}")
            self._logger.debug(f"Using device temperature {self.current_temperature}")

        self._valid_state.set()

    async def push_state_update(self):
        """Push any pending state updates to the unit
        """
        if not self._dirty:
            return

        if not self.device_cipher:
            await self.bind()

        self._logger.debug("Pushing state updates to (%s)", str(self.device_info))

        props = {}
        for name in self._dirty:
            value = self._properties.get(name)
            self._logger.debug("Sending remote state update %s -> %s", name, value)
            props[name] = value
            if name == Props.TEMP_SET.value:
                props[Props.TEMP_BIT.value] = self._properties.get(Props.TEMP_BIT.value)
                props[Props.TEMP_UNIT.value] = self._properties.get(
                    Props.TEMP_UNIT.value
                )

        if not self._buzzer:
            self._logger.debug("Disabling buzzer for command")
            props["Buzzer_ON_OFF"] = 1

        try:
            await self.send(self.create_command_message(self.device_info, **props))

        except asyncio.TimeoutError:
            raise DeviceTimeoutError
        else:
            self._dirty.clear()


    def __eq__(self, other):
        """Compare two devices for equality based on their properties state and device info."""
        return self.device_info == other.device_info \
            and self.raw_properties == other.raw_properties \
            and self.device_cipher.key == other.device_cipher.key

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def raw_properties(self) -> dict:
        return self._properties

    def get_property(self, name) -> Optional[Any]:
        """Generic lookup of properties tracked from the physical device"""
        if self._properties:
            return self._properties.get(name.value)
        return None

    def set_property(self, name, value):
        """Generic setting of properties for the physical device"""
        if not self._properties:
            self._properties = {}

        if self._properties.get(name.value) == value:
            return
        else:
            self._properties[name.value] = value
            if name.value not in self._dirty:
                self._dirty.append(name.value)

    @property
    def has_valid_state(self) -> bool:
        return self._valid_state.is_set()

    @property
    def power(self) -> Optional[bool]:
        prop = self.get_property(Props.POWER)
        return bool(prop) if prop is not None else None

    @power.setter
    def power(self, value: int):
        self.set_property(Props.POWER, int(value))

    @property
    def mode(self) -> Optional[int]:
        return self.get_property(Props.MODE)

    @mode.setter
    def mode(self, value: int):
        self.set_property(Props.MODE, int(value))

    def _convert_to_units(self, value, bit):
        if self.temperature_units != TemperatureUnits.F.value:
            return value

        if value < TEMP_MIN_TABLE or value > TEMP_MAX_TABLE:
            raise ValueError(f"Specified temperature {value} is out of range.")

        matching_temset = [t for t in TEMP_TABLE if t["temSet"] == value]

        try:
            f = next(t for t in matching_temset if t["temRec"] == bit)
        except StopIteration:
            f = matching_temset[0]

        return f["f"]

    @property
    def target_temperature(self) -> Optional[int]:
        temset = self.get_property(Props.TEMP_SET)
        temrec = self.get_property(Props.TEMP_BIT)
        if temset is None or temrec is None:
            return None
        return self._convert_to_units(temset, temrec)

    @target_temperature.setter
    def target_temperature(self, value: int):
        def validate(val):
            if val > TEMP_MAX or val < TEMP_MIN:
                raise ValueError(f"Specified temperature {val} is out of range.")

        if self.temperature_units == 1:
            rec = generate_temperature_record(value)
            validate(rec["temSet"])
            self.set_property(Props.TEMP_SET, rec["temSet"])
            self.set_property(Props.TEMP_BIT, rec["temRec"])
        else:
            validate(value)
            self.set_property(Props.TEMP_SET, int(value))

    @property
    def temperature_units(self) -> Optional[int]:
        return self.get_property(Props.TEMP_UNIT)

    @temperature_units.setter
    def temperature_units(self, value: int):
        self.set_property(Props.TEMP_UNIT, int(value))

    @property
    def current_temperature(self) -> Optional[int]:
        prop = self.get_property(Props.TEMP_SENSOR)
        if prop is not None:
            converted = self._convert_sensor_temperature(prop)
            if converted is not None:
                return converted

        return self.target_temperature

    @property
    def fan_speed(self) -> Optional[int]:
        return self.get_property(Props.FAN_SPEED)

    @fan_speed.setter
    def fan_speed(self, value: int):
        self.set_property(Props.FAN_SPEED, int(value))

    @property
    def fresh_air(self) -> Optional[bool]:
        prop = self.get_property(Props.FRESH_AIR)
        return bool(prop) if prop is not None else None

    @fresh_air.setter
    def fresh_air(self, value: bool):
        self.set_property(Props.FRESH_AIR, int(value))

    @property
    def xfan(self) -> Optional[bool]:
        prop = self.get_property(Props.XFAN)
        return bool(prop) if prop is not None else None

    @xfan.setter
    def xfan(self, value: bool):
        self.set_property(Props.XFAN, int(value))

    @property
    def anion(self) -> Optional[bool]:
        prop = self.get_property(Props.ANION)
        return bool(prop) if prop is not None else None

    @anion.setter
    def anion(self, value: bool):
        self.set_property(Props.ANION, int(value))

    @property
    def sleep(self) -> Optional[bool]:
        prop = self.get_property(Props.SLEEP)
        return bool(prop) if prop is not None else None

    @sleep.setter
    def sleep(self, value: bool):
        self.set_property(Props.SLEEP, int(value))
        self.set_property(Props.SLEEP_MODE, int(value))

    @property
    def light(self) -> Optional[bool]:
        prop = self.get_property(Props.LIGHT)
        return bool(prop) if prop is not None else None

    @light.setter
    def light(self, value: bool):
        self.set_property(Props.LIGHT, int(value))

    @property
    def horizontal_swing(self) -> Optional[int]:
        return self.get_property(Props.SWING_HORIZ)

    @horizontal_swing.setter
    def horizontal_swing(self, value: int):
        self.set_property(Props.SWING_HORIZ, int(value))

    @property
    def vertical_swing(self) -> Optional[int]:
        return self.get_property(Props.SWING_VERT)

    @vertical_swing.setter
    def vertical_swing(self, value: int):
        self.set_property(Props.SWING_VERT, int(value))

    @property
    def quiet(self) -> Optional[int]:
        return self.get_property(Props.QUIET)

    @quiet.setter
    def quiet(self, value: bool):
        self.set_property(Props.QUIET, 2 if value else 0)

    @property
    def turbo(self) -> Optional[bool]:
        prop = self.get_property(Props.TURBO)
        return bool(prop) if prop is not None else None

    @turbo.setter
    def turbo(self, value: bool):
        self.set_property(Props.TURBO, int(value))

    @property
    def steady_heat(self) -> Optional[bool]:
        prop = self.get_property(Props.STEADY_HEAT)
        return bool(prop) if prop is not None else None

    @steady_heat.setter
    def steady_heat(self, value: bool):
        self.set_property(Props.STEADY_HEAT, int(value))

    @property
    def power_save(self) -> Optional[bool]:
        prop = self.get_property(Props.POWER_SAVE)
        return bool(prop) if prop is not None else None

    @power_save.setter
    def power_save(self, value: bool):
        self.set_property(Props.POWER_SAVE, int(value))

    @property
    def light_sensor(self) -> Optional[bool]:
        prop = self.get_property(Props.LIGHT_SENSOR)
        return bool(prop) if prop is not None else None

    @property
    def uvc_control(self) -> Optional[bool]:
        prop = self.get_property(Props.UVC_CONTROL)
        return bool(prop) if prop is not None else None

    @property
    def all_error(self) -> Optional[int]:
        return self.get_property(Props.ALL_ERROR)

    @property
    def app_timer(self) -> Optional[int]:
        return self.get_property(Props.APP_TIMER)

    @property
    def ai_energy_save_display(self) -> Optional[bool]:
        prop = self.get_property(Props.AI_ENERGY_SAVE_DISPLAY)
        return bool(prop) if prop is not None else None

    @property
    def model_type(self) -> Optional[Any]:
        return self.get_property(Props.MODEL_TYPE)

    def _convert_sensor_temperature(self, prop) -> Optional[int]:
        """Sensor rule: TemSen/TemsSenOut raws are Celsius + TEMP_OFFSET.

        Wire encoding (upstream convention): the AC reports sensors as
        °C + 40 so wire values stay non-negative; firmware v4 reports
        plain °C (detected when a raw arrives below TEMP_OFFSET, see
        handle_state_update). Ground truth 2026-10-16 (operator
        thermometers vs MANUAL EXPERIMENT_01 snapshots): outdoor raw
        69-70 against 28 °C weather, indoor raw 70-72 against 29 °C
        room — raw-40 matches within integer rounding, while the 02-04
        raw-is-Fahrenheit reading was ~8 °C off on both sensors and is
        retired. Unit-aware: the result runs through _convert_to_units,
        so F-mode devices read °F (TemUn still never picks the formula,
        only the display units — D-06). Raw 0 is the no-sensor sentinel
        yielding None (falls back to the setpoint); wrong-type raws
        yield None instead of raising (02-02 guard).
        """
        if prop is None:
            return None

        try:
            raw = int(prop)
        except (TypeError, ValueError):
            logging.warning("Converting unexpected temperature sensor value %s", prop)
            return None

        if raw == 0:
            return None

        bit = self.get_property(Props.TEMP_BIT)
        bit = bit if bit is not None else 0
        v = self.version and int(self.version.split(".")[0])
        try:
            if v == 4:
                return self._convert_to_units(raw, bit)
            return self._convert_to_units(raw - TEMP_OFFSET, bit)
        except ValueError:
            logging.warning("Converting unexpected temperature sensor value %s", prop)
            return None

    @property
    def current_temperature_outdoor(self) -> Optional[int]:
        """Outdoor temperature from TemsSenOut, using the same offset rules as indoor."""
        return self._convert_sensor_temperature(
            self.get_property(Props.TEMP_SENSOR_OUTDOOR)
        )

    @property
    def fault_display(self) -> Optional[Any]:
        return self.get_property(Props.FAULT_DISPLAY)

    @property
    def anti_direct_blow(self) -> Optional[bool]:
        prop = self.get_property(Props.ANTI_DIRECT_BLOW)
        return bool(prop) if prop is not None else None

    @property
    def elec_energy(self) -> Optional[Any]:
        return self.get_property(Props.ELEC_ENERGY)

    @property
    def sleep_curve_l1(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_L1)

    @property
    def sleep_curve_h1(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_H1)

    @property
    def sleep_curve_l2(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_L2)

    @property
    def sleep_curve_h2(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_H2)

    @property
    def sleep_curve_l3(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_L3)

    @property
    def sleep_curve_h3(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_H3)

    @property
    def sleep_curve_l4(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_L4)

    @property
    def sleep_curve_h4(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_H4)

    @property
    def sleep_curve_l5(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_L5)

    @property
    def sleep_curve_h5(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_H5)

    @property
    def sleep_curve_l6(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_L6)

    @property
    def sleep_curve_h6(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_H6)

    @property
    def sleep_curve_l7(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_L7)

    @property
    def sleep_curve_h7(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_H7)

    @property
    def sleep_curve_l8(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_L8)

    @property
    def sleep_curve_h8(self) -> Optional[int]:
        return self.get_property(Props.SLEEP_CURVE_H8)

    @property
    def target_humidity(self) -> Optional[int]:
        prop = self.get_property(Props.HUM_SET)
        return 15 + (prop * 5) if prop is not None else None

    @target_humidity.setter
    def target_humidity(self, value: int):
        def validate(val):
            if value > HUMIDITY_MAX or val < HUMIDITY_MIN:
                raise ValueError(f"Specified temperature {val} is out of range.")

        self.set_property(Props.HUM_SET, (value - 15) // 5)

    @property
    def dehumidifier_mode(self) -> Optional[int]:
        return self.get_property(Props.DEHUMIDIFIER_MODE)

    @property
    def current_humidity(self) -> Optional[int]:
        return self.get_property(Props.HUM_SENSOR)

    @property
    def clean_filter(self) -> Optional[bool]:
        prop = self.get_property(Props.CLEAN_FILTER)
        return bool(prop) if prop is not None else None

    @property
    def water_full(self) -> Optional[bool]:
        prop = self.get_property(Props.WATER_FULL)
        return bool(prop) if prop is not None else None

    @property
    def buzzer(self) -> bool:
        return self._buzzer

    @buzzer.setter
    def buzzer(self, value: bool):
        self._buzzer = bool(value)
