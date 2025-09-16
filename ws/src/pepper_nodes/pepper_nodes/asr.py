import numpy as np
from numpy import ndarray
import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import ParameterDescriptor
import torch
from audio_utils import pcm2float
from transformers import AutoProcessor, AutoModel, WhisperProcessor
from pepper_interfaces.srv import Asr
from transformers import GenerationConfig

class LanguageNotSupportedError(Exception):
    def __init__(self, *args):
        super().__init__("Language not supported. Choose one of the following: " + ", ".join(ASRNode.ALLOWED_LANGUAGES))

class ASRNode(Node):

    ALLOWED_LANGUAGES = ['it', 'en']

    def __init__(self):
        super().__init__("asr_node")
        self.declare_parameter("language", "it", 
                               descriptor=ParameterDescriptor(description="Laguage for audio transcription: 'it' or 'en'"))
        self.language = self.get_parameter("language").get_parameter_value().string_value
        if self.language not in ASRNode.ALLOWED_LANGUAGES:
            raise LanguageNotSupportedError()
        self.device = "cpu" if not torch.cuda.is_available() else "cuda"
        self.dtype = torch.float32
        self.model_name = "efficient-speech/lite-whisper-medium-fast" #modify with your model
        self.model = self.load_model(self.model_name)
        self.processor, self.generation_config = self.load_processor_and_gen_config()
        self.srv = self.create_service(Asr, "asr", self._callback)
        self.get_logger().info(f"ASR Node initialized with model {self.model_name} on device {self.device} with dtype {self.dtype} for language {self.language}")

    def load_model(self, model_name: str):
        model = AutoModel.from_pretrained(
            model_name, 
            trust_remote_code=True,
        )
        model.to(self.device, dtype=self.dtype)
        self.get_logger().info(f"Device: {model.device}, dtype: {model.dtype}")
        return model
    
    def load_processor_and_gen_config(self):

        def get_efficient_speech_processor(model_id):
            if "small" in model_id:
                processor: WhisperProcessor = AutoProcessor.from_pretrained("openai/whisper-small")
                generation_config = GenerationConfig.from_pretrained("openai/whisper-small")
            elif "medium" in model_id:
                processor: WhisperProcessor = AutoProcessor.from_pretrained("openai/whisper-medium")
                generation_config = GenerationConfig.from_pretrained("openai/whisper-medium")
            elif "large" in model_id:
                processor: WhisperProcessor = AutoProcessor.from_pretrained("openai/whisper-large-v3-turbo")
                generation_config = GenerationConfig.from_pretrained("openai/whisper-large-v3")
            elif "tiny" in model_id:
                processor: WhisperProcessor = AutoProcessor.from_pretrained("openai/whisper-tiny")
                generation_config = GenerationConfig.from_pretrained("openai/whisper-tiny")
            else:
                raise ValueError(f"Model {model_id} not supported")
            return processor, generation_config

        if "efficient-speech" in self.model_name:
            processor, generation_config = get_efficient_speech_processor(self.model_name)
        else:
            processor: WhisperProcessor = AutoProcessor.from_pretrained(self.model_name)
            generation_config = GenerationConfig.from_pretrained(self.model_name)
        processor.tokenizer.set_prefix_tokens(language=self.language, task="transcribe")
        return processor, generation_config
    
    def predict(self, audio) -> list:
        audio = np.asarray(audio, dtype=np.float32)
        assert audio.ndim == 1, "Audio must be a 1D array"
        assert audio.dtype == np.float32, "Audio must be a float32 array"
        input_features = self.processor(audio, sampling_rate=16000, return_tensors="pt").input_features
        input_features = input_features.to(self.device, dtype=self.dtype)
        predicted_ids = self.model.generate(input_features, self.generation_config, language=self.language, task="transcribe")
        transcription = self.processor.batch_decode(
            predicted_ids, 
            skip_special_tokens=True
        )[0]

        self.get_logger().info(f"ASR Output: {transcription}")
        return transcription

    def _callback(self, req: Asr.Request, resp: Asr.Response):
        audio = req.audio_features
        text = self.predict(audio)
        resp = Asr.Response(text=str(text))
        return resp

def main():
    rclpy.init()
    node = ASRNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        import sys
        print(sys.exc_info())
        node.destroy_node()
        rclpy.shutdown()

def test():
    from torchcodec.decoders import AudioDecoder
    rclpy.init()
    node = ASRNode()
    audio_decoder = AudioDecoder("/workspace/ws/src/pepper_nodes/pepper_nodes/audio.wav", sample_rate=16000, num_channels=1)
    audio = audio_decoder.get_all_samples().data.squeeze(0).numpy()
    text = node.predict(audio)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()