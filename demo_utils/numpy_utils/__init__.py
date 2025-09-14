import numpy as np
from std_msgs.msg import Float32MultiArray, MultiArrayDimension

def convert2array(msg, dtype=np.float32) -> np.ndarray:
    dim = msg.layout.dim
    size = [s.size for s in dim]
    data = msg.data
    arr = np.array(data, dtype=dtype)
    arr = np.reshape(arr, size)
    return arr

def convert2float32msg(data):
    data = np.array(data, dtype=np.float32)
    data_np_shape = data.shape
    dim = [MultiArrayDimension(size=d) for d in data_np_shape]
    msg = Float32MultiArray()
    msg.data = data.flatten().tolist()
    msg.layout.dim = dim
    return msg