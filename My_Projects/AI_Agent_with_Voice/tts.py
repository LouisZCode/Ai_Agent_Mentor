import threading
import queue
import time
import os
import sys
import re
import numpy as np
import sounddevice as sd
import shutil
from datetime import datetime

class TextToSpeech:
    """
    Text-to-Speech engine using XTTS-v2 for high-quality speech synthesis.
    """
    def __init__(self, model_name="tts_models/multilingual/multi-dataset/xtts_v2"):
        self.model_name = model_name
        self.is_initialized = False
        self.initialized = False  # For compatibility with existing code 
        self.tts_available = False
        self.sample_rate = 24000
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.stop_event = threading.Event()
        self.processing_thread = None
        self.tts = None  # Instance of the TTS model
        
        # Current settings
        self.current_speaker = None
        self.language = "en"
        self.speakers = {}
        
        # Initialize TTS (will be done in a background thread)
        self.initialization_thread = threading.Thread(target=self._initialize_tts)
        self.initialization_thread.daemon = True
        self.initialization_thread.start()
    
    def _initialize_tts(self):
        """Initialize the XTTS-v2 engine in a background thread to not block UI"""
        try:
            print("Initializing XTTS-v2 engine...")
            
            # First, fix the PyTorch 2.6+ weights_only issue
            self._fix_pytorch_weights_issue()
            
            # Import TTS after fixing the PyTorch issue
            try:
                from TTS.api import TTS
                self.tts_available = True
            except ImportError:
                print("TTS package not found. Voice output will not be available.")
                print("Try running: pip install TTS")
                self.tts_available = False
                self.is_initialized = True  # Mark as initialized but unavailable
                return
            
            # Determine device (CPU/GPU)
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"XTTS will use device: {self.device}")
            
            # Initialize the model with a try-except block
            try:
                self.tts = TTS(self.model_name, gpu=(self.device == "cuda"))
                self.initialized = True
            except Exception as e:
                print(f"Failed to initialize XTTS model: {e}")
                print("Fall back to system TTS if available")
                self.initialized = False
                self.tts = None
                return
            
            # Initialize with at least a default speaker
            self.speakers = {"Default": "default"}
            self.current_speaker = "Default"
            
            # Try to get available speakers
            try:
                speakers = self.tts.synthesizer.tts_model.speaker_manager.speakers
                if speakers and len(speakers) > 0:
                    self.speakers = speakers
                    self.current_speaker = list(self.speakers.keys())[0]
                    print(f"Found {len(self.speakers)} speaker(s)")
                    print(f"Set default speaker to: {self.current_speaker}")
            except Exception as e:
                print(f"Could not load speakers, using default: {e}")
            
            # Load any existing custom voices
            self._load_custom_voices()
            
            # Test the audio system to make sure output works
            self.test_audio()
            
            self.is_initialized = True
            print("✓ XTTS-v2 engine initialized successfully")
            
        except Exception as e:
            print(f"Error initializing XTTS-v2 engine: {e}")
            self.is_initialized = False
    
    def _fix_pytorch_weights_issue(self):
        """Fix for PyTorch 2.6+ weights_only parameter change"""
        try:
            import torch
            
            # Get PyTorch version
            torch_version = tuple(map(int, torch.__version__.split('.')[:2]))
            
            # Only apply fixes for PyTorch 2.6+
            if torch_version >= (2, 6):
                print(f"Applying PyTorch {torch.__version__} compatibility fixes for XTTS")
                
                # Method 1: Add all necessary classes to safe globals (most reliable method)
                if hasattr(torch, 'serialization') and hasattr(torch.serialization, 'add_safe_globals'):
                    # List of classes that need to be added as safe
                    safe_classes = [
                        "TTS.tts.configs.xtts_config.XttsConfig",
                        "TTS.utils.audio.AudioProcessor",
                        "TTS.tts.models.xtts.Xtts",
                        "builtins.set",
                        "builtins.frozenset"
                    ]
                    
                    for cls in safe_classes:
                        try:
                            torch.serialization.add_safe_globals([cls])
                            print(f"Added {cls} to PyTorch safe globals")
                        except Exception as e:
                            print(f"Could not add {cls} to safe globals: {e}")
                
                # Method 2: Monkey patch torch.load as a backup
                original_load = torch.load
                def patched_load(*args, **kwargs):
                    if 'weights_only' not in kwargs:
                        kwargs['weights_only'] = False
                    return original_load(*args, **kwargs)
                
                torch.load = patched_load
                print("Patched torch.load with weights_only=False by default")
            
        except ImportError:
            print("PyTorch not found. Please install: pip install torch")
            raise
    
    def _load_custom_voices(self):
        """Load any existing custom voices from the custom_voices directory"""
        try:
            custom_voices_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_voices")
            if not os.path.exists(custom_voices_dir):
                os.makedirs(custom_voices_dir, exist_ok=True)
                return
                
            # List all .wav files in the directory
            for filename in os.listdir(custom_voices_dir):
                if filename.endswith(".wav"):
                    voice_path = os.path.join(custom_voices_dir, filename)
                    voice_name = os.path.splitext(filename)[0]
                    
                    # Add to speakers dictionary
                    self.speakers[voice_name] = voice_path
                    print(f"Loaded custom voice: {voice_name}")
        except Exception as e:
            print(f"Error loading custom voices: {e}")
    
    def get_available_speakers(self):
        """Get list of available voices"""
        if not self.is_initialized:
            return ["XTTS Initializing..."]
        return list(self.speakers.keys())
    
    def set_speaker(self, speaker_name):
        """Set the current speaker voice"""
        if not self.is_initialized:
            return False
        
        if speaker_name in self.speakers:
            self.current_speaker = speaker_name
            print(f"Changed speaker to: {speaker_name}")
            return True
        return False
    
    def set_language(self, language_code):
        """Set the speech language (ISO code)"""
        self.language = language_code
    
    def speak(self, text):
        """Add text to the speech queue"""
        if not self.is_initialized or not self.tts:
            print("TTS engine not available")
            return False
        
        # Check if text is empty
        if not text or not text.strip():
            return False
        
        try:
            # Split long text into sentences for better speech flow
            sentences = self._split_into_sentences(text)
            
            # Add each sentence to the queue
            for sentence in sentences:
                if sentence.strip():
                    self.speech_queue.put(sentence.strip())
            
            # Start processing if not already running
            self._ensure_processing_thread()
            return True
        except Exception as e:
            print(f"Error queueing speech: {e}")
            return False
    
    def _split_into_sentences(self, text):
        """Split text into natural sentences"""
        # Split on common sentence terminators, preserving the terminator
        pattern = r'(?<=[.!?])\s+'
        sentences = re.split(pattern, text)
        
        # Further split very long sentences (over 100 chars) at commas
        final_sentences = []
        for sentence in sentences:
            if len(sentence) > 100:
                comma_parts = re.split(r'(?<=,)\s+', sentence)
                final_sentences.extend(comma_parts)
            else:
                final_sentences.append(sentence)
        
        # Remove any empty sentences and ensure they're not too long
        # XTTS has a context limit usually around 250 chars
        cleaned_sentences = []
        for s in final_sentences:
            s = s.strip()
            if not s:
                continue
                
            # Further break down very long sentences (XTTS limit ~250 chars)
            if len(s) > 200:
                parts = [s[i:i+200] for i in range(0, len(s), 200)]
                cleaned_sentences.extend(parts)
            else:
                cleaned_sentences.append(s)
                
        return cleaned_sentences
    
    def _ensure_processing_thread(self):
        """Make sure the processing thread is running"""
        if not self.processing_thread or not self.processing_thread.is_alive():
            self.stop_event.clear()
            self.processing_thread = threading.Thread(target=self._process_queue)
            self.processing_thread.daemon = True
            self.processing_thread.start()
    
    def _process_queue(self):
        """Process items in the speech queue"""
        while not self.stop_event.is_set():
            try:
                # Get text from queue with timeout
                text = self.speech_queue.get(timeout=0.5)
                
                try:
                    self.is_speaking = True
                    print(f"🔊 Speaking: '{text}'")
                    
                    # Check if we're using a custom voice (from a wav file)
                    if isinstance(self.speakers.get(self.current_speaker), str) and self.speakers[self.current_speaker].endswith('.wav'):
                        # Use custom voice (cloned)
                        speaker_wav = self.speakers[self.current_speaker]
                        audio = self.tts.tts(
                            text=text,
                            speaker_wav=speaker_wav,
                            language=self.language
                        )
                    else:
                        # Use built-in voice
                        audio = self.tts.tts(
                            text=text,
                            speaker=self.current_speaker,
                            language=self.language
                        )
                    
                    # Convert to proper format for sounddevice
                    audio_np = np.array(audio)
                    
                    # Play the audio using sounddevice
                    sd.play(audio_np, self.sample_rate)
                    
                    # Mark the queue item as done immediately so next sentence can be processed
                    # This allows us to generate the next sentence while the current one is playing
                    self.speech_queue.task_done()
                    
                    # Wait until audio is finished playing
                    sd.wait()
                    
                finally:
                    self.is_speaking = False
                
            except queue.Empty:
                # Queue is empty, just continue and check stop_event again
                continue
            
            except Exception as e:
                print(f"Error in TTS processing: {e}")
                try:
                    # Make sure we mark the queue item as done even if there's an error
                    self.speech_queue.task_done()
                except:
                    pass
                continue
    
    def stop(self):
        """Stop all speech and processing"""
        # Signal thread to stop
        self.stop_event.set()
        
        # Stop any current audio playback
        sd.stop()
        
        # Clear the queue
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
        
        # Wait for thread to finish if it exists
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
            
        self.is_speaking = False
        print("Speech stopped")
    
    def is_busy(self):
        """Check if TTS is currently busy speaking"""
        return self.is_speaking or not self.speech_queue.empty()
        
    def debug_audio_devices(self):
        """Print information about audio devices to help debugging"""
        try:
            import sounddevice as sd
            print("\nAudio Device Information:")
            print("-" * 50)
            devices = sd.query_devices()
            default_output = sd.query_devices(kind='output')
            print(f"Default output device: {default_output['name']}")
            
            print("\nAvailable Output Devices:")
            for i, dev in enumerate(devices):
                if dev['max_output_channels'] > 0:
                    print(f"[{i}] {dev['name']} (Channels: {dev['max_output_channels']})")
            
            print("-" * 50)
        except Exception as e:
            print(f"Error getting audio device info: {e}")
            
    def test_audio(self):
        """Generate a test sound to verify audio is working"""
        try:
            import numpy as np
            import sounddevice as sd
            
            # Generate a simple beep sound
            sample_rate = 44100
            duration = 0.5  # half second
            frequency = 440  # A4 note
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            beep = 0.5 * np.sin(2 * np.pi * frequency * t)
            
            # Play the beep
            sd.play(beep, sample_rate)
            sd.wait()  # Wait until sound is finished
            print("Test audio played successfully")
            return True
        except Exception as e:
            print(f"Error playing test audio: {e}")
            return False
            
    def clone_voice(self, audio_data=None, audio_file_path=None, voice_name=None):
        """Clone a voice from audio data or file and add it to available voices"""
        if not self.is_initialized or not self.tts:
            print("TTS engine not initialized. Cannot clone voice.")
            return False, "TTS engine not initialized"
            
        if audio_data is None and audio_file_path is None:
            return False, "No audio provided for voice cloning"
            
        # Generate a name if not provided
        if not voice_name:
            voice_name = f"ClonedVoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        try:
            # Create custom voices directory if it doesn't exist
            custom_voices_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_voices")
            os.makedirs(custom_voices_dir, exist_ok=True)
            
            # Determine the file path to save the voice sample
            target_file_path = os.path.join(custom_voices_dir, f"{voice_name}.wav")
            
            # If audio data is provided (from recording), save it to a WAV file
            if audio_data is not None:
                import wave
                with wave.open(target_file_path, 'wb') as wf:
                    wf.setnchannels(1)  # Mono
                    wf.setsampwidth(2)   # 16-bit
                    wf.setframerate(24000)  # 24kHz sampling rate
                    wf.writeframes(audio_data.tobytes())
            # If file path is provided, copy the file
            elif audio_file_path:
                shutil.copy(audio_file_path, target_file_path)
                
            # Test if the voice clone works
            print(f"Testing voice clone with file: {target_file_path}")
            test_audio = self.tts.tts(
                text="Voice cloning test successful.",
                speaker_wav=target_file_path,
                language="en"
            )
            
            # If we reached here, cloning was successful
            # Add to available speakers dictionary
            self.speakers[voice_name] = target_file_path
            print(f"Voice cloning successful. Added '{voice_name}' to available voices.")
            
            return True, voice_name
            
        except Exception as e:
            print(f"Error cloning voice: {e}")
            # Clean up any partial files
            try:
                if os.path.exists(target_file_path):
                    os.remove(target_file_path)
            except:
                pass
            return False, str(e)
    
    def get_cloned_voices(self):
        """Get a list of cloned voices"""
        cloned_voices = []
        for name, path in self.speakers.items():
            if isinstance(path, str) and path.endswith('.wav'):
                cloned_voices.append(name)
        return cloned_voices
    
    def record_voice_sample(self, duration=10, sample_rate=24000):
        """Record a voice sample for cloning"""
        try:
            print(f"Recording voice sample for {duration} seconds...")
            # Record audio
            recording = sd.rec(int(duration * sample_rate), 
                              samplerate=sample_rate, 
                              channels=1,
                              dtype='float32')
            
            # Wait for recording to complete
            sd.wait()
            
            # Validate recording
            if recording is None or recording.size == 0:
                print("Error: No audio data was recorded")
                return False, "No audio data was recorded"
            
            # Normalize audio (ensure values are between -1 and 1)
            max_abs = np.max(np.abs(recording))
            if max_abs < 0.01:  # Check if recording is too quiet
                print("Warning: Recording volume may be too low")
                # Continue anyway, but with a warning
            
            if max_abs > 0:
                recording = recording / max_abs * 0.9
                
            print("Recording complete!")
            return True, recording
        
        except Exception as e:
            print(f"Error recording voice: {e}")
            return False, str(e)
