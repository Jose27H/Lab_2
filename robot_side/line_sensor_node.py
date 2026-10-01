#!/usr/bin/env python3
"""
INSTRUCTOR ONLY - runs ON THE ROBOT, not on the lab computer.

Only needed if your TurboPi image does not already publish the 4-channel
line sensor as a ROS topic (check first with  python tools/list_topics.py line).

Reads the sensor over I2C and publishes it as

    /line_sensor   std_msgs/msg/Int32MultiArray   data = [s1, s2, s3, s4]   1 = black

at 20 Hz, which is what turbopi/config.py expects by default.

    # on the robot (ssh in, inside the ROS 2 environment):
    pip install smbus2
    python3 line_sensor_node.py
    python3 line_sensor_node.py --ros-args -p i2c_address:=120 -p register:=1

VERIFY: the address (0x78) and register (0x01) are taken from Hiwonder's
TurboPi Python SDK (FourInfrared). `i2cdetect -y 1` on the robot should
show a device at 0x78. If the GUI's sensor lights come on over WHITE rather
than black, set LINE_INVERT = True in turbopi/config.py.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray

try:
    from smbus2 import SMBus
except ImportError:                                      # pragma: no cover
    from smbus import SMBus


class LineSensorNode(Node):
    def __init__(self):
        super().__init__("line_sensor")
        self.declare_parameter("i2c_bus", 1)
        self.declare_parameter("i2c_address", 0x78)
        self.declare_parameter("register", 0x01)
        self.declare_parameter("rate_hz", 20.0)
        p = lambda name: self.get_parameter(name).value
        self.bus = SMBus(p("i2c_bus"))
        self.address, self.register = p("i2c_address"), p("register")
        self.pub = self.create_publisher(Int32MultiArray, "/line_sensor", 10)
        self.create_timer(1.0 / p("rate_hz"), self.tick)
        self.get_logger().info(f"publishing /line_sensor from I2C 0x{self.address:02x}")

    def tick(self):
        try:
            value = self.bus.read_byte_data(self.address, self.register)
        except OSError as e:
            self.get_logger().warn(f"I2C read failed: {e}", throttle_duration_sec=2.0)
            return
        # Publish every tick, changed or not: the lab computer treats silence
        # as "sensor dead" and stops line following (LINE_STALE_S).
        self.pub.publish(Int32MultiArray(data=[value >> bit & 1 for bit in range(4)]))


def main():
    rclpy.init()
    node = LineSensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
