#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Basic style definitions for DogeDictate
"""

# Basic colors
class Colors:
    PRIMARY = "#6750A4"
    SECONDARY = "#625B71"
    BACKGROUND = "#FFFFFF"
    TEXT = "#1C1B1F"
    ERROR = "#B3261E"

# Basic window style
MAIN_WINDOW_STYLE = """
QMainWindow {
    background-color: #FFFFFF;
}

QWidget#sidebar {
    background-color: #F0F0F0;
    min-width: 200px;
    max-width: 200px;
    padding: 10px;
}

QLabel {
    color: #000000;
    min-height: 20px;
}

QPushButton {
    background-color: #E0E0E0;
    border: 1px solid #CCCCCC;
    padding: 8px;
    min-width: 80px;
    min-height: 30px;
    text-align: left;
}

QPushButton:hover {
    background-color: #D0D0D0;
}

QPushButton[type="nav-button"] {
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 8px 16px;
    width: 100%;
}

QPushButton[type="nav-button"]:hover {
    background-color: #E0E0E0;
}

QPushButton[type="nav-button"]:checked {
    background-color: #D0D0D0;
    font-weight: bold;
}

QComboBox {
    padding: 5px 10px;
    border: 1px solid #CCCCCC;
    min-height: 30px;
    background-color: #FFFFFF;
    border-radius: 4px;
}

QComboBox:hover {
    border-color: #999999;
}

QComboBox:focus {
    border-color: #6750A4;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: url(resources/icons/dropdown.png);
    width: 12px;
    height: 12px;
}

QComboBox::down-arrow:on {
    top: 1px;
}

QComboBox QAbstractItemView {
    border: 1px solid #CCCCCC;
    background-color: #FFFFFF;
    selection-background-color: #F0F0F0;
    selection-color: #000000;
    padding: 4px;
}

QScrollBar:vertical {
    border: none;
    background: #F0F0F0;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #CCCCCC;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #999999;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background: #F0F0F0;
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #CCCCCC;
    min-width: 20px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background: #999999;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: none;
}

QLineEdit {
    padding: 5px;
    border: 1px solid #CCCCCC;
    min-height: 30px;
    background-color: #FFFFFF;
}

QGroupBox {
    margin-top: 20px;
    padding: 15px;
    font-weight: bold;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QTabWidget::pane {
    border: 1px solid #CCCCCC;
    padding: 10px;
    background-color: #FFFFFF;
}

QTabBar::tab {
    background-color: #E0E0E0;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-bottom: none;
}

QTabBar::tab:!selected {
    margin-top: 2px;
}

QWidget#content {
    padding: 20px;
    background-color: #FFFFFF;
}

QScrollArea {
    border: none;
    background-color: #FFFFFF;
}

QLabel[type="title"] {
    font-size: 24px;
    font-weight: bold;
    min-height: 30px;
}

QLabel[type="subtitle"] {
    font-size: 14px;
    color: #666666;
    min-height: 20px;
}

QLabel[type="description"] {
    color: #666666;
    font-size: 12px;
    margin-top: 2px;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #CCCCCC;
    border-radius: 3px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #4CAF50;
    border-color: #4CAF50;
}

QCheckBox::indicator:hover {
    border-color: #999999;
}
"""

# Basic floating bar style
FLOATING_BAR_STYLE = """
QWidget {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
}

QLabel {
    color: #000000;
    min-height: 20px;
}

QPushButton {
    background-color: #E0E0E0;
    border: 1px solid #CCCCCC;
    padding: 5px;
    min-width: 60px;
    min-height: 25px;
}

QPushButton:hover {
    background-color: #D0D0D0;
}

QProgressBar {
    border: 1px solid #CCCCCC;
    background-color: #FFFFFF;
    height: 6px;
}

QProgressBar::chunk {
    background-color: #4CAF50;
}
"""

def create_toggle_style():
    """Create style for toggle switches"""
    return """
    QCheckBox {
        spacing: 5px;
        min-height: 24px;
    }
    QCheckBox::indicator {
        width: 24px;
        height: 24px;
    }
    """ 