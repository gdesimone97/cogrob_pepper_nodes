import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from pepper_interfaces.msg import SoftBioInfo, SoftBioList
import numpy as np
from cv_bridge import CvBridge
from deepface import DeepFace

NODE_NAME = 'soft_biometrics_detector'

class SoftBiometricsDetector(Node):

    BIOMETRICS = ['age', 'gender', 'race', 'emotion']

    def __init__(self):
        super().__init__(NODE_NAME)
        self._init_models()
        self.br = CvBridge()
        self.pub_biometrics = self.create_publisher(SoftBioList, "/in_rgb/biometrics", 10)
        self.sub_img = self.create_subscription(Image, "/in_rgb", self.img_callback, 10)
        self.get_logger().info(f"{NODE_NAME} node has been started.")
    
    def _init_models(self):
        img_np = np.zeros((256, 256, 3), dtype=np.uint8)
        DeepFace.analyze(img_np, actions=self.BIOMETRICS, enforce_detection=False, silent=True)

    def img_callback(self, msg: Image):
        img_np = self.br.imgmsg_to_cv2(msg)
        biometrics = DeepFace.analyze(img_np, actions=self.BIOMETRICS, enforce_detection=False, silent=True)
        biometrics_list_msg = SoftBioList()
        for bio in biometrics:
            biometrics_msg = self.biometrics2msg(bio)
            biometrics_list_msg.soft_biometrics.append(biometrics_msg)
        self.pub_biometrics.publish(biometrics_list_msg)
    
    def biometrics2msg(self, data_dict: dict):
        results = {}
        for k in self.BIOMETRICS:
            target_k = "dominant_" + k if k != "age" else k
            data = data_dict.get(target_k, None)
            if data is not None:
                results[k] = data
        msg = SoftBioInfo(**results)
        return msg

def test():
    import cv2 as cv
    from pathlib import Path
    curr_dir = Path(__file__).parent
    img = cv.imread(curr_dir.joinpath("test.jpg").as_posix())
    assert img is not None, "Test image not found."
    rclpy.init()
    node = SoftBiometricsDetector()
    node.img_callback(node.br.cv2_to_imgmsg(img))

def main():
    rclpy.init()
    node = SoftBiometricsDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    test()