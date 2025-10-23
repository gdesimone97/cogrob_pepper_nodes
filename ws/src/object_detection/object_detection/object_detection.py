from ultralytics import YOLO
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from pepper_interfaces.srv import ObjectDetection
from pepper_interfaces.msg import Detection
import cv2
from cv_bridge import CvBridge
from typing import List

class ObjDetector(Node):
    NODE_NAME  = "object_detector_node"

    def __init__(self):
        super().__init__(self.NODE_NAME)
        self.model = YOLO("yolo11n")
        self.br = CvBridge()
        self.sub_image = self.create_subscription(Image, "/in_rgb", self.detect, qos_profile=1)
        self.detect_srv = self.create_service(ObjectDetection, "detect_objects", self.detect_callback)
        self.pub_image = self.create_publisher(Image, "/in_rgb/detect", qos_profile=10)
        self.get_logger().info("Object Detector Node has been started.")
    
    def detect(self, img_msg: Image):
        img = self.br.imgmsg_to_cv2(img_msg)
        predict = self.model(img)[0]
        nw_img = self._draw_boxes(img, predict)
        nw_img_msg = self.br.cv2_to_imgmsg(nw_img, encoding='rgb8')
        self.pub_image.publish(nw_img_msg)
        return predict
    
    def detect_callback(self, request: ObjectDetection.Request, response: ObjectDetection.Response):
        img_msg = request.image
        predict = self.detect(img_msg)
        detections = self._predict2detect_msg(predict)
        response.detections = detections
        return response
    
    def _predict2detect_msg(self, predict) -> List[Detection]:
        boxes = predict.boxes.xyxy.tolist()
        names = predict.names
        class_ids = predict.boxes.cls.tolist()
        
        assert len(boxes) == len(class_ids), "Mismatch between boxes and class IDs"
        class_ids = list(map(int, class_ids))
        detetions = []
        for i, box in enumerate(boxes):
            detetion = Detection()
            detetion.class_id = class_ids[i]
            detetion.class_name = names[class_ids[i]]
            detetion.box = box
            detetions.append(detetion)
        return detetions

    def _draw_boxes(self, org_img, predict):

        boxes = predict.boxes.xyxy.tolist()
        names = predict.names
        class_ids = predict.boxes.cls.tolist()
        nw_img = org_img

        # Draw bounding boxes on the image
        for box, class_id in zip(boxes, class_ids):
            x1, y1, x2, y2 = map(int, box)
            label = names[class_id]
            nw_img = cv2.rectangle(nw_img, (x1, y1), (x2, y2), color=(0, 0, 255), thickness=2)

            # Put class name
            cv2.putText(nw_img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=0.5, color=(255, 0, 0), thickness=2)
        
        return nw_img

def test():
    from threading import Thread
    import sys
    from pathlib import Path
    curr_dir = Path(__file__).parent
    rclpy.init()
    node = ObjDetector()
    th = Thread(target=rclpy.spin, args=(node,), daemon=True)
    th.start()
    image = cv2.imread(curr_dir.joinpath("bus.jpg").as_posix())
    assert image is not None, "Image not found"
    image_msg = node.br.cv2_to_imgmsg(image)
    client = node.create_client(ObjectDetection, "detect_objects")
    req = ObjectDetection.Request()
    req.image = image_msg
    resp = client.call(req)
    print(resp)
    sys.exit()


def main():
    rclpy.init()
    node = ObjDetector()
    rclpy.spin(node)

if __name__ == "__main__":
    test()