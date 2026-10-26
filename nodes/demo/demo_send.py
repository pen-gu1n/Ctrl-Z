import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ShogiTalker(Node):

  def __init__(self):
    super().__init__('shogi_talker')
    # "shogi_move" という名前の通信チャンネル（トピック）を作成
    self.publisher_ = self.create_publisher(String, 'shogi_move', 10)
    # 1秒ごとに timer_callback を呼び出すタイマーをセット
    self.timer = self.create_timer(1.0, self.timer_callback)

  def timer_callback(self):
    msg = String()
    msg.data = '76kei'  # 送信する将棋の指し手データ（7六桂）
    self.publisher_.publish(msg)
    self.get_logger().info(f'[送信] 将棋の指し手を送りました: {msg.data}')


def main(args=None):
  rclpy.init(args=args)
  node = ShogiTalker()
  try:
    rclpy.spin(node)
  except KeyboardInterrupt:
    pass
  finally:
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
  main()
