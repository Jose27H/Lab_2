"""
Self-check:   python run_robot.py --check

Tests Task 1 (the GUI button), Task 2 (line_position) and Task 3
(LineFollower) on THIS computer - no robot needed. Run it after every change.
"""
import time
import tkinter as tk
import types

from . import gui as gui_module
from .config import ROBOT_IP, ROSBRIDGE_PORT, FOLLOW_SPEED, TURN_GAIN, SEARCH_TURN, MAX_LINEAR
from .rosbridge_client import RosbridgeClient

B, W = True, False          # sensor shorthand: B = sees Black, W = sees White
NOT_STARTED = object()


def _fmt(sensors):
    return "".join("B" if s else "W" for s in sensors)


def _close(got, want):
    try:
        return len(got) == len(want) and all(abs(g - w) < 1e-6 for g, w in zip(got, want))
    except TypeError:
        return False


def _captured_client():
    """A client whose _send() records messages instead of sending them."""
    client = RosbridgeClient(ROBOT_IP, ROSBRIDGE_PORT)
    sent = []
    client.connected = True
    client._send = sent.append
    return client, sent


def _load_student_module():
    errors = []
    module = gui_module.load_line_follower(errors.append)
    return module, (errors[0] if errors else None)


# ---------------------------------------------------------------- Task 1 --

def _check_task1():
    """Returns a dict TODO -> (problems, not_started)."""
    try:
        root = tk.Tk()
    except tk.TclError as e:
        skip = ([f"skipped - no display available ({e})"], False)
        return {"1A": skip, "1B": skip, "1C": skip}
    root.withdraw()
    client, sent = _captured_client()
    try:
        gui = gui_module.TeleopGUI(root, client, start=False)
    except Exception as e:
        root.destroy()
        crash = ([f"building the window crashed with {type(e).__name__}: {e}"], False)
        return {"1A": crash, "1B": ([], True), "1C": ([], True)}

    class FakeFollower:
        def step(self, sensors):
            return 0.11, 0.0, 0.22
    fake = types.SimpleNamespace(LineFollower=FakeFollower)
    real_loader = gui_module.load_line_follower
    gui_module.load_line_follower = lambda report: fake
    results = {}
    try:
        # TODO 1A - the button exists, is on screen, and is wired up
        btn = getattr(gui, "line_btn", None)
        if btn is None:
            results["1A"] = ([], True)
        else:
            p = []
            if not isinstance(btn, tk.Button):
                p.append("self.line_btn should be a tk.Button")
            else:
                if btn.winfo_manager() == "":
                    p.append("the button is created but never placed - did you call .pack()?")
                if btn.cget("text") != "Start Line Follow":
                    p.append(f'button text should be "Start Line Follow", got {btn.cget("text")!r}')
                if not str(btn.cget("command")):
                    p.append("the button has no command= - clicking it does nothing")
            results["1A"] = (p, False)

        # TODO 1B - toggling switches the mode on, then off
        gui.toggle_line_follow()
        first = gui.line_mode
        gui.toggle_line_follow()
        second = gui.line_mode
        if not first and not second:
            results["1B"] = ([], True)
        else:
            p = []
            if not first:
                p.append("toggle_line_follow() with line_mode OFF should turn it ON")
            if second:
                p.append("toggle_line_follow() with line_mode ON should turn it OFF")
            results["1B"] = (p, False)
        # and through the button itself, if both 1A and 1B work
        if isinstance(btn, tk.Button) and not results["1A"][0] and not results["1B"][0] \
                and not results["1B"][1]:
            btn.invoke()
            if not gui.line_mode:
                results["1A"][0].append("clicking the button did not start line following - "
                                        "is command=self.toggle_line_follow ?")
            gui.stop_line_follow()

        # TODO 1C - publish_loop() asks the line follower while line_mode is on
        gui.running = False                      # run publish_loop() exactly once
        gui.start_line_follow()
        client.line_sensors, client.line_stamp = (W, B, B, W), time.time()
        sent.clear()
        gui.publish_loop()
        twist = sent[-1]["msg"] if sent else {}
        got = (twist.get("linear", {}).get("x"), twist.get("angular", {}).get("z"))
        gui.stop_line_follow()
        gui.joy_y = 1.0
        sent.clear()
        gui.publish_loop()
        joy_lx = sent[-1]["msg"]["linear"]["x"] if sent else None
        if got == (0.0, 0.0) and joy_lx == MAX_LINEAR:
            results["1C"] = ([], True)
        else:
            p = []
            if not _close(got, (0.11, 0.22)):
                p.append("with line_mode ON, publish_loop() should send what line_command() "
                         f"returns; a follower returning (0.11, 0.0, 0.22) gave linear.x, "
                         f"angular.z = {got}")
            if joy_lx != MAX_LINEAR:
                p.append("with line_mode OFF, the joystick must still drive the robot "
                         f"(knob fully up should send linear.x={MAX_LINEAR}, got {joy_lx})")
            results["1C"] = (p, False)
    finally:
        gui_module.load_line_follower = real_loader
        root.destroy()
    return results


# ---------------------------------------------------------------- Task 2 --

LINE_POSITION_CASES = [
    ((W, B, B, W), 0.0,  "line under the two middle sensors -> centred"),
    ((W, B, W, W), -0.5, "only centre-left sees it -> slightly LEFT"),
    ((W, W, B, W), 0.5,  "only centre-right sees it -> slightly RIGHT"),
    ((B, W, W, W), -1.5, "only the leftmost sees it -> far LEFT"),
    ((W, W, W, B), 1.5,  "only the rightmost sees it -> far RIGHT"),
    ((B, B, W, W), -1.0, "two left sensors -> average of -1.5 and -0.5"),
    ((W, W, B, B), 1.0,  "two right sensors -> average of 0.5 and 1.5"),
    ((W, B, B, B), 0.5,  "three sensors -> average of -0.5, 0.5, 1.5"),
    ((B, B, B, B), 0.0,  "all four (a crossing line) -> centred"),
]


def _check_task2(module):
    func = getattr(module, "line_position", None)
    if func is None or all(func(s) is None for s, _, _ in LINE_POSITION_CASES):
        return [], True                       # missing, or still the empty skeleton
    problems = []
    got = func((W, W, W, W))
    if got is not None:
        problems.append(f"no sensor sees the line (WWWW) -> must return None, got {got!r}")
    for sensors, want, desc in LINE_POSITION_CASES:
        got = func(list(sensors))            # must work for lists too
        if not isinstance(got, (int, float)) or abs(got - want) > 1e-6:
            problems.append(f"{desc}\n            line_position({_fmt(sensors)}) "
                            f"should be {want:+.1f}, got {got!r}")
    return problems, False


# ---------------------------------------------------------------- Task 3 --

def _check_task3a(module):
    cls = getattr(module, "LineFollower", None)
    if cls is None:
        return [], True
    cases = [
        ((W, B, B, W), (FOLLOW_SPEED, 0.0, 0.0),                "centred -> drive straight"),
        ((B, W, W, W), (FOLLOW_SPEED, 0.0, +1.5 * TURN_GAIN),   "line far LEFT -> turn LEFT (+az)"),
        ((W, W, W, B), (FOLLOW_SPEED, 0.0, -1.5 * TURN_GAIN),   "line far RIGHT -> turn RIGHT (-az)"),
        ((W, W, B, B), (FOLLOW_SPEED, 0.0, -1.0 * TURN_GAIN),   "line RIGHT -> turn right, less"),
        ((W, B, W, W), (FOLLOW_SPEED, 0.0, +0.5 * TURN_GAIN),   "line slightly LEFT -> gentle left"),
        ((W, W, W, W), (0.0, 0.0, 0.0),
         "never seen a line -> STOP (do not wander off)"),
    ]
    results = [cls().step(s) for s, _, _ in cases]   # a NEW follower for each case
    if all(r is None for r in results):
        return [], True
    problems = []
    for (sensors, want, desc), got in zip(cases, results):
        if not _close(got, want):
            problems.append(f"{desc}\n            step({_fmt(sensors)}) should return "
                            f"{tuple(round(v, 3) for v in want)}, got {got!r}")
    return problems, False


def _check_task3b(module):
    cls = getattr(module, "LineFollower", None)
    if cls is None:
        return [], True
    LOST = (W, W, W, W)
    sequences = [
        ([(B, W, W, W), LOST], (0.0, 0.0, +SEARCH_TURN),
         "line was last seen on the LEFT, now lost -> spin LEFT to find it"),
        ([(W, W, W, B), LOST], (0.0, 0.0, -SEARCH_TURN),
         "line was last seen on the RIGHT, now lost -> spin RIGHT to find it"),
        ([(W, W, W, B), LOST, LOST, LOST], (0.0, 0.0, -SEARCH_TURN),
         "lost for several steps -> KEEP spinning the same way"),
        ([(W, B, B, W), LOST], (0.0, 0.0, 0.0),
         "line was centred, then vanished (end of the line) -> STOP"),
        ([(B, W, W, W), LOST, (W, W, W, B), LOST], (0.0, 0.0, -SEARCH_TURN),
         "found again on the RIGHT, lost again -> memory must be UPDATED, spin RIGHT"),
    ]
    outputs = []
    for steps, _, _ in sequences:
        follower = cls()
        out = None
        for s in steps:
            out = follower.step(s)
        outputs.append(out)
    if all(o is None or _close(o, (0.0, 0.0, 0.0)) for o in outputs[:2]):
        return [], True                       # empty skeleton, or still Task 3A's "lost -> stop"
    problems = []
    for (steps, want, desc), got in zip(sequences, outputs):
        if not _close(got, want):
            trace = " -> ".join(_fmt(s) for s in steps)
            problems.append(f"{desc}\n            steps {trace}: last step should return "
                            f"{tuple(round(v, 3) for v in want)}, got {got!r}")
    return problems, False


# ------------------------------------------------------------------ main --

def _run(fn, *args):
    try:
        return fn(*args)
    except Exception as e:                    # a crash in student code
        return [f"crashed with {type(e).__name__}: {e}"], False


def self_check():
    print("Lab 2 self-check (no robot needed)\n")
    task1 = _check_task1()
    module, load_error = _load_student_module()

    rows = [
        ("Task 1", "TODO 1A", "Line Follow button exists and is on screen",   task1["1A"]),
        ("Task 1", "TODO 1B", "toggle_line_follow() switches the mode",       task1["1B"]),
        ("Task 1", "TODO 1C", "publish_loop() uses the line follower",        task1["1C"]),
    ]
    missing = module is None and "not found" in load_error
    if module is None:
        result = ([], True) if missing else ([load_error], False)
        for step, title in (("Step 2 ", "line_position() - perception"),
                            ("Step 3A", "LineFollower.step() - reflex"),
                            ("Step 3B", "LineFollower.step() - memory")):
            rows.append((f"Task {step[5]}", step, title, result))
    else:
        rows += [
            ("Task 2", "Step 2 ", "line_position() - perception",  _run(_check_task2, module)),
            ("Task 3", "Step 3A", "LineFollower.step() - reflex",  _run(_check_task3a, module)),
            ("Task 3", "Step 3B", "LineFollower.step() - memory",  _run(_check_task3b, module)),
        ]

    summary = {}
    for task, step, title, (problems, not_started) in rows:
        if not_started:
            state = "not done yet"
        elif problems:
            state = f"{len(problems)} problem(s)"
        else:
            state = "ok"
        print(f"{task}  {step:<7}  {title:<46} {state}")
        for p in problems:
            print(f"        FAIL: {p}")
        summary.setdefault(task, []).append(state)

    print()
    if missing:
        print("(line_follower.py does not exist yet - you create it at the start of Task 2.)\n")
    for task, states in summary.items():
        if all(s == "ok" for s in states):
            print(f"{task}: complete.")
        elif all(s == "not done yet" for s in states):
            print(f"{task}: not started.")
        else:
            print(f"{task}: not finished - fix the FAILs above and run --check again.")
    return 0 if all(s == "ok" for states in summary.values() for s in states) else 1
