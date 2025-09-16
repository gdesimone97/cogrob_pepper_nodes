#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: furushchev <furushchev@jsk.imi.i.u-tokyo.ac.jp>

import angles
from contextlib import contextmanager
from typing import List
import usb.core
import usb.util
import pyaudio
import math
import numpy as np
import rclpy.time
import tf_transformations as T
import os
import rclpy
from rclpy.clock import ClockType
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.executors import MultiThreadedExecutor
from rcl_interfaces.msg import SetParametersResult
from std_srvs.srv import SetBool
import struct
import sys
import time
from audio_common_msgs.msg import AudioData
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool, Int32, ColorRGBA
from pepper_interfaces.msg import MetaMic
from ros_utils import *
from pepper_nodes.respeaker.config_dict import RESPEAKER_PARAMETERS_ROS

try:
    from pixel_ring import usb_pixel_ring_v2
except IOError as e:
    print(e)
    raise RuntimeError("Check the device is connected and recognized")


# suppress error messages from ALSA
# https://stackoverflow.com/questions/7088672/pyaudio-working-but-spits-out-error-messages-each-time
# https://stackoverflow.com/questions/36956083/how-can-the-terminal-output-of-executables-run-by-python-functions-be-silenced-i
@contextmanager
def ignore_stderr(enable=True):
    if enable:
        devnull = None
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            stderr = os.dup(2)
            sys.stderr.flush()
            os.dup2(devnull, 2)
            try:
                yield
            finally:
                os.dup2(stderr, 2)
                os.close(stderr)
        finally:
            if devnull is not None:
                os.close(devnull)
    else:
        yield


# Partly copied from https://github.com/respeaker/usb_4_mic_array
# parameter list
# name: (id, offset, type, max, min , r/w, info)
RESPEAKER_PARAMETERS = {
    'AECFREEZEONOFF': (18, 7, 'int', 1, 0, 'rw', 'Adaptive Echo Canceler updates inhibit.', '0 = Adaptation enabled', '1 = Freeze adaptation, filter only'),
    'AECNORM': (18, 19, 'float', 16, 0.25, 'rw', 'Limit on norm of AEC filter coefficients'),
    'AECPATHCHANGE': (18, 25, 'int', 1, 0, 'ro', 'AEC Path Change Detection.', '0 = false (no path change detected)', '1 = true (path change detected)'),
    'RT60': (18, 26, 'float', 0.9, 0.25, 'ro', 'Current RT60 estimate in seconds'),
    'HPFONOFF': (18, 27, 'int', 3, 0, 'rw', 'High-pass Filter on microphone signals.', '0 = OFF', '1 = ON - 70 Hz cut-off', '2 = ON - 125 Hz cut-off', '3 = ON - 180 Hz cut-off'),
    'RT60ONOFF': (18, 28, 'int', 1, 0, 'rw', 'RT60 Estimation for AES. 0 = OFF 1 = ON'),
    'AECSILENCELEVEL': (18, 30, 'float', 1, 1e-09, 'rw', 'Threshold for signal detection in AEC [-inf .. 0] dBov (Default: -80dBov = 10log10(1x10-8))'),
    'AECSILENCEMODE': (18, 31, 'int', 1, 0, 'ro', 'AEC far-end silence detection status. ', '0 = false (signal detected) ', '1 = true (silence detected)'),
    'AGCONOFF': (19, 0, 'int', 1, 0, 'rw', 'Automatic Gain Control. ', '0 = OFF ', '1 = ON'),
    'AGCMAXGAIN': (19, 1, 'float', 1000, 1, 'rw', 'Maximum AGC gain factor. ', '[0 .. 60] dB (default 30dB = 20log10(31.6))'),
    'AGCDESIREDLEVEL': (19, 2, 'float', 0.99, 1e-08, 'rw', 'Target power level of the output signal. ', '[-inf .. 0] dBov (default: -23dBov = 10log10(0.005))'),
    'AGCGAIN': (19, 3, 'float', 1000, 1, 'rw', 'Current AGC gain factor. ', '[0 .. 60] dB (default: 0.0dB = 20log10(1.0))'),
    'AGCTIME': (19, 4, 'float', 1, 0.1, 'rw', 'Ramps-up / down time-constant in seconds.'),
    'CNIONOFF': (19, 5, 'int', 1, 0, 'rw', 'Comfort Noise Insertion.', '0 = OFF', '1 = ON'),
    'FREEZEONOFF': (19, 6, 'int', 1, 0, 'rw', 'Adaptive beamformer updates.', '0 = Adaptation enabled', '1 = Freeze adaptation, filter only'),
    'STATNOISEONOFF': (19, 8, 'int', 1, 0, 'rw', 'Stationary noise suppression.', '0 = OFF', '1 = ON'),
    'GAMMA_NS': (19, 9, 'float', 3, 0, 'rw', 'Over-subtraction factor of stationary noise. min .. max attenuation'),
    'MIN_NS': (19, 10, 'float', 1, 0, 'rw', 'Gain-floor for stationary noise suppression.', '[-inf .. 0] dB (default: -16dB = 20log10(0.15))'),
    'NONSTATNOISEONOFF': (19, 11, 'int', 1, 0, 'rw', 'Non-stationary noise suppression.', '0 = OFF', '1 = ON'),
    'GAMMA_NN': (19, 12, 'float', 3, 0, 'rw', 'Over-subtraction factor of non- stationary noise. min .. max attenuation'),
    'MIN_NN': (19, 13, 'float', 1, 0, 'rw', 'Gain-floor for non-stationary noise suppression.', '[-inf .. 0] dB (default: -10dB = 20log10(0.3))'),
    'ECHOONOFF': (19, 14, 'int', 1, 0, 'rw', 'Echo suppression.', '0 = OFF', '1 = ON'),
    'GAMMA_E': (19, 15, 'float', 3, 0, 'rw', 'Over-subtraction factor of echo (direct and early components). min .. max attenuation'),
    'GAMMA_ETAIL': (19, 16, 'float', 3, 0, 'rw', 'Over-subtraction factor of echo (tail components). min .. max attenuation'),
    'GAMMA_ENL': (19, 17, 'float', 5, 0, 'rw', 'Over-subtraction factor of non-linear echo. min .. max attenuation'),
    'NLATTENONOFF': (19, 18, 'int', 1, 0, 'rw', 'Non-Linear echo attenuation.', '0 = OFF', '1 = ON'),
    'NLAEC_MODE': (19, 20, 'int', 2, 0, 'rw', 'Non-Linear AEC training mode.', '0 = OFF', '1 = ON - phase 1', '2 = ON - phase 2'),
    'SPEECHDETECTED': (19, 22, 'int', 1, 0, 'ro', 'Speech detection status.', '0 = false (no speech detected)', '1 = true (speech detected)'),
    'FSBUPDATED': (19, 23, 'int', 1, 0, 'ro', 'FSB Update Decision.', '0 = false (FSB was not updated)', '1 = true (FSB was updated)'),
    'FSBPATHCHANGE': (19, 24, 'int', 1, 0, 'ro', 'FSB Path Change Detection.', '0 = false (no path change detected)', '1 = true (path change detected)'),
    'TRANSIENTONOFF': (19, 29, 'int', 1, 0, 'rw', 'Transient echo suppression.', '0 = OFF', '1 = ON'),
    'VOICEACTIVITY': (19, 32, 'int', 1, 0, 'ro', 'VAD voice activity status.', '0 = false (no voice activity)', '1 = true (voice activity)'),
    'STATNOISEONOFF_SR': (19, 33, 'int', 1, 0, 'rw', 'Stationary noise suppression for ASR.', '0 = OFF', '1 = ON'),
    'NONSTATNOISEONOFF_SR': (19, 34, 'int', 1, 0, 'rw', 'Non-stationary noise suppression for ASR.', '0 = OFF', '1 = ON'),
    'GAMMA_NS_SR': (19, 35, 'float', 3, 0, 'rw', 'Over-subtraction factor of stationary noise for ASR. ', '[0.0 .. 3.0] (default: 1.0)'),
    'GAMMA_NN_SR': (19, 36, 'float', 3, 0, 'rw', 'Over-subtraction factor of non-stationary noise for ASR. ', '[0.0 .. 3.0] (default: 1.1)'),
    'MIN_NS_SR': (19, 37, 'float', 1, 0, 'rw', 'Gain-floor for stationary noise suppression for ASR.', '[-inf .. 0] dB (default: -16dB = 20log10(0.15))'),
    'MIN_NN_SR': (19, 38, 'float', 1, 0, 'rw', 'Gain-floor for non-stationary noise suppression for ASR.', '[-inf .. 0] dB (default: -10dB = 20log10(0.3))'),
    'GAMMAVAD_SR': (19, 39, 'float', 1000, 0, 'rw', 'Set the threshold for voice activity detection.', '[-inf .. 60] dB (default: 3.5dB 20log10(1.5))'),
    # 'KEYWORDDETECT': (20, 0, 'int', 1, 0, 'ro', 'Keyword detected. Current value so needs polling.'),
    'DOAANGLE': (21, 0, 'int', 359, 0, 'ro', 'DOA angle. Current value. Orientation depends on build configuration.')
}


class RespeakerInterface(object):
    VENDOR_ID = 0x2886
    PRODUCT_ID = 0x0018
    TIMEOUT = 100000

    def __init__(self, node: Node):
        self.node = node
        self.dev = usb.core.find(idVendor=self.VENDOR_ID,
                                 idProduct=self.PRODUCT_ID)
        if not self.dev:
            raise RuntimeError("Failed to find Respeaker device")
        self.node.get_logger().info("Initializing Respeaker device")
        self.dev.reset()
        self.pixel_ring = usb_pixel_ring_v2.PixelRing(self.dev)
        self.set_led_think()
        time.sleep(10)  # it will take 10 seconds to re-recognize as audio device
        self.set_led_trace()
        self.node.get_logger().info("Respeaker device initialized (Version: %s)" % self.version)

    def __del__(self):
        try:
            self.close()
        except:
            pass
        finally:
            self.dev = None

    def write(self, name, value):
        try:
            data = RESPEAKER_PARAMETERS[name]
        except KeyError:
            return

        if data[5] == 'ro':
            raise ValueError('{} is read-only'.format(name))

        id = data[0]

        # 4 bytes offset, 4 bytes value, 4 bytes type
        if data[2] == 'int':
            payload = struct.pack(b'iii', data[1], int(value), 1)
        else:
            payload = struct.pack(b'ifi', data[1], float(value), 0)

        self.dev.ctrl_transfer(
            usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, 0, id, payload, self.TIMEOUT)

    def read(self, name):
        try:
            data = RESPEAKER_PARAMETERS[name]
        except KeyError:
            return

        id = data[0]

        cmd = 0x80 | data[1]
        if data[2] == 'int':
            cmd |= 0x40

        length = 8

        try:
            response = self.dev.ctrl_transfer(
                usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
                0, cmd, id, length, self.TIMEOUT)
        except usb.core.USBError as e:
            self.node.get_logger().fatal("Mic USB error")
            self.node.destroy_node()
            raise usb.core.USBError(e.strerror)


        response = struct.unpack(b'ii', response.tobytes())

        if data[2] == 'int':
            result = response[0]
        else:
            result = response[0] * (2.**response[1])

        return result

    def set_led_think(self):
        self.pixel_ring.set_brightness(10)
        self.pixel_ring.think()

    def set_led_trace(self):
        self.pixel_ring.set_brightness(20)
        self.pixel_ring.trace()

    def set_led_color(self, r, g, b, a):
        self.pixel_ring.set_brightness(int(20 * a))
        self.pixel_ring.set_color(r=int(r*255), g=int(g*255), b=int(b*255))

    def set_vad_threshold(self, db):
        self.write('GAMMAVAD_SR', db)

    def is_voice(self):
        return self.read('VOICEACTIVITY')

    @property
    def direction(self):
        return self.read('DOAANGLE')

    @property
    def version(self):
        return self.dev.ctrl_transfer(
            usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, 0x80, 0, 1, self.TIMEOUT)[0]

    def close(self):
        """
        close the interface
        """
        usb.util.dispose_resources(self.dev)


class RespeakerAudio():
    def __init__(self, node: Node, on_audio, channels=None, suppress_error=True):
        self.node = node
        self.logger = self.node.get_logger()
        self.on_audio = on_audio
        self.pub_meta = self.node.create_publisher(MetaMic, "/meta/mic", qos_profile=LATCH_PROFILE)
        with ignore_stderr(enable=suppress_error):
            self.pyaudio = pyaudio.PyAudio()
        self.available_channels = None
        self.channels = channels
        self.device_index = None
        self.rate = 16000
        self.chunk = 1024
        self.bitwidth = 2
        self.bitdepth = 16
        self.publish_meta()

        # find device
        count = self.pyaudio.get_device_count()
        self.logger.debug("%d audio devices found" % count)
        for i in range(count):
            info = self.pyaudio.get_device_info_by_index(i)
            name = info["name"]
            chan = info["maxInputChannels"]
            self.logger.debug(" - %d: %s" % (i, name))
            if name.lower().find("respeaker") >= 0:
                self.available_channels = chan
                self.device_index = i
                self.logger.info("Found %d: %s (channels: %d)" % (i, name, chan))
                break
        if self.device_index is None:
            self.logger.warn("Failed to find respeaker device by name. Using default input")
            info = self.pyaudio.get_default_input_device_info()
            self.available_channels = info["maxInputChannels"]
            self.device_index = info["index"]

        if self.available_channels != 6:
            self.logger.warn("%d channel is found for respeaker" % self.available_channels)
            self.logger.warn("You may have to update firmware.")
        if self.channels is None:
            self.channels = range(self.available_channels)
        else:
            self.channels = filter(lambda c: 0 <= c < self.available_channels, self.channels)
        if not self.channels:
            raise RuntimeError('Invalid channels %s. (Available channels are %s)' % (
                self.channels, self.available_channels))
        self.logger.info('Using channels %s' % self.channels)

        self.stream = self.pyaudio.open(
            input=True, start=False,
            format=pyaudio.paInt16,
            channels=self.available_channels,
            rate=self.rate,
            frames_per_buffer=self.chunk,
            stream_callback=self.stream_callback,
            input_device_index=self.device_index,
        )

    def publish_meta(self):
        msg = MetaMic(
            sample_rate=self.rate,
            chunks_len=self.chunk
        )
        self.pub_meta.publish(msg)
    
    def __del__(self):
        self.stop()
        try:
            self.stream.close()
        except:
            pass
        finally:
            self.stream = None
        try:
            self.pyaudio.terminate()
        except:
            pass

    def stream_callback(self, in_data, frame_count, time_info, status):
        # split channel
        data = np.frombuffer(in_data, dtype=np.int16)
        chunk_per_channel = len(data) // self.available_channels
        data = np.reshape(data, (chunk_per_channel, self.available_channels))
        for chan in self.channels:
            chan_data = data[:, chan]
            # invoke callback
            self.on_audio(chan_data.tobytes(), chan)
        return None, pyaudio.paContinue

    def start(self):
        if self.stream.is_stopped():
            self.stream.start_stream()

    def stop(self):
        if self.stream.is_active():
            self.stream.stop_stream()


class RespeakerNode(Node):

    ADDITIONAL_ROS_PARAMETERS = ROS2ParamList(
        ROS2Param("update_rate", dest="update_rate", value=10.0),
        ROS2Param("sensor_frame_id", dest="sensor_frame_id", value="respeaker_base"),
        ROS2Param("doa_xy_offset", dest="doa_xy_offset", value=0.0),
        ROS2Param("doa_yaw_offset", dest="doa_yaw_offset", value=90.0),
        ROS2Param("speech_prefetch", dest="speech_prefetch", value=3.0),         # No default given in original code
        ROS2Param("speech_continuation", dest="speech_continuation", value=2.0),     # No default given
        ROS2Param("max_duration", dest="speech_max_duration", value=60),            # No default given
        ROS2Param("min_duration", dest="speech_min_duration", value=0.1),            # No default given
        ROS2Param("main_channel", dest="main_channel", value=0),
        ROS2Param("suppress_pyaudio_error", dest="suppress_pyaudio_error", value=True),
    )

    OVERALL_PARAMETERS = ROS2ParamList(*RESPEAKER_PARAMETERS_ROS, *ADDITIONAL_ROS_PARAMETERS)
    
    NODE_NAME = "respeaker_node"

    def __init__(self):
        
        super().__init__(self.NODE_NAME)

        #Custom variables
        self._is_vad_active = True
        self._vad_active_service = self.create_service(SetBool, "/mic/active", self._vad_active_callback)
        
        self.context.on_shutdown(self.on_shutdown)
        self.respeaker = RespeakerInterface(self)

        # init config
        self.config = None
        init_params = init_parameters(self, self.OVERALL_PARAMETERS)
        self.add_on_set_parameters_callback(self.on_config)
        self.init_reaspeaker_parameters()
        
        #
        self.respeaker_audio = RespeakerAudio(self, self.on_audio, suppress_error=self.suppress_pyaudio_error)
        self.speech_audio_buffer = str()
        self.is_speeching = False
        self.speech_stopped = self.get_clock().now()
        self.prev_is_voice = None
        self.prev_doa = None
        # advertise

        self.pub_vad = self.create_publisher(Bool, "is_speeching", qos_profile=LATCH_PROFILE)
        self.pub_doa_raw = self.create_publisher(Int32, "sound_direction", qos_profile=LATCH_PROFILE)
        self.pub_doa = self.create_publisher(PoseStamped, "sound_localization", qos_profile=LATCH_PROFILE)
        self.pub_audio = self.create_publisher(AudioData, "audio", 10)
        self.pub_speech_audio = self.create_publisher(AudioData, "speech_audio", 10)
        self.pub_audios = {
            c: self.create_publisher(AudioData, f"audio/channel{c}", 10)
            for c in self.respeaker_audio.channels
        }

        # start
        self.speech_prefetch_bytes = int(
            self.speech_prefetch * self.respeaker_audio.rate * self.respeaker_audio.bitdepth / 8.0)
        self.speech_prefetch_buffer = b""
        self.respeaker_audio.start()
        self.info_timer = self.create_timer(1.0 / self.update_rate, self.on_timer)
        self.timer_led = None
        self.sub_led = self.create_subscription(
                                                ColorRGBA,
                                                "status_led",
                                                self.on_status_led,
                                                qos_profile=10)

    def _vad_active_callback(self, req: SetBool.Request, resp: SetBool.Response):
        self._is_vad_active = req.data
        self.speech_audio_buffer = str()
        self.speech_prefetch_buffer = b""
        self.is_speeching = False
        self.speech_stopped = rclpy.time.Time(clock_type=ClockType.ROS_TIME)
        self.prev_is_voice = None
        self.prev_doa = None    
        resp.success = self._is_vad_active
        return resp
    
    def init_reaspeaker_parameters(self):
        for p in RESPEAKER_PARAMETERS_ROS:
            name = p.name
            p_value = self.get_parameter(name).value
            self.respeaker.write(name, p_value)

    def on_shutdown(self):
        try:
            self.respeaker.close()
        except:
            pass
        finally:
            self.respeaker = None
        try:
            self.respeaker_audio.stop()
        except:
            pass
        finally:
            self.respeaker_audio = None

    def on_config(self, params: List[Parameter]):
        
        for p in params:
            if p in self.ADDITIONAL_ROS_PARAMETERS:
                defalut_reconfigure(self, [p], self.OVERALL_PARAMETERS)

            else:
                prev_val = self.respeaker.read(p.name)
                value = p.value
                if prev_val != value:
                    self.respeaker.write(p.name, value)
                    self.get_logger().warn(f"Reconfigure: {p.name}: {value}")

        return SetParametersResult(successful=True)

    def on_status_led(self, msg):
        self.respeaker.set_led_color(r=msg.r, g=msg.g, b=msg.b, a=msg.a)
        if self.timer_led and self.timer_led.is_alive():
            self.timer_led.destroy()

        self.timer_led = self.create_timer(
            3.0,  # seconds
            lambda: self.respeaker.set_led_trace()
        )

    def on_audio(self, data, channel):
        self.pub_audios[channel].publish(AudioData(data=data))
        if channel == self.main_channel:
            self.pub_audio.publish(AudioData(data=data))
            if self.is_speeching:
                if len(self.speech_audio_buffer) == 0:
                    self.speech_audio_buffer = self.speech_prefetch_buffer
                self.speech_audio_buffer += data
            else:
                self.speech_prefetch_buffer += data
                self.speech_prefetch_buffer = self.speech_prefetch_buffer[-self.speech_prefetch_bytes:]

    def on_timer(self):
        
        if not self._is_vad_active:
            return
        
        stamp = self.get_clock().now()
        is_voice = self.respeaker.is_voice()
        doa_rad = math.radians(self.respeaker.direction - 180.0)
        doa_rad = angles.shortest_angular_distance(
            doa_rad, math.radians(self.doa_yaw_offset))
        doa = math.degrees(doa_rad)

        # vad
        if is_voice != self.prev_is_voice:
            self.pub_vad.publish(Bool(data=bool(is_voice)))
            self.prev_is_voice = is_voice

        # doa
        if doa != self.prev_doa:
            self.pub_doa_raw.publish(Int32(data=int(doa)))
            self.prev_doa = doa

            msg = PoseStamped()
            msg.header.frame_id = self.sensor_frame_id
            msg.header.stamp = stamp.to_msg()
            ori = T.quaternion_from_euler(math.radians(doa), 0, 0)
            msg.pose.position.x = self.doa_xy_offset * np.cos(doa_rad)
            msg.pose.position.y = self.doa_xy_offset * np.sin(doa_rad)
            msg.pose.orientation.w = ori[0]
            msg.pose.orientation.x = ori[1]
            msg.pose.orientation.y = ori[2]
            msg.pose.orientation.z = ori[3]
            self.pub_doa.publish(msg)

        # speech audio
        if is_voice:
            self.speech_stopped = stamp
        diff = (stamp - self.speech_stopped).nanoseconds *1e-9 
        if diff < self.speech_continuation:
            self.is_speeching = True
        elif self.is_speeching:
            buf = self.speech_audio_buffer
            self.speech_audio_buffer = str()
            self.is_speeching = False
            duration = 8.0 * len(buf) * self.respeaker_audio.bitwidth
            duration = duration / self.respeaker_audio.rate / self.respeaker_audio.bitdepth
            self.get_logger().info("Speech detected for %.3f seconds" % duration)
            if self.speech_min_duration <= duration < self.speech_max_duration:

                self.pub_speech_audio.publish(AudioData(data=buf))

def main():
    if not rclpy.ok():
        rclpy.init()
    n = RespeakerNode()
    rclpy.spin(n)

if __name__ == '__main__':
    main()
