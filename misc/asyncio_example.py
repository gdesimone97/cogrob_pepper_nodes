import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import asyncio

class AsyncNode(Node):
    def __init__(self):
        super().__init__('async_node')

        self.subscription = self.create_subscription(
            String,
            'chatter',
            self.listener_callback,
            10
        )

        self.timer = self.create_timer(1.0, self.timer_callback)

    def listener_callback(self, msg):
        self.get_logger().info(f'Received: "{msg.data}" — starting async operation...')
        # Schedule the async task without blocking the executor
        asyncio.create_task(self.async_blocking_operation())

    async def async_blocking_operation(self):
        await asyncio.sleep(5)  # Non-blocking sleep
        self.get_logger().info('Finished async operation.')

    def timer_callback(self):
        self.get_logger().info('Timer callback running.')

def main(args=None):
    rclpy.init(args=args)
    node = AsyncNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
