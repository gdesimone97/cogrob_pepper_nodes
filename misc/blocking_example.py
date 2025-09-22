import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time

class BlockingNode(Node):
    def __init__(self):
        super().__init__('blocking_node')

        # Subscriber that simulates a blocking operation
        self.subscription = self.create_subscription(
            String,
            'chatter',
            self.listener_callback,
            10
        )

        # Timer that should run every second
        self.timer = self.create_timer(1.0, self.timer_callback)

    def listener_callback(self, msg):
        self.get_logger().info(f'Received: "{msg.data}" — starting blocking
                               operation...')
        time.sleep(5)  # Simulate a blocking operation
        self.get_logger().info('Finished blocking operation.')

    def timer_callback(self):
        self.get_logger().info('Timer callback running.')

def main(args=None):
    rclpy.init(args=args)
    node = BlockingNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()