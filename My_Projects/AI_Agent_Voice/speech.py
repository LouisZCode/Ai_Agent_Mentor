import os
import sys
import json
import queue
import threading
import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer

class SpeechRecognizer:
    """
    Handles speech recognition using Vosk for offline processing
    """
    def __init__(self, model_path=None, sample_rate=16000, device_index=None, default_device_name="SSL 2 USB Audio"):
        self.sample_rate = sample_rate
        
        # Try to find the preferred device if specified and device_index is None
        if device_index is None and default_device_name:
            device_index = self.find_device_by_name(default_device_name)
            if device_index is not None:
                print(f"Using preferred microphone: {default_device_name} (index: {device_index})")
                
        self.device_index = device_index
        
        # Try to find the model in different locations
        if model_path is None:
            # List of possible model locations to try
            possible_paths = [
                "vosk-model-small-en-us-0.15",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "vosk-model-small-en-us-0.15"),
                os.path.join(os.getcwd(), "vosk-model-small-en-us-0.15"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pycache_", "vosk-model-small-en-us-0.15")
            ]
            
            # Try each path
            model_found = False
            for path in possible_paths:
                if os.path.exists(path):
                    self.model_path = path
                    model_found = True
                    print(f"Found Vosk model at: {path}")
                    break
            
            if not model_found:
                print("VOSK model not found. Attempted these locations:")
                for path in possible_paths:
                    print(f"- {path}")
                print("\nPlease download the model from https://alphacephei.com/vosk/models")
                print("and extract it to one of the locations above.")
                
                # Ask user for model path
                user_path = input("\nOr enter the full path to the model directory: ").strip()
                if user_path and os.path.exists(user_path):
                    self.model_path = user_path
                    model_found = True
                else:
                    sys.exit(1)
        else:
            self.model_path = model_path
            if not os.path.exists(self.model_path):
                print(f"VOSK model not found at {self.model_path}")
                print("Please download the model from https://alphacephei.com/vosk/models")
                print(f"and extract it to {self.model_path}")
                sys.exit(1)
        
        self.recognizer = None
        self.audio_queue = queue.Queue()
        # Renamed to avoid conflict with the method name
        self.should_stop = threading.Event()
        self.listening_thread = None
        self.callback = None
        
        # Initialize model
        try:
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)  # Show word timestamps
            print(f"Successfully initialized Vosk model from {self.model_path}")
        except Exception as e:
            print(f"Error initializing Vosk model: {e}")
            sys.exit(1)
        
        # Variables for detecting speech
        self.silence_threshold = 0.03  # Energy level below which is considered silence
        self.speech_detected = False
        self.silent_frames = 0
        self.silent_threshold = 30  # Number of silent frames before processing
        self.current_speech = ""
        
        # Audio level monitoring
        self.current_audio_level = 0.0
        self.audio_level_lock = threading.Lock()
        self.audio_level_decay = 0.7  # How quickly the level falls (lower = faster)
        self.audio_level_scale = 8.0  # Multiplier to make levels more visible
    
    def find_device_by_name(self, name_substring):
        """Find a device by substring in its name"""
        devices = sd.query_devices()
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Input devices (microphones)
                # Check if the name contains the substring (case insensitive)
                if name_substring.lower() in device['name'].lower():
                    return i
        
        return None  # No matching device found
        
    def _audio_callback(self, indata, frames, time, status):
        """Callback for sounddevice to process audio chunks"""
        if status:
            print(f"Audio status: {status}")
        
        # Add audio data to queue
        self.audio_queue.put(bytes(indata))
        
        # Calculate energy level (for silence detection)
        # Use RMS (root mean square) for better sensitivity
        energy = np.sqrt(np.mean(np.square(indata)))
        
        # Update audio level meter (with lock for thread safety)
        with self.audio_level_lock:
            # If new level is higher, jump to it immediately
            if energy > self.current_audio_level:
                # Fast attack - jump to new level
                self.current_audio_level = energy
            # Otherwise decay slowly toward zero
            else:
                # Smooth release - decay toward zero
                self.current_audio_level = self.current_audio_level * self.audio_level_decay
        
        # Simple silence detection
        if energy > self.silence_threshold:
            self.speech_detected = True
            self.silent_frames = 0
        elif self.speech_detected:
            self.silent_frames += 1
            if self.silent_frames > self.silent_threshold:
                self.speech_detected = False
    
    def get_audio_level(self):
        """Get the current audio input level (normalized)"""
        with self.audio_level_lock:
            # Scale the level
            scaled_level = self.current_audio_level * self.audio_level_scale
            
            # Return 0 for very low levels to ensure no visualization during silence
            if scaled_level < 0.02:
                return 0.0
                
            # Clamp between 0.0 and 1.0
            level = min(1.0, max(0.0, scaled_level))
            return level
    
    def process_audio(self):
        """Process audio data from the queue"""
        while not self.should_stop.is_set():
            try:
                # Get audio data from queue with timeout
                audio_data = self.audio_queue.get(timeout=0.5)
                
                # Process audio chunk
                if self.recognizer.AcceptWaveform(audio_data):
                    result_json = self.recognizer.Result()
                    result = json.loads(result_json)
                    
                    # Extract text from result
                    text = result.get('text', '').strip()
                    
                    # If we have text and a callback, call it
                    if text and self.callback:
                        self.callback(text)
                
            except queue.Empty:
                # If queue is empty, just continue
                continue
            except Exception as e:
                print(f"Error processing audio: {e}")
                continue
    
    def start_listening(self, callback):
        """Start listening for speech"""
        if self.listening_thread and self.listening_thread.is_alive():
            print("Already listening")
            return
        
        # Set callback function
        self.callback = callback
        
        # Reset stop event
        self.should_stop.clear()
        
        # Start processing thread
        self.listening_thread = threading.Thread(target=self.process_audio)
        self.listening_thread.daemon = True
        self.listening_thread.start()
        
        # Start audio stream
        try:
            # Use the specified device if provided
            if self.device_index is not None:
                self.stream = sd.RawInputStream(
                    samplerate=self.sample_rate,
                    blocksize=8000,
                    channels=1,
                    dtype='int16',
                    callback=self._audio_callback,
                    device=self.device_index
                )
            else:
                self.stream = sd.RawInputStream(
                    samplerate=self.sample_rate,
                    blocksize=8000,
                    channels=1,
                    dtype='int16',
                    callback=self._audio_callback
                )
            self.stream.start()
            device_info = sd.query_devices(self.device_index or sd.default.device[0], 'input')
            print(f"Listening for speech on device: {device_info['name']}")
            return True
        except Exception as e:
            print(f"Error starting audio stream: {e}")
            self.should_stop.set()
            self.callback = None
            return False
    
    def stop_listening(self):
        """Stop listening for speech"""
        if not self.listening_thread or not self.listening_thread.is_alive():
            print("Not currently listening")
            return
        
        # Set stop event and wait for thread to finish
        self.should_stop.set()
        
        # Stop audio stream
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        # Wait for thread to finish
        self.listening_thread.join(timeout=1.0)
        print("Stopped listening")

    @staticmethod
    def list_microphones():
        """List available microphones"""
        devices = sd.query_devices()
        microphones = []
        
        print("\nAvailable Microphones:")
        print("-" * 50)
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Input devices (microphones)
                print(f"[{i}] {device['name']}")
                microphones.append((i, device['name']))
        
        print("-" * 50)
        return microphones

# Simple test function
if __name__ == "__main__":
    def on_speech(text):
        print(f"Recognized: {text}")
    
    # List available microphones
    mics = SpeechRecognizer.list_microphones()
    
    if mics:
        # Let the user choose a microphone
        choice = input("Select microphone number (or press Enter for default): ").strip()
        device_idx = None
        if choice and choice.isdigit():
            device_idx = int(choice)
        
        # Create the recognizer with selected device
        sr = SpeechRecognizer(device_index=device_idx)
        sr.start_listening(on_speech)
        
        print("Listening for speech. Press Ctrl+C to exit.")
        try:
            while True:
                print(f"Audio level: {'#' * int(sr.get_audio_level() * 50)}")
                time.sleep(0.1)
        except KeyboardInterrupt:
            sr.stop_listening()
            print("Stopped listening.")
    else:
        print("No microphones found!")