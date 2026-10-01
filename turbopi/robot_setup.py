"""
Starts the line-sensor publisher on the robot, so nothing has to be
installed there. (Provided - you do not need to read or change this.)

The stock TurboPi image reads the 4-channel line sensor only inside
Hiwonder's own demo programs; it never publishes it as a ROS topic, so
rosbridge cannot see it. This module SSHes into the robot and runs
robot_side/line_sensor_node.py inside the robot's ROS container:

  - nothing is copied or installed: the code is passed on the command line
  - it stops when the robot is switched off, and is started again the next
    time run_robot.py connects
  - if the topic already has a publisher, it does nothing (no duplicates)
"""
import base64
import os
import shlex

from .config import (ROBOT_IP, ROBOT_SSH_USER, ROBOT_SSH_PASSWORD,
                     ROBOT_CONTAINER, LINE_TOPIC)

MARKER = "lab2_line_sensor"     # tags the process so it can be found / stopped
NODE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "robot_side", "line_sensor_node.py")


def _ssh(command):
    """Run one shell command on the robot. Returns (exit code, output)."""
    import paramiko                     # imported here so the rest works without it
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ROBOT_IP, username=ROBOT_SSH_USER, password=ROBOT_SSH_PASSWORD,
                timeout=10, allow_agent=False, look_for_keys=False)
    try:
        _, out, err = ssh.exec_command(command, timeout=30)
        text = out.read().decode(errors="replace") + err.read().decode(errors="replace")
        return out.channel.recv_exit_status(), text.strip()
    finally:
        ssh.close()


def has_publisher(client):
    """True/False if rosapi can tell us, None if it cannot."""
    answer = client.call_service("/rosapi/publishers", {"topic": LINE_TOPIC})
    return None if answer is None else bool(answer.get("publishers"))


def start_line_sensor():
    """Start the publisher on the robot if it is not already running.
    Returns a one-line description of what happened."""
    with open(NODE_FILE, "rb") as f:
        code = base64.b64encode(f.read()).decode()
    python = f"import base64; exec(base64.b64decode('{code}'))"
    # Run as 'ubuntu', the same user as rosbridge: ROS 2's shared-memory
    # transport silently drops data between processes of different users.
    inner = (f"source /opt/ros/humble/setup.bash && "
             f"exec python3 -c {shlex.quote(python)} {MARKER}")
    command = (f"docker exec {ROBOT_CONTAINER} pgrep -f {MARKER} >/dev/null && echo already-running || "
               f"docker exec -u ubuntu -d {ROBOT_CONTAINER} bash -c {shlex.quote(inner)}")
    status, output = _ssh(command)
    if status != 0:
        raise RuntimeError(output or f"exit status {status}")
    return "line sensor publisher already running" if "already-running" in output \
        else "started the line sensor publisher on the robot"


def stop_line_sensor():
    status, output = _ssh(f"docker exec {ROBOT_CONTAINER} pkill -f {MARKER}")
    return "stopped" if status == 0 else "was not running"


def ensure_line_sensor(client):
    """Called once per connection by the GUI. Returns a message for the
    user, or None if everything was already fine."""
    if has_publisher(client):
        return None
    try:
        return start_line_sensor().capitalize() + "."
    except ImportError:
        return "Line sensor: run  pip install -r requirements.txt  (paramiko is missing)."
    except Exception as e:
        return f"Could not start the line sensor on the robot over SSH: {e}"
