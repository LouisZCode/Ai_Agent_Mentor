import threading
import queue

class ChatbotController:
    """
    Controller class that coordinates between the model and the view
    """
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.response_queue = queue.Queue()
        
        # Connect view callbacks
        self.view.set_send_callback(self.handle_user_message)
        self.view.set_reset_callback(self.reset_conversation)
        self.view.set_model_change_callback(self.handle_model_change)
        
        # Initialize model with the default selection from view
        self.model.model_name = self.view.get_selected_model()
        
        # Start response checker
        self.view.start_response_checker(self.check_for_responses)
    
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
    
    def handle_user_message(self, message):
        """Process a user message"""
        # Add to memory
        self.model.add_to_memory("user", message)
        
        # Update UI
        self.view.display_user_message(message)
        self.view.start_thinking_animation()  # Start the thinking animation
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
            # Generate thinking
            thinking = self.model.generate_thinking(message)
            
            # Generate response
            response = self.model.generate_response(
                thinking, 
                self.view.get_show_thinking()
            )
            
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
            self.view.display_ai_response(response)  # This will stop the animation and display the response
            self.view.set_status("Ready")
            self.view.set_input_enabled(True)