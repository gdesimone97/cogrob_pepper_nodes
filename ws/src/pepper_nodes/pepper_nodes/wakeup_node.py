#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from pepper_interfaces.srv import WakeUp, Rest
from pepper_nodes import PepperNode
from pepper_nodes.utils import Session

class WakeUpNode(PepperNode):

    def __init__(self):
        """
        The function initializes a node for waking up a robot and performs necessary setup tasks.
        """
        super().__init__('wakeup_node')
        self.session = Session(self.ip, self.port)
        self.motion_proxy = self.session.get_service("ALMotion")
        self.posture_proxy = self.session.get_service("ALRobotPosture")

        self.wakeup_service = self.create_service(WakeUp, 'wakeup', self.wakeup_callback)
        self.rest_service = self.create_service(Rest, 'rest', self.rest_callback)

        self.get_logger().info("WakeUpNode initialized")
        self.wakeup()
        self.stand()

    def rest_callback(self, request, response):
        """
        The `rest_callback` function attempts to make a robot rest and retries if it fails, setting the
        response acknowledgment to "ACK".
        
        :param request: The `request` parameter in the `rest_callback` function likely contains
        information or data related to the request being made to the function. This could include any
        input parameters, headers, or other details that the function needs to process in order to
        perform its task. In this specific context, the `request
        :param response: The `response` parameter in the `rest_callback` function is an object that
        likely represents the response that will be sent back to the client or caller of this function.
        In this specific code snippet, the `response` object seems to have an attribute `ack` that is
        being set to the string
        :return: The `response` object is being returned.
        """
        try:
            self.motion_proxy.rest()
        except Exception as e:
            self.get_logger().warn(f"Rest failed, retrying: {e}")
            self.motion_proxy = self.session.get_service("ALMotion")
            self.motion_proxy.rest()
        response.ack = "ACK"
        return response

    def wakeup_callback(self, request, response):
        """
        The `wakeup_callback` function attempts to wake up and stand a robot, retrying if an exception
        occurs, and then sets the response acknowledgment to "ACK".
        
        :param request: The `request` parameter in the `wakeup_callback` function likely contains
        information or data that is being sent to the function when it is called. This information could
        be related to the request that triggered the callback, such as specific instructions or commands
        that the function needs to process.
        :param response: The `response` parameter in the `wakeup_callback` function is an object that
        likely contains information or data related to the response of the function.
        :return: the response object with the acknowledgment set to "ACK".
        """
        try:
            self.wakeup()
            self.stand()
        except Exception as e:
            self.get_logger().warn(f"WakeUp failed, retrying: {e}")
            self.motion_proxy = self.session.get_service("ALMotion")
            self.posture_proxy = self.session.get_service("ALRobotPosture")
            self.wakeup()
            self.stand()
        response.ack = "ACK"
        return response

    def wakeup(self):
        """
        The `wakeup` function in Python uses the `motion_proxy` to wake up the robot.
        """
        self.motion_proxy.wakeUp()
    
    def stand(self):
        """
        The function "stand" sets the robot's posture to "StandInit" with a speed of 0.5.
        """
        self.posture_proxy.goToPosture("StandInit", 0.5)

def main():

    rclpy.init()
    node = WakeUpNode()

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
