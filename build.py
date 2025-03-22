#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build script for DogeDictate
Creates executable packages for Windows and macOS
"""

import os
import sys
import shutil
import subprocess
import platform

def build_windows():
    """Build Windows executable"""
    print("Building Windows executable...")
    
    # Create dist directory if it doesn't exist
    if not os.path.exists("dist"):
        os.makedirs("dist")
    
    # Build with PyInstaller
    subprocess.run([
        "pyinstaller",
        "--name=DogeDictate",
        "--windowed",
        "--icon=resources/icons/app_icon.ico",
        "--add-data=resources;resources",
        "--hidden-import=pynput.keyboard._win32",
        "--hidden-import=pynput.mouse._win32",
        "main.py"
    ], check=True)
    
    print("Windows build completed successfully!")

def build_macos():
    """Build macOS application"""
    print("Building macOS application...")
    
    # Create dist directory if it doesn't exist
    if not os.path.exists("dist"):
        os.makedirs("dist")
    
    # Build with PyInstaller
    subprocess.run([
        "pyinstaller",
        "--name=DogeDictate",
        "--windowed",
        "--icon=resources/icons/app_icon.icns",
        "--add-data=resources:resources",
        "--hidden-import=pynput.keyboard._darwin",
        "--hidden-import=pynput.mouse._darwin",
        "main.py"
    ], check=True)
    
    print("macOS build completed successfully!")

def main():
    """Main build function"""
    # Determine platform
    if platform.system() == "Windows":
        build_windows()
    elif platform.system() == "Darwin":  # macOS
        build_macos()
    else:
        print(f"Unsupported platform: {platform.system()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 