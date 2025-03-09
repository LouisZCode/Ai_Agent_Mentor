import tkinter as tk
from tkinter import scrolledtext, ttk, BooleanVar, StringVar, font, Toplevel, Canvas
import time

class MicrophoneSelector:
    """Dialog for selecting microphones"""
    def __init__(self, parent, microphones):
        self.parent = parent
        self.microphones = microphones
        self.selected_mic = None
        self.dialog = None
    
    def show(self):
        # Create dialog window
        self.dialog = Toplevel(self.parent)
        self.dialog.title("Select Microphone")
        self.dialog.geometry("400x300")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.parent.winfo_screenwidth() // 2) - (width // 2)
        y = (self.parent.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create content
        frame = ttk.Frame(self.dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Select a microphone to use:").pack(pady=(0, 10))
        
        # Create listbox for microphones
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Helvetica", 10))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=listbox.yview)
        
        # Add microphones to listbox
        for idx, name in self.microphones:
            listbox.insert(tk.END, f"[{idx}] {name}")
        
        # Select first item
        if self.microphones:
            listbox.selection_set(0)
            listbox.activate(0)
        
        # Create buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Use Default", command=self.use_default).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(btn_frame, text="Select", command=lambda: self.select(listbox)).pack(side=tk.RIGHT)
        
        # Set up double-click selection
        listbox.bind("<Double-1>", lambda event: self.select(listbox))
        
        # Make dialog modal
        self.dialog.wait_window()
        
        return self.selected_mic
    
    def select(self, listbox):
        """Handle selection from listbox"""
        if not listbox.curselection():
            return
        
        # Get selected index
        idx = listbox.curselection()[0]
        
        # Get microphone ID
        mic_idx, _ = self.microphones[idx]
        self.selected_mic = mic_idx
        
        # Close dialog
        self.dialog.destroy()
    
    def use_default(self):
        """Use default microphone"""
        self.selected_mic = None
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel selection"""
        self.dialog.destroy()

class ChatbotView:
    """
    View class that handles the UI
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Luis AI HUB")
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
        
        # Audio visualization variables
        self.audio_viz_timer_id = None
        self.audio_viz_canvas = None
        self.audio_level_callback = None
        
        # Available models
        self.available_models = ["qwq:latest", "llama3.1:8b", "deepseek-r1:32b"]
        
        # Set up the interface
        self._setup_ui()
        
        # Initialize callbacks
        self.send_callback = None
        self.reset_callback = None
        self.model_change_callback = None
        self.voice_toggle_callback = None
        self.select_mic_callback = None
    
    def _setup_ui(self):
        """Set up the UI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar frame
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Model selection dropdown - Set default to Llama model
        ttk.Label(toolbar_frame, text="Model:").pack(side=tk.LEFT, padx=(0, 5))
        self.model_var = StringVar(value="llama3.1:8b")  # Default to Llama model
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
        
        # Voice controls frame (right side of toolbar)
        voice_frame = ttk.Frame(toolbar_frame)
        voice_frame.pack(side=tk.RIGHT, padx=(0, 0))
        
        # Microphone selection button
        self.mic_button = ttk.Button(
            voice_frame,
            text="🎤 Select Mic",
            command=self._on_select_mic
        )
        self.mic_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Audio level visualization (hidden by default)
        self.audio_viz_frame = ttk.Frame(voice_frame)
        self.audio_viz_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        # Canvas for audio level visualization
        self.audio_viz_canvas = Canvas(
            self.audio_viz_frame, 
            width=100,  # Width of the level meter
            height=20,  # Height of the level meter
            bg="light gray",
            highlightthickness=1,
            highlightbackground="gray"
        )
        self.audio_viz_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Initially hide the visualization
        self.audio_viz_frame.pack_forget()
        
        # Voice input toggle button
        self.voice_active = False
        self.voice_button = ttk.Button(
            voice_frame,
            text="🎤 Enable Voice",
            command=self._on_voice_toggle
        )
        self.voice_button.pack(side=tk.LEFT, padx=(0, 0))
        
        # Update thinking checkbox visibility based on selected model
        self._update_thinking_checkbox_visibility()
        
        # Create conversation display
        self.conversation_display = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=26,
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
        self.conversation_display.tag_configure("voice", foreground="orange")
        
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
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.input_field.bind("<Return>", self._on_send)
        
        # Send button with matched size
        self.send_button = ttk.Button(
            input_frame, 
            text="Send", 
            command=self._on_send,
            padding=(10, 15)
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
    
    def _on_select_mic(self):
        """Handle microphone selection button click"""
        if self.select_mic_callback:
            self.select_mic_callback()
    
    def _on_voice_toggle(self):
        """Handle voice button click"""
        self.voice_active = not self.voice_active
        
        if self.voice_active:
            self.voice_button.config(text="🎤 Disable Voice")
            self.set_status("Voice input active - speak clearly")
            
            # Show and start the audio visualization
            self.audio_viz_frame.pack(side=tk.LEFT, padx=(0, 10))
            self.start_audio_visualization()
        else:
            self.voice_button.config(text="🎤 Enable Voice")
            self.set_status("Voice input disabled")
            
            # Stop and hide the audio visualization
            self.stop_audio_visualization()
            self.audio_viz_frame.pack_forget()
        
        # Notify controller about voice toggle
        if self.voice_toggle_callback:
            self.voice_toggle_callback(self.voice_active)
    
    def start_audio_visualization(self):
        """Start the audio level visualization"""
        self.stop_audio_visualization()  # Stop any existing visualization
        
        def update_viz():
            if not self.voice_active or not self.audio_level_callback:
                return
            
            # Get current audio level (0.0 to 1.0) from callback
            level = self.audio_level_callback()
            
            # Update visualization
            self._update_audio_viz(level)
            
            # Schedule next update
            self.audio_viz_timer_id = self.root.after(33, update_viz)  # ~30 fps
        
        # Start the updates
        update_viz()
    
    def _update_audio_viz(self, level):
        """Update the audio level visualization with a new level (0.0 to 1.0)"""
        if not self.audio_viz_canvas:
            return
        
        # Clear canvas
        self.audio_viz_canvas.delete("all")
        
        # Get canvas dimensions
        width = self.audio_viz_canvas.winfo_width()
        height = self.audio_viz_canvas.winfo_height()
        
        # Ensure we have dimensions
        if width < 10 or height < 5:
            width = 100
            height = 20
        
        # Calculate bar width based on level
        bar_width = int(width * level)
        
        # Only show visualization if the level is above a minimal threshold
        if level > 0.01:  # Skip drawing for very low levels (silence)
            # Determine color based on level with smooth gradient
            if level < 0.3:
                # Green gradient (darker to lighter as level increases)
                green_intensity = int(128 + (level / 0.3) * 127)
                color = f"#4C{green_intensity:02X}50"
            elif level < 0.7:
                # Yellow gradient (transition from green to yellow to orange)
                yellow_factor = (level - 0.3) / 0.4  # 0 to 1 in medium range
                r = int(76 + yellow_factor * 179)  # 4C to FF
                g = int(175 - yellow_factor * 50)   # AF to 89
                b = int(80 - yellow_factor * 80)    # 50 to 00
                color = f"#{r:02X}{g:02X}{b:02X}"
            else:
                # Red gradient (more intense as level increases)
                red_intensity = int(220 + (level - 0.7) / 0.3 * 35)
                red_intensity = min(255, red_intensity)  # Ensure we don't exceed 255
                color = f"#{red_intensity:02X}3030"
            
            # Draw the audio level bar 
            self.audio_viz_canvas.create_rectangle(
                0, 0, bar_width, height, 
                fill=color, outline="", width=0
            )
            
            # Add shimmer effect for high levels
            if level > 0.8:
                # Draw some shimmer highlights
                for i in range(3):
                    pos = bar_width * (0.2 + 0.25 * i)
                    if pos < bar_width:
                        highlight_width = 2 + i * 2
                        try:
                            # Try with stipple for shimmer effect
                            self.audio_viz_canvas.create_line(
                                pos, 2, pos, height-2,
                                fill="#FFFFFF",
                                width=highlight_width,
                                stipple="gray50"
                            )
                        except tk.TclError:
                            # Fallback if stipple is not supported
                            self.audio_viz_canvas.create_line(
                                pos, 2, pos, height-2,
                                fill="#FFFFFF",
                                width=highlight_width
                            )
        
        # Draw level markers with labels
        markers = [0.25, 0.5, 0.75]  # At 25%, 50%, 75%
        for marker in markers:
            x = width * marker
            # Line
            self.audio_viz_canvas.create_line(
                x, height, x, 0, 
                fill="gray", width=1, dash=(1, 2)
            )
    
    def stop_audio_visualization(self):
        """Stop the audio level visualization"""
        if self.audio_viz_timer_id:
            self.root.after_cancel(self.audio_viz_timer_id)
            self.audio_viz_timer_id = None
    
    def set_audio_level_callback(self, callback):
        """Set the callback function to get the current audio level"""
        self.audio_level_callback = callback
    
    def show_microphone_selector(self, microphones):
        """Show microphone selection dialog"""
        selector = MicrophoneSelector(self.root, microphones)
        return selector.show()
    
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
    
    def set_voice_toggle_callback(self, callback):
        """Set the callback for when voice input is toggled"""
        self.voice_toggle_callback = callback
    
    def set_select_mic_callback(self, callback):
        """Set the callback for when microphone selection is requested"""
        self.select_mic_callback = callback
    
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
    
    def display_user_message(self, message, is_voice=False):
        """Display a user message in the conversation"""
        self.conversation_display.config(state=tk.NORMAL)
        
        if is_voice:
            self.conversation_display.insert(tk.END, "You (voice):\n", "speaker")
            self.conversation_display.insert(tk.END, f"{message}\n\n", "voice")
        else:
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