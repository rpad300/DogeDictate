#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a simple app icon for DogeDictate
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

def generate_icon(output_path, size=256, bg_color=(52, 152, 219), text_color=(255, 255, 255)):
    """
    Generate a simple app icon with the letter 'D'
    
    Args:
        output_path (str): Path to save the icon
        size (int): Icon size in pixels
        bg_color (tuple): Background color (R, G, B)
        text_color (tuple): Text color (R, G, B)
    """
    # Create a new image with the specified background color
    img = Image.new('RGB', (size, size), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, or use default
    try:
        # Try to load a nice font, fall back to default
        font_size = int(size * 0.6)
        try:
            if os.name == 'nt':  # Windows
                font = ImageFont.truetype("arial.ttf", font_size)
            else:  # macOS/Linux
                font = ImageFont.truetype("Arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    except:
        font = None
    
    # Draw the letter 'D' in the center
    text = "D"
    
    # Get text size
    if hasattr(draw, 'textsize'):
        text_width, text_height = draw.textsize(text, font=font)
    else:
        # For newer Pillow versions
        try:
            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:4]
        except:
            text_width, text_height = size // 2, size // 2
    
    # Calculate position to center the text
    position = ((size - text_width) // 2, (size - text_height) // 2)
    
    # Draw the text
    draw.text(position, text, fill=text_color, font=font)
    
    # Save the image
    img.save(output_path)
    print(f"Icon generated and saved to: {output_path}")

if __name__ == "__main__":
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Generate PNG icon
    png_path = os.path.join(script_dir, "app_icon.png")
    generate_icon(png_path)
    
    # Generate ICO file for Windows
    try:
        from PIL import Image
        img = Image.open(png_path)
        ico_path = os.path.join(script_dir, "app_icon.ico")
        img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
        print(f"ICO file generated and saved to: {ico_path}")
    except Exception as e:
        print(f"Failed to generate ICO file: {str(e)}")
    
    print("Icon generation completed!") 