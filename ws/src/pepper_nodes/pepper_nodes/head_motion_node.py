#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from pepper_nodes import PepperNode
from pepper_nodes.utils import Session

class HeadMotionNode(PepperNode):

    def __init__(self):
        """
        The function initializes a node for controlling head motion in a robotics system.
        """
        super().__init__('head_motion_node')
        self.session = Session(self.ip, self.port)
        self.motion_proxy = self.session.get_service("ALMotion")

        self.yaw_subscriber = self.create_subscription(
            Float32MultiArray,
            '/head_rotation/yaw',
            self.head_yaw_callback,
            10
        )

        self.pitch_subscriber = self.create_subscription(
            Float32MultiArray,
            '/head_rotation/pitch',
            self.head_pitch_callback,
            10
        )

        self.get_logger().info("HeadMotionNode initialized")

    def head_yaw_callback(self, msg):
        """
        The function `head_yaw_callback` sets the yaw angle of a robot's head based on incoming data.
        """
        try:
            self.motion_proxy.setAngles(["HeadYaw"], [msg.data[0]], msg.data[1])
        except Exception as e:
            self.get_logger().warn(f"Yaw failed, retrying: {e}")
            self.motion_proxy = self.session.get_service("ALMotion")
            self.motion_proxy.setAngles(["HeadYaw"], [msg.data[0]], msg.data[1])

    def head_pitch_callback(self, msg):
        """
        The `head_pitch_callback` function sets the pitch angle of a robot's head based on incoming
        data.
        """
        try:
            self.motion_proxy.setAngles(["HeadPitch"], [msg.data[0]], msg.data[1])
        except Exception as e:
            self.get_logger().warn(f"Pitch failed, retrying: {e}")
            self.motion_proxy = self.session.get_service("ALMotion")
            self.motion_proxy.setAngles(["HeadPitch"], [msg.data[0]], msg.data[1])

def main():
    rclpy.init()
    node = HeadMotionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        import sys
        print(sys.exc_info())
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()