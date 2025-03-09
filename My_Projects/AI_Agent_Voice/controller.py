import threading
import queue
from speech import SpeechRecognizer

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
        self.default_device_name = "Input 1 (2- SSL 2 USB Audio Dev"  # Set your default device here
        
        # Connect view callbacks
        self.view.set_send_callback(self.handle_user_message)
        self.view.set_reset_callback(self.reset_conversation)
        self.view.set_model_change_callback(self.handle_model_change)
        self.view.set_voice_toggle_callback(self.handle_voice_toggle)
        self.view.set_select_mic_callback(self.handle_mic_selection)
        
        # Set up audio level callback
        self.view.set_audio_level_callback(self.get_audio_level)
        
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
    
    def get_audio_level(self):
        """Get the current audio level for visualization"""
        if self.speech_recognizer:
            return self.speech_recognizer.get_audio_level()
        return 0.0  # Default level when no recognizer is active
    
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
                
                # Start listening with callback
                success = self.speech_recognizer.start_listening(self.handle_voice_input)
                if success:
                    self.view.set_status("Voice input active - speak clearly")
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
            self.view.set_status("Voice input disabled")
    
    def handle_voice_input(self, text):
        """Handle voice input text"""
        if not text:
            return
        
        # Process the voice input as a user message
        self.handle_user_message(text, is_voice=True)
    
    def handle_user_message(self, message, is_voice=False):
        """Process a user message"""
        # Add to memory
        self.model.add_to_memory("user", message)
        
        # Update UI
        self.view.display_user_message(message, is_voice)
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
            self.view.display_ai_response(response)
            self.view.set_status("Ready")
            self.view.set_input_enabled(True)