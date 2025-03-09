import os
import sys
import json
import queue
import threading
import time
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
        self.partial_callback = None  # New callback for partial results
        
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
        
        # Variables for handling partial results
        self.last_partial_time = 0
        self.partial_delay = 0.1  # Seconds between partial updates (shorter for word-by-word)
        self.last_partial_text = ""  # Track the last partial text to detect new words
        
        # Variables for handling silence detection
        self.silence_start_time = 0
        self.silence_timeout = 2.0  # 2 seconds of silence to trigger completion (reduced from 3)
        self.word_callback = None  # Callback for individual words
    
    def find_device_by_name(self, name_substring):
        """Find a device by substring in its name"""
        devices = sd.query_devices()
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Input devices (microphones)
                # Check if the name contains the substring (case insensitive)
                if name_substring.lower() in device['name'].lower():
                    return i
        
        return None  # No matching device found
        
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice to process audio chunks"""
        if status:
            print(f"Audio status: {status}")
        
        # Add audio data to queue
        self.audio_queue.put(bytes(indata))
        
        # Calculate energy level (for silence detection only)
        energy = np.mean(np.abs(indata))
        current_time = time.time()
        
        # Simple silence detection
        if energy > self.silence_threshold:
            self.speech_detected = True
            self.silent_frames = 0
            self.silence_start_time = 0  # Reset silence timer
        elif self.speech_detected:
            self.silent_frames += 1
            
            # Start silence timer if this is the beginning of silence
            if self.silent_frames == 1:
                self.silence_start_time = current_time
            
            # Check if silence timeout has been reached
            if self.silence_start_time > 0 and (current_time - self.silence_start_time) > self.silence_timeout:
                # If silence has lasted long enough, end the utterance
                if self.callback and self.last_partial_text.strip():
                    print(f"Silence detected for {self.silence_timeout}s - completing utterance: '{self.last_partial_text}'")
                    self.callback(self.last_partial_text.strip())
                    self.last_partial_text = ""  # Reset for next utterance
                    self.silence_start_time = 0
                    self.speech_detected = False
            
            # Traditional end-of-speech detection
            if self.silent_frames > self.silent_threshold:
                self.speech_detected = False
    
    # Audio level method removed
    
    def process_audio(self):
        """Process audio data from the queue"""
        while not self.should_stop.is_set():
            try:
                # Get audio data from queue with timeout
                audio_data = self.audio_queue.get(timeout=0.5)
                
                # Check for partial results if we have a word callback and speech is detected
                if (self.word_callback or self.partial_callback) and self.speech_detected:
                    # Only get partial results at certain intervals to avoid flickering
                    current_time = time.time()
                    if current_time - self.last_partial_time > self.partial_delay:
                        self.last_partial_time = current_time
                        
                        # Get partial result
                        partial_json = self.recognizer.PartialResult()
                        partial_result = json.loads(partial_json)
                        
                        # Extract text from partial result
                        partial_text = partial_result.get('partial', '').strip()
                        
                        # Check if we have new words (by comparing with last partial text)
                        if partial_text and partial_text != self.last_partial_text:
                            # For word-by-word, extract just the new words
                            if self.word_callback:
                                # If previous text is a substring of current text, extract only new words
                                if partial_text.startswith(self.last_partial_text) and len(self.last_partial_text) > 0:
                                    new_words = partial_text[len(self.last_partial_text):].strip()
                                    if new_words:  # Only call if there are actual new words
                                        self.word_callback(new_words)
                                else:
                                    # If not a simple extension, just use the whole new text
                                    # This handles cases where Vosk corrects previous words
                                    self.word_callback(partial_text)
                            
                            # For standard partial updates, send the full text
                            if self.partial_callback:
                                self.partial_callback(partial_text)
                            
                            # Save current text for comparison next time
                            self.last_partial_text = partial_text
                
                # Process audio chunk for final results
                if self.recognizer.AcceptWaveform(audio_data):
                    result_json = self.recognizer.Result()
                    result = json.loads(result_json)
                    
                    # Extract text from result
                    text = result.get('text', '').strip()
                    
                    # Reset state variables
                    self.last_partial_text = ""
                    
                    # If we have text and a callback, call it
                    if text and self.callback:
                        self.callback(text)
                
            except queue.Empty:
                # If queue is empty, just continue
                continue
            except Exception as e:
                print(f"Error processing audio: {e}")
                continue
    
    def start_listening(self, callback, partial_callback=None, word_callback=None):
        """Start listening for speech"""
        if self.listening_thread and self.listening_thread.is_alive():
            print("Already listening")
            return
        
        # Set callback functions
        self.callback = callback
        self.partial_callback = partial_callback
        self.word_callback = word_callback
        
        # Reset state variables
        self.last_partial_text = ""
        self.silence_start_time = 0
        
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
            self.partial_callback = None
            self.word_callback = None
            return False
    
    def stop_listening(self):
        """Stop listening for speech"""
        if not self.listening_thread or not self.listening_thread.is_alive():
            print("Not currently listening")
            return
        
        # Check if we have a partial utterance that hasn't been finalized due to silence
        if self.last_partial_text.strip() and self.callback:
            # Send the accumulated partial text as a final result
            print(f"Finalizing utterance on stop: '{self.last_partial_text}'")
            self.callback(self.last_partial_text.strip())
        
        # Set stop event and wait for thread to finish
        self.should_stop.set()
        
        # Stop audio stream
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        # Wait for thread to finish
        self.listening_thread.join(timeout=1.0)
        
        # Clear callbacks
        self.callback = None
        self.partial_callback = None
        self.word_callback = None
        
        # Reset state variables
        self.last_partial_text = ""
        self.silence_start_time = 0
        
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