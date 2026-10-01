# Lab 2: Line Following on the TurboPi

In Lab 1 you drove the TurboPi yourself: you were the "brain", and the program
turned your joystick movements into motor commands. In Lab 2 you hand that job
over to the program. The robot will use its **line sensor** to follow a black
line on the floor, with nobody at the controls.

This is your first **autonomous agent**. It repeats one loop over and over:

```
   sense  ──►  decide  ──►  act  ──►  sense  ──►  decide  ──►  act  ...  (10 times a second)
```

You'll build it in three tasks:

| Task | What you do | Where |
|---|---|---|
| **Task 1** | Add a **Line Follow** button to your Lab 1 GUI | `turbopi/gui.py` |
| **Task 2** | Line following, step 1 (**perception**): turn 4 sensor readings into one number, "where is the line?" | `line_follower.py` (a file you create) |
| **Task 3** | Line following, step 2 (**action**): turn "where is the line?" into a steering command, then give the robot a memory so it can find the line again when it loses it | `line_follower.py` |

---

## Quick reference

```bash
pip install -r requirements.txt     # once per computer
python run_robot.py --check         # test your work. No robot needed. Run it often.
python run_robot.py                 # open the window and connect to the robot
```

On macOS or Linux you may need `python3` / `pip3` instead of `python` / `pip`.

---

## Contents

1. [What's in this repo](#1-whats-in-this-repo)
2. [Getting started](#2-getting-started)
3. [How line following works](#3-how-line-following-works) (read this before Task 2)
4. [Task 1: Add the Line Follow button](#4-task-1-add-the-line-follow-button)
5. [Task 2: Perception, "where is the line?"](#5-task-2-perception-where-is-the-line)
6. [Task 3: Action, "which way do I steer?"](#6-task-3-action-which-way-do-i-steer)
7. [Running on the track](#7-running-on-the-track)
8. [Troubleshooting](#8-troubleshooting)
9. [Extensions (optional)](#9-extensions-optional)
10. [For instructors and TAs](#10-for-instructors-and-tas)

---

## 1. What's in this repo

In Lab 1, everything lived in one long file, `teleop_scaffold.py`. Lab 2 starts
from the **completed** Lab 1 program, split into small files that each do one
job. You'll find the code you wrote last week in there:

```
Lab_2/
├── README.md               ← you are here
├── requirements.txt        ← Python packages to install
├── run_robot.py            ← START HERE: runs the program or the self-check
├── line_follower.py        ← YOU CREATE THIS FILE in Task 2 (it is not here yet)
├── turbopi/                ← the provided code (Lab 1, reorganised)
│   ├── config.py           ← every setting: IP address, speeds, topics, tuning
│   ├── rosbridge_client.py ← talks to the robot (cmd_vel, servos, sonar, line sensor)
│   ├── drive.py            ← joystick → velocity (your Lab 1 TODO 2)
│   ├── gui.py              ← the window. Task 1 is in here.
│   └── check.py            ← the self-check run by --check
├── tools/
│   └── list_topics.py      ← lists the robot's ROS topics (handy for debugging)
└── robot_side/             ← instructors only; runs on the robot (see section 10)
```

Where each part of the Lab 1 file went:

| In Lab 1's `teleop_scaffold.py` | Now in |
|---|---|
| the settings block at the top (`ROBOT_IP`, `MAX_LINEAR`, ...) | `turbopi/config.py` |
| `class RosbridgeClient` (TODOs 1, 4, 5, 6, 7) | `turbopi/rosbridge_client.py` |
| `twist_from_joystick()` (TODO 2) | `turbopi/drive.py` |
| `class TeleopGUI` (TODO 3) | `turbopi/gui.py` |
| the `--check` code | `turbopi/check.py` |
| `main()` | `run_robot.py` |

**What's new since Lab 1:**

- `rosbridge_client.py` also subscribes to the line sensor. The latest reading is
  always available as `client.line_sensors`.
- The window has a **Line sensors** panel showing the 4 sensors live.
- `gui.py` has helper methods that start and stop line following safely. You'll
  wire them up in Task 1.

> **Why split the file up?** Each file now answers one question. "How do I talk
> to the robot?" → `rosbridge_client.py`. "What does the window look like?" →
> `gui.py`. When something breaks, you know where to look. And your line-follower
> logic gets its own file with **no** GUI or networking code in it, so it's short,
> readable and easy to test.

You don't need to change anything in `config.py`, `rosbridge_client.py` or
`drive.py`, except the tuning values in `config.py` during Task 3.

---

## 2. Getting started

### 2.1 Get the code

```bash
git clone <this repository's URL>
cd Lab_2
```

(Or download the ZIP from GitHub and unzip it.) From now on, **run every command
from inside the `Lab_2` folder**, the one that contains `run_robot.py`.

### 2.2 Install the one package it needs

```bash
pip install -r requirements.txt
```

This installs `websocket-client`, the same package as in Lab 1.

### 2.3 Run the self-check (no robot needed)

```bash
python run_robot.py --check
```

You should see:

```
Lab 2 self-check (no robot needed)

Task 1  TODO 1A  Line Follow button exists and is on screen     not done yet
Task 1  TODO 1B  toggle_line_follow() switches the mode         not done yet
Task 1  TODO 1C  publish_loop() uses the line follower          not done yet
Task 2  Step 2   line_position() - perception                   not done yet
Task 3  Step 3A  LineFollower.step() - reflex                   not done yet
Task 3  Step 3B  LineFollower.step() - memory                   not done yet

(line_follower.py does not exist yet - you create it at the start of Task 2.)
...
```

"not done yet" everywhere is correct: you haven't started. As you finish each
part it changes to `ok`. If something is wrong, it prints a `FAIL:` line that
says what it expected and what your code did.

### 2.4 Connect to the robot and run the program

1. Turn the robot on and wait for it to finish booting (about a minute).
2. Connect the lab computer to the **robot's Wi-Fi**, exactly as in Lab 1.
3. Run:

   ```bash
   python run_robot.py
   ```

4. Check the top line of the window says **"rosbridge: connected to 192.168.149.1"** in green.
5. Drive around a little with the joystick to make sure everything from Lab 1 still works.
6. **Look at the "Line sensors" panel.** Pick the robot up, or slide it by hand, so
   the black line passes under the front bumper. The four squares should turn
   black one at a time as each sensor passes over the line.

> **Checkpoint:** if the squares light up in the right order (left square when the
> line is under the left side of the bumper), you're ready to start. If they stay
> grey, or light up in the wrong order or backwards, tell your TA before
> continuing. That's a setting in `config.py`, not something wrong with your code.

---

## 3. How line following works

**Read this whole section before Task 2.** The tasks will make much more sense.

### 3.1 The sensor

Under the TurboPi's front bumper is a **4-channel infrared line sensor**. Each
channel is a tiny infrared LED next to a light detector, pointing down at the floor.

- A **light** floor reflects the infrared light back → the detector sees it → **"no line"**.
- A **black** line absorbs the infrared light → nothing comes back → **"line!"**.

So each channel gives exactly **one bit**: *"I see black"* or *"I don't."* That's
the whole percept. The robot never sees the line's shape, only four yes/no
answers, ten times a second.

In your code the reading arrives as a tuple of 4 booleans, left to right, as seen
from **behind** the robot looking forward:

```
                  FRONT of the robot  (driving direction ↑)
         ┌──────────────────────────────────────────┐
         │    [L]       [CL]       [CR]       [R]   │  ← 4 sensors under the bumper
         └──────────────────────────────────────────┘
index:        0          1          2          3

sensors = (False, True, True, False)     True = this sensor sees BLACK
```

### 3.2 What the readings mean

Picture the black line under the bumper:

| `sensors` | Picture | Meaning |
|---|---|---|
| `(F, T, T, F)` | `· █ █ ·` | Line is centred. Go straight. |
| `(F, T, F, F)` | `· █ · ·` | Line is a bit to the **left**. |
| `(T, F, F, F)` | `█ · · ·` | Line is far to the **left**. Turn left hard! |
| `(F, F, T, T)` | `· · █ █` | Line is to the **right**. |
| `(T, T, T, T)` | `█ █ █ █` | A crossing line or a very wide patch. Treat it as centred. |
| `(F, F, F, F)` | `· · · ·` | **No line at all.** We've lost it (or it ended). |

### 3.3 Step 1, perception: four bits → one number

Writing a separate rule for each of the 16 possible readings would be messy. A
better approach is to **summarise** the reading as one number: the line's
**position**.

Give each sensor a **weight** equal to its distance from the centre of the bumper:

```
sensor:     L      CL     CR      R
weight:   -1.5   -0.5   +0.5   +1.5
```

The line's position is the **average weight of the sensors that see black**:

| `sensors` | Sensors on the line | Position |
|---|---|---|
| `· █ █ ·` | CL, CR | (−0.5 + 0.5) / 2 = **0.0** (centred) |
| `· █ · ·` | CL | −0.5 / 1 = **−0.5** (a bit left) |
| `█ █ · ·` | L, CL | (−1.5 − 0.5) / 2 = **−1.0** (left) |
| `· · · █` | R | **+1.5** (far right) |
| `· · · ·` | none | no line → **`None`** |

**Negative = line is on the LEFT. Positive = line is on the RIGHT. Zero = centred.**

This is what you'll write in **Task 2**. Notice that most of the "intelligence"
is in this step: once you know where the line is, deciding what to do is much easier.

### 3.4 Step 2, action: one number → a steering command

The robot drives forward at a steady speed and **turns toward the line**. The
further off-centre the line is, the harder it turns:

```
turn rate  =  (some constant)  ×  position
```

This is called **proportional control**. The constant is `TURN_GAIN` in
`config.py`. Compare it with the simpler **bang-bang** approach: "line on the left?
turn left at full rate. On the right? turn right at full rate". Bang-bang works,
but the robot zig-zags because it always over-corrects. Proportional control turns
gently for small errors and hard for big ones, so it drives much more smoothly.

#### ⚠ The sign trap (like Lab 1's TODO 2)

Remember the ROS convention from Lab 1: **`angular.z` is positive for a LEFT
(counter-clockwise) turn.** Now fill in this table in your head:

| Line is... | `position` is... | Robot must turn... | `az` must be... |
|---|---|---|---|
| on the left | negative | left | ? |
| on the right | positive | right | ? |

If your answer is "`az` has the **opposite** sign to `position`", you've spotted
the trap. Your formula needs a minus sign somewhere. If you get this wrong, the
robot turns *away* from the line and drives off immediately. `--check` will
catch it before the robot does.

### 3.5 Losing the line, and why a memory helps

On a sharp curve the line can slide out from under all four sensors. The reading
is now `(F, F, F, F)`, and a robot that only looks at the current reading has
**no idea** which way to go.

But a moment ago it *did* know. If the last position it saw was on the left, the
line almost certainly left on the left. So the agent should **remember** where it
last saw the line, and when it loses the line, **spin toward that side** until
the line reappears.

| Last seen... | Now sees nothing → |
|---|---|
| on the left (position < 0) | spin **left** on the spot (`az = +SEARCH_TURN`) |
| on the right (position > 0) | spin **right** on the spot (`az = −SEARCH_TURN`) |
| dead centre (position = 0) | the line probably **ended**. **Stop.** |
| never seen at all | don't wander off. **Stop.** |

### 3.6 The AI connection: two kinds of agent

This lab builds two classic agent designs from the course:

- **Task 3A: simple reflex agent.** The action depends **only on the current
  percept**: `action = f(sensors)`. It's fast and simple, and it's helpless when the
  percept doesn't contain enough information (line lost).
- **Task 3B: model-based reflex agent.** The agent keeps **internal state**, here
  a single number, `last_position`, that summarises the past. The action
  depends on the current percept **and** that state. One remembered number is
  enough to fix the lost-line problem.

As you test, think about this: *what does the robot actually "know" at each
moment, and where does that knowledge come from?*

### 3.7 How your code gets called

You don't write a loop. The GUI already runs one: `publish_loop()` runs every
100 ms (10 times a second). After Task 1, while line following is on, each run of
that loop does this:

```
publish_loop()                            (turbopi/gui.py, every 100 ms)
  └─ line_command()                       (provided: safety checks)
       └─ your_follower.step(sensors)     ← YOUR CODE (Task 3)
            └─ line_position(sensors)     ← YOUR CODE (Task 2)
            returns (lx, ly, az)
  └─ client.cmd_vel(lx, ly, az)           (Lab 1: sends it to the robot)
```

`line_command()` also handles safety for you:

- If the sensor stops sending data, line following switches off.
- If your code crashes, line following switches off and the error is printed in the terminal.
- No matter what your code returns, the speeds are capped at the Lab 1 limits.

---

## 4. Task 1: Add the Line Follow button

**Goal:** a button in the window that switches line following on and off.

Open **`turbopi/gui.py`**. There are three TODOs. Search the file for `TODO 1`.

### TODO 1A: create the button (`build_layout()`)

Create a `tk.Button` and store it in **`self.line_btn`**:

- parent: `line_row` (the frame created just above the TODO)
- text: `"Start Line Follow"`, width: `20`
- when clicked, it calls `self.toggle_line_follow`

Then `.pack()` it.

💡 Use the **STOP** button a few lines above as your model. It does almost exactly
the same thing.

⚠ Write `command=self.toggle_line_follow` **without** `()`. You're handing tkinter
the method so it can call it **later**, on each click. With `()`, Python calls it
**right now**, while the window is still being built.

### TODO 1B: make the button toggle (`toggle_line_follow()`)

When the button is clicked:

- if line following is **on** (`self.line_mode` is `True`), call `self.stop_line_follow()`
- otherwise, call `self.start_line_follow()`

`start_line_follow()` and `stop_line_follow()` are provided. Read them: they load
your `line_follower.py`, change the button's text and colour, and show messages.

### TODO 1C: let the line follower drive (`publish_loop()`)

Right now `publish_loop()` always gets the velocity from the joystick:

```python
lx, ly, az = twist_from_joystick(self.joy_x, self.joy_y, self.turn)
```

Change it so that **while `self.line_mode` is `True`** the velocity comes from
`self.line_command()` instead (it also returns `(lx, ly, az)`), and from the
joystick otherwise.

> **Think about it:** this is the *only* place that decides what velocity to send.
> Why does that make the robot easier to keep safe?

### Check Task 1

```bash
python run_robot.py --check
```

All three `Task 1` lines should say `ok`. Then run `python run_robot.py`: the
button should be there. Clicking it now shows *"line_follower.py not found"*. That's
expected, because you haven't written the line follower yet.

**Safety features you get for free once Task 1 works:** while line following is
on, **touching the joystick**, pressing **STOP** or pressing the **space bar**
switches it off immediately and gives you control back.

---

## 5. Task 2: Perception, "where is the line?"

**Goal:** a function that turns the 4 sensor readings into one position number
(section 3.3).

### 5.1 Create your file

Create a **new, empty file** named exactly **`line_follower.py`** in the
`Lab_2` folder, next to `run_robot.py` (**not** inside `turbopi/`).

```
Lab_2/
├── run_robot.py
├── line_follower.py      ← here
└── turbopi/
```

In VS Code: right-click the `Lab_2` folder → **New File** → `line_follower.py`.

Run `python run_robot.py --check`. The "not found" note should disappear, and
Tasks 2 and 3 should still say `not done yet`.

### 5.2 Write `line_position()`

Type this into `line_follower.py`, then replace the `TODO` with your code:

```python
"""
Lab 2 - my line follower.

Step 2 (Task 2): line_position()  - perception: 4 sensors -> one number
Step 3 (Task 3): LineFollower     - action: that number -> a velocity
"""
from turbopi.config import FOLLOW_SPEED, TURN_GAIN, SEARCH_TURN

# Where each sensor sits, left to right, measured from the centre of the bumper.
SENSOR_WEIGHTS = (-1.5, -0.5, 0.5, 1.5)


def line_position(sensors):
    """sensors: 4 booleans (leftmost .. rightmost), True = sees black.

    Returns the AVERAGE weight of the sensors that see the line
    (negative = line is LEFT of centre, positive = RIGHT, 0.0 = centred),
    or None if no sensor sees the line.
    """
    # TODO (Task 2)
```

**Requirements:**

- Return `None` (not `0`!) when no sensor sees the line. `0.0` means "centred",
  which is a completely different situation.
- `sensors` may be a tuple or a list. Don't modify it.
- Don't hard-code the 16 cases. Use `SENSOR_WEIGHTS` and a loop (or
  `zip(SENSOR_WEIGHTS, sensors)`).

💡 Work out the examples in the table in section 3.3 by hand first. Your function
should produce exactly those numbers.

### 5.3 Check Task 2

```bash
python run_robot.py --check
```

`Task 2 ... ok`. If not, each `FAIL:` line shows the sensor pattern (`B` = black,
`W` = white), what was expected and what you returned.

### 5.4 Try it on the robot (it won't move)

Run `python run_robot.py`. Under the sensor squares, the window now shows
**your** `line_position()` result, live. Slide the robot slowly across the line by
hand and watch the number go from about −1.5 to +1.5. Move it onto plain floor,
away from the line, and you should see `None (no line)`.

> **Try this:** lift the robot off the floor. All four squares turn **black**. Why?
> (Hint: what does the detector receive when there's no surface to reflect the
> infrared light?) The robot's "percept" is not the same thing as the world.

> **Think about it:** with 4 on/off sensors, how many different position values
> can your function produce? What does that mean for how smoothly the robot can
> steer?

*(If you edit `line_follower.py` while the program is running, restart the
program to see your new `line_position()` in the readout.)*

---

## 6. Task 3: Action, "which way do I steer?"

**Goal:** an agent that, given the sensors, returns the velocity to send.

Add this class **below** `line_position()` in `line_follower.py`:

```python
class LineFollower:
    """The line-following agent. The GUI creates ONE of these when you click
    Start Line Follow, then calls step() 10 times a second."""

    def __init__(self):
        # TODO (Step 3B): the agent's memory goes here
        pass

    def step(self, sensors):
        """sensors: 4 booleans, as for line_position().
        Returns (lx, ly, az): forward m/s, left m/s, turn rad/s (+ = LEFT)."""
        position = line_position(sensors)

        # TODO (Step 3A): no line -> stop. Otherwise drive forward and steer.

        # TODO (Step 3B): remember where the line was; when it is lost,
        #                 spin toward the side where it was last seen.
```

Use the three tuning values from `config.py` (already imported at the top of your
file): `FOLLOW_SPEED`, `TURN_GAIN` and `SEARCH_TURN`. **Don't type the numbers
in yourself.** That way you can tune the robot later without touching your code.

### Step 3A: a simple reflex agent

Make `step()` return:

| Situation | `lx` | `ly` | `az` |
|---|---|---|---|
| line seen (`position` is a number) | `FOLLOW_SPEED` | `0.0` | proportional to `position`, using `TURN_GAIN` (**watch the sign!** See section 3.4) |
| no line (`position` is `None`) | `0.0` | `0.0` | `0.0` (stop) |

Check: `Step 3A ... ok`. (`Step 3B` will still say `not done yet`.)

**Try it on the track now** (see section 7). The robot should follow straight lines
and gentle curves. On a sharp curve it will probably lose the line and **stop**.
That's the limit of a simple reflex agent. Step 3B fixes it.

### Step 3B: add memory (a model-based reflex agent)

1. In `__init__`, create `self.last_position` and set it to `None` ("I have never
   seen the line").
2. In `step()`, every time you **do** see the line, store its position in
   `self.last_position`.
3. When you **don't** see the line, use `self.last_position` to choose, following
   the table in section 3.5:
   - last seen on the left → `(0.0, 0.0, +SEARCH_TURN)`
   - last seen on the right → `(0.0, 0.0, -SEARCH_TURN)`
   - last seen exactly centred, or never seen → `(0.0, 0.0, 0.0)`

⚠ Use `self.last_position`, not a plain `last_position`. A plain local variable
disappears at the end of every `step()` call, so the robot would never remember
anything.

Check: every line `ok`:

```
Task 1: complete.
Task 2: complete.
Task 3: complete.
```

---

## 7. Running on the track

### Safety first

- Start with the robot **on the line**, pointing along it, with plenty of space around the track.
- Keep a hand near the keyboard. **Space bar** or **STOP** stops it instantly, and so does
  touching the joystick.
- Closing the window also stops the robot (that was Lab 1's TODO 3).

### Run it

1. `python run_robot.py`, and wait for the green "connected".
2. Place the robot on the line. Check the sensor squares show the line roughly in the middle.
3. Click **Start Line Follow**. The button turns green and the status bar shows `[LINE]`.
4. Watch the status bar: it shows the exact `linear.x` and `angular.z` your agent sends each step.
5. Click **Stop Line Follow** (or press space) to stop.

**After editing `line_follower.py`:** click **Stop**, then **Start** again. Your
file is reloaded every time you press Start, so you don't need to restart the program.
**After editing `config.py`:** close the window and run the program again.

### Tuning (in `turbopi/config.py`)

| You see... | Probably because... | Try |
|---|---|---|
| Robot wobbles or zig-zags along a straight line | Steering over-corrects | **Lower** `TURN_GAIN` |
| Robot drifts off the outside of curves | Steering too weak | **Raise** `TURN_GAIN`, or **lower** `FOLLOW_SPEED` |
| Fine on straights, loses the line on sharp turns | Too fast for 10 decisions/second | **Lower** `FOLLOW_SPEED` (but keep it ≥ 0.15) |
| Spins searching but some wheels don't move | Below the motors' dead zone | Keep `SEARCH_TURN` ≥ 1.4 (Lab 1: below ~1.4 rad/s some wheels stall) |
| Robot doesn't move at all with the line centred | `FOLLOW_SPEED` < 0.15 m/s | The motors don't turn below 0.15 m/s (Lab 1's `MIN_LINEAR`) |
| Turns **away** from the line | Sign error in `az` | Re-read section 3.4. `--check` should be failing too. |

Change **one** value at a time, and write down what you tried and what happened.

> **Think about it:** at `FOLLOW_SPEED = 0.20` m/s the robot travels 2 cm between
> decisions (100 ms apart). Why does going faster make the robot worse at
> following, even if the motors could handle it?

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `websocket-client is not installed` | `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'turbopi'` | You're not in the `Lab_2` folder. `cd` into the folder containing `run_robot.py`. |
| "line_follower.py not found" when you click Start | The file is in the wrong place or misnamed. It must be `Lab_2/line_follower.py`, next to `run_robot.py`. Check for `line_follower.py.txt` on Windows (turn on "File name extensions" in Explorer). |
| "rosbridge: NOT connected" (red) | You're not on the robot's Wi-Fi, or the robot is still booting. It retries every 3 seconds on its own. |
| Sensor squares stay grey; "position: (no sensor data)" | The line sensor topic isn't arriving. Tell your TA (see section 10). |
| "Line sensor is not responding - line following stopped" | Same as above: no sensor data for over 1 second. |
| "Your LineFollower.step() failed: ..." | Your code raised an error. The full traceback is in the **terminal** you launched from. Often `step()` returns nothing (forgot `return`) or returns 2 values instead of 3. |
| `--check` says `skipped - no display available` | Task 1 needs a screen to build the window. Run the check on the lab computer, not over SSH. |
| `--check` crashes with "toggle_line_follow() ran while the window was still being built" | Remove the `()` after `command=self.toggle_line_follow` (TODO 1A). |

---

## 9. Extensions (optional)

Finished early? Try one of these. Add a **new** class or setting rather than
changing your working one, so `--check` still passes.

1. **Keyboard shortcut.** Make the `l` key toggle line following. (`bind_keys()`
   in `gui.py`. How is `c` bound?)
2. **Obstacle stop.** Combine Lab 1's sonar with Lab 2: stop following when
   `client.distance_mm` is below `SONAR_WARN_MM`. Where's the right place for that
   check: your `LineFollower`, or `line_command()`? Why?
3. **Steer by strafing.** The TurboPi has mecanum wheels and can slide sideways
   (`ly`, from Lab 1). Write a follower that keeps the robot pointing straight and
   corrects with `ly` instead of `az`. On which tracks is this better or worse?
4. **Smarter search.** If the search spin goes on too long (say, a full turn),
   give up and stop. *Hint:* count the `step()` calls since the line was lost.
5. **Smoother speed.** Slow down on curves: make `lx` smaller when `|position|` is large.
6. **PD control.** Also use how fast the position is *changing* (this position
   minus the previous one) to damp the wobble. This is the "D" in a PID controller.

---

## 10. For instructors and TAs

**Answers** are not in this repository. Keep them separate.

**Before the lab, confirm the line sensor topic on your robot image.** With the
lab computer on the robot's Wi-Fi:

```bash
python tools/list_topics.py line          # topics with "line" in their name
python tools/list_topics.py --echo <topic>  # watch it while sliding the robot over a line
```

- If the robot already publishes the sensor, set `LINE_TOPIC` and `LINE_TYPE` in
  `turbopi/config.py`. `parse_line_message()` in `rosbridge_client.py` accepts either
  `{"data": [s1, s2, s3, s4]}` or `{"data": <4-bit mask>}`. Adapt it there if your
  topic uses another format. Student code only ever sees 4 booleans.
- A topic marked `(NO PUBLISHER - no data will arrive)` only exists because something
  subscribed to it (for example a running `run_robot.py`). It doesn't count. On our
  stock Hiwonder TurboPi ROS 2 image, the IR line sensor is **not** published.
  (`/line_following` is Hiwonder's *camera*-based line follower, not this sensor.)
- If it isn't published, run `robot_side/line_sensor_node.py` **on the robot**. It reads the
  sensor over I2C and publishes `/line_sensor` (`std_msgs/msg/Int32MultiArray`, 20 Hz),
  which matches the defaults in `config.py`. Read the notes at the top of that file
  first, and check its I2C address and register on your hardware.
- Line following stops if no sensor message arrives for `LINE_STALE_S` (1 s). If your
  topic only publishes when the value **changes**, raise that value or republish at a
  fixed rate.
- If the sensor squares light up in the wrong order, change `LINE_CHANNEL_ORDER`. If they
  light up over white instead of black, set `LINE_INVERT = True`. Both are in
  `config.py`, so students' code stays the same on every robot.

**Track:** black electrical tape (about 1.5–2 cm wide) on a light, matte floor
works well. Include at least one straight, one gentle curve and one sharp curve. The
sharp curve is what makes the difference between Step 3A and 3B visible.
