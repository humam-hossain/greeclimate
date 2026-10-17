import asyncio
import enum
import logging

import pytest

from greeclimate.cipher import CipherV1
from greeclimate.device import (
    Device,
    DeviceInfo,
    Props,
    TemperatureUnits,
    sensor_raw_to_celsius_str,
)
from greeclimate.exceptions import DeviceNotBoundError, DeviceTimeoutError


class FakeProps(enum.Enum):
    FAKE = "fake"


def get_mock_info():
    return (
        "1.1.1.0",
        "7000",
        "aabbcc001122",
        "MockDevice1",
        "MockBrand",
        "MockModel",
        "0.0.1-fake",
    )


def get_mock_state():
    return {
        "Pow": 1,
        "Mod": 3,
        "SetTem": 25,
        "TemSen": 29,
        "TemUn": 0,
        "WdSpd": 0,
        "Air": 0,
        "Blo": 0,
        "Health": 0,
        "SwhSlp": 0,
        "SlpMod": 0,
        "Lig": 1,
        "SwingLfRig": 1,
        "SwUpDn": 1,
        "Quiet": 0,
        "Tur": 0,
        "StHt": 0,
        "SvSt": 0,
        "TemRec": 0,
        "HeatCoolType": 0,
        "hid": "362001000762+U-CS532AE(LT)V3.31.bin",
        "Dmod": 0,
        "Dwet": 5,
        "DwatSen": 58,
        "Dfltr": 0,
        "DwatFul": 0,
        "LigSen": 0,
        "UvcControl": 0,
        "AllErr": 0,
        "AppTimer": 0,
        "AIEnSaveDis": 0,
        "ModelType": 1,
        "TemsSenOut": 70,
        "FaultDisplay": "0",
        "AntiDirectBlow": 0,
        "ElcEn": 0,
        "InHid": 0,
        "OEEPHid": 0,
        "OTAHid": "",
        "bc": "00000000000000000000000000000000",
        "Slp1L1": 160,
        "Slp1H1": 0,
        "Slp1L2": 160,
        "Slp1H2": 0,
        "Slp1L3": 160,
        "Slp1H3": 0,
        "Slp1L4": 160,
        "Slp1H4": 0,
        "Slp1L5": 160,
        "Slp1H5": 0,
        "Slp1L6": 160,
        "Slp1H6": 0,
        "Slp1L7": 160,
        "Slp1H7": 0,
        "Slp1L8": 160,
        "Slp1H8": 0,
    }


def get_mock_state_off():
    return {
        "Pow": 0,
        "Mod": 0,
        "SetTem": 0,
        "TemSen": 0,
        "TemUn": 0,
        "WdSpd": 0,
        "Air": 0,
        "Blo": 0,
        "Health": 0,
        "SwhSlp": 0,
        "SlpMod": 0,
        "Lig": 0,
        "SwingLfRig": 0,
        "SwUpDn": 0,
        "Quiet": 0,
        "Tur": 0,
        "StHt": 0,
        "SvSt": 0,
        "TemRec": 0,
        "HeatCoolType": 0,
        "Dmod": 0,
        "Dwet": 0,
        "DwatSen": 0,
        "Dfltr": 0,
        "DwatFul": 0,
        "LigSen": 0,
        "UvcControl": 0,
        "AllErr": 0,
        "AppTimer": 0,
        "AIEnSaveDis": 0,
        "ModelType": 1,
        "TemsSenOut": 0,
        "FaultDisplay": "0",
        "AntiDirectBlow": 0,
        "ElcEn": 0,
        "InHid": 0,
        "OEEPHid": 0,
        "OTAHid": "",
        "bc": "00000000000000000000000000000000",
        "Slp1L1": 160,
        "Slp1H1": 0,
        "Slp1L2": 160,
        "Slp1H2": 0,
        "Slp1L3": 160,
        "Slp1H3": 0,
        "Slp1L4": 160,
        "Slp1H4": 0,
        "Slp1L5": 160,
        "Slp1H5": 0,
        "Slp1L6": 160,
        "Slp1H6": 0,
        "Slp1L7": 160,
        "Slp1H7": 0,
        "Slp1L8": 160,
        "Slp1H8": 0,
    }


def get_mock_state_on():
    return {
        "Pow": 1,
        "Mod": 1,
        "SetTem": 1,
        "TemSen": 1,
        "TemUn": 1,
        "WdSpd": 1,
        "Air": 1,
        "Blo": 1,
        "Health": 1,
        "SwhSlp": 1,
        "SlpMod": 1,
        "Lig": 1,
        "SwingLfRig": 1,
        "SwUpDn": 1,
        "Quiet": 2,
        "Tur": 1,
        "StHt": 1,
        "SvSt": 1,
        "TemRec": 0,
        "HeatCoolType": 0,
        "Dmod": 0,
        "Dwet": 3,
        "DwatSen": 1,
        "Dfltr": 0,
        "DwatFul": 0,
        "LigSen": 1,
        "UvcControl": 1,
        "AllErr": 0,
        "AppTimer": 30,
        "AIEnSaveDis": 1,
        "ModelType": 1,
        "TemsSenOut": 70,
        "FaultDisplay": "0",
        "AntiDirectBlow": 1,
        "ElcEn": 0,
        "InHid": 0,
        "OEEPHid": 0,
        "OTAHid": "",
        "bc": "00000000000000000000000000000000",
        "Slp1L1": 160,
        "Slp1H1": 0,
        "Slp1L2": 160,
        "Slp1H2": 0,
        "Slp1L3": 160,
        "Slp1H3": 0,
        "Slp1L4": 160,
        "Slp1H4": 0,
        "Slp1L5": 160,
        "Slp1H5": 0,
        "Slp1L6": 160,
        "Slp1H6": 0,
        "Slp1L7": 160,
        "Slp1H7": 0,
        "Slp1L8": 160,
        "Slp1H8": 0,
    }


def get_mock_state_no_temperature():
    return {
        "Pow": 1,
        "Mod": 3,
        "SetTem": 25,
        "TemUn": 0,
        "WdSpd": 0,
        "Air": 0,
        "Blo": 0,
        "Health": 0,
        "SwhSlp": 0,
        "SlpMod": 0,
        "Lig": 1,
        "SwingLfRig": 1,
        "SwUpDn": 1,
        "Quiet": 0,
        "Tur": 0,
        "StHt": 0,
        "SvSt": 0,
        "TemRec": 0,
        "HeatCoolType": 0,
        "Dmod": 0,
        "Dwet": 1,
        "DwatSen": 1,
        "Dfltr": 0,
        "DwatFul": 0,
        "LigSen": 0,
        "UvcControl": 0,
        "AllErr": 0,
        "AppTimer": 0,
        "AIEnSaveDis": 0,
        "ModelType": 1,
        "TemsSenOut": 0,
        "FaultDisplay": "0",
        "AntiDirectBlow": 0,
        "ElcEn": 0,
        "InHid": 0,
        "OEEPHid": 0,
        "OTAHid": "",
        "bc": "00000000000000000000000000000000",
    }


def get_mock_state_bad_temp():
    return {"TemSen": 69, "hid": "362001060297+U-CS532AF(MTK).bin"}


def get_mock_state_0c_v4_temp():
    return {"TemSen": 0, "hid": "362001000762+U-CS532AE(LT)V4.bin"}


def get_mock_state_0c_v3_temp():
    return {"TemSen": 0, "hid": "362001000762+U-CS532AE(LT)V3.31.bin"}


async def generate_device_mock_async():
    d = Device(DeviceInfo("1.1.1.1", 7000, "f4911e7aca59", "1e7aca59"))
    await d.bind(key="St8Vw1Yz4Bc7Ef0H", cipher=CipherV1())
    return d


def test_device_info_equality(send):
    """The only way to get the key through binding is by scanning first"""

    props = [
        "1.1.1.0",
        "7000",
        "aabbcc001122",
        "MockDevice1",
        "MockBrand",
        "MockModel",
        "0.0.1-fake",
    ]

    # When all properties match the device info is the same
    assert DeviceInfo(*props) == DeviceInfo(*props)

    # When any property differs the device info is not the same
    for i in range(2, len(props)):
        new_props = props.copy()
        new_props[i] = "modified_prop"
        assert DeviceInfo(*new_props) != DeviceInfo(*props)


@pytest.mark.asyncio
async def test_get_device_info(cipher, send):
    """Initialize device, check properties."""

    info = DeviceInfo(*get_mock_info())
    device = Device(info)

    assert device.device_info == info

    fake_key = "abcdefgh12345678"
    await device.bind(key=fake_key, cipher=CipherV1())

    assert device.device_cipher is not None
    assert device.device_cipher.key == fake_key


@pytest.mark.asyncio
async def test_device_bind(cipher, send):
    """Check that the device returns a device key when binding."""

    info = DeviceInfo(*get_mock_info())
    device = Device(info, timeout=1, bind_timeout=1)
    fake_key = "abcdefgh12345678"
    
    def fake_send(*args, **kwargs):
        """Emulate a bind event"""
        if not device.ready.is_set():
            device.device_cipher = CipherV1(fake_key.encode())
            device.handle_device_bound(fake_key)
        else:
            device.handle_state_update(**get_mock_state())
    send.side_effect = fake_send

    assert device.device_info == info
    await device.bind()
    assert send.call_count == 2   # 1 for bind, 2 for update_state

    assert device.device_cipher is not None
    assert device.device_cipher.key == fake_key
    
    # Bind with cipher already set
    await device.bind()
    assert send.call_count == 3 


@pytest.mark.asyncio
async def test_device_bind_timeout(cipher, send):
    """Check that the device handles timeout errors when binding."""
    info = DeviceInfo(*get_mock_info())
    device = Device(info, timeout=1, bind_timeout=1)

    with pytest.raises(DeviceTimeoutError):
        await device.bind()
        assert send.call_count == 1

    assert device.device_cipher is None


@pytest.mark.asyncio
async def test_device_bind_none(cipher, send):
    """Check that the device handles bad binding sequences."""
    info = DeviceInfo(*get_mock_info())
    device = Device(info, timeout=1, bind_timeout=1)

    def fake_send(*args, **kwargs):
        device.ready.set()
    send.side_effect = fake_send

    with pytest.raises(DeviceNotBoundError):
        await device.bind()
        assert send.call_count == 1

    assert device.device_cipher is None


@pytest.mark.asyncio
async def test_device_late_bind_from_update(cipher, send):
    """Check that the device handles late binding sequences."""
    info = DeviceInfo(*get_mock_info())
    device = Device(info, timeout=1, bind_timeout=1)
    fake_key = "abcdefgh12345678"

    def fake_send(*args, **kwargs):
        if not device.ready.is_set():
            device.device_cipher = CipherV1(fake_key.encode())
            device.handle_device_bound(fake_key)
        else:
            device.handle_state_update(**get_mock_state())
    send.side_effect = fake_send

    await device.update_state()
    assert send.call_count == 3
    assert device.device_cipher.key == fake_key

    device.power = True

    send.side_effect = None
    await device.push_state_update()
    
    assert device.device_cipher is not None
    assert device.device_cipher.key == fake_key


@pytest.mark.asyncio
async def test_device_late_bind_from_request_version(cipher, send):
    """Check that the device handles late binding sequences."""
    info = DeviceInfo(*get_mock_info())
    device = Device(info, timeout=1, bind_timeout=1)
    fake_key = "abcdefgh12345678"

    def fake_send(*args, **kwargs):
        if not device.ready.is_set():
            device.device_cipher = CipherV1(fake_key.encode())
            device.handle_device_bound(fake_key)
        else:
            device.handle_state_update(**get_mock_state())
    send.side_effect = fake_send

    await device.request_version()
    assert send.call_count == 3
    assert device.device_cipher.key == fake_key
    
    
@pytest.mark.asyncio
async def test_device_bind_no_cipher(cipher, send):
    """Check that the device handles late binding sequences."""
    info = DeviceInfo(*get_mock_info())
    device = Device(info, timeout=1, bind_timeout=1)
    fake_key = "abcdefgh12345678"
    
    with pytest.raises(ValueError):
        await device.bind(fake_key)


@pytest.mark.asyncio
async def test_device_bind_no_device_info(cipher, send):
    """Check that the device handles late binding sequences."""
    device = Device(None, timeout=1, bind_timeout=1)
    
    with pytest.raises(DeviceNotBoundError):
        await device.bind()


@pytest.mark.asyncio
async def test_update_properties(cipher, send):
    """Check that properties can be updates."""
    device = await generate_device_mock_async()

    for p in Props:
        assert device.get_property(p) is None

    def fake_send(*args, **kwargs):
        state = get_mock_state()
        device.handle_state_update(**state)
    send.side_effect = fake_send

    await device.update_state()

    for p in Props:
        assert device.get_property(p) is not None
        assert device.get_property(p) == get_mock_state()[p.value]


@pytest.mark.asyncio
async def test_update_properties_timeout(cipher, send):
    """Check that timeouts are handled when properties are updates."""
    device = await generate_device_mock_async()

    send.side_effect = asyncio.TimeoutError
    with pytest.raises(DeviceTimeoutError):
        await device.update_state()


@pytest.mark.asyncio
async def test_set_properties_not_dirty(cipher, send):
    """Check that the state isn't pushed when properties unchanged."""
    device = await generate_device_mock_async()

    await device.push_state_update()
    assert send.call_count == 0


@pytest.mark.asyncio
async def test_set_properties(cipher, send):
    """Check that state is pushed when properties are updated."""
    device = await generate_device_mock_async()

    device.power = True
    device.mode = 1
    device.temperature_units = 1
    device.fan_speed = 1
    device.fresh_air = True
    device.xfan = True
    device.anion = True
    device.sleep = True
    device.light = True
    device.horizontal_swing = 1
    device.vertical_swing = 1
    device.quiet = True
    device.turbo = True
    device.steady_heat = True
    device.power_save = True
    # 02-04 read-only narrowing (D-08): light_sensor, uvc_control, app_timer,
    # ai_energy_save_display, and anti_direct_blow are getter-only, so they are
    # never assigned here and never pushed; test_new_app_properties pins the
    # AttributeError half of that contract below.
    device.target_humidity = 30

    await device.push_state_update()
    send.assert_called_once()

    for p in Props:
        if p not in (
            Props.TEMP_SENSOR,
            Props.TEMP_SET,
            Props.TEMP_BIT,
            Props.UNKNOWN_HEATCOOLTYPE,
            Props.HUM_SENSOR,
            Props.DEHUMIDIFIER_MODE,
            Props.WATER_FULL,
            Props.CLEAN_FILTER,
            Props.ALL_ERROR,
            Props.MODEL_TYPE,
            Props.TEMP_SENSOR_OUTDOOR,
            Props.FAULT_DISPLAY,
            Props.ELEC_ENERGY,
            # 02-04: the five narrowed props are read-only and never pushed.
            Props.LIGHT_SENSOR,
            Props.UVC_CONTROL,
            Props.APP_TIMER,
            Props.AI_ENERGY_SAVE_DISPLAY,
            Props.ANTI_DIRECT_BLOW,
            Props.SLEEP_CURVE_L1,
            Props.SLEEP_CURVE_H1,
            Props.SLEEP_CURVE_L2,
            Props.SLEEP_CURVE_H2,
            Props.SLEEP_CURVE_L3,
            Props.SLEEP_CURVE_H3,
            Props.SLEEP_CURVE_L4,
            Props.SLEEP_CURVE_H4,
            Props.SLEEP_CURVE_L5,
            Props.SLEEP_CURVE_H5,
            Props.SLEEP_CURVE_L6,
            Props.SLEEP_CURVE_H6,
            Props.SLEEP_CURVE_L7,
            Props.SLEEP_CURVE_H7,
            Props.SLEEP_CURVE_L8,
            Props.SLEEP_CURVE_H8,
        ):
            assert device.get_property(p) is not None
            assert device.get_property(p) == get_mock_state_on()[p.value]


@pytest.mark.asyncio
async def test_set_properties_timeout(cipher, send):
    """Check timeout handling when pushing state changes."""
    device = await generate_device_mock_async()

    device.power = True
    device.mode = 1
    device.temperature_units = 1
    device.fan_speed = 1
    device.fresh_air = True
    device.xfan = True
    device.anion = True
    device.sleep = True
    device.light = True
    device.horizontal_swing = 1
    device.vertical_swing = 1
    device.quiet = True
    device.turbo = True
    device.steady_heat = True
    device.power_save = True
    
    assert len(device._dirty)

    send.reset_mock()
    send.side_effect = [asyncio.TimeoutError, asyncio.TimeoutError, asyncio.TimeoutError]
    with pytest.raises(DeviceTimeoutError):
        await device.push_state_update()

    assert len(device._dirty)


@pytest.mark.asyncio
async def test_uninitialized_properties(cipher, send):
    """Check uninitialized property handling."""
    device = await generate_device_mock_async()

    assert not device.power
    assert device.mode is None
    assert device.target_temperature is None
    assert device.current_temperature is None
    assert device.temperature_units is None
    assert device.fan_speed is None
    assert device.target_humidity is None
    assert not device.fresh_air
    assert not device.xfan
    assert not device.anion
    assert not device.sleep
    assert not device.light
    assert device.horizontal_swing is None
    assert device.vertical_swing is None
    assert not device.quiet
    assert not device.turbo
    assert not device.steady_heat
    assert not device.power_save
    assert not device.light_sensor
    assert not device.uvc_control
    assert device.all_error is None
    assert device.app_timer is None
    assert not device.ai_energy_save_display
    assert device.model_type is None
    assert device.current_temperature_outdoor is None
    assert device.fault_display is None
    assert not device.anti_direct_blow
    assert device.elec_energy is None
    assert device.in_hid is None
    assert device.oeep_hid is None
    assert device.ota_hid is None
    assert device.bc is None


@pytest.mark.asyncio
async def test_update_current_temp_unsupported(cipher, send):
    """Check that properties can be updates."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        state = get_mock_state_no_temperature()
        device.handle_state_update(**state)
    send.side_effect = fake_send

    await device.update_state()

    assert device.get_property(Props.TEMP_SENSOR) is None
    assert device.current_temperature == device.target_temperature


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "temsen,hid",
    [
        (69, "362001000762+U-CS532AE(LT)V3.31.bin"),
        (61, "362001061060+U-W04HV3.29.bin"),
        (62, "362001061147+U-ZX6045RV1.01.bin"),
    ],
)
async def test_update_current_temp_v3(temsen, hid, cipher, send):
    """Check that properties can be updates."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        device.handle_state_update(TemSen=temsen, hid=hid)
    send.side_effect = fake_send

    await device.update_state()
    
    assert device.get_property(Props.TEMP_SENSOR) is not None
    # Sensor rule (ground truth 2026-10-16): raws are °C + TEMP_OFFSET,
    # so the getter returns temsen - 40; display helper shows the dual form.
    assert device.current_temperature == temsen - 40


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "temsen,hid",
    [
        (21, "362001060297+U-CS532AF(MTK)V4.bin"),
        (21, "362001060297+U-CS532AF(MTK)V2.bin"),
        (22, "362001061383+U-BL3332_JDV1.bin"),
        (23, "362001061217+U-W04NV7.bin"),
    ],
)
async def test_update_current_temp_v4(temsen, hid, cipher, send):
    """Check that properties can be updates."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        device.handle_state_update(TemSen=temsen, hid=hid)
    send.side_effect = fake_send

    await device.update_state()

    assert device.get_property(Props.TEMP_SENSOR) is not None
    assert device.current_temperature == temsen


@pytest.mark.asyncio
async def test_update_current_temp_bad(cipher, send):
    """Check that properties can be updates."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        device.handle_state_update(**get_mock_state_bad_temp())
    send.side_effect = fake_send

    await device.update_state()

    # Sensor rule: raw 69 is °C + 40, so 29 °C.
    assert device.current_temperature == 29


@pytest.mark.asyncio
async def test_update_current_temp_0C_v4(cipher, send):
    """Check that properties can be updates."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        device.handle_state_update(**get_mock_state_0c_v4_temp())
    send.side_effect = fake_send

    await device.update_state()

    # 02-04 locked rule (was `== get_mock_state_0c_v4_temp()["TemSen"]` == 0):
    # raw 0 is the no-sensor sentinel yielding None, so the getter falls back
    # to the target exactly like the v3 0C case below.
    assert device.current_temperature == device.target_temperature


@pytest.mark.asyncio
async def test_update_current_temp_0C_v3(cipher, send):
    """Check for devices without a temperature sensor."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        device.handle_state_update(**get_mock_state_0c_v3_temp())
    send.side_effect = fake_send

    await device.update_state()

    assert device.current_temperature == device.target_temperature


@pytest.mark.asyncio
@pytest.mark.parametrize("temperature", [18, 19, 20, 21, 22])
async def test_send_temperature_celsius(temperature, cipher, send):
    """Check that temperature is set and read properly in C."""
    state = get_mock_state()
    # Sensor rule: the AC reports TemSen as °C + 40, so the echo carries
    # temperature + 40 while the setpoint path still speaks Celsius.
    state["TemSen"] = temperature + 40
    device = await generate_device_mock_async()
    device.temperature_units = TemperatureUnits.C
    device.target_temperature = temperature

    await device.push_state_update()
    assert send.call_count == 1

    def fake_send(*args, **kwargs):
        device.handle_state_update(**state)
    send.side_effect = fake_send

    await device.update_state()

    # Sensor rule: the echo carries temSet + 40 and the getter strips the
    # offset, so the Celsius reading round-trips through the offset path.
    assert device.current_temperature == temperature


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "temperature", [60, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 86]
)
async def test_send_temperature_farenheit(temperature, cipher, send):
    """Check that temperature is set and read properly in F."""
    temSet = round((temperature - 32.0) * 5.0 / 9.0)
    temRec = (int)((((temperature - 32.0) * 5.0 / 9.0) - temSet) > 0)

    state = get_mock_state()
    # Sensor rule: the echo carries temSet + 40 with a TemRec table round-trip.
    state["TemSen"] = temSet + 40
    state["TemRec"] = temRec
    state["TemUn"] = 1
    device = await generate_device_mock_async()

    device.temperature_units = TemperatureUnits.F
    device.target_temperature = temperature

    await device.push_state_update()
    assert send.call_count == 1

    def fake_send(*args, **kwargs):
        device.handle_state_update(**state)
    send.side_effect = fake_send

    await device.update_state()

    assert device.current_temperature == temperature


@pytest.mark.asyncio
@pytest.mark.parametrize("temperature", [-270, -61, 61, 100])
async def test_send_temperature_out_of_range_celsius(temperature, cipher, send):
    """Check that bad temperatures raise the appropriate error."""
    device = await generate_device_mock_async()

    device.temperature_units = TemperatureUnits.C
    with pytest.raises(ValueError):
        device.target_temperature = temperature


@pytest.mark.asyncio
@pytest.mark.parametrize("temperature", [-270, -61, 141])
async def test_send_temperature_out_of_range_farenheit_set(temperature, cipher, send):
    """Check that bad temperatures raise the appropriate error."""
    device = await generate_device_mock_async()

    for p in Props:
        assert device.get_property(p) is None

    device.temperature_units = TemperatureUnits.F
    with pytest.raises(ValueError):
        device.target_temperature = temperature


@pytest.mark.asyncio
@pytest.mark.parametrize("temperature", [-270, 150])
async def test_send_temperature_out_of_range_farenheit_get(temperature, cipher, send):
    """Check that bad temperatures raise the appropriate error."""
    device = await generate_device_mock_async()

    device.set_property(Props.TEMP_SET, 20)
    device.set_property(Props.TEMP_SENSOR, temperature)
    device.set_property(Props.TEMP_BIT, 0)
    device.temperature_units = TemperatureUnits.F

    t = device.current_temperature
    assert t == 68


@pytest.mark.asyncio
async def test_enable_disable_sleep_mode(cipher, send):
    """Check that properties can be updates."""
    device = await generate_device_mock_async()

    device.sleep = True
    await device.push_state_update()
    assert send.call_count == 1

    assert device.get_property(Props.SLEEP) == 1
    assert device.get_property(Props.SLEEP_MODE) == 1

    device.sleep = False
    await device.push_state_update()
    assert send.call_count == 2

    assert device.get_property(Props.SLEEP) == 0
    assert device.get_property(Props.SLEEP_MODE) == 0


@pytest.mark.asyncio
async def test_new_app_properties(cipher, send):
    """Newer app cols should be readable and (where applicable) writable."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        device.handle_state_update(**get_mock_state())
    send.side_effect = fake_send

    await device.update_state()

    assert device.light_sensor is False
    assert device.uvc_control is False
    assert device.all_error == 0
    assert device.app_timer == 0
    assert device.ai_energy_save_display is False
    assert device.model_type == 1
    assert device.fault_display == "0"
    assert device.anti_direct_blow is False
    assert device.elec_energy == 0
    # get_mock_state TemSen=29 is below TEMP_OFFSET, so firmware is treated as v4
    # and TemsSenOut uses the no-offset path (same as indoor TemSen on v4).
    assert device.version == "4.0"
    assert device.current_temperature_outdoor == 70
    # Identity fields extracted from the same state update
    assert device.in_hid == 0
    assert device.oeep_hid == 0
    assert device.ota_hid == ""
    assert device.bc == "00000000000000000000000000000000"

    # Read-only fields should not be writable via setters
    assert type(device).all_error.fset is None
    assert type(device).model_type.fset is None
    assert type(device).fault_display.fset is None
    assert type(device).elec_energy.fset is None
    assert type(device).current_temperature_outdoor.fset is None
    # 02-04 narrowed props (D-08) plus all 16 sleep getters: fset is None.
    assert type(device).light_sensor.fset is None
    assert type(device).uvc_control.fset is None
    assert type(device).app_timer.fset is None
    assert type(device).ai_energy_save_display.fset is None
    assert type(device).anti_direct_blow.fset is None
    for name in SLEEP_GETTERS:
        assert getattr(type(device), name).fset is None

    # 02-04 read-only rewrite (was: assign the five narrowed props, assert the
    # values stuck, then assert the push payload carried them): assignment now
    # raises AttributeError, nothing dirties, and push sends nothing.
    with pytest.raises(AttributeError):
        device.light_sensor = True
    with pytest.raises(AttributeError):
        device.uvc_control = True
    with pytest.raises(AttributeError):
        device.app_timer = 45
    with pytest.raises(AttributeError):
        device.ai_energy_save_display = True
    with pytest.raises(AttributeError):
        device.anti_direct_blow = True

    assert device._dirty == []

    send.reset_mock()
    send.side_effect = None
    await device.push_state_update()
    send.assert_not_called()


SLEEP_GETTERS = (
    "sleep_curve_l1",
    "sleep_curve_h1",
    "sleep_curve_l2",
    "sleep_curve_h2",
    "sleep_curve_l3",
    "sleep_curve_h3",
    "sleep_curve_l4",
    "sleep_curve_h4",
    "sleep_curve_l5",
    "sleep_curve_h5",
    "sleep_curve_l6",
    "sleep_curve_h6",
    "sleep_curve_l7",
    "sleep_curve_h7",
    "sleep_curve_l8",
    "sleep_curve_h8",
)


@pytest.mark.asyncio
async def test_sleep_curve_raw_defaults(cipher, send):
    """All 16 sleep getters return their 160/0 raw defaults with no interpretation."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        device.handle_state_update(**get_mock_state())
    send.side_effect = fake_send

    await device.update_state()

    for n in range(1, 9):
        assert getattr(device, f"sleep_curve_l{n}") == 160
        assert getattr(device, f"sleep_curve_h{n}") == 0


@pytest.mark.asyncio
async def test_sleep_curve_missing_column_returns_none(cipher, send):
    """Sleep getters return None when the AC never reported the column."""
    device = await generate_device_mock_async()
    device.handle_state_update(Pow=1)

    for name in SLEEP_GETTERS:
        assert getattr(device, name) is None


def test_sleep_curve_getters_are_read_only():
    """All 16 sleep properties are getter-only (no setter block at all)."""
    for name in SLEEP_GETTERS:
        assert getattr(Device, name).fset is None


@pytest.mark.asyncio
async def test_sleep_curve_wrong_type_passthrough(cipher, send):
    """Wrong-type dat yields the raw value, never a crash (tolerant lookup)."""
    device = await generate_device_mock_async()
    device.handle_state_update(Slp1L1="bad", Slp1H1=[0])

    assert device.sleep_curve_l1 == "bad"
    assert device.sleep_curve_h1 == [0]


# Newest operational cols from app ↔ AC traffic (sleep-curve Slp1* live in
# SLEEP_CURVE_COLS below and are asserted separately).
# Identity strings (hid/InHid/OEEPHid/OTAHid/bc) are Device attributes, not Props.
NEWEST_APP_COLS = {
    "Pow",
    "Mod",
    "TemUn",
    "SetTem",
    "TemRec",
    "WdSpd",
    "Tur",
    "Quiet",
    "SwUpDn",
    "SwingLfRig",
    "Air",
    "Blo",
    "Health",
    "SvSt",
    "Lig",
    "StHt",
    "SwhSlp",
    "SlpMod",
    "LigSen",
    "UvcControl",
    "Dmod",
    "Dwet",
    "HeatCoolType",
    "AllErr",
    "AppTimer",
    "AIEnSaveDis",
    "ModelType",
    "TemsSenOut",
    "FaultDisplay",
    "AntiDirectBlow",
    "ElcEn",
}

# Older fields kept for compatibility even if absent from newest app captures.
LEGACY_COMPAT_COLS = {
    "TemSen",
    "DwatSen",
    "Dfltr",
    "DwatFul",
}

# Sleep-curve cols (Slp1L*/Slp1H*) joined Props in Phase 2; the exclusion set is
# empty and the asserts below require the sleep cols instead of forbidding them.
EXCLUDED_SLEEP_CURVE_COLS = set()

SLEEP_CURVE_COLS = {
    "Slp1L1", "Slp1L2", "Slp1L3", "Slp1L4", "Slp1L5", "Slp1L6", "Slp1L7", "Slp1L8",
    "Slp1H1", "Slp1H2", "Slp1H3", "Slp1H4", "Slp1H5", "Slp1H6", "Slp1H7", "Slp1H8",
}

IDENTITY_COLS = {"hid", "InHid", "OEEPHid", "OTAHid", "bc"}


def test_props_include_newest_app_cols_and_legacy():
    """Props must cover newest app cols without dropping legacy fields."""
    prop_values = {p.value for p in Props}

    missing_new = NEWEST_APP_COLS - prop_values
    assert not missing_new, f"Missing newest app cols from Props: {missing_new}"

    missing_legacy = LEGACY_COMPAT_COLS - prop_values
    assert not missing_legacy, f"Legacy cols were removed from Props: {missing_legacy}"

    # Sleep curve cols are required members of Props (no unused marker, raw only)
    assert not (EXCLUDED_SLEEP_CURVE_COLS & prop_values)
    assert SLEEP_CURVE_COLS <= prop_values, (
        f"Missing sleep curve cols from Props: {SLEEP_CURVE_COLS - prop_values}"
    )

    # Identity cols are Device attributes, not Props members
    assert not (IDENTITY_COLS & prop_values)
    assert set(Device.IDENTITY_COLS) == IDENTITY_COLS

    # Every Props member must appear in the primary mock state used by update tests
    mock_keys = set(get_mock_state()) - IDENTITY_COLS
    missing_mock = prop_values - mock_keys
    assert not missing_mock, f"get_mock_state missing Props: {missing_mock}"


@pytest.mark.asyncio
async def test_update_state_requests_new_and_legacy_props(cipher, send):
    """update_state should query every Props value, including newer app cols."""
    device = await generate_device_mock_async()
    # Already bound with hid from a prior state so hid is not re-requested alone
    device.hid = "362001000762+U-CS532AE(LT)V3.31.bin"

    captured = {}

    async def fake_send(data, *args, **kwargs):
        pack = data.get("pack") if isinstance(data, dict) else None
        if isinstance(pack, dict) and "cols" in pack:
            captured["cols"] = list(pack["cols"])
        device.handle_state_update(**get_mock_state())

    send.side_effect = fake_send
    await device.update_state()

    assert "cols" in captured
    requested = set(captured["cols"])

    # Every Props member is requested on status update
    for p in Props:
        assert p.value in requested
        assert device.get_property(p) == get_mock_state()[p.value]

    # Newly added protocol fields from recent app traffic
    for name in (
        "LigSen",
        "UvcControl",
        "AllErr",
        "AppTimer",
        "AIEnSaveDis",
        "ModelType",
        "TemsSenOut",
        "FaultDisplay",
        "AntiDirectBlow",
        "ElcEn",
    ):
        assert name in requested
        assert name in {p.value for p in Props}

    # Legacy fields retained for older units (not always in newest app cols)
    for name in LEGACY_COMPAT_COLS:
        assert name in requested
        assert name in {p.value for p in Props}

    # Sleep curve cols are part of the bulk Props poll; identity strings are not
    assert not (EXCLUDED_SLEEP_CURVE_COLS & requested)
    assert SLEEP_CURVE_COLS <= requested
    assert "InHid" not in requested
    assert "OEEPHid" not in requested
    assert "OTAHid" not in requested
    assert "bc" not in requested


@pytest.mark.asyncio
async def test_push_includes_new_writable_props(cipher, send):
    """Narrowed new props are read-only: assignment raises, push sends nothing."""
    device = await generate_device_mock_async()

    # 02-04 read-only rewrite (was: assign five props, assert all five in the
    # command payload): with the D-08 setters deleted, every assignment below
    # must raise AttributeError and the dirty list must stay empty.
    with pytest.raises(AttributeError):
        device.light_sensor = True
    with pytest.raises(AttributeError):
        device.uvc_control = True
    with pytest.raises(AttributeError):
        device.app_timer = 15
    with pytest.raises(AttributeError):
        device.ai_energy_save_display = True
    with pytest.raises(AttributeError):
        device.anti_direct_blow = True

    assert device._dirty == []

    await device.push_state_update()
    send.assert_not_called()


@pytest.mark.asyncio
async def test_request_version_fetches_identity_cols(cipher, send):
    """request_version should query all identity/firmware string cols."""
    device = await generate_device_mock_async()
    captured = {}

    async def fake_send(data, *args, **kwargs):
        pack = data.get("pack") if isinstance(data, dict) else None
        if isinstance(pack, dict) and "cols" in pack:
            captured["cols"] = list(pack["cols"])
        device.handle_state_update(
            hid="362001065279+U-WB05RT13V1.21.bin",
            InHid=0,
            OEEPHid=0,
            OTAHid="ota-build",
            bc="00000000000000000000000000000000",
        )

    send.side_effect = fake_send
    await device.request_version()

    assert captured["cols"] == list(Device.IDENTITY_COLS)
    assert device.hid == "362001065279+U-WB05RT13V1.21.bin"
    assert device.version == "1.21"
    assert device.in_hid == 0
    assert device.oeep_hid == 0
    assert device.ota_hid == "ota-build"
    assert device.bc == "00000000000000000000000000000000"


@pytest.mark.asyncio
async def test_outdoor_temperature_v4(cipher, send):
    """Outdoor sensor follows the same v4 no-offset rule as indoor TemSen."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        device.handle_state_update(
            hid="362001000762+U-CS532AE(LT)V4.bin",
            TemsSenOut=21,
            TemRec=0,
        )

    send.side_effect = fake_send
    await device.update_state()
    assert device.current_temperature_outdoor == 21


@pytest.mark.asyncio
async def test_outdoor_temperature_v3_offset(cipher, send):
    """Outdoor sensor strips the +40 offset on pre-v4 firmware."""
    device = await generate_device_mock_async()
    # Keep check_version from rewriting firmware based on indoor TemSen.
    device.check_version = False
    device.version = "3.31"
    device.handle_state_update(TemsSenOut=70, TemRec=0)
    # 70 - 40 = 30 °C (ground truth 2026-10-16: raw 69-70 ≈ 28 °C weather).
    assert device.current_temperature_outdoor == 30


@pytest.mark.asyncio
async def test_outdoor_temperature_invalid_raw(cipher, send):
    """Invalid outdoor sensor values should not raise."""
    device = await generate_device_mock_async()
    device.handle_state_update(TemsSenOut="not-a-temp", TemRec=0)
    assert device.current_temperature_outdoor is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        (70, "70 (30 C)"),
        (68, "68 (28 C)"),
        (66, "66 (26 C)"),
        (71, "71 (31 C)"),
    ],
)
def test_sensor_raw_to_celsius_str_dual_display(raw, expected):
    """The raw-to-C display rule pins exact raw + (raw - 40) dual output."""
    assert sensor_raw_to_celsius_str(raw) == expected


@pytest.mark.asyncio
async def test_sensor_temperature_ignores_temun(cipher, send):
    """TemUn never picks the formula: raws decode identically, only display units differ (D-06)."""
    device = await generate_device_mock_async()
    device.check_version = False
    device.handle_state_update(TemSen=68, TemsSenOut=70, TemUn=0, TemRec=0)
    assert device.current_temperature == 28
    assert device.current_temperature_outdoor == 30
    assert sensor_raw_to_celsius_str(68) == "68 (28 C)"
    assert sensor_raw_to_celsius_str(70) == "70 (30 C)"
    device.handle_state_update(TemSen=68, TemsSenOut=70, TemUn=1, TemRec=0)
    # Same physical temps through the F table: 28 °C -> 82 °F, 30 °C -> 86 °F.
    assert device.current_temperature == 82
    assert device.current_temperature_outdoor == 86


@pytest.mark.asyncio
async def test_identity_fields_not_in_raw_properties(cipher, send):
    """Identity cols are Device attributes, not raw HVAC property dict entries."""
    device = await generate_device_mock_async()
    device.handle_state_update(**get_mock_state())

    assert device.hid is not None
    assert "hid" not in device.raw_properties
    assert "InHid" not in device.raw_properties
    assert "OEEPHid" not in device.raw_properties
    assert "OTAHid" not in device.raw_properties
    assert "bc" not in device.raw_properties
    # Operational props remain in raw_properties
    assert "Pow" in device.raw_properties
    assert "TemsSenOut" in device.raw_properties
    assert "AIEnSaveDis" in device.raw_properties


@pytest.mark.asyncio
async def test_request_version_timeout(cipher, send):
    """request_version should surface device timeouts."""
    device = await generate_device_mock_async()
    send.side_effect = asyncio.TimeoutError
    with pytest.raises(DeviceTimeoutError):
        await device.request_version()


@pytest.mark.asyncio
async def test_model_type_string_from_device(cipher, send):
    """Some firmwares report ModelType as a string; expose it as-is."""
    device = await generate_device_mock_async()
    device.handle_state_update(ModelType="32776")
    assert device.model_type == "32776"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "temperature", [59, 77, 86]
)
async def test_mismatch_temrec_farenheit(temperature, cipher, send):
    """Check that temperature is set and read properly in F."""
    temSet = round((temperature - 32.0) * 5.0 / 9.0)
    temRec = (int)((((temperature - 32.0) * 5.0 / 9.0) - temSet) > 0)
    
    state = get_mock_state()
    # Sensor rule: the echo carries temSet + 40, so a mismatched TemRec
    # falls back to the first table record for that temSet — the assert
    # below still passes through the offset path.
    state["TemSen"] = temSet + 40
    # Now, we alter the temRec on the device so it is not found in the table.
    state["TemRec"] = (temRec + 1) % 2
    state["TemUn"] = 1
    device = await generate_device_mock_async()
    device.temperature_units = TemperatureUnits.F
    device.target_temperature = temperature
    
    await device.push_state_update()
    assert send.call_count == 1

    def fake_send(*args, **kwargs):
        device.handle_state_update(**state)
    send.side_effect = None

    await device.update_state()

    assert device.current_temperature == temperature


@pytest.mark.asyncio
async def test_device_equality(send):
    """Check that two devices with the same info and key are equal."""

    info1 = DeviceInfo(*get_mock_info())
    device1 = Device(info1)
    await device1.bind(key="fake_key", cipher=CipherV1())

    info2 = DeviceInfo(*get_mock_info())
    device2 = Device(info2)
    await device2.bind(key="fake_key", cipher=CipherV1())

    assert device1 == device2

    # Change the key of the second device
    await device2.bind(key="another_fake_key", cipher=CipherV1())
    assert device1 != device2

    # Change the info of the second device
    info2 = DeviceInfo(*get_mock_info())
    device2 = Device(info2)
    device2.power = True
    await device2.bind(key="fake_key", cipher=CipherV1())
    assert device1 != device2


def test_device_key_set_get():
    """Check that the device key can be set and retrieved."""
    device = Device(DeviceInfo(*get_mock_info()))
    device.device_cipher = CipherV1()
    device.device_key = "fake_key"
    assert device.device_key == "fake_key"


@pytest.mark.asyncio
async def test_buzzer_default(cipher, send):
    """Check that buzzer is enabled by default."""
    device = await generate_device_mock_async()
    assert device.buzzer is True


@pytest.mark.asyncio
async def test_buzzer_disabled(cipher, send):
    """Check that disabling buzzer injects Buzzer_ON_OFF into commands."""
    device = await generate_device_mock_async()

    device.power = True
    device.buzzer = False
    await device.push_state_update()
    assert send.call_count == 1
    assert "Buzzer_ON_OFF" in send.call_args_list[0].args[0]["pack"]["opt"]
    assert not device.buzzer

    send.reset_mock()

    device.power = False
    device.buzzer = True
    await device.push_state_update()
    assert send.call_count == 1
    assert "Buzzer_ON_OFF" not in send.call_args_list[0].args[0]["pack"]["opt"]
    assert device.buzzer


@pytest.mark.asyncio
async def test_buzzer_disabled_every_command(cipher, send):
    """Check that Buzzer_ON_OFF is sent with every command when disabled."""
    device = await generate_device_mock_async()
    device.buzzer = False

    device.power = True
    await device.push_state_update()
    assert "Buzzer_ON_OFF" in send.call_args_list[0].args[0]["pack"]["opt"]

    send.reset_mock()

    device.mode = 1
    await device.push_state_update()
    assert "Buzzer_ON_OFF" in send.call_args_list[0].args[0]["pack"]["opt"]


@pytest.mark.asyncio
async def has_valid_state_with_valid_properties(cipher, send):
    """Check that the device has a valid state with valid properties."""
    device = await generate_device_mock_async()

    def fake_send(*args, **kwargs):
        state = get_mock_state()
        device.handle_state_update(**state)
    send.side_effect = fake_send

    await device.update_state()
    assert device.has_valid_state is True
   
   
@pytest.mark.asyncio
async def request_version_timeout_error(cipher, send):
    """Check that request_version raises DeviceTimeoutError when a timeout occurs."""
    device = await generate_device_mock_async()

    send.side_effect = asyncio.TimeoutError

    with pytest.raises(DeviceTimeoutError):
        await device.request_version()


# Tolerant transport edges (02-02): the AC drops AIEnSaveDis from `dat` while
# the request list stays fixed, so the fork zips strictly by the returned cols.
STAGE_2_REQUESTED_28 = [
    "Pow", "Mod", "TemUn", "SetTem", "TemRec", "WdSpd", "Tur", "Quiet",
    "SwUpDn", "SwingLfRig", "Air", "Blo", "Health", "SvSt", "Lig",
    "StHt", "SwhSlp", "SlpMod", "LigSen", "UvcControl", "Dmod",
    "Dwet", "HeatCoolType", "AllErr", "AppTimer", "AIEnSaveDis",
    "hid", "ModelType",
]


@pytest.mark.asyncio
async def test_dropped_aiensavedis_no_shift_and_none(cipher, send):
    """A reply missing AIEnSaveDis must not shift later cols; absent key reads None.

    The AC omits the column from both returned cols and dat (27/27, no length
    mismatch), so this proves zip-by-returned-cols, not the length guard.
    """
    device = await generate_device_mock_async()
    returned = [c for c in STAGE_2_REQUESTED_28 if c != "AIEnSaveDis"]
    values = list(range(len(returned)))

    device.packet_received(
        {"pack": {"t": "dat", "cols": returned, "dat": values}},
        ("1.1.1.1", 7000),
    )

    assert len(STAGE_2_REQUESTED_28) == 28
    assert len(returned) == 27
    assert device.hid == 25
    assert device.model_type == 26
    assert device.get_property(Props.AI_ENERGY_SAVE_DISPLAY) is None
    assert device.ai_energy_save_display is None


@pytest.mark.asyncio
async def test_dropped_tail_truncation_warns_and_reads_none(cipher, send, caplog):
    """A short dat drops only the tail keys with a warning; head values stay put."""
    device = await generate_device_mock_async()

    with caplog.at_level(logging.WARNING, logger="greeclimate.network"):
        device.packet_received(
            {"pack": {"t": "dat", "cols": ["Pow", "Mod", "SetTem"], "dat": [1, 0]}},
            ("1.1.1.1", 7000),
        )

    assert device.get_property(Props.POWER) == 1
    assert device.get_property(Props.MODE) == 0
    assert device.get_property(Props.TEMP_SET) is None
    assert any("length mismatch" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_wrong_type_tolerant_no_raise_and_none(cipher, send):
    """Wrong-type dat values must not raise; converted getters yield None."""
    device = await generate_device_mock_async()
    device.handle_state_update(TemSen="bad", TemRec=0, WdSpd={"odd": 1})

    assert device.version is None
    assert device.current_temperature is None
    assert device.fan_speed == {"odd": 1}


@pytest.mark.asyncio
async def test_identity_version_probe_accepts_observed_values(cipher, send):
    """request_version asks the five identity cols together; empties/zeros are values, not errors."""
    device = await generate_device_mock_async()
    captured = {}

    async def fake_send(data, *args, **kwargs):
        pack = data.get("pack") if isinstance(data, dict) else None
        if isinstance(pack, dict) and "cols" in pack:
            captured["cols"] = list(pack["cols"])
        device.handle_state_update(
            hid="362001065279+U-WB05RT13V1.21.bin",
            InHid=0,
            OEEPHid=0,
            OTAHid="",
            bc="00000000000000000000000000000000",
        )

    send.side_effect = fake_send
    await device.request_version()

    assert captured["cols"] == list(Device.IDENTITY_COLS)
    assert set(captured["cols"]) == {"hid", "InHid", "OEEPHid", "OTAHid", "bc"}
    assert device.hid == "362001065279+U-WB05RT13V1.21.bin"
    assert device.version == "1.21"
    assert device.in_hid == 0
    assert device.oeep_hid == 0
    assert device.ota_hid == ""
    assert device.bc == "00000000000000000000000000000000"
    assert len(device.bc) == 32


@pytest.mark.asyncio
async def test_version_untouched_for_non_string_hid(cipher, send):
    """A non-string hid updates the attribute but leaves the parsed version alone."""
    device = await generate_device_mock_async()
    device.handle_state_update(hid="362001065279+U-WB05RT13V1.21.bin")
    assert device.version == "1.21"

    device.handle_state_update(hid=12345)
    assert device.hid == 12345
    assert device.version == "1.21"


@pytest.mark.asyncio
async def test_identity_keep_last_ota_hid_on_empty_reply(cipher, send):
    """Cols absent from a reply (e.g. the empty OTAHid probe) keep previous values."""
    device = await generate_device_mock_async()
    device.handle_state_update(
        hid="362001065279+U-WB05RT13V1.21.bin",
        InHid=0,
        OEEPHid=0,
        OTAHid="ota-build",
        bc="00000000000000000000000000000000",
    )

    device.handle_state_update(Pow=1)  # reply carrying no identity keys
    device.handle_state_update()  # empty reply, e.g. the empty-cols OTAHid probe

    assert device.hid == "362001065279+U-WB05RT13V1.21.bin"
    assert device.version == "1.21"
    assert device.in_hid == 0
    assert device.oeep_hid == 0
    assert device.ota_hid == "ota-build"
    assert device.bc == "00000000000000000000000000000000"


@pytest.mark.asyncio
async def test_fan_speed_sentinel_raw_transient(cipher, send):
    """WdSpd stepless transient 70 must surface raw with no client-side clamping."""
    device = await generate_device_mock_async()
    device.handle_state_update(WdSpd=70)

    assert device.fan_speed == 70
    assert device.get_property(Props.FAN_SPEED) == 70

    # The setter takes any int as-is too; no range validation hides transients.
    device.fan_speed = 70
    assert device.get_property(Props.FAN_SPEED) == 70


@pytest.mark.asyncio
async def test_quiet_sentinel_raw_transient(cipher, send):
    """Quiet -1 no-op sentinel surfacing as 65535 must surface raw, unconverted."""
    device = await generate_device_mock_async()
    device.handle_state_update(Quiet=65535)

    assert device.quiet == 65535
    assert device.get_property(Props.QUIET) == 65535


@pytest.mark.asyncio
async def test_fault_display_int_and_str_passthrough(cipher, send):
    """FaultDisplay passes through both live int 0 and mock string "0" unchanged."""
    device = await generate_device_mock_async()

    device.handle_state_update(FaultDisplay=0)
    assert device.fault_display == 0

    device.handle_state_update(FaultDisplay="0")
    assert device.fault_display == "0"


@pytest.mark.asyncio
async def test_model_type_raw_int_passthrough(cipher, send):
    """ModelType passes through a raw int just as honestly as the string shape."""
    device = await generate_device_mock_async()
    device.handle_state_update(ModelType=32776)

    assert device.model_type == 32776 
