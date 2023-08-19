About
-----

This software provides basic CLI and API functionality for controlling a single
fan and reading sensor values from the AC Infinity Controller 69 Pro. 

Install
-------

::

    pip install acinf

This script was authored for python 3.10 and Linux, but other python versions and operating
systems may work.

Usage
-----

If everything is installed correctly, command ``acinf`` should have the following output::

    $ acinf
    usage: acinf [-h] [--log-level {debug,info,warning,error}] mac_address {get,set} [value]
    acinf: error: the following arguments are required: mac_address, action

To set fan level to 5 use command for example `MAC address`_ DE:AD:BE:EF:CA:FE::

    acinf DE:AD:BE:EF:CA:FE set 5

To show all values to stdout in json format::

    $ acinf DE:AD:BE:EF:CA:FE get
    {
        "temperature_c": 18.56,
        "temperature_f": 65.408,
        "humidity": 70.03,
        "vpd_kpa": 0.61
    }

To retrieve just a single value as ASCII float to stdout, combine `get` with any
of the following values *temperature_c*, *temperature_f*, *humidity*,
*vpd_kpa*::

    $ acinf DE:AD:BE:EF:CA:FE get temperature_f
    65.408

MAC address
-----------

To determine the MAC address of your AC Infinity controller on Linux, ensure the
bluetooth package is installed and execute `bluetoothctl`, then, command `scan on`,
examine devices marked 'NEW', or, enter command `devices`.

AC infinity controllers are marked 'ACI-E', as in the example below::

    linux# bluetoothctl
    Agent registered
    [CHG] Controller 00:11:22:33:44:66 Pairable: yes
    [bluetooth]# scan on
    Discovery started
    [CHG] Controller 00:11:22:33:44:66 Discovering: yes
    [NEW] Device AB:CD:EF:AB:CD:EF AB-CD-EF-AB-CD-EF
    [NEW] Device DE:AD:BE:EF:CA:FE ACI-E
    [NEW] Device AB:CD:EF:AB:CD:FF AB-CD-EF-AB-CD-FF

Pairing
-------

If you haven't previously paired with your device, do that now. Press and Hold
the bluetooth button on the controller until it begins flashing, then,
enter bluetoothctl command, `pair DE:AD:BE:EF:CA:FE`.

About
-----

This software is not affiliated with AC Infinity. AC Infinity is a trademark of
AC Infinity Inc. This software is not guaranteed to work with any particular
AC Infinity product. It is not guaranteed to work at all. Use at your own risk.

Caveats
-------

- Although 4 fans may be connected to the controller, this software only supports
  controlling a single fan.
- Do not execute more than 1 of these processes at a time. All 'get' and 'set' commands
  are failed if they exceed 1 minute, and so any scheduled execution of this command
  should be limited to approximately once per 2 minutes.
- This API and software has a very slow startup time, because it reconnects
  to the bluetooth device each time. Although it is possible to re-use a connection,
  I found persistent connections to be unreliable over long durations.
- Errors may often report to stderr, about timeout or failure to discover or connect,
  especially for long receiver distances, but all get or set operations are
  automatically retried for a full minute before failure.

Contributing
------------

This project is not very serious, if you wish to expand it for more features and devices,
consider making a pull requests and becoming a co-maintainer and feel free to fork.
Thanks, enjoy, and best wishes!
