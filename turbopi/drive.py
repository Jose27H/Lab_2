"""
Joystick -> velocity: twist_from_joystick() from Lab 1 (TODO 2, completed).

You do NOT need to change anything in this file for Lab 2. It is only used
while YOU are driving; while the robot follows the line, your LineFollower
(line_follower.py) decides the velocity instead.
"""
import math

from .config import JOY_DEADZONE, MAX_LINEAR, MIN_LINEAR, MAX_ANGULAR

# The stick snaps to the nearest of 8 compass directions. Order starts at E
# and goes counter-clockwise in 45 degree steps (matches atan2 with +y = UP).
_EIGHT_DIRECTIONS = [
    (1, 0), (1, 1), (0, 1), (-1, 1),
    (-1, 0), (-1, -1), (0, -1), (1, -1),
]


def snap_to_8_directions(joy_x, joy_y):
    """Return (dir_x, dir_y), each in {-1, 0, 1}; (0, 0) inside JOY_DEADZONE."""
    if math.hypot(joy_x, joy_y) < JOY_DEADZONE:
        return 0, 0
    angle = math.degrees(math.atan2(joy_y, joy_x)) % 360
    return _EIGHT_DIRECTIONS[round(angle / 45) % 8]


def twist_from_joystick(joy_x, joy_y, turn):
    """Convert the window's input state into Twist values.

        joy_x : -1.0 .. 1.0    knob position, +1 = pushed fully RIGHT
        joy_y : -1.0 .. 1.0    knob position, +1 = pushed fully UP
        turn  : -1, 0, +1      +1 while "Rotate L" is held, -1 while "Rotate R" is held

    Returns (lx, ly, az): forward m/s, LEFT m/s, turn rad/s (+ = counter-clockwise).
    Remember the Lab 1 sign trap: ROS +y is LEFT, but the joystick's +x is RIGHT.
    """
    dir_x, dir_y = snap_to_8_directions(joy_x, joy_y)
    axes_active = abs(dir_x) + abs(dir_y)
    if axes_active == 2:
        # Diagonal: keep all 4 mecanum wheels turning - one wheel pair at
        # MAX_LINEAR, the other at MIN_LINEAR (the slowest speed that moves).
        vx = (MAX_LINEAR + MIN_LINEAR) / 2
        vy = (MAX_LINEAR - MIN_LINEAR) / 2
        lx, ly = dir_y * vx, -dir_x * vy
    elif axes_active == 1:
        lx, ly = dir_y * MAX_LINEAR, -dir_x * MAX_LINEAR
    else:
        lx = ly = 0.0
    return lx, ly, turn * MAX_ANGULAR
