# DogeDictate Installation Guide

This guide will help you install and set up DogeDictate on your system.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- A working microphone
- Internet connection (for cloud-based speech recognition services)

## Installation

### Windows

1. **Install Python**:
   - Download and install Python 3.8 or higher from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Download DogeDictate**:
   - Download the latest release from the [GitHub repository](https://github.com/dogedictate/dogedictate/releases)
   - Or clone the repository: `git clone https://github.com/dogedictate/dogedictate.git`

3. **Install Dependencies**:
   - Open Command Prompt
   - Navigate to the DogeDictate directory: `cd path\to\dogedictate`
   - Install required packages: `pip install -r requirements.txt`

4. **Run DogeDictate**:
   - Run the application: `python main.py`

### macOS

1. **Install Python**:
   - Download and install Python 3.8 or higher from [python.org](https://www.python.org/downloads/)
   - Or use Homebrew: `brew install python`

2. **Download DogeDictate**:
   - Download the latest release from the [GitHub repository](https://github.com/dogedictate/dogedictate/releases)
   - Or clone the repository: `git clone https://github.com/dogedictate/dogedictate.git`

3. **Install Dependencies**:
   - Open Terminal
   - Navigate to the DogeDictate directory: `cd path/to/dogedictate`
   - Install required packages: `pip3 install -r requirements.txt`

4. **Run DogeDictate**:
   - Run the application: `python3 main.py`

## Building Executable (Optional)

If you want to create a standalone executable:

### Windows

1. Install PyInstaller: `pip install pyinstaller`
2. Run the build script: `python build.py`
3. The executable will be created in the `dist` directory

### macOS

1. Install PyInstaller: `pip3 install pyinstaller`
2. Run the build script: `python3 build.py`
3. The application bundle will be created in the `dist` directory

## Configuration

When you first run DogeDictate, you'll need to:

1. **Set up a Speech Recognition Service**:
   - For Whisper (OpenAI): Enter your API key
   - For Azure Speech Services: Enter your API key and region
   - For Google Speech-to-Text: Select your credentials JSON file

2. **Configure Hotkeys**:
   - Set up push-to-talk and hands-free hotkeys
   - Configure language-specific hotkeys if needed

3. **Select Microphone**:
   - Choose your preferred microphone from the list

## Troubleshooting

### Microphone Not Working

- Make sure your microphone is properly connected
- Check if it's set as the default recording device in your system settings
- Test the microphone in the Audio tab of DogeDictate settings

### Speech Recognition Not Working

- Verify your API key or credentials are correct
- Check your internet connection
- Make sure the selected service supports your language

### Hotkeys Not Responding

- Check if there are conflicts with other applications
- Try using different key combinations
- Restart the application after changing hotkey settings

## Getting Help

If you encounter any issues:

- Check the [GitHub Issues](https://github.com/dogedictate/dogedictate/issues) page
- Submit a new issue with details about your problem
- Contact support at support@dogedictate.com 