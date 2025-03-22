#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Update script for DogeDictate
"""

import sys
import os
import subprocess
import platform
import json
import requests

# Current version
CURRENT_VERSION = "0.1.0"

# GitHub repository information
REPO_OWNER = "dogedictate"
REPO_NAME = "dogedictate"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

def check_for_updates():
    """Check if updates are available"""
    print(f"Current version: {CURRENT_VERSION}")
    print("Checking for updates...")
    
    try:
        # Get latest release information from GitHub
        response = requests.get(API_URL)
        response.raise_for_status()
        
        release_info = response.json()
        latest_version = release_info["tag_name"].lstrip("v")
        
        print(f"Latest version: {latest_version}")
        
        # Compare versions
        if latest_version > CURRENT_VERSION:
            print(f"Update available: {CURRENT_VERSION} -> {latest_version}")
            return True, latest_version, release_info["html_url"]
        else:
            print("You have the latest version.")
            return False, CURRENT_VERSION, None
    
    except Exception as e:
        print(f"Error checking for updates: {str(e)}")
        return False, CURRENT_VERSION, None

def update_application(version, download_url):
    """Update the application"""
    print(f"Updating to version {version}...")
    
    try:
        # Backup current configuration
        if os.path.exists(os.path.join(os.environ.get("APPDATA", ""), "DogeDictate", "config.json")):
            print("Backing up configuration...")
            backup_config()
        
        # Download and install the update
        print(f"Please download the latest version from: {download_url}")
        print("After downloading, please follow the installation instructions.")
        
        # Open the download URL in the default browser
        if platform.system() == "Windows":
            os.startfile(download_url)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", download_url])
        else:
            subprocess.run(["xdg-open", download_url])
        
        return True
    
    except Exception as e:
        print(f"Error updating application: {str(e)}")
        return False

def backup_config():
    """Backup the current configuration"""
    try:
        config_dir = os.path.join(os.environ.get("APPDATA", ""), "DogeDictate")
        config_file = os.path.join(config_dir, "config.json")
        backup_file = os.path.join(config_dir, "config.json.bak")
        
        if os.path.exists(config_file):
            with open(config_file, "r") as src:
                with open(backup_file, "w") as dst:
                    dst.write(src.read())
            
            print(f"Configuration backed up to: {backup_file}")
            return True
        else:
            print("No configuration file found.")
            return False
    
    except Exception as e:
        print(f"Error backing up configuration: {str(e)}")
        return False

def main():
    """Main function"""
    print("DogeDictate Update Utility")
    print("=========================")
    
    # Check for updates
    update_available, latest_version, download_url = check_for_updates()
    
    if update_available:
        # Ask user if they want to update
        response = input("Do you want to update now? (y/n): ").lower()
        
        if response == "y":
            # Update the application
            if update_application(latest_version, download_url):
                print("Update process started. Please follow the instructions.")
                return 0
            else:
                print("Update failed.")
                return 1
        else:
            print("Update cancelled.")
            return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 