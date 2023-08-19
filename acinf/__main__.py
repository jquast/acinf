#!/usr/bin/env python
# This single-file script controls fan levels and retrieves sensor data from an
# AC Infinity 69 controller.
#
# This script is a bit slow, because we forcefully disconnect using 'bluetoothctl' command
# before re-connecting and re-subscribing to the notification channel. The reason this is
# done is because it is much more reliable with it than without it.
import json
import logging
import asyncio
import struct
import collections
import subprocess

# 3rd party
import wrapt_timeout_decorator
import crccheck.crc
import tenacity
import bleak

BinDef = collections.namedtuple('BINDATA', ('fmt', 'byte_range', 'transform'))
BinaryDefinitions = {
    'temperature_c': BinDef(fmt='>H', byte_range=slice(8, 10), transform=lambda val: float(val) / 100.0),
    'temperature_f': BinDef(fmt='>H', byte_range=slice(8, 10), transform=lambda val: (((float(val) / 100.0) * 9.0) / 5.0) + 32.0),
    'humidity': BinDef(fmt='>H', byte_range=slice(10, 12), transform=lambda val: float(val) / 100.0),
    'vpd_kpa': BinDef(fmt='>H', byte_range=slice(12, 14), transform=lambda val: float(val) / 100.0),
}

UUID_READ_ADDRESS = "70d51002-2c7f-4e75-ae8a-d758951ce4e0"
UUID_WRITE_ADDRESS = "70d51001-2c7f-4e75-ae8a-d758951ce4e0"

log = logging.Logger('acinf')

@tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
                stop=tenacity.stop_after_delay(60),
                before_sleep=tenacity.before_sleep_log(log, logging.WARNING))
@wrapt_timeout_decorator.timeout(60)
async def get_ac_infinity_fan(mac_address):
    # need to disconnect before re-connecting again, for some reason.
    # this isn't possible with bleak, but it is possible with 'bluetoothctl' cli, stdout and error is redirected to /dev/null,
    if subprocess.call(['which', 'bluetoothctl'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        subprocess.call(['bluetoothctl', 'disconnect', mac_address], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    async with bleak.BleakClient(mac_address) as client:
        queue = asyncio.Queue()
        async def callback_handler(sender, data):
            log.debug('got %r from %r', data.hex(), mac_address)
            if len(data) == 34:
                await queue.put(data)
                await client.stop_notify(UUID_READ_ADDRESS)
            else:
                log.debug('dumped bytes, %r', data)
        await client.start_notify(UUID_READ_ADDRESS, callback_handler)

        data = await queue.get()
        return {
            name: acb.transform(struct.unpack(acb.fmt, data[acb.byte_range])[0])
            for name, acb in BinaryDefinitions.items()
        }

@tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
                stop=tenacity.stop_after_delay(60),
                before_sleep=tenacity.before_sleep_log(log, logging.WARNING))
@wrapt_timeout_decorator.timeout(60)
async def set_ac_infinity_fan(mac_address: str, velocity: int):
    client = bleak.BleakClient(mac_address)
    await client.connect()
    # "magic" values from mikeybatoz,
    # https://community.home-assistant.io/t/ac-infinity-bluetooth-69-pro-controllers-successful/514068/8
    aciuni = bytes.fromhex("a5000008013bb191")
    header = bytes.fromhex("00031001")
    power = bytes.fromhex("0212")
    direction = bytes.fromhex("01")
    params = bytes.fromhex("ff01")
    crcinst = crccheck.crc.Crc16CcittFalse()
    crcinst.process(header)
    crcinst.process(power)
    crcinst.process(direction)
    crcinst.process(bytes([velocity]))
    crcinst.process(params)
    data = aciuni + header + power + direction + bytes([velocity]) + params + crcinst.finalbytes()
    await client.write_gatt_char(UUID_WRITE_ADDRESS, data)
    await client.disconnect()

async def program(mac_address, action, value=None, log_level='ERROR'):
    logging.basicConfig(level=getattr(logging, log_level), format='%(asctime)s %(module)s %(levelname)s %(message)s')

    # for any reason, it is necessary to first 'discover' devices before communicating with them.
    ble_devices = await bleak.BleakScanner.discover()

    # warn about unfound devices; tenacity and .connect() can still push through, anyway
    if mac_address not in [d.address.upper() for d in ble_devices]:
        maybe_others = f", {len(mac_address)} found: {[d.address for d in ble_devices]}"
        log.warning(f"BLE Discover failed for {mac_address}{maybe_others}")

    if action == "get":
        data = await get_ac_infinity_fan(mac_address)
        if value is None:
            print(json.dumps(data, indent=4))
        else:
            print(data[value])
    else:  # "set"
        await set_ac_infinity_fan(mac_address=mac_address, velocity=value)


def parse_args():
    import argparse
    # parse arguments: $ python3 blefan_controller.py MAC_ADDRESS (get|set) (attribute|fan_level)
    attribute_names = BinaryDefinitions.keys()
    parser = argparse.ArgumentParser(epilog=f'Attributes available by "get" action: {", ".join(attribute_names)}')
    parser.add_argument('--log-level', default='ERROR', choices=['debug', 'info', 'warning', 'error'], help='log level')
    parser.add_argument('mac_address', type=str, help='MAC address of AC Infinity fan')
    parser.add_argument('action', type=str, choices=['get', 'set'], help='get or set fan level')
    parser.add_argument('value', default=None, nargs='?', type=str, help='get: given attribute, set: given fan level')
    vals = vars(parser.parse_args())
    if vals['action'] == 'set':
        try:
            vals['value'] = int(vals['value'])
            if vals['value'] not in range(0, 11):
                raise ValueError(vals['value'])
        except ValueError:
            parser.error('Third argument must be fan level 0-10, got: %r' % vals['value'])
    if vals['action'] == 'get' and vals['value'] is not None:
        assert vals['value'] in attribute_names, vals['value']
    vals['mac_address'] = vals['mac_address'].upper()
    vals['log_level'] = vals['log_level'].upper()
    return vals

def main():
    asyncio.run(program(**parse_args()))

if __name__ == '__main__':
    main()
