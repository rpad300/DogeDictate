#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a simple dropdown arrow icon
"""

import os
from PIL import Image, ImageDraw

def generate_dropdown_icon(output_path, size=12, color=(95, 99, 104)):
    """
    Generate a simple dropdown arrow icon
    
    Args:
        output_path (str): Path to save the icon
        size (int): Icon size in pixels
        color (tuple): Arrow color (R, G, B)
    """
    # Create a transparent image
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a triangle
    points = [(size//4, size//3), (size*3//4, size//3), (size//2, size*2//3)]
    draw.polygon(points, fill=color)
    
    # Save the image
    img.save(output_path)
    print(f"Dropdown icon generated and saved to: {output_path}")

if __name__ == "__main__":
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Generate dropdown icon
    generate_dropdown_icon(os.path.join(script_dir, "dropdown.png")) 