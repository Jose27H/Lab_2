"""
TeleopGUI - the window from Lab 1, plus a line-sensor panel (provided) and
the Line Follow button (YOU add it: Task 1).

    Task 1   TODO 1A  create the "Line Follow" button          build_layout()
             TODO 1B  make the button switch the mode on/off   toggle_line_follow()
             TODO 1C  let the line follower drive the robot    publish_loop()

How the pieces fit together:

    mouse / keys  --->  joy_x, joy_y, turn  ---\
                                                >-- publish_loop() --> client.cmd_vel()
    line sensors  --->  your LineFollower   ---/        (10 times a second)

publish_loop() is the ONE place a velocity is chosen and sent. Task 1C
teaches it to ask your LineFollower instead of the joystick while
line_mode is on.
"""
import importlib
import sys
import threading
import time
import tkinter as tk
import traceback

from .config import (
    ROBOT_IP, JOY_SIZE, KNOB_RADIUS, PUBLISH_PERIOD_MS, SERVO_PERIOD_MS, SERVO_STEP,
    PAN_LEFT, PAN_RIGHT, TILT_UP, TILT_DOWN, SONAR_WARN_MM,
    MAX_LINEAR, MAX_ANGULAR, LINE_STALE_S, AUTO_START_LINE_SENSOR,
)
from .drive import snap_to_8_directions, twist_from_joystick
from .robot_setup import ensure_line_sensor


def load_line_follower(report):
    """Import (or re-import, to pick up your edits) YOUR line_follower.py.
    Returns the module, or None after calling report(<what went wrong>)."""
    try:
        if "line_follower" in sys.modules:
            return importlib.reload(sys.modules["line_follower"])
        return importlib.import_module("line_follower")
    except ModuleNotFoundError as e:
        if e.name != "line_follower":
            raise
        report("line_follower.py not found - create it next to run_robot.py (README, Task 2)")
    except Exception as e:
        traceback.print_exc()
        report(f"line_follower.py has an error: {e!r} (full details in the terminal)")
    return None


class TeleopGUI:
    """The window. Turns mouse/keyboard input (or your LineFollower) into
    velocity commands and publishes them at a steady rate."""

    def __init__(self, root, client, start=True):
        self.root = root
        self.client = client
        self.joy_x = 0.0
        self.joy_y = 0.0
        self.turn = 0.0
        self.cam_dx = 0
        self.cam_dy = 0
        self.running = True

        self.line_mode = False      # True while the robot is following the line
        self.follower = None        # your LineFollower object while line_mode is on
        self.line_module = load_line_follower(lambda text: None)   # quietly, for the readout

        root.title(f"TurboPi Lab 2 - {ROBOT_IP}")
        root.resizable(False, False)
        self.build_layout()
        self.bind_keys()
        root.protocol("WM_DELETE_WINDOW", self.quit)

        if start:                   # (the self-check builds the window with start=False)
            threading.Thread(target=self.connect_loop, daemon=True).start()
            self.publish_loop()
            self.servo_loop()

    # ---------- layout ----------

    def build_layout(self):
        self.conn_lbl = tk.Label(self.root, text="rosbridge: connecting...",
                                 fg="dark orange", anchor="w")
        self.conn_lbl.pack(fill=tk.X, padx=10, pady=(8, 0))

        main = tk.Frame(self.root)
        main.pack(padx=10, pady=4)

        # --- left: joystick, rotate/stop buttons, line follow button ---
        left = tk.Frame(main)
        left.grid(row=0, column=0, padx=(0, 16))
        tk.Label(left, text="Drive (drag the knob; release to stop)").pack()
        self.canvas = tk.Canvas(left, width=JOY_SIZE, height=JOY_SIZE,
                                bg="white", highlightthickness=1)
        self.canvas.pack(pady=4)
        c = JOY_SIZE / 2
        self.canvas.create_oval(10, 10, JOY_SIZE - 10, JOY_SIZE - 10,
                                outline="gray70", width=2)
        self.canvas.create_line(c, 10, c, JOY_SIZE - 10, fill="gray85")
        self.canvas.create_line(10, c, JOY_SIZE - 10, c, fill="gray85")
        self.knob = self.canvas.create_oval(
            c - KNOB_RADIUS, c - KNOB_RADIUS, c + KNOB_RADIUS, c + KNOB_RADIUS,
            fill="steelblue", outline="")
        self.canvas.bind("<ButtonPress-1>", self.on_drag)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        row = tk.Frame(left)
        row.pack(pady=6)
        self.make_hold_button(row, "⟲ Rotate L", +1.0).pack(side=tk.LEFT, padx=4)
        tk.Button(row, text="STOP", fg="white", bg="firebrick", width=8,
                  command=self.stop_all).pack(side=tk.LEFT, padx=4)
        self.make_hold_button(row, "Rotate R ⟳", -1.0).pack(side=tk.LEFT, padx=4)

        line_row = tk.Frame(left)       # the Line Follow button goes in here
        line_row.pack(pady=(0, 6))

        # TODO 1A: create the Line Follow button and put it on the screen.
        #
        #   - It must be stored in self.line_btn (other code updates its
        #     text and colour through that name).
        #   - Its parent is line_row (the frame created just above).
        #   - Its text should be "Start Line Follow" and width 20.
        #   - Clicking it must call self.toggle_line_follow.
        #     (Look at how the STOP button above is created: same idea.)
        #   - Then .pack() it, or it will never appear.
        #
        #   Two lines. See "Task 1" in the README.

        # --- right: sonar, line sensors, camera pad ---
        right = tk.Frame(main)
        right.grid(row=0, column=1, sticky="n")

        tk.Label(right, text="Sonar").pack(pady=(4, 0))
        self.sonar_lbl = tk.Label(right, text="waiting...", fg="gray40",
                                  font=("TkDefaultFont", 12, "bold"))
        self.sonar_lbl.pack(pady=(0, 10))

        tk.Label(right, text="Line sensors (black = sees line)").pack()
        self.line_canvas = tk.Canvas(right, width=4 * 34 + 6, height=52,
                                     highlightthickness=0)
        self.line_canvas.pack()
        self.line_cells = []
        for i, name in enumerate(("L", "CL", "CR", "R")):
            x = 6 + i * 34
            self.line_cells.append(self.line_canvas.create_rectangle(
                x, 4, x + 28, 32, fill="gray80", outline="gray50"))
            self.line_canvas.create_text(x + 14, 44, text=name)
        self.line_pos_lbl = tk.Label(right, text="position: -", font=("Courier", 10))
        self.line_pos_lbl.pack(pady=(0, 10))

        tk.Label(right, text="Camera\nhold a button or an arrow key").pack()
        pad = tk.Frame(right)
        pad.pack(pady=4)
        self.make_cam_button(pad, "▲", dy=TILT_UP).grid(row=0, column=1)
        self.make_cam_button(pad, "◀", dx=PAN_LEFT).grid(row=1, column=0)
        tk.Button(pad, text="⌂", width=3,
                  command=lambda: self.client.move_camera(center=True)).grid(row=1, column=1)
        self.make_cam_button(pad, "▶", dx=PAN_RIGHT).grid(row=1, column=2)
        self.make_cam_button(pad, "▼", dy=TILT_DOWN).grid(row=2, column=1)

        # --- messages, then the status bar ---
        self.msg_lbl = tk.Label(self.root, text="", anchor="w", fg="navy",
                                wraplength=JOY_SIZE * 2 + 40, justify=tk.LEFT)
        self.msg_lbl.pack(fill=tk.X, padx=10)
        self.status = tk.Label(self.root, text="", anchor="w", relief=tk.SUNKEN,
                               font=("Courier", 10))
        self.status.pack(fill=tk.X, padx=10, pady=(0, 8))

    def make_hold_button(self, parent, text, direction):
        """A button that turns the robot only WHILE it is held down."""
        btn = tk.Button(parent, text=text, width=10)
        btn.bind("<ButtonPress-1>", lambda e: self.set_turn(direction))
        btn.bind("<ButtonRelease-1>", lambda e: self.set_turn(0.0))
        return btn

    def make_cam_button(self, parent, text, dx=0, dy=0):
        """The camera keeps stepping (in servo_loop) while the button is held."""
        btn = tk.Button(parent, text=text, width=3)
        btn.bind("<ButtonPress-1>", lambda e: self.cam_press(dx, dy))
        btn.bind("<ButtonRelease-1>", lambda e: self.cam_release(dx, dy))
        return btn

    def bind_keys(self):
        self.root.bind("<space>", lambda e: self.stop_all())
        for key, dx, dy in (("Left", PAN_LEFT, 0), ("Right", PAN_RIGHT, 0),
                            ("Up", 0, TILT_UP), ("Down", 0, TILT_DOWN)):
            self.root.bind(f"<KeyPress-{key}>",
                           lambda e, dx=dx, dy=dy: self.cam_press(dx, dy))
            self.root.bind(f"<KeyRelease-{key}>",
                           lambda e, dx=dx, dy=dy: self.cam_release(dx, dy))
        self.root.bind("c", lambda e: self.client.move_camera(center=True))

    def show_message(self, text):
        self.msg_lbl.config(text=text)

    # ---------- networking ----------

    def connect_loop(self):
        """Background thread: connect, and reconnect if the link drops.
        After each new connection, make sure the robot is publishing the
        line sensor (see turbopi/robot_setup.py)."""
        while self.running:
            if not self.client.connected:
                self.client.connect()
                if self.client.connected and AUTO_START_LINE_SENSOR:
                    note = ensure_line_sensor(self.client)
                    if note:
                        print(note)
                        # tkinter may only be touched from the main thread
                        self.root.after(0, self.show_message, note)
            time.sleep(3)

    # ---------- line following (Lab 2) ----------

    def toggle_line_follow(self):
        """Called when the Line Follow button is clicked."""
        # TODO 1B: if line following is ON (self.line_mode is True), turn it
        #          off by calling self.stop_line_follow(); otherwise turn it
        #          on by calling self.start_line_follow(). Four lines.
        pass

    def start_line_follow(self):
        """Load YOUR line_follower.py, create a LineFollower, and switch the
        robot into line-following mode. (Provided.)"""
        if not hasattr(self, "status"):
            raise RuntimeError(
                "toggle_line_follow() ran while the window was still being built. "
                "In TODO 1A write  command=self.toggle_line_follow  (no brackets): "
                "with brackets Python calls it immediately instead of on click.")
        module = load_line_follower(self.show_message)
        if module is None:
            return
        self.line_module = module
        if not hasattr(module, "LineFollower"):
            self.show_message("line_follower.py has no LineFollower class yet - that is Task 3.")
            return
        self.joy_x = self.joy_y = self.turn = 0.0
        self.draw_knob(0, 0)
        self.follower = module.LineFollower()
        self.line_mode = True
        self.show_message("Line following ON. Drag the joystick, press STOP or space to take over.")
        if hasattr(self, "line_btn"):
            self._idle_bg = self.line_btn.cget("bg")     # to restore when stopped
            self.line_btn.config(text="Stop Line Follow", bg="green3")

    def stop_line_follow(self, reason="Line following OFF."):
        """Leave line-following mode; the joystick is in charge again. (Provided.)"""
        was_on = self.line_mode
        self.line_mode = False
        self.follower = None
        if was_on:
            self.show_message(reason)
        if hasattr(self, "line_btn") and was_on:
            self.line_btn.config(text="Start Line Follow", bg=self._idle_bg)

    def line_command(self):
        """Ask YOUR LineFollower what to do with the latest sensor reading.
        Returns (lx, ly, az). Stops safely if anything goes wrong. (Provided.)"""
        sensors = self.client.line_sensors
        if sensors is None or time.time() - self.client.line_stamp > LINE_STALE_S:
            self.stop_line_follow("Line sensor is not responding - line following stopped.")
            return 0.0, 0.0, 0.0
        try:
            lx, ly, az = self.follower.step(sensors)
        except Exception as e:
            traceback.print_exc()
            self.stop_line_follow(f"Your LineFollower.step() failed: {e!r} "
                                  "(full details in the terminal)")
            return 0.0, 0.0, 0.0
        # Safety net: never send more than the Lab 1 limits, whatever step() says.
        def clamp(v, limit):
            return max(-limit, min(limit, float(v)))
        return clamp(lx, MAX_LINEAR), clamp(ly, MAX_LINEAR), clamp(az, MAX_ANGULAR)

    def update_line_display(self):
        """Light up the 4 sensor squares and show YOUR line_position() result."""
        sensors = self.client.line_sensors
        for cell, on in zip(self.line_cells, sensors or (None,) * 4):
            colour = "gray80" if on is None else ("black" if on else "white")
            self.line_canvas.itemconfig(cell, fill=colour)
        func = getattr(self.line_module, "line_position", None)
        if sensors is None:
            text = "position: (no sensor data)"
        elif func is None:
            text = "position: (write line_position - Task 2)"
        else:
            try:
                pos = func(sensors)
                if pos is None:
                    text = "position: None  (no line)"
                else:
                    side = "LEFT" if pos < 0 else "RIGHT" if pos > 0 else "centre"
                    text = f"position: {pos:+.2f}  ({side})"
            except Exception as e:
                text = f"position: line_position() error: {type(e).__name__}"
        self.line_pos_lbl.config(text=text)

    # ---------- input handlers ----------

    def set_turn(self, direction):
        self.turn = direction

    def cam_press(self, dx=0, dy=0):
        if dx:
            self.cam_dx = dx
        if dy:
            self.cam_dy = dy

    def cam_release(self, dx=0, dy=0):
        if dx and self.cam_dx == dx:
            self.cam_dx = 0
        if dy and self.cam_dy == dy:
            self.cam_dy = 0

    def on_drag(self, event):
        """Mouse pressed or dragged on the joystick. Touching the joystick
        always takes control back from the line follower."""
        if self.line_mode:
            self.stop_line_follow("Joystick touched - line following OFF.")
        c = JOY_SIZE / 2
        usable = c - 10 - KNOB_RADIUS
        self.joy_x = max(-1.0, min(1.0, (event.x - c) / usable))
        self.joy_y = -max(-1.0, min(1.0, (event.y - c) / usable))  # screen y grows DOWN
        dir_x, dir_y = snap_to_8_directions(self.joy_x, self.joy_y)
        self.draw_knob(dir_x * usable, -dir_y * usable)

    def on_release(self, event):
        self.joy_x = self.joy_y = 0.0
        self.draw_knob(0, 0)

    def draw_knob(self, px, py):
        c = JOY_SIZE / 2
        self.canvas.coords(self.knob,
                           c + px - KNOB_RADIUS, c + py - KNOB_RADIUS,
                           c + px + KNOB_RADIUS, c + py + KNOB_RADIUS)

    def stop_all(self):
        """STOP button / space bar: stop everything, including line following."""
        self.stop_line_follow("STOP pressed - line following OFF.")
        self.joy_x = self.joy_y = 0.0
        self.turn = 0.0
        self.draw_knob(0, 0)

    # ---------- repeating loops ----------

    def publish_loop(self):
        """Runs every PUBLISH_PERIOD_MS and ALWAYS publishes the current
        desired velocity, so if this program dies the robot stops."""

        # TODO 1C: while self.line_mode is True, the velocity must come from
        #          the line follower - self.line_command() returns (lx, ly, az)
        #          - and NOT from the joystick. Turn the line below into an
        #          if / else. Four lines.
        lx, ly, az = twist_from_joystick(self.joy_x, self.joy_y, self.turn)

        self.client.cmd_vel(lx, ly, az)

        mode = "LINE" if self.line_mode else "JOY "
        self.status.config(
            text=f"[{mode}] linear.x={lx:+.2f}  linear.y={ly:+.2f}  angular.z={az:+.2f}"
                 f"   pan={self.client.pan}  tilt={self.client.tilt}")

        if self.client.connected:
            text, colour = f"rosbridge: connected to {ROBOT_IP}", "green4"
        else:
            text = (f"rosbridge: NOT connected - {self.client.error or 'connecting...'}"
                    "  (retrying)")
            colour = "red"
        self.conn_lbl.config(text=text, fg=colour)

        d = self.client.distance_mm
        if d is None:
            self.sonar_lbl.config(text="waiting...", fg="gray40")
        elif d < SONAR_WARN_MM:
            self.sonar_lbl.config(text=f"{d / 10:.0f} cm  TOO CLOSE", fg="red")
        else:
            self.sonar_lbl.config(text=f"{d / 10:.0f} cm", fg="green4")

        self.update_line_display()

        if self.running:
            self.root.after(PUBLISH_PERIOD_MS, self.publish_loop)

    def servo_loop(self):
        """Steps the camera while a pad button or arrow key is held."""
        if self.cam_dx or self.cam_dy:
            self.client.move_camera(pan_step=self.cam_dx * SERVO_STEP,
                                    tilt_step=self.cam_dy * SERVO_STEP)
        if self.running:
            self.root.after(SERVO_PERIOD_MS, self.servo_loop)

    def quit(self):
        """Window closed: stop the robot (Lab 1, TODO 3), then disconnect."""
        self.running = False
        self.line_mode = False
        self.client.cmd_vel(0.0, 0.0, 0.0)
        time.sleep(0.2)
        self.client.disconnect()
        self.root.destroy()
