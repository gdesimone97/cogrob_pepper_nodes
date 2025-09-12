#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from pepper_interfaces.srv import ExecuteJS, LoadUrl
from pepper_nodes import PepperNode
from pepper_nodes.utils import Session

class TabletNode(PepperNode):

    def __init__(self):
        """
        The `__init__` function initializes a TabletNode object by setting up a session, tablet proxy,
        and services for executing JavaScript and loading URLs.
        """
        super().__init__('tablet_node')
        self.session = Session(self.ip, self.port)
        self.tablet_proxy = self.session.get_service("ALTabletService")
        self.tablet_proxy.resetTablet()

        self.execute_js_service = self.create_service(ExecuteJS, 'execute_js', self.execute_js_callback)
        self.load_url_service = self.create_service(LoadUrl, 'load_url', self.load_url_callback)

        self.get_logger().info("TabletNode initialized")

    def load_url_callback(self, request, response):
        """
        This Python function attempts to show a webview on a tablet using a provided URL and retries if
        it fails.
        """
        try:
            self.tablet_proxy.showWebview(request.url)
        except Exception as e:
            self.get_logger().warn(f"Load URL failed, retrying: {e}")
            self.tablet_proxy = self.session.get_service("ALTabletService")
            self.tablet_proxy.showWebview(request.url)
        response.ack = "ACK"
        return response

    def execute_js_callback(self, request, response):
        """
        The function `execute_js_callback` attempts to execute a JavaScript callback using a tablet
        proxy service, handling exceptions and logging warnings if necessary.
        """
        try:
            self.tablet_proxy.executeJS(request.js)
        except Exception as e:
            self.get_logger().warn(f"Execute JS failed, retrying: {e}")
            self.tablet_proxy = self.session.get_service("ALTabletService")
            self.tablet_proxy.executeJS(request.js)
        response.ack = "ACK"
        return response

def main():
    rclpy.init()
    node = TabletNode()

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