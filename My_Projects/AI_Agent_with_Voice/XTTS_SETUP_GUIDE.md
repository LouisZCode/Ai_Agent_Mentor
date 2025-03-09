# XTTS-v2 Setup Guide for Luis AI HUB

This guide will help you set up the high-quality XTTS-v2 text-to-speech system for Luis AI HUB.

## Prerequisites

- Python 3.8 or newer
- Visual C++ Build Tools (for Windows)
- At least 4GB of free disk space (for model downloads)
- 4GB+ RAM (8GB+ recommended)

## Step 1: Install Visual C++ Build Tools (Windows Only)

1. Download from [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. During installation, select "Desktop development with C++"
3. Complete the installation (may take 10-15 minutes)

## Step 2: Create a Virtual Environment (Recommended)

Creating a virtual environment helps prevent package conflicts:

```bash
# Create a virtual environment
python -m venv tts-env

# Activate the environment
# Windows:
tts-env\Scripts\activate
# macOS/Linux:
source tts-env/bin/activate
```

## Step 3: Install the Required Packages

```bash
# Update pip to the latest version
pip install --upgrade pip

# Install PyTorch - GPU version if you have NVIDIA GPU with CUDA
# For CUDA support (much faster):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CPU only (slower but works everywhere):
pip install torch torchvision torchaudio

# Install the TTS package
pip install TTS

# Install other required packages
pip install sounddevice numpy vosk
```

## Step 4: Fix PyTorch 2.6+ Issues (If Needed)

If you're using PyTorch 2.6 or newer and encountering "weights_only" errors, you need to add safe globals. The TTS module already tries to handle this, but you can manually fix it by running:

```python
import torch
# Allow XTTS classes to be loaded
torch.serialization.add_safe_globals(["TTS.tts.configs.xtts_config.XttsConfig"])
```

## Step 5: First Run Configuration

1. Start the application: `python main.py`
2. On first run, it will download the XTTS-v2 model (about 1.5GB)
3. This may take several minutes depending on your internet connection
4. Look for "XTTS-v2 engine initialized successfully" in the console

## Step 6: Testing and Troubleshooting

### Testing Your Installation

1. Enable the "AI Voice" checkbox in the UI
2. Send a message to get an AI response
3. You should see "🔊 Speaking: '...'" messages in the console
4. Make sure your system volume is turned up

### Common Issues and Solutions

#### No Sound Output

- Ensure your speakers/headphones are working with other applications
- Try a different audio output device
- Check the console for any error messages related to sounddevice

#### Installation Errors with TTS Package

- Make sure Visual C++ Build Tools are properly installed
- Try installing in a clean virtual environment
- Update all dependencies: `pip install --upgrade pip setuptools wheel`

#### "weights_only" Errors with PyTorch 2.6+

These errors look like:
```
WeightsUnpickler error: Unsupported global: GLOBAL TTS.tts.configs.xtts_config.XttsConfig
```

Solution:
- Downgrade PyTorch to 2.5.x: `pip install torch==2.5.0`
- Or use the patched torch.load as implemented in the TTS module

#### Performance Issues (Slow Speech Generation)

- If you have an NVIDIA GPU, make sure you installed the CUDA version of PyTorch
- If using CPU only, speech generation will be slower, especially for the first sentence

## Advanced Configuration

### Custom Voices

XTTS-v2 supports custom voices through speaker embeddings. To use a custom voice:

1. Prepare a 3-10 second clear audio recording (.wav format)
2. Place it in a known directory
3. Use the TTS API with your custom reference:
   ```python
   audio = tts.tts(text="Hello world", speaker_wav="path/to/your/audio.wav")
   ```

### Multiple Languages

XTTS-v2 supports multiple languages including English, Spanish, French, German, Italian, Portuguese, Polish, Turkish, Russian, Dutch, Czech, Arabic, Chinese, Japanese, Korean, and more.

To change the language:
1. Select a voice that supports multiple languages
2. Set the language parameter: `tts.set_language("fr")` (for French)

## Questions or Issues?

If you encounter any issues not covered in this guide, please check the TTS documentation or reach out for support.
