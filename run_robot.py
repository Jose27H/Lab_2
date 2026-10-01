#!/usr/bin/env python3
"""
COSC 3P71 - Lab 2: Line following.  Start here.

    python run_robot.py --check     # test your work - no robot needed
    python run_robot.py             # open the window and connect to the robot

Runs on the LAB COMPUTER and talks to the TurboPi over Wi-Fi (rosbridge),
exactly like Lab 1. See README.md for the full instructions.
"""
import sys
import tkinter as tk

from turbopi.config import ROBOT_IP, ROSBRIDGE_PORT
from turbopi.gui import TeleopGUI
from turbopi.rosbridge_client import RosbridgeClient


def main():
    if "--check" in sys.argv:
        from turbopi.check import self_check
        sys.exit(self_check())
    client = RosbridgeClient(ROBOT_IP, ROSBRIDGE_PORT)
    root = tk.Tk()
    TeleopGUI(root, client)
    root.mainloop()


if __name__ == "__main__":
    main()
