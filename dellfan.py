#! /usr/bin/env python3

import argparse
import psutil
import subprocess
import sys
import time


def ipmi_raw(bytes_):
    subprocess.check_call(
        ["ipmitool", "raw"] + ["0x{:02x}".format(b) for b in bytes_]
    )


# Magic bytes from
# https://www.reddit.com/r/homelab/comments/7xqb11/dell_fan_noise_control_silence_your_poweredge/
def ipmi_disable_fan_control():
    ipmi_raw([0x30, 0x30, 0x01, 0x00])


def ipmi_set_fan_speed(speed):
    raw = int(round(speed*100))
    raw = min(raw, 100)
    ipmi_raw([0x30, 0x30, 0x02, 0xff, raw])


def temperature_to_fan_speed(temperature):
    # This is totally adhoc
    fan_speed = 1.0
    if temperature < 40:
        fan_speed = 0.0
    elif temperature < 70:
        fan_speed = (temperature - 40) / 30 * 0.5
    else:
        fan_speed = 1.0
    return fan_speed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r", "--poll-rate",
        type=float, default=10.,
    )
    parser.add_argument(
        "--dump-curve",
        action="store_true",
    )
    parser.add_argument(
        "--print",
        action="store_true",
    )
    args = parser.parse_args()

    if args.dump_curve:
        # Useful for debugging
        for t in range(10, 100):
            print(t, temperature_to_fan_speed(t))
        sys.exit()

    # TODO: Systemd watchdog

    # TODO: Trap kills and enable
    print("Disabling automatic fan control")
    ipmi_disable_fan_control()

    print("Entering the feedback loop")
    next_run = time.monotonic()
    while True:
        now = time.monotonic()
        if now < next_run:
            time.sleep(next_run - now)
        next_run = time.monotonic() + args.poll_rate

        # Get the temperatures and pick the maximal one
        temperature = max(t.current for t in psutil.sensors_temperatures()["coretemp"])
        # Adjust the fan speed
        # TODO: Add some hysteresis here
        fan_speed = temperature_to_fan_speed(temperature)
        ipmi_set_fan_speed(fan_speed)
        if args.print:
            print(temperature, fan_speed)
