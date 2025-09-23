import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Empty
import time
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup

class BlockingNode(Node):
    def __init__(self):
        super().__init__('blocking_node')
        self.fut = None

        # Subscriber that simulates a blocking operation
        self.test_server = self.create_service(
            Empty,
            'test_service',
            self.callback,
        )
        self.client = self.create_client(Empty, 'test_service')
        # Timer that should run every second
        self.timer = self.create_timer(1.0, self.timer_callback)

    def callback(self, req: Empty.Request, res: Empty.Response) -> Empty.Response:
        self.get_logger().info('Service callback started, simulating blocking operation...')
        time.sleep(5)  # Simulate a blocking operation
        return res

    def timer_callback(self):
        self.get_logger().info('Timer callback running.')
        if self.fut is None or self.fut.done():
            if self.client.wait_for_service(timeout_sec=1.0):
                req = Empty.Request()
                self.fut = self.client.call_async(req)
            else:
                self.get_logger().error('Service not available, waiting again...')

def main(args=None):
    rclpy.init(args=args)
    node = BlockingNode()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    executor.spin()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()