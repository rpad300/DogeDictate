# DogeDictate Development Guide

This guide provides information for developers who want to contribute to the DogeDictate project.

## Project Structure

```
DogeDictate/
├── main.py                 # Main entry point
├── run.py                  # Simple run script
├── setup.py                # Setup script for installation
├── build.py                # Build script for creating executables
├── check_requirements.py   # Script to check system requirements
├── update.py               # Script to check for and apply updates
├── uninstall.py            # Script to uninstall the application
├── requirements.txt        # Python dependencies
├── README.md               # Project overview
├── INSTALL.md              # Installation guide
├── LICENSE                 # MIT License
├── .gitignore              # Git ignore file
├── src/                    # Source code
│   ├── __init__.py         # Package initialization
│   ├── core/               # Core functionality
│   │   ├── __init__.py
│   │   ├── config_manager.py     # Configuration management
│   │   ├── hotkey_manager.py     # Hotkey handling
│   │   └── dictation_manager.py  # Dictation control
│   ├── gui/                # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py        # Main settings window
│   │   ├── hotkey_dialog.py      # Hotkey configuration dialog
│   │   └── floating_bar.py       # Floating status bar
│   └── services/           # Speech recognition services
│       ├── __init__.py
│       ├── whisper_service.py    # OpenAI Whisper integration
│       ├── azure_service.py      # Azure Speech Services integration
│       └── google_service.py     # Google Speech-to-Text integration
└── resources/              # Application resources
    ├── __init__.py
    ├── icons/              # Application icons
    └── sounds/             # Sound effects
```

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dogedictate/dogedictate.git
   cd dogedictate
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

## Development Workflow

1. **Create a new branch for your feature**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and test them**:
   - Implement your feature or fix
   - Test thoroughly on both Windows and macOS if possible
   - Ensure code follows the project's style guidelines

3. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

4. **Push your branch and create a pull request**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Coding Guidelines

- Follow PEP 8 style guidelines
- Use docstrings for all functions, classes, and modules
- Keep functions small and focused on a single task
- Write clear, descriptive variable and function names
- Add comments for complex logic
- Include error handling for all external operations

## Testing

- Test on both Windows and macOS platforms
- Test with different microphones
- Test with different speech recognition services
- Test with multiple languages
- Test edge cases and error conditions

## Building Executables

To build standalone executables:

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

2. **Run the build script**:
   ```bash
   python build.py
   ```

3. **Test the executable**:
   - Ensure it works on a clean system
   - Check that all features function correctly

## Current Status and Next Steps

### Completed
- Basic project structure
- Core functionality (configuration, hotkeys, dictation)
- GUI components (main window, hotkey dialog, floating bar)
- Speech recognition service integrations
- Build and installation scripts

### To Do
- Implement system tray icon
- Add more comprehensive error handling
- Improve microphone level visualization
- Add more sound effects
- Implement automatic word learning
- Create comprehensive test suite
- Add localization support
- Improve documentation

## Getting Help

If you need help with development:

- Check the existing code for examples
- Review the project documentation
- Contact the project maintainers
- Open an issue on GitHub 