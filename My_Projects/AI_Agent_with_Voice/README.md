# Luis AI HUB with Text-to-Speech

This project extends the Luis AI HUB application with speech input and output capabilities, providing a natural voice interface for interacting with language models through Ollama.

## Features

- **Voice Input**: Speak naturally to the AI using offline speech recognition
- **Voice Output**: Hear the AI's responses with text-to-speech
- **Conversation Display**: See both your input and AI responses with color coding
- **Multiple LLM Support**: Connect to different Ollama models
- **Voice Selection**: Choose from multiple voices for AI responses

## Text-to-Speech Options

The application supports two TTS engines with automatic fallback:

1. **XTTS-v2** (Primary - High Quality)
   - Advanced deep learning TTS with natural-sounding voices
   - Supports multiple languages and voices
   - Requires additional dependencies (see installation)

2. **System TTS** (Fallback - Easy Setup)
   - Uses your operating system's built-in TTS capabilities
   - No additional dependencies required
   - Quality varies depending on your OS

## Installation

### Basic Installation
This gets you running with speech recognition and system TTS:

```
pip install sounddevice numpy pyttsx3 vosk
```

### Full Installation (for High-Quality TTS)
For the best experience with XTTS-v2 (requires Visual C++ Build Tools):

1. Install Visual C++ Build Tools:
   - Download from [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - During installation, select "Desktop development with C++"

2. Install Python packages:
   ```
   pip install TTS torch sounddevice numpy pyttsx3 vosk
   ```

3. First run will download the required models (~1.5GB for XTTS-v2)

## Troubleshooting

### TTS Installation Issues

If you encounter errors installing the TTS package:

1. Make sure you have Visual C++ Build Tools installed
2. Try upgrading pip: `pip install --upgrade pip`
3. If still having issues, the application will automatically use system TTS

### No Sound

If you can't hear the TTS:

1. Make sure your speakers are on and volume is up
2. Check if other applications can play sound
3. Try selecting a different voice from the dropdown

## Usage

1. Start the application with `python main.py`
2. Select a language model from the dropdown
3. Enable voice input with the microphone button
4. Enable AI voice with the "AI Voice" checkbox
5. Select a voice from the dropdown
6. Start speaking or typing to interact with the AI

## Requirements

- Python 3.8+
- Ollama running locally with supported models
- 4GB+ RAM
- For XTTS: GPU with 4GB+ VRAM for optimal performance (optional)

## Future Improvements

- Voice cloning capabilities
- Speed and pitch controls for TTS
- Multiple language support
- Voice command system for controlling the application
