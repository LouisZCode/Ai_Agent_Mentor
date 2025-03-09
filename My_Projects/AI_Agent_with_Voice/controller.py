import threading
import queue
from speech import SpeechRecognizer
from tts import TextToSpeech

class ChatbotController:
    """
    Controller class that coordinates between the model and the view
    """
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.response_queue = queue.Queue()
        
        # Initialize speech recognizer (None until activated)
        self.speech_recognizer = None
        self.selected_mic_index = None
        self.default_device_name = "Input 1 (2- SSL 2 USB Audio Dev)"  # Fixed closing parenthesis
        
        # Initialize text-to-speech
        self.tts = None
        self.tts_enabled = False
        self.tts_init_checked = False
        try:
            # Try to initialize the TTS engine
            self.tts = TextToSpeech()
            
            # Print audio device information to help debug issues
            try:
                self.tts.debug_audio_devices()
            except Exception as e:
                print(f"Could not print audio device info: {e}")
            
            # Update UI to show initialization is in progress
            voice_list = ["Initializing..."]
            self.view.update_voice_list(voice_list)
            self.view.set_status(f"TTS initializing - please wait...")
            
            # Start a timer to check for TTS initialization completion
            self.view.root.after(2000, self.check_tts_initialization)
            
        except Exception as e:
            print(f"Error initializing TTS: {e}")
            self.view.update_voice_list(["TTS Error"])
            self.view.set_status("TTS initialization failed")
        
        # Connect view callbacks
        self.view.set_send_callback(self.handle_user_message)
        self.view.set_reset_callback(self.reset_conversation)
        self.view.set_model_change_callback(self.handle_model_change)
        self.view.set_voice_toggle_callback(self.handle_voice_toggle)
        self.view.set_select_mic_callback(self.handle_mic_selection)
        
        # Set callbacks for TTS controls
        self.view.set_tts_toggle_callback(self.handle_tts_toggle)
        self.view.set_voice_change_callback(self.handle_voice_change)
        
        # Set callbacks for voice cloning
        self.view.set_clone_voice_callback(self.handle_voice_cloning)
        
        # Initialize model with the default selection from view
        self.model.model_name = self.view.get_selected_model()
        
        # Start response checker
        self.view.start_response_checker(self.check_for_responses)
        
        # Try to find the default microphone index
        try:
            temp_recognizer = SpeechRecognizer()
            self.selected_mic_index = temp_recognizer.find_device_by_name(self.default_device_name)
            if self.selected_mic_index is not None:
                mic_name = next((name for idx, name in temp_recognizer.list_microphones() 
                                 if idx == self.selected_mic_index), "Unknown")
                self.view.set_status(f"Default microphone: {mic_name}")
            else:
                self.view.set_status("Using system default microphone")
        except Exception as e:
            print(f"Error finding default microphone: {e}")
    
    def handle_voice_cloning(self):
        """Handle voice cloning request"""
        if not self.tts or not hasattr(self.tts, 'is_initialized') or not self.tts.is_initialized:
            self.view.set_status("TTS not initialized. Cannot clone voice.")
            return
        
        # Define callbacks for the voice cloning dialog
        def record_callback():
            """Callback to record audio for voice cloning"""
            try:
                return self.tts.record_voice_sample(duration=10)
            except Exception as e:
                print(f"Error recording voice sample: {e}")
                return False, str(e)
        
        def clone_callback(audio_data, voice_name):
            """Callback to clone voice from recorded audio"""
            try:
                # Verify audio_data is valid
                if audio_data is None:
                    print("Error: No audio data provided to clone_callback")
                    return False, "No audio data available"
                    
                # Check if audio data is empty or invalid
                import numpy as np
                if isinstance(audio_data, np.ndarray) and (audio_data.size == 0 or np.max(np.abs(audio_data)) < 0.01):
                    print("Error: Audio data is empty or too quiet")
                    return False, "Recording seems to be empty or too quiet. Please try again with more volume."
                
                success, result = self.tts.clone_voice(audio_data=audio_data, voice_name=voice_name)
                
                # If cloning was successful, update the voice list
                if success:
                    voices = self.tts.get_available_speakers()
                    self.view.update_voice_list(voices)
                    
                    # Automatically select the new voice
                    self.view.voice_var.set(result)
                    self.tts.set_speaker(result)
                
                return success, result
            except Exception as e:
                print(f"Error cloning voice: {e}")
                return False, str(e)
        
        # Show the voice cloning dialog
        self.view.show_voice_cloning_dialog(record_callback, clone_callback)
    
    def check_tts_initialization(self):
        """Check if TTS initialization is complete"""
        if not self.tts:
            self.view.set_status("TTS not available")
            self.view.update_voice_list(["No TTS Available"])
            self.tts_init_checked = True
            return
            
        if hasattr(self.tts, 'is_initialized'):
            if self.tts.is_initialized:
                # TTS is initialized, update UI
                voices = self.tts.get_available_speakers()
                self.view.update_voice_list(voices)
                self.view.set_status("TTS initialized and ready")
                self.view.tts_checkbox.config(state="normal") # Enable the TTS checkbox
                self.view.enable_voice_cloning(True)  # Enable voice cloning button
                self.tts_init_checked = True
                print("TTS initialization complete!")
            else:
                # Still initializing, check again in 2 seconds
                self.view.root.after(2000, self.check_tts_initialization)
        else:
            # No initialization property, assume it failed
            self.view.update_voice_list(["TTS Error"])
            self.view.set_status("TTS initialization missing")
            self.tts_init_checked = True
    
    def handle_tts_toggle(self, enabled):
        """Handle TTS toggle in the UI"""
        self.tts_enabled = enabled
        
        # If initialization check wasn't completed, do it now
        if not self.tts_init_checked:
            self.check_tts_initialization()
        
        # Check if TTS is actually available
        if enabled and not self.tts:
            self.view.set_status("TTS not available - see console for details")
            # Reset the toggle in the UI
            self.view.tts_enabled.set(False)
            self.tts_enabled = False
            return
            
        if enabled and not hasattr(self.tts, 'is_initialized') or not self.tts.is_initialized:
            self.view.set_status("TTS still initializing - please wait")
            # Reset the toggle in the UI
            self.view.tts_enabled.set(False)
            self.tts_enabled = False
            return
        
        # Stop any current speech if disabling
        if not enabled and self.tts:
            self.tts.stop()
            
        self.view.set_status(f"AI voice {'enabled' if enabled else 'disabled'}")

    def handle_voice_change(self, voice_name):
        """Handle voice selection change"""
        if self.tts and hasattr(self.tts, 'is_initialized') and self.tts.is_initialized:
            success = self.tts.set_speaker(voice_name)
            if success:
                self.view.set_status(f"Voice changed to {voice_name}")
            else:
                self.view.set_status(f"Could not set voice to {voice_name}")
                print(f"Failed to set voice to {voice_name}")
        else:
            self.view.set_status("Cannot change voice - TTS not initialized")
            print("Cannot change voice - TTS not available or not initialized")
    
    def reset_conversation(self):
        """Reset the conversation to initial state"""
        self.model.reset_memory()
        self.view.clear_conversation()
        self.view.display_welcome_message()
        self.view.set_status("Conversation restarted")
        
        # Clear any pending responses
        while not self.response_queue.empty():
            try:
                self.response_queue.get_nowait()
            except queue.Empty:
                break
    
    def handle_model_change(self, new_model_name):
        """Handle model selection change"""
        # Update model name
        self.model.model_name = new_model_name
        
        # Reset conversation when model changes
        self.reset_conversation()
        
        # Update status
        self.view.set_status(f"Model changed to {new_model_name}")
    
    def handle_mic_selection(self):
        """Handle microphone selection request"""
        # Get list of available microphones
        try:
            # Create a temporary SpeechRecognizer just to get the microphone list
            temp_recognizer = SpeechRecognizer()
            microphones = temp_recognizer.list_microphones()
            
            # Show microphone selector dialog
            selected_mic = self.view.show_microphone_selector(microphones)
            
            # Update the selected microphone
            if selected_mic is not None:  # None means "use default"
                self.selected_mic_index = selected_mic
                mic_name = next((name for idx, name in microphones if idx == selected_mic), "Unknown")
                self.view.set_status(f"Selected microphone: {mic_name}")
            else:
                # Try to use the default named device
                default_idx = temp_recognizer.find_device_by_name(self.default_device_name)
                if default_idx is not None:
                    self.selected_mic_index = default_idx
                    mic_name = next((name for idx, name in microphones if idx == default_idx), "Unknown")
                    self.view.set_status(f"Using default microphone: {mic_name}")
                else:
                    self.selected_mic_index = None
                    self.view.set_status("Using system default microphone")
                
            # If we already have a speech recognizer, recreate it with the new microphone
            if self.speech_recognizer:
                # Remember if it was active
                was_active = hasattr(self.speech_recognizer, 'stream')
                
                # Stop the current one
                self.speech_recognizer.stop_listening()
                
                # Create a new one with the selected microphone
                self.speech_recognizer = SpeechRecognizer(
                    device_index=self.selected_mic_index,
                    default_device_name=self.default_device_name
                )
                
                # Restart if it was active
                if was_active:
                    self.speech_recognizer.start_listening(self.handle_voice_input)
                    
        except Exception as e:
            self.view.set_status(f"Error listing microphones: {str(e)}")
    
    def handle_voice_toggle(self, is_active):
        """Handle voice input toggle"""
        if is_active:
            try:
                # Initialize speech recognizer if not already done
                if self.speech_recognizer is None:
                    self.speech_recognizer = SpeechRecognizer(
                        device_index=self.selected_mic_index,
                        default_device_name=self.default_device_name
                    )
                
                # Start voice UI by clearing any previous voice display
                self.view.start_voice_input()
                
                # Start listening with callbacks for both word and final results
                success = self.speech_recognizer.start_listening(
                    callback=self.handle_voice_input,
                    word_callback=self.handle_word_input
                )
                
                if success:
                    self.view.set_status("Voice input active - speak clearly")
                    # Ensure button shows correct state
                    self.view.voice_active = True
                    self.view.voice_button.config(text="🎤 Disable Voice")
                else:
                    # If failed to start, reset the button state
                    self.view.voice_active = False
                    self.view.voice_button.config(text="🎤 Enable Voice")
                    self.view.set_status("Failed to start voice input")
            except Exception as e:
                self.view.voice_active = False
                self.view.voice_button.config(text="🎤 Enable Voice")
                self.view.set_status(f"Error activating voice: {str(e)}")
        else:
            # Stop listening
            if self.speech_recognizer:
                self.speech_recognizer.stop_listening()
                # End voice input display
                self.view.end_voice_input()
            
            # Ensure button shows correct state
            self.view.voice_active = False
            self.view.voice_button.config(text="🎤 Enable Voice")
            self.view.set_status("Voice input disabled")
    
    def handle_word_input(self, text):
        """Handle new word(s) detected in speech"""
        if not text:
            return
        
        # Update the display with the new word(s)
        self.view.append_voice_text(text)
    
    def handle_voice_input(self, text):
        """Handle complete voice input text"""
        if not text:
            return
        
        # Process the voice input as a user message
        self.handle_user_message(text, is_voice=True)
    
    def handle_user_message(self, message, is_voice=False):
        """Process a user message"""
        # Add to memory
        self.model.add_to_memory("user", message)
        
        # Update UI (for keyboard input - voice input already updated in real-time)
        if not is_voice:
            self.view.display_user_message(message)
            
        self.view.start_thinking_animation()
        self.view.set_status("Thinking...")
        self.view.set_input_enabled(False)
        
        # Start processing in background
        threading.Thread(
            target=self.process_message_thread,
            args=(message,),
            daemon=True
        ).start()
    
    def process_message_thread(self, message):
        """Background thread to process user message"""
        try:
            # Generate response directly (no thinking step)
            response = self.model.generate_response()
            
            # Add to memory
            self.model.add_to_memory("agent", response)
            
            # Queue response for UI
            self.response_queue.put(response)
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            self.response_queue.put(error_msg)
    
    def check_for_responses(self):
        """Check for responses in the queue and update UI"""
        if not self.response_queue.empty():
            response = self.response_queue.get()
            
            # Create a sentence speaker function for progressive TTS
            def speak_sentence(sentence):
                if self.tts_enabled and self.tts and hasattr(self.tts, 'is_initialized') and self.tts.is_initialized:
                    print(f"Speaking sentence: '{sentence}'")
                    self.tts.speak(sentence)
            
            # Only use progressive speech if TTS is enabled
            speak_callback = None
            if self.tts_enabled and self.tts and hasattr(self.tts, 'is_initialized') and self.tts.is_initialized:
                speak_callback = speak_sentence
                print("Progressive speech enabled - will speak as text displays")
            
            # Display the response with progressive speech
            self.view.display_ai_response(response, speak_callback=speak_callback)
                    
            self.view.set_status("Ready")
            self.view.set_input_enabled(True)
