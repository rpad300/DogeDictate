#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Uninstall script for DogeDictate
"""

import sys
import os
import shutil
import platform
import subprocess

def get_config_dir():
    """Get the configuration directory"""
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("APPDATA", ""), "DogeDictate")
    else:  # macOS and Linux
        return os.path.join(os.path.expanduser("~"), ".dogedictate")

def backup_config():
    """Backup the configuration"""
    config_dir = get_config_dir()
    config_file = os.path.join(config_dir, "config.json")
    backup_file = os.path.join(os.path.expanduser("~"), "dogedictate_config_backup.json")
    
    if os.path.exists(config_file):
        try:
            shutil.copy2(config_file, backup_file)
            print(f"Configuration backed up to: {backup_file}")
            return True
        except Exception as e:
            print(f"Error backing up configuration: {str(e)}")
            return False
    else:
        print("No configuration file found.")
        return False

def remove_config():
    """Remove the configuration directory"""
    config_dir = get_config_dir()
    
    if os.path.exists(config_dir):
        try:
            shutil.rmtree(config_dir)
            print(f"Configuration directory removed: {config_dir}")
            return True
        except Exception as e:
            print(f"Error removing configuration directory: {str(e)}")
            return False
    else:
        print("No configuration directory found.")
        return False

def remove_startup_entry():
    """Remove startup entry"""
    if platform.system() == "Windows":
        startup_dir = os.path.join(os.environ.get("APPDATA", ""), 
                                  "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        startup_file = os.path.join(startup_dir, "DogeDictate.lnk")
        
        if os.path.exists(startup_file):
            try:
                os.remove(startup_file)
                print("Startup entry removed.")
                return True
            except Exception as e:
                print(f"Error removing startup entry: {str(e)}")
                return False
        else:
            print("No startup entry found.")
            return False
    else:  # macOS
        # For macOS, we would need to remove from Login Items
        print("Please remove DogeDictate from your login items manually.")
        return True

def main():
    """Main function"""
    print("DogeDictate Uninstall Utility")
    print("============================")
    
    # Ask for confirmation
    print("\nThis will uninstall DogeDictate from your system.")
    print("Your configuration will be backed up before removal.")
    response = input("Do you want to continue? (y/n): ").lower()
    
    if response != "y":
        print("Uninstall cancelled.")
        return 0
    
    # Backup configuration
    print("\nBacking up configuration...")
    backup_config()
    
    # Remove configuration
    print("\nRemoving configuration...")
    remove_config()
    
    # Remove startup entry
    print("\nRemoving startup entry...")
    remove_startup_entry()
    
    # Inform about manual removal
    print("\nTo complete the uninstallation, please:")
    print("1. Delete the DogeDictate directory")
    print("2. Remove any shortcuts from your desktop or start menu")
    
    print("\nUninstallation completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 