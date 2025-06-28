#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 wheatfox
import RPi.GPIO as gpio
import time
import signal
import sys
import yaml
import os
from typing import Dict, Optional, List


class HCSR04Driver:
    def __init__(self, trig: int, echo: int):
        """
        Initialize the HC-SR04 ultrasonic sensor driver

        Args:
            trig (int): GPIO number for trigger
            echo (int): GPIO number for echo
        """
        self.trig_pin = trig
        self.echo_pin = echo

        gpio.setwarnings(False)
        gpio.setmode(gpio.BCM)
        gpio.setup(self.trig_pin, gpio.OUT)
        gpio.setup(self.echo_pin, gpio.IN)

    def get_distance(self) -> Optional[float]:
        try:            
            gpio.output(self.trig_pin, False)
            time.sleep(0.1)
            gpio.output(self.trig_pin, True)
            time.sleep(0.00001)
            gpio.output(self.trig_pin, False)

            while gpio.input(self.echo_pin) == 0:
                pulse_start = time.time()

            while gpio.input(self.echo_pin) == 1:
                pulse_end = time.time()

            pulse_duration = pulse_end - pulse_start

            if pulse_duration >= 0.01746:
                return None

            distance = pulse_duration * 17000

            if distance > 300 or distance == 0:
                return None

            return round(distance, 3)

        except Exception as e:
            print(f"error getting distance: {e}")
            return None


class MultiHCSR04Driver:
    def __init__(self, sensor_configs: Optional[List[Dict[str, int]]] = None):
        if sensor_configs is None:
            # Try to load from YAML file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "sensors.yaml")
            try:
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    sensor_configs = config["sensors"]
                    print(
                        f"successfully loaded sensor configurations from {config_path}"
                    )
            except Exception as e:
                print(f"failed to load sensor configurations: {str(e)}")
                raise

        self.sensors = {}
        for idx, config in enumerate(sensor_configs):
            name = config.get("name", f"sensor{idx}")
            self.sensors[name] = HCSR04Driver(config["trig"], config["echo"])

    def get_all_distances(self) -> Dict[str, Optional[float]]:
        return {name: sensor.get_distance() for name, sensor in self.sensors.items()}

    def get_sensor_names(self) -> List[str]:
        return list(self.sensors.keys())

    def cleanup(self):
        gpio.cleanup()

    def __str__(self):
        # print each sensor name and trig and echo pin
        return "\n".join(
            [f"{name}: trig={sensor.trig_pin}, echo={sensor.echo_pin}"
             for name, sensor in self.sensors.items()]
        )


def main():
    def signal_handler(signal, frame):
        print("You pressed Ctrl+C!")
        driver.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Initialize driver without explicit configs - will load from YAML
    driver = MultiHCSR04Driver()

    print("starting ultrasonic sensor driver")
    print(
        f"initialized {len(driver.get_sensor_names())} sensors: {driver}"
    )

    try:
        while True:
            distances = driver.get_all_distances()
            for sensor_name, distance in distances.items():
                if distance is None:
                    print(f"{sensor_name}: measurement failed")
                else:
                    print(f"{sensor_name}: {distance} cm")
            time.sleep(0.1)

    except Exception as e:
        print(f"error: {e}")
    finally:
        driver.cleanup()


if __name__ == "__main__":
    main()
