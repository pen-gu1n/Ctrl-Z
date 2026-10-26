import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ShogiListener(Node):

  def __init__(self):
    super().__init__('shogi_listener')
    # "shogi_move" トピックからデータが届いたら listener_callback を実行する設定
    self.subscription = self.create_subscription(
        String, 'shogi_move', self.listener_callback, 10
    )

  def listener_callback(self, msg):
    self.get_logger().info(f'[受信] アーム制御ノードが指し手を受け取りました: {msg.data}')


def main(args=None):
  rclpy.init(args=args)
  node = ShogiListener()
  try:
    rclpy.spin(node)
  except KeyboardInterrupt:
    pass
  finally:
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
  main()
