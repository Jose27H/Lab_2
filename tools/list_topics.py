#!/usr/bin/env python3
"""
List every ROS topic the robot publishes, and (optionally) watch one.

    python tools/list_topics.py                    # every topic and its type
    python tools/list_topics.py line               # only topics containing "line"
    python tools/list_topics.py --echo /line_sensor     # print messages as they arrive

Use it to find the line sensor's topic if LINE_TOPIC in turbopi/config.py
is wrong for your robot. Needs the rosapi node, which the TurboPi's
rosbridge launch normally starts.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from turbopi.config import ROBOT_IP, ROSBRIDGE_PORT          # noqa: E402
from turbopi.rosbridge_client import RosbridgeClient          # noqa: E402


def main():
    client = RosbridgeClient(ROBOT_IP, ROSBRIDGE_PORT)
    client.connect()
    if not client.connected:
        sys.exit(f"Could not connect to rosbridge at {ROBOT_IP}:{ROSBRIDGE_PORT}: {client.error}")

    if "--echo" in sys.argv:
        topic = sys.argv[sys.argv.index("--echo") + 1]
        found = client.call_service("/rosapi/topic_type", {"topic": topic}) or {}
        msg_type = found.get("type")
        if not msg_type:
            sys.exit(f"{topic}: no such topic (or rosapi is not running)")
        print(f"{topic}  [{msg_type}]   Ctrl+C to stop")
        client.subscribe(topic, msg_type, lambda msg: print(msg))
        try:
            while client.connected:
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass
    else:
        result = client.call_service("/rosapi/topics")
        if result is None:
            sys.exit("No answer from /rosapi/topics - is the rosapi node running on the robot?")
        filt = next((a for a in sys.argv[1:] if not a.startswith("-")), "").lower()
        pairs = sorted(zip(result.get("topics", []), result.get("types", [])))
        for topic, msg_type in pairs:
            if filt in topic.lower():
                # A topic shows up as soon as anyone SUBSCRIBES to it (including
                # rosbridge, on behalf of run_robot.py) - flag the ones nobody publishes.
                pubs = (client.call_service("/rosapi/publishers", {"topic": topic}) or {})
                note = "" if pubs.get("publishers") else "   (NO PUBLISHER - no data will arrive)"
                print(f"{topic:<55} {msg_type}{note}")
    client.disconnect()


if __name__ == "__main__":
    main()
