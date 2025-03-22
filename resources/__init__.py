#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Resources module for DogeDictate
Handles access to resource files
"""

import os
import sys

def get_resource_path(*paths):
    """Get the path to a resource file"""
    # If we're running from a PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Get the path to the _MEIPASS directory
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        # Get the path to the resources directory
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
    
    # Join the base path with the requested paths
    return os.path.join(base_path, *paths)

# Get the path to the resources directory
RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(RESOURCES_DIR, "icons")
SOUNDS_DIR = os.path.join(RESOURCES_DIR, "sounds")

def get_resource_path(resource_type, filename):
    """
    Get the absolute path to a resource file
    
    Args:
        resource_type (str): Type of resource (icons, sounds, etc.)
        filename (str): Name of the resource file
        
    Returns:
        str: Absolute path to the resource file
    """
    if resource_type == "icons":
        return os.path.join(ICONS_DIR, filename)
    elif resource_type == "sounds":
        return os.path.join(SOUNDS_DIR, filename)
    else:
        return os.path.join(RESOURCES_DIR, filename) 