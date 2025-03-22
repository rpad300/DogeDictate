#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Styles for DogeDictate GUI
"""

class Colors:
    """Color constants for the application"""
    PRIMARY = "#4a86e8"
    SECONDARY = "#6aa84f"
    BACKGROUND = "#2d2d2d"
    FOREGROUND = "#ffffff"
    BORDER = "#444444"
    HOVER = "#3d3d3d"
    ACTIVE = "#555555"
    ERROR = "#ff0000"
    WARNING = "#ffcc00"
    SUCCESS = "#00cc00"
    DISABLED = "#888888"

def create_toggle_style():
    """Create style for toggle switches"""
    return """
        QCheckBox {
            spacing: 5px;
        }
        
        QCheckBox::indicator {
            width: 36px;
            height: 18px;
            border-radius: 9px;
            background-color: #888888;
        }
        
        QCheckBox::indicator:checked {
            background-color: """ + Colors.PRIMARY + """;
        }
        
        QCheckBox::indicator:unchecked {
            background-color: #888888;
        }
    """

MAIN_WINDOW_STYLE = """
    QMainWindow {
        background-color: """ + Colors.BACKGROUND + """;
        color: """ + Colors.FOREGROUND + """;
    }
    
    QTabWidget {
        background-color: """ + Colors.BACKGROUND + """;
    }
    
    QTabWidget::pane {
        border: 1px solid """ + Colors.BORDER + """;
        background-color: """ + Colors.BACKGROUND + """;
    }
    
    QTabBar::tab {
        background-color: """ + Colors.BACKGROUND + """;
        color: """ + Colors.FOREGROUND + """;
        padding: 8px 12px;
        border: 1px solid """ + Colors.BORDER + """;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    
    QTabBar::tab:selected {
        background-color: """ + Colors.ACTIVE + """;
    }
    
    QTabBar::tab:hover:!selected {
        background-color: """ + Colors.HOVER + """;
    }
    
    QPushButton {
        background-color: """ + Colors.PRIMARY + """;
        color: """ + Colors.FOREGROUND + """;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
    }
    
    QPushButton:hover {
        background-color: #5a96f8;
    }
    
    QPushButton:pressed {
        background-color: #3a76d8;
    }
    
    QPushButton:disabled {
        background-color: """ + Colors.DISABLED + """;
    }
    
    QLineEdit, QComboBox, QSpinBox {
        background-color: #3d3d3d;
        color: """ + Colors.FOREGROUND + """;
        border: 1px solid """ + Colors.BORDER + """;
        padding: 5px;
        border-radius: 4px;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    
    QComboBox::down-arrow {
        width: 12px;
        height: 12px;
    }
    
    QLabel {
        color: """ + Colors.FOREGROUND + """;
    }
    
    QScrollArea, QScrollBar {
        background-color: """ + Colors.BACKGROUND + """;
        color: """ + Colors.FOREGROUND + """;
    }
    
    QGroupBox {
        border: 1px solid """ + Colors.BORDER + """;
        border-radius: 4px;
        margin-top: 10px;
        padding-top: 10px;
        color: """ + Colors.FOREGROUND + """;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 5px;
    }
"""

FLOATING_BAR_STYLE = """
    QWidget {
        background-color: """ + Colors.BACKGROUND + """;
        color: """ + Colors.FOREGROUND + """;
        border: 1px solid """ + Colors.BORDER + """;
        border-radius: 5px;
    }
    
    QPushButton {
        background-color: transparent;
        border: none;
        padding: 5px;
        border-radius: 3px;
    }
    
    QPushButton:hover {
        background-color: """ + Colors.HOVER + """;
    }
    
    QPushButton:pressed {
        background-color: """ + Colors.ACTIVE + """;
    }
    
    QProgressBar {
        border: 1px solid """ + Colors.BORDER + """;
        border-radius: 3px;
        background-color: #3d3d3d;
        text-align: center;
    }
    
    QProgressBar::chunk {
        background-color: """ + Colors.PRIMARY + """;
        width: 10px;
        margin: 0px;
    }
    
    QLabel {
        color: """ + Colors.FOREGROUND + """;
    }
""" 