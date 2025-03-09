import tkinter as tk
from tkinter import scrolledtext, ttk, BooleanVar, StringVar, font, Toplevel, Canvas, messagebox
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


class VoiceCloningDialog:
    """Dialog for voice cloning"""
    def __init__(self, parent, record_callback=None, clone_callback=None):
        self.parent = parent
        self.record_callback = record_callback
        self.clone_callback = clone_callback
        self.dialog = None
        self.recording = None  # Explicitly initialize to None
        self.is_recording = False
        self.recording_thread = None
        self.progress_var = None
        self.progress_bar = None
        self.status_var = None
        self.record_button = None
        self.clone_button = None
        self.voice_name_entry = None
    
    def show(self):
        # Create dialog window
        self.dialog = Toplevel(self.parent)
        self.dialog.title("Clone Voice")
        self.dialog.geometry("400x380")
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
        
        # Instructions
        ttk.Label(frame, text="Voice Cloning Setup", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))
        
        # Voice Name Entry
        name_frame = ttk.Frame(frame)
        name_frame.pack(fill=tk.X, pady=(5, 15))
        
        ttk.Label(name_frame, text="Voice Name:").pack(side=tk.LEFT)
        self.voice_name_entry = ttk.Entry(name_frame, width=25)
        self.voice_name_entry.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        self.voice_name_entry.insert(0, "My Custom Voice")
        
        # Instructions
        instructions = (
            "1. Click 'Record Sample' and speak clearly for 10 seconds\n"
            "2. Say a full sentence with varied intonation\n"
            "3. Maintain consistent distance from microphone\n"
            "4. Avoid background noise during recording\n"
            "5. Click 'Clone Voice' when satisfied with recording"
        )
        
        instructions_frame = ttk.LabelFrame(frame, text="Instructions")
        instructions_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(instructions_frame, text=instructions, justify=tk.LEFT).pack(padx=10, pady=10)
        
        # Progress bar for recording
        progress_frame = ttk.Frame(frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to record")
        status_label = ttk.Label(frame, textvariable=self.status_var)
        status_label.pack(pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Record button
        self.record_button = ttk.Button(
            btn_frame,
            text="Record Sample (10s)",
            command=self._on_record
        )
        self.record_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Clone button (initially disabled)
        self.clone_button = ttk.Button(
            btn_frame,
            text="Clone Voice",
            command=self._on_clone,
            state="disabled"
        )
        self.clone_button.pack(side=tk.LEFT)
        
        # Cancel button
        ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT)
        
        # Make dialog modal
        self.dialog.wait_window()
    
    def _on_record(self):
        """Handle record button click"""
        if self.is_recording:
            self.status_var.set("Recording in progress, please wait...")
            return
        
        # Reset previous recording if any
        self.recording = None  # Explicitly set to None
        self.progress_var.set(0)
        self.status_var.set("Starting recording in 1 second...")
        self.record_button.config(state="disabled")
        self.clone_button.config(state="disabled")
        
        # Update UI before recording starts
        self.dialog.update()
        
        # Short delay before recording starts
        self.dialog.after(1000, self._start_recording)
    
    def _start_recording(self):
        """Start the actual recording process"""
        self.is_recording = True
        self.status_var.set("Recording... Speak now!")
        
        # Start a timer to update progress bar
        self._update_progress_bar(0, 10.0)
        
        # Call the record callback
        if self.record_callback:
            # Start recording in a separate thread to keep UI responsive
            import threading
            self.recording_thread = threading.Thread(target=self._record_thread)
            self.recording_thread.daemon = True
            self.recording_thread.start()
    
    def _record_thread(self):
        """Background thread for recording"""
        try:
            success, result = self.record_callback()
            
            # Update UI in main thread
            self.dialog.after(0, lambda: self._recording_complete(success, result))
        except Exception as e:
            self.dialog.after(0, lambda: self._recording_complete(False, str(e)))
    
    def _recording_complete(self, success, result):
        """Called when recording is complete"""
        self.is_recording = False
        
        if success and result is not None:  # Ensure result is not None
            self.recording = result
            self.status_var.set("Recording complete! Click 'Clone Voice' to continue.")
            self.clone_button.config(state="normal")
        else:
            self.recording = None  # Explicitly set to None on failure
            self.status_var.set(f"Recording failed: {result}")
        
        self.record_button.config(state="normal")
    
    def _update_progress_bar(self, current_time, total_time):
        """Update the progress bar during recording"""
        if not self.is_recording:
            return
            
        # Calculate percentage
        percentage = (current_time / total_time) * 100
        self.progress_var.set(percentage)
        
        # If not completed yet, schedule another update
        if current_time < total_time:
            self.dialog.after(100, lambda: self._update_progress_bar(current_time + 0.1, total_time))
        else:
            # Progress complete - reset progress bar after a delay
            self.dialog.after(500, lambda: self.progress_var.set(100))
    
    def _on_clone(self):
        """Handle clone button click"""
        if self.recording is None:  # Fixed: Check if recording is None instead of boolean evaluation
            self.status_var.set("No recording available. Record a sample first.")
            return
            
        voice_name = self.voice_name_entry.get().strip()
        if not voice_name:
            self.status_var.set("Please enter a name for this voice.")
            return
            
        self.status_var.set("Cloning voice... This may take a moment.")
        self.clone_button.config(state="disabled")
        self.record_button.config(state="disabled")
        
        # Update UI
        self.dialog.update()
        
        # Call the clone callback
        if self.clone_callback:
            # Start cloning in a separate thread to keep UI responsive
            import threading
            clone_thread = threading.Thread(
                target=lambda: self._clone_thread(voice_name)
            )
            clone_thread.daemon = True
            clone_thread.start()
    
    def _clone_thread(self, voice_name):
        """Background thread for cloning"""
        try:
            success, result = self.clone_callback(self.recording, voice_name)
            
            # Update UI in main thread
            self.dialog.after(0, lambda: self._cloning_complete(success, result))
        except Exception as e:
            self.dialog.after(0, lambda: self._cloning_complete(False, str(e)))
    
    def _cloning_complete(self, success, result):
        """Called when cloning is complete"""
        if success:
            self.status_var.set(f"Voice '{result}' successfully cloned!")
            messagebox.showinfo("Success", f"Voice '{result}' has been successfully cloned and added to your voice list!")
            self.dialog.destroy()
        else:
            self.status_var.set(f"Cloning failed: {result}")
            self.clone_button.config(state="normal")
            self.record_button.config(state="normal")


class ChatbotView:
    """
    View class that handles the UI
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Luis AI HUB")
        self.root.geometry("800x650")  # Increased height for the voice controls
        
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
        self.voice_toggle_callback = None
        self.select_mic_callback = None
        self.tts_toggle_callback = None
        self.voice_change_callback = None
        self.clone_voice_callback = None
    
    def _setup_ui(self):
        """Set up the UI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar frame - TOP SECTION (Model controls only)
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
        self.conversation_display.tag_configure("voice_typing", foreground="#FF8800")
        
        # Voice input variables
        self.voice_input_active = False
        self.voice_line_start = None
        self.voice_text_start = None
        
        # Create improved input area - MIDDLE SECTION
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=(5, 5))
        
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
        
        # BOTTOM SECTION - Voice controls (now below the input area)
        voice_section_frame = ttk.LabelFrame(main_frame, text="Voice Controls")
        voice_section_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Create a grid layout for voice controls with column configuration
        voice_grid = ttk.Frame(voice_section_frame, padding=10)
        voice_grid.pack(fill=tk.X)
        voice_grid.columnconfigure(0, weight=1)  # Input section takes 50%
        voice_grid.columnconfigure(1, weight=1)  # Output section takes 50%
        
        # INPUT SECTION - Left side
        input_controls = ttk.LabelFrame(voice_grid, text="Voice Input")
        input_controls.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        input_buttons = ttk.Frame(input_controls, padding=5)
        input_buttons.pack(fill=tk.X)
        
        # Microphone selection button
        self.mic_button = ttk.Button(
            input_buttons,
            text="🎤 Select Mic",
            command=self._on_select_mic,
            width=12
        )
        self.mic_button.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        
        # Voice input toggle button
        self.voice_active = False
        self.voice_button = ttk.Button(
            input_buttons,
            text="🎤 Enable Voice",
            command=self._on_voice_toggle,
            width=12
        )
        self.voice_button.pack(side=tk.LEFT, pady=5)
        
        # OUTPUT SECTION - Right side
        output_controls = ttk.LabelFrame(voice_grid, text="AI Voice Output")
        output_controls.grid(row=0, column=1, sticky="ew")
        
        output_frame = ttk.Frame(output_controls, padding=5)
        output_frame.pack(fill=tk.X)
        
        # TTS toggle
        self.tts_enabled = BooleanVar(value=False)
        self.tts_checkbox = ttk.Checkbutton(
            output_frame,
            text="Enable AI Voice",
            variable=self.tts_enabled,
            command=self._on_tts_toggle
        )
        self.tts_checkbox.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        self.tts_checkbox.config(state="disabled")  # Disabled until TTS is ready
        
        # Voice selection dropdown
        ttk.Label(output_frame, text="Voice:").pack(side=tk.LEFT, padx=(0, 5))
        self.voice_var = StringVar(value="Default")
        self.voice_dropdown = ttk.Combobox(
            output_frame,
            textvariable=self.voice_var,
            state="readonly",
            width=15
        )
        self.voice_dropdown.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        self.voice_dropdown.bind("<<ComboboxSelected>>", self._on_voice_change)
        
        # Voice cloning button
        self.clone_voice_button = ttk.Button(
            output_frame,
            text="Clone Voice",
            command=self._on_clone_voice,
            width=12
        )
        self.clone_voice_button.pack(side=tk.LEFT, pady=5)
        self.clone_voice_button.config(state="disabled")  # Disabled until TTS is ready
        
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
        # Toggle active state
        new_active_state = not self.voice_active
        
        # Update UI immediately to give instant feedback
        if new_active_state:
            self.voice_button.config(text="🎤 Disable Voice")
        else:
            self.voice_button.config(text="🎤 Enable Voice")
        
        # Notify controller (which will set the actual state based on success/failure)
        if self.voice_toggle_callback:
            self.voice_toggle_callback(new_active_state)
    
    def _on_tts_toggle(self):
        """Handle TTS toggle"""
        if self.tts_toggle_callback:
            self.tts_toggle_callback(self.tts_enabled.get())

    def _on_voice_change(self, event=None):
        """Handle voice selection change"""
        if self.voice_change_callback:
            self.voice_change_callback(self.voice_var.get())
    
    def _on_clone_voice(self):
        """Handle voice cloning button click"""
        if self.clone_voice_callback:
            self.clone_voice_callback()
        
    def set_tts_toggle_callback(self, callback):
        """Set callback for TTS toggle"""
        self.tts_toggle_callback = callback
        
    def set_voice_change_callback(self, callback):
        """Set callback for voice change"""
        self.voice_change_callback = callback
    
    def set_clone_voice_callback(self, callback):
        """Set callback for voice cloning"""
        self.clone_voice_callback = callback
        
    def update_voice_list(self, voices):
        """Update the list of available voices"""
        current = self.voice_var.get()
        self.voice_dropdown['values'] = voices
        
        # Keep current selection if possible
        if current in voices:
            self.voice_var.set(current)
        elif voices:
            self.voice_var.set(voices[0])
    
    def enable_voice_cloning(self, enabled=True):
        """Enable or disable the voice cloning button"""
        self.clone_voice_button.config(state="normal" if enabled else "disabled")
    
    def start_voice_input(self):
        """Initialize the voice input display"""
        # If we already have voice input active, clean up first
        if self.voice_input_active:
            self.end_voice_input()
        
        self.conversation_display.config(state=tk.NORMAL)
        
        # Add the speaker line
        self.voice_line_start = self.conversation_display.index(tk.END)
        self.conversation_display.insert(tk.END, "You (voice):\n", "speaker")
        
        # Mark where the text will start
        self.voice_text_start = self.conversation_display.index(tk.END)
        
        # Set active flag
        self.voice_input_active = True
        
        # Make sure it's visible
        self.conversation_display.see(tk.END)
        self.conversation_display.config(state=tk.DISABLED)
    
    def append_voice_text(self, text):
        """Append new word(s) to the voice input display"""
        if not self.voice_input_active:
            # If voice input isn't active yet, start it
            self.start_voice_input()
        
        self.conversation_display.config(state=tk.NORMAL)
        
        # Append the new text with the voice_typing tag
        self.conversation_display.insert(tk.END, f"{text} ", "voice_typing")
        
        # Make sure it's visible
        self.conversation_display.see(tk.END)
        self.conversation_display.config(state=tk.DISABLED)
    
    def end_voice_input(self):
        """Finalize the voice input display"""
        if not self.voice_input_active:
            return
        
        self.conversation_display.config(state=tk.NORMAL)
        
        # Add a double newline to separate from next message
        self.conversation_display.insert(tk.END, "\n\n")
        
        # Change text tag from voice_typing to final voice tag
        if self.voice_text_start:
            # Get all text from the voice input
            text_end = self.conversation_display.index(tk.END + "-3c")  # Account for the \n\n we just added
            
            # Change tag from temporary to final
            self.conversation_display.tag_remove("voice_typing", self.voice_text_start, text_end)
            self.conversation_display.tag_add("voice", self.voice_text_start, text_end)
        
        # Reset markers
        self.voice_input_active = False
        self.voice_line_start = None
        self.voice_text_start = None
        
        # Make sure it's visible
        self.conversation_display.see(tk.END)
        self.conversation_display.config(state=tk.DISABLED)
    
    def show_microphone_selector(self, microphones):
        """Show microphone selection dialog"""
        selector = MicrophoneSelector(self.root, microphones)
        return selector.show()
    
    def show_voice_cloning_dialog(self, record_callback=None, clone_callback=None):
        """Show voice cloning dialog"""
        dialog = VoiceCloningDialog(self.root, record_callback, clone_callback)
        dialog.show()
    
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
        # If we have an active voice input, end it first
        if self.voice_input_active:
            self.end_voice_input()
            # Since we just added the speaker line and the message in end_voice_input,
            # we don't need to do it again
            return
        
        # Normal display logic
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
        
        # Insert AI speaker line with proper spacing
        self.conversation_display.config(state=tk.NORMAL)
        
        # Ensure there's proper spacing before AI's response
        current_position = self.conversation_display.index(tk.END + "-1c")
        last_chars = self.conversation_display.get(f"{current_position}-2c", current_position)
        
        # If we don't already have a double newline, add proper spacing
        if last_chars != "\n\n":
            self.conversation_display.insert(tk.END, "\n")
        
        # Now add the AI speaker tag
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
    
    def display_ai_response(self, response, speak_callback=None):
        """Display an AI response with typing animation and progressive speech"""
        # Stop the thinking animation (if any)
        self.stop_thinking_animation()
        
        self.conversation_display.config(state=tk.NORMAL)
        # No need to insert "AI:" again as it was already inserted by thinking animation
        
        # Split response into sentences to handle progressive speech
        import re
        sentences = re.split(r'(?<=[.!?])\s+', response)
        
        current_sentence = ""
        current_position = 0
        
        # Process each character, tracking sentence boundaries
        for char in response:
            # Add the character to the display
            self.conversation_display.insert(tk.END, char, "ai")
            self.conversation_display.see(tk.END)
            self.conversation_display.update()
            
            # Add to current sentence
            current_sentence += char
            current_position += 1
            
            # Check if we've completed a sentence
            if char in '.!?' and (current_position >= len(response) or response[current_position].isspace()):
                # Complete sentence detected - send it for speech if callback provided
                if speak_callback and current_sentence.strip():
                    speak_callback(current_sentence.strip())
                    current_sentence = ""
            
            time.sleep(0.01)  # Adjust for typing speed
        
        # Handle any remaining text as a sentence
        if speak_callback and current_sentence.strip():
            speak_callback(current_sentence.strip())
        
        self.conversation_display.insert(tk.END, "\n\n")
        self.conversation_display.see(tk.END)
        self.conversation_display.config(state=tk.DISABLED)
        
        # Ensure we're ready for a fresh voice input next time
        self.voice_input_active = False  # Reset voice input state
    
    def start_response_checker(self, check_function):
        """Start the response checker thread"""
        def check_and_reschedule():
            check_function()
            self.root.after(100, check_and_reschedule)
        
        # Start the first check
        self.root.after(100, check_and_reschedule)
