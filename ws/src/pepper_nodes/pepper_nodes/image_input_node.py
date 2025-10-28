#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np
from pepper_nodes import PepperNode
from pepper_nodes.utils import Session

TOP_CAMERA = 0
BOTTOM_CAMERA = 1
DEPTH_CAMERA = 2

RES_120P = 0
RES_240P = 1
RES_480P = 2
RES_960P = 3

COLORSPACE_RGB = 13

class ImageInputNode(PepperNode):

    def __init__(self):
        """
        The function initializes an image input node for capturing RGB camera stream with specified
        resolution and frame rate.
        """
        super().__init__('image_input_node')

        self.fps = 20
        resolution = RES_480P
        rgb_camera = TOP_CAMERA

        if resolution == RES_120P:
            self.width, self.height = 160, 120
        elif resolution == RES_240P:
            self.width, self.height = 320, 240
        elif resolution == RES_480P:
            self.width, self.height = 640, 480
        elif resolution == RES_960P:
            self.width, self.height = 1280, 960
        else:
            self.width, self.height = None, None

        self.session = Session(self.ip, self.port)
        self.camera = self.session.get_service("ALVideoDevice")
        self.rgb_sub = self.camera.subscribeCamera("RGB Stream", rgb_camera, resolution, COLORSPACE_RGB, self.fps)

        if not self.rgb_sub:
            subs = self.camera.getSubscribers()
            [self.camera.unsubscribe(s) for s in subs]
            self.rgb_sub = self.camera.subscribeCamera("RGB Stream", rgb_camera, resolution, COLORSPACE_RGB, self.fps)
            if not self.rgb_sub:
                raise Exception("Camera is not initialized properly")

        self.image_publisher = self.create_publisher(Image, 'in_rgb', 1)
        self.bridge = CvBridge()
        self.timer = self.create_timer(1.0 / self.fps, self.publish_frame)

        self.get_logger().info("ImageInputNode initialized")

    def get_color_frame(self):
        """
        This function retrieves a color frame from a camera and returns it as a numpy array.
        :return: The `get_color_frame` method returns an image frame in RGB format captured by the
        camera.
        """
        raw_rgb = self.camera.getImageRemote(self.rgb_sub)
        image = np.frombuffer(raw_rgb[6], np.uint8).reshape(raw_rgb[1], raw_rgb[0], 3)
        return image

    def publish_frame(self):
        """
        This function publishes a color frame as an image message.
        """
        frame = self.get_color_frame()
        if frame is not None:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="rgb8")
            msg.header.stamp = self.get_clock().now().to_msg()
            self.image_publisher.publish(msg)

    def stop(self):
        """
        The `stop` function unsubscribes the camera from the RGB topic.
        """
        self.camera.unsubscribe(self.rgb_sub)

def main():
    rclpy.init()
    node = ImageInputNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        import sys
        print(sys.exc_info())
        node.stop()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
