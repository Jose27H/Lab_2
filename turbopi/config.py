"""
Every setting the program uses, in one place.

Lab 1 had these at the top of teleop_scaffold.py. They are unchanged, except
for the new "Line follower (Lab 2)" section at the bottom.

If something needs tuning (speeds, gains, the robot's IP address), it is
tuned HERE - no other file should contain a "magic number".
"""

# -- Robot connection ---------------------------------------------------------
ROBOT_IP       = "192.168.149.1"
ROSBRIDGE_PORT = 9090

# -- Driving (Lab 1, Part H) --------------------------------------------------
CMD_VEL_TOPIC  = "/cmd_vel"
CMD_VEL_TYPE   = "geometry_msgs/msg/Twist"
MAX_LINEAR  = 0.25          # m/s at full joystick deflection
MIN_LINEAR  = 0.15          # m/s: below this the motors do not turn at all (measured)
MAX_ANGULAR = 1.5           # rad/s while a rotate button is held (below ~1.4 some wheels stall)
PUBLISH_PERIOD_MS = 100     # send /cmd_vel 10 times a second, whether or not input changed
JOY_DEADZONE = 0.3          # stick displacement below this counts as centred (stopped)

# -- Camera pan/tilt servos (Lab 1, Part I) -----------------------------------
SERVO_TOPIC = "/ros_robot_controller/pwm_servo/set_state"
SERVO_TYPE  = "ros_robot_controller_msgs/msg/SetPWMServoState"
SERVO_PAN, SERVO_TILT = 2, 1                            # servo ids
SERVO_MIN, SERVO_MAX, SERVO_CENTER = 1000, 2000, 1500   # pulse width, microseconds
SERVO_STEP = 50             # microseconds per step while a control is held
SERVO_PERIOD_MS = 100       # step 10 times a second while held
SERVO_DURATION = 0.05       # seconds the servo is given to reach each step
# A LARGER pan pulse turns the camera LEFT; a LOWER tilt pulse points it UP.
PAN_LEFT, PAN_RIGHT = +1, -1
TILT_UP, TILT_DOWN = -1, +1

# -- Ultrasonic distance sensor (Lab 1, Part J) -------------------------------
SONAR_TOPIC = "/sonar_controller/get_distance"
SONAR_TYPE  = "std_msgs/msg/Int32"              # distance in MILLIMETRES
SONAR_WARN_MM = 200                             # readout turns red closer than this
SUBSCRIBE_THROTTLE_MS = 100     # at most one message per topic per 100 ms from rosbridge

# -- GUI ----------------------------------------------------------------------
JOY_SIZE    = 240           # joystick canvas size in pixels
KNOB_RADIUS = 24

# -- Line follower (Lab 2) ----------------------------------------------------
# The TurboPi has a 4-channel infrared line sensor under its front bumper.
# Each channel reports one thing: "I see black" or "I do not".
#
# The stock robot image does not publish it, so on connect run_robot.py
# starts robot_side/line_sensor_node.py on the robot over SSH (nothing is
# installed; see turbopi/robot_setup.py and README section 10).
LINE_TOPIC = "/line_sensor"
LINE_TYPE  = "std_msgs/msg/Int32MultiArray"     # data = [s1, s2, s3, s4], 1 = black
AUTO_START_LINE_SENSOR = True
ROBOT_SSH_USER     = "pi"           # same on every robot (all flashed from one image)
ROBOT_SSH_PASSWORD = "raspberrypi"
ROBOT_CONTAINER    = "turbopi"      # the Docker container ROS 2 runs in

# Which raw channel is physically LEFTMOST, second, third, RIGHTMOST, as seen
# from BEHIND the robot looking forward. Fix this (not the student code) if
# the sensor lights in the GUI come on in the wrong order.
LINE_CHANNEL_ORDER = (0, 1, 2, 3)
LINE_INVERT = False         # set True if the lights are ON over white and OFF over black
LINE_STALE_S = 1.0          # line following stops if no sensor reading for this long

# Tuning for YOUR line follower (Lab 2, Task 3). Change these, not your code.
FOLLOW_SPEED = 0.20         # m/s forward while the line is in view (keep >= MIN_LINEAR)
TURN_GAIN    = 1.0          # rad/s of turn per unit of line position
SEARCH_TURN  = 1.5          # rad/s spin while searching for a lost line
