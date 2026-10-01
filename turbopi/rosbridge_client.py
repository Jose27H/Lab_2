"""
RosbridgeClient - everything that talks to the robot.

This is the RosbridgeClient class you completed in Lab 1 (TODOs 1, 4, 5, 6, 7
are filled in), plus one new sensor for Lab 2: the line follower.

rosbridge speaks JSON. Everything we send is a dictionary with an "op" key:

    {"op": "advertise", "topic": ..., "type": ...}   "I will publish this type on this topic"
    {"op": "publish",   "topic": ..., "msg": {...}}  "here is one message"
    {"op": "subscribe", "topic": ..., "type": ...}   "send me every message on this topic"

and rosbridge sends the same "publish" shape back for every message on a
topic we subscribed to.

You do NOT need to change anything in this file for Lab 2.
"""
import itertools
import json
import threading
import time

try:
    import websocket                    # from the websocket-client package
except ImportError:                     # pragma: no cover
    raise SystemExit("websocket-client is not installed. Run:  pip install -r requirements.txt")

from .config import (
    CMD_VEL_TOPIC, CMD_VEL_TYPE,
    SERVO_TOPIC, SERVO_TYPE, SERVO_PAN, SERVO_TILT,
    SERVO_MIN, SERVO_MAX, SERVO_CENTER, SERVO_DURATION,
    SONAR_TOPIC, SONAR_TYPE, SUBSCRIBE_THROTTLE_MS,
    LINE_TOPIC, LINE_TYPE, LINE_CHANNEL_ORDER, LINE_INVERT,
)


def parse_line_message(msg):
    """Turn one line-sensor message into a tuple of 4 booleans:

        (leftmost, left-centre, right-centre, rightmost)    True = sees BLACK

    Accepts the two shapes a 4-channel sensor is usually published in:
        {"data": [1, 0, 0, 1]}     a list, one entry per channel
        {"data": 9}                a bitmask, bit 0 = channel 1 ... bit 3 = channel 4
    LINE_CHANNEL_ORDER and LINE_INVERT (config.py) fix wiring differences.
    """
    data = msg.get("data")
    if isinstance(data, (list, tuple)):
        raw = [bool(v) for v in data[:4]]
    elif isinstance(data, int):
        raw = [bool(data >> bit & 1) for bit in range(4)]
    else:
        return None
    if len(raw) < 4:
        return None
    ordered = [raw[i] for i in LINE_CHANNEL_ORDER]
    if LINE_INVERT:
        ordered = [not v for v in ordered]
    return tuple(ordered)


class RosbridgeClient:
    """One websocket to rosbridge, plus the robot-side state we care about:
    where the camera servos are (pan, tilt), the latest sonar reading
    (distance_mm) and - new in Lab 2 - the line sensors (line_sensors)."""

    def __init__(self, ip, port):
        self.ip, self.port = ip, port
        self.ws = None
        self.connected = False
        self.error = ""                 # last connection problem, for the status line
        self._lock = threading.Lock()   # only one thread may send at a time
        self._callbacks = {}            # topic -> function to call with each message
        self._pending = {}              # service call id -> [threading.Event, response]
        self._ids = itertools.count(1)

        self.pan = SERVO_CENTER         # where we last sent the camera servos
        self.tilt = SERVO_CENTER
        self.distance_mm = None         # latest sonar reading; None until one arrives

        self.line_sensors = None        # latest (L, CL, CR, R) booleans; None until one arrives
        self.line_stamp = 0.0           # time.time() when the last line reading arrived

    # ---------- connection plumbing ----------

    def connect(self):
        try:
            self.ws = websocket.WebSocket()
            self.ws.connect(f"ws://{self.ip}:{self.port}", timeout=5)
            self.connected = True
            self.error = ""
            self._send({"op": "advertise", "topic": CMD_VEL_TOPIC, "type": CMD_VEL_TYPE})
            self._send({"op": "advertise", "topic": SERVO_TOPIC,   "type": SERVO_TYPE})
            threading.Thread(target=self._receive_loop, daemon=True).start()
            self.subscribe(SONAR_TOPIC, SONAR_TYPE, self.sonar_callback)
            self.subscribe(LINE_TOPIC, LINE_TYPE, self.line_callback)      # Lab 2
        except Exception as e:
            self.connected = False
            self.error = str(e)

    def _send(self, data):
        """Send one dictionary to rosbridge as JSON text."""
        if not self.connected or self.ws is None:
            return
        with self._lock:
            try:
                self.ws.send(json.dumps(data))
            except Exception as e:
                self.connected = False
                self.error = str(e)

    def _receive_loop(self):
        """Background thread: read everything rosbridge sends us."""
        ws = self.ws
        while self.connected and ws is self.ws:
            try:
                text = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                if self.connected:
                    self.connected = False
                    self.error = str(e)
                break
            try:
                self._dispatch(json.loads(text))
            except ValueError:
                pass

    def _dispatch(self, data):
        """Route one incoming rosbridge message to the right place."""
        op = data.get("op")
        if op == "publish":
            callback = self._callbacks.get(data.get("topic"))
            if callback:
                callback(data.get("msg", {}))
        elif op == "service_response":
            waiter = self._pending.get(data.get("id"))
            if waiter:
                waiter[1] = data
                waiter[0].set()

    def disconnect(self):
        self.connected = False
        if self.ws is not None:
            try:
                self.ws.abort()
                self.ws.shutdown()
            except Exception:
                pass

    def call_service(self, service, args=None, timeout=5.0):
        """Call a ROS service and wait for the answer (used by tools/list_topics.py).
        Returns the response's "values" dictionary, or None on timeout/failure."""
        call_id = f"call_{next(self._ids)}"
        waiter = self._pending[call_id] = [threading.Event(), None]
        self._send({"op": "call_service", "id": call_id,
                    "service": service, "args": args or {}})
        waiter[0].wait(timeout)
        del self._pending[call_id]
        response = waiter[1]
        if not response or response.get("result") is False:
            return None
        return response.get("values", {})

    # ---------- driving (Lab 1, Part H) ----------

    def cmd_vel(self, lx, ly, az):
        """Publish one Twist: lx = forward m/s, ly = left m/s, az = turn rad/s (+ = left)."""
        self._send({
            "op": "publish",
            "topic": CMD_VEL_TOPIC,
            "msg": {
                "linear":  {"x": float(lx), "y": float(ly), "z": 0.0},
                "angular": {"x": 0.0, "y": 0.0, "z": float(az)},
            },
        })

    # ---------- camera servos (Lab 1, Part I) ----------

    def set_servos(self, pan, tilt):
        """Move the pan servo to `pan` and the tilt servo to `tilt` (microseconds)."""
        self._send({
            "op": "publish",
            "topic": SERVO_TOPIC,
            "msg": {
                "state": [
                    {"id": [SERVO_PAN],  "position": [int(pan)],  "offset": [0]},
                    {"id": [SERVO_TILT], "position": [int(tilt)], "offset": [0]},
                ],
                "duration": SERVO_DURATION,
            },
        })

    def move_camera(self, pan_step=0, tilt_step=0, center=False):
        """Nudge the camera by a step (or re-centre it), clamped to the servo range."""
        if center:
            self.pan = self.tilt = SERVO_CENTER
        else:
            self.pan = max(SERVO_MIN, min(SERVO_MAX, self.pan + pan_step))
            self.tilt = max(SERVO_MIN, min(SERVO_MAX, self.tilt + tilt_step))
        self.set_servos(self.pan, self.tilt)

    # ---------- sensors (Lab 1, Part J and Lab 2) ----------

    def subscribe(self, topic, msg_type, callback):
        """Ask rosbridge to send us every message on `topic`; call callback(msg) with each."""
        self._callbacks[topic] = callback
        self._send({"op": "subscribe", "topic": topic, "type": msg_type,
                    "throttle_rate": SUBSCRIBE_THROTTLE_MS})

    def sonar_callback(self, msg):
        """std_msgs/msg/Int32: distance in millimetres. (Runs on the receive thread.)"""
        self.distance_mm = msg["data"]

    def line_callback(self, msg):
        """One line-sensor message. (Runs on the receive thread - store, don't draw.)"""
        sensors = parse_line_message(msg)
        if sensors is not None:
            self.line_sensors = sensors
            self.line_stamp = time.time()
