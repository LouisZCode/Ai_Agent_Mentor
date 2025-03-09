import tkinter as tk
from tkinter import scrolledtext, ttk, BooleanVar, StringVar, font
import time

class ChatbotView:
    """
    View class that handles the UI
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Luis AI HUB")  # Updated title
        self.root.geometry("800x600")
        
        # Animation state variables
        self.animation_timer_id = None
        self.animation_frame = 0
        self.animation_frames = [
            "Thinking •      ",
            "Thinking  •     ",
            "Thinking   •    ",
            "Thinking    •   ",
            "Thinking     •  ",
            "Thinking      • "
        ]
        
        # Available models
        self.available_models = ["qwq:latest", "llama3.1:8b", "deepseek-r1:32b"]
        
        # Set up the interface
        self._setup_ui()
        
        # Initialize callbacks
        self.send_callback = None
        self.reset_callback = None
        self.model_change_callback = None
    
    def _setup_ui(self):
        """Set up the UI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar frame
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Model selection dropdown
        ttk.Label(toolbar_frame, text="Model:").pack(side=tk.LEFT, padx=(0, 5))
        self.model_var = StringVar(value="llama3.1:8b")  # Default to first model
        self.model_dropdown = ttk.Combobox(
            toolbar_frame,
            textvariable=self.model_var,
            values=self.available_models,
            state="readonly",
            width=15
        )
        self.model_dropdown.pack(side=tk.LEFT, padx=(0, 15))
        self.model_dropdown.bind("<<ComboboxSelected>>", self._on_model_change)
        
        # Restart button
        self.restart_button = ttk.Button(
            toolbar_frame,
            text="Restart Conversation",
            command=self._on_reset
        )
        self.restart_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Show thinking checkbox
        self.show_thinking_var = BooleanVar(value=False)
        self.show_thinking_frame = ttk.Frame(toolbar_frame)
        self.show_thinking_frame.pack(side=tk.LEFT, padx=(0, 10))
        self.show_thinking_check = ttk.Checkbutton(
            self.show_thinking_frame, 
            text="Show Thinking Process", 
            variable=self.show_thinking_var
        )
        self.show_thinking_check.pack(side=tk.LEFT)
        
        # Update thinking checkbox visibility based on selected model
        self._update_thinking_checkbox_visibility()
        
        # Create conversation display
        self.conversation_display = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=26,  # Reduced to make more room for input
            font=("Helvetica", 10)
        )
        self.conversation_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.conversation_display.config(state=tk.DISABLED)
        
        # Tag configuration for different speakers
        self.conversation_display.tag_configure("speaker", font=("Helvetica", 10, "bold"))
        self.conversation_display.tag_configure("ai", foreground="blue")
        self.conversation_display.tag_configure("user", foreground="green")
        self.conversation_display.tag_configure("system", foreground="gray")
        self.conversation_display.tag_configure("thinking", foreground="purple")
        
        # Create improved input area
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=(5, 15))
        
        # Create a custom style for the input field
        input_style = ttk.Style()
        input_style.configure("Input.TEntry", padding=(10, 8))
        
        # Custom font for input field
        input_font = font.Font(family="Helvetica", size=12)
        
        # Input field - Using a larger style and custom padding
        self.input_field = ttk.Entry(
            input_frame, 
            width=70,
            style="Input.TEntry",
            font=input_font
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)  # Added vertical padding
        self.input_field.bind("<Return>", self._on_send)
        
        # Send button with matched size
        self.send_button = ttk.Button(
            input_frame, 
            text="Send", 
            command=self._on_send,
            padding=(10, 15)  # Increased button padding to match input field height
        )
        self.send_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Display welcome message
        self.display_welcome_message()
        
        # Set focus to input field
        self.input_field.focus()
    
    def _update_thinking_checkbox_visibility(self):
        """Update visibility of thinking checkbox based on selected model"""
        current_model = self.model_var.get()
        
        # Hide checkbox for llama3.1 model
        if current_model == "llama3.1:8b":
            self.show_thinking_frame.pack_forget()
        else:
            # Make sure it's visible for other models
            self.show_thinking_frame.pack(side=tk.LEFT, padx=(0, 10))
    
    def _on_model_change(self, event=None):
        """Handle model selection change"""
        # Update thinking checkbox visibility
        self._update_thinking_checkbox_visibility()
        
        # Notify controller about model change
        if self.model_change_callback:
            self.model_change_callback(self.model_var.get())
    
    def _on_send(self, event=None):
        """Handle send button click or Enter key"""
        message = self.input_field.get().strip()
        if not message or not self.send_callback:
            return
        
        # Clear input field
        self.input_field.delete(0, tk.END)
        
        # Call the registered callback
        self.send_callback(message)
    
    def _on_reset(self):
        """Handle reset button click"""
        if self.reset_callback:
            self.reset_callback()
    
    def set_send_callback(self, callback):
        """Set the callback for when a message is sent"""
        self.send_callback = callback
    
    def set_reset_callback(self, callback):
        """Set the callback for when the conversation is reset"""
        self.reset_callback = callback
    
    def set_model_change_callback(self, callback):
        """Set the callback for when the model is changed"""
        self.model_change_callback = callback
    
    def get_selected_model(self):
        """Get the currently selected model"""
        return self.model_var.get()
    
    def get_show_thinking(self):
        """Get the current show thinking setting"""
        # Always return False for llama3.1 model
        if self.model_var.get() == "llama3.1:8b":
            return False
        return self.show_thinking_var.get()
    
    def set_status(self, status):
        """Update the status bar text"""
        self.status_var.set(status)
    
    def set_input_enabled(self, enabled):
        """Enable or disable input controls"""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.input_field.config(state=state)
        self.send_button.config(state=state)
        self.restart_button.config(state=state)
        self.model_dropdown.config(state="readonly" if enabled else tk.DISABLED)
        if enabled:
            self.input_field.focus()
    
    def clear_conversation(self):
        """Clear the conversation display"""
        # Cancel any ongoing animation
        self.stop_thinking_animation()
        
        self.conversation_display.config(state=tk.NORMAL)
        self.conversation_display.delete(1.0, tk.END)
        self.conversation_display.config(state=tk.DISABLED)
    
    def display_welcome_message(self):
        """Display initial welcome message"""
        self.conversation_display.config(state=tk.NORMAL)
        self.conversation_display.insert(tk.END, "System:\n", "speaker")
        welcome_text = f"Welcome to Luis AI HUB!\nUsing model: {self.model_var.get()}\nType your message below to start chatting.\n\n"
        self.conversation_display.insert(tk.END, welcome_text, "system")
        self.conversation_display.config(state=tk.DISABLED)
    
    def display_user_message(self, message):
        """Display a user message in the conversation"""
        self.conversation_display.config(state=tk.NORMAL)
        self.conversation_display.insert(tk.END, "You:\n", "speaker")
        self.conversation_display.insert(tk.END, f"{message}\n\n", "user")
        self.conversation_display.see(tk.END)
        self.conversation_display.config(state=tk.DISABLED)
    
    def start_thinking_animation(self):
        """Start the thinking animation in the conversation"""
        # Cancel any existing animation
        self.stop_thinking_animation()
        
        # Reset animation frame
        self.animation_frame = 0
        
        # Insert AI speaker line
        self.conversation_display.config(state=tk.NORMAL)
        self.conversation_display.insert(tk.END, "AI:\n", "speaker")
        
        # Insert initial thinking text
        self.conversation_display.insert(tk.END, self.animation_frames[0], "thinking")
        self.conversation_display.see(tk.END)
        
        # Mark the position for animation updates
        self.animation_start_mark = self.conversation_display.index(tk.INSERT + " linestart")
        self.animation_end_mark = self.conversation_display.index(tk.INSERT)
        
        self.conversation_display.config(state=tk.DISABLED)
        
        # Start the animation cycle
        self._animate_thinking()
        
    def _animate_thinking(self):
        """Update the thinking animation frame"""
        # Advance to next frame
        self.animation_frame = (self.animation_frame + 1) % len(self.animation_frames)
        
        # Update the animation text
        self.conversation_display.config(state=tk.NORMAL)
        self.conversation_display.delete(self.animation_start_mark, self.animation_end_mark)
        self.conversation_display.insert(self.animation_start_mark, self.animation_frames[self.animation_frame], "thinking")
        self.animation_end_mark = f"{self.animation_start_mark} + {len(self.animation_frames[self.animation_frame])}c"
        self.conversation_display.see(tk.END)
        self.conversation_display.config(state=tk.DISABLED)
        
        # Schedule next frame
        self.animation_timer_id = self.root.after(150, self._animate_thinking)
    
    def stop_thinking_animation(self):
        """Stop the thinking animation"""
        # Cancel the timer if it exists
        if self.animation_timer_id:
            self.root.after_cancel(self.animation_timer_id)
            self.animation_timer_id = None
        
        # Remove the animation text if it exists
        try:
            self.conversation_display.config(state=tk.NORMAL)
            self.conversation_display.delete(self.animation_start_mark, self.animation_end_mark)
            self.conversation_display.config(state=tk.DISABLED)
        except (AttributeError, tk.TclError):
            # Animation marks might not exist, or might be invalid
            pass
    
    def display_ai_response(self, response):
        """Display an AI response with typing animation"""
        # Stop the thinking animation (if any)
        self.stop_thinking_animation()
        
        self.conversation_display.config(state=tk.NORMAL)
        # No need to insert "AI:" again as it was already inserted by thinking animation
        
        # Stream the text with typing effect
        for char in response:
            self.conversation_display.insert(tk.END, char, "ai")
            self.conversation_display.see(tk.END)
            self.conversation_display.update()
            time.sleep(0.01)  # Adjust for typing speed
        
        self.conversation_display.insert(tk.END, "\n\n")
        self.conversation_display.see(tk.END)
        self.conversation_display.config(state=tk.DISABLED)
    
    def start_response_checker(self, check_function):
        """Start the response checker thread"""
        def check_and_reschedule():
            check_function()
            self.root.after(100, check_and_reschedule)
        
        # Start the first check
        self.root.after(100, check_and_reschedule)