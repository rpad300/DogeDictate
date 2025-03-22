#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Style definitions for DogeDictate
"""

# Main color palette
PRIMARY_COLOR = "#4A86E8"  # Blue
SECONDARY_COLOR = "#34A853"  # Green
ACCENT_COLOR = "#FBBC05"  # Yellow
ERROR_COLOR = "#EA4335"  # Red
BACKGROUND_COLOR = "#F8F9FA"  # Light gray
TEXT_COLOR = "#202124"  # Dark gray
LIGHT_TEXT_COLOR = "#5F6368"  # Medium gray

# Style sheets
MAIN_WINDOW_STYLE = f"""
QMainWindow, QDialog {{
    background-color: {BACKGROUND_COLOR};
}}

QTabWidget::pane {{
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    background-color: white;
    padding: 5px;
}}

QTabBar::tab {{
    background-color: #e0e0e0;
    border: 1px solid #c0c0c0;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 8px 12px;
    margin-right: 2px;
    color: {LIGHT_TEXT_COLOR};
}}

QTabBar::tab:selected {{
    background-color: white;
    border-bottom: none;
    color: {PRIMARY_COLOR};
    font-weight: bold;
}}

QGroupBox {{
    font-weight: bold;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    margin-top: 1.5ex;
    padding: 10px;
    background-color: white;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: {PRIMARY_COLOR};
}}

QPushButton {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: #3B78DE;
}}

QPushButton:pressed {{
    background-color: #2D5BB9;
}}

QPushButton:disabled {{
    background-color: #A4A4A4;
}}

QLineEdit {{
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 8px;
    background-color: white;
}}

QComboBox {{
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 8px;
    background-color: white;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: url(resources/icons/dropdown.png);
    width: 12px;
    height: 12px;
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
}}

QCheckBox::indicator:unchecked {{
    border: 1px solid #d0d0d0;
    border-radius: 3px;
    background-color: white;
}}

QCheckBox::indicator:checked {{
    border: 1px solid {SECONDARY_COLOR};
    border-radius: 3px;
    background-color: {SECONDARY_COLOR};
}}

QProgressBar {{
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    text-align: center;
    background-color: white;
    height: 12px;
}}

QProgressBar::chunk {{
    background-color: {SECONDARY_COLOR};
    border-radius: 3px;
}}

QLabel {{
    color: {TEXT_COLOR};
}}

QLabel[title="true"] {{
    font-size: 16px;
    font-weight: bold;
    color: {PRIMARY_COLOR};
}}

QLabel[subtitle="true"] {{
    font-size: 14px;
    color: {LIGHT_TEXT_COLOR};
}}
"""

FLOATING_BAR_STYLE = f"""
QWidget {{
    background-color: rgba(50, 50, 50, 220);
    border-radius: 6px;
}}

QLabel {{
    color: white;
    font-weight: bold;
}}

QPushButton {{
    background-color: transparent;
    color: white;
    border: 1px solid white;
    border-radius: 3px;
    padding: 3px 8px;
}}

QPushButton:hover {{
    background-color: rgba(255, 255, 255, 30);
}}

QPushButton:pressed {{
    background-color: rgba(255, 255, 255, 50);
}}

QPushButton#closeButton {{
    border: none;
    font-weight: bold;
    font-size: 14px;
}}
"""

HOTKEY_DIALOG_STYLE = f"""
QDialog {{
    background-color: {BACKGROUND_COLOR};
}}

QLabel[heading="true"] {{
    font-size: 18px;
    font-weight: bold;
    color: {PRIMARY_COLOR};
}}

QLabel[description="true"] {{
    font-size: 14px;
    color: {LIGHT_TEXT_COLOR};
    margin-bottom: 10px;
}}

QLineEdit {{
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 8px;
    background-color: white;
    font-weight: bold;
}}

QPushButton#resetButton {{
    background-color: {LIGHT_TEXT_COLOR};
}}

QPushButton#saveButton {{
    background-color: {SECONDARY_COLOR};
}}
"""

# Function to create a toggle button style
def create_toggle_style(enabled_color=SECONDARY_COLOR):
    return f"""
        QCheckBox {{
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 40px;
            height: 20px;
            border-radius: 10px;
        }}
        
        QCheckBox::indicator:unchecked {{
            background-color: #d0d0d0;
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {enabled_color};
        }}
    """ 