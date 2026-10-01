#!/usr/bin/env python3
"""
Start, stop or check the line-sensor publisher on the robot by hand.
(run_robot.py starts it automatically; this is for testing and debugging.)

    python tools/line_sensor.py            # start it (if not already running)
    python tools/line_sensor.py --stop     # stop it
    python tools/line_sensor.py --watch    # print the 4 sensors live; Ctrl+C to stop
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from turbopi.config import ROBOT_IP, ROSBRIDGE_PORT, LINE_TOPIC, LINE_TYPE   # noqa: E402
from turbopi.robot_setup import start_line_sensor, stop_line_sensor        # noqa: E402
from turbopi.rosbridge_client import RosbridgeClient                       # noqa: E402


def main():
    if "--stop" in sys.argv:
        print("line sensor publisher:", stop_line_sensor())
        return
    if "--watch" not in sys.argv:
        print(start_line_sensor())
        return
    client = RosbridgeClient(ROBOT_IP, ROSBRIDGE_PORT)
    client.connect()
    if not client.connected:
        sys.exit(f"Could not connect to rosbridge at {ROBOT_IP}:{ROSBRIDGE_PORT}: {client.error}")
    client.subscribe(LINE_TOPIC, LINE_TYPE, client.line_callback)
    print("   L  CL  CR   R      (# = sees black)   Ctrl+C to stop")
    try:
        while client.connected:
            s = client.line_sensors
            age = time.time() - client.line_stamp
            row = "  ".join(" #" if v else " ." for v in s) if s else "no data yet"
            print(f"\r  {row}    {'' if s is None or age < 1 else '(STALE)':8}", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()
    client.disconnect()


if __name__ == "__main__":
    main()
