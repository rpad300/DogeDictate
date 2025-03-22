#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Language Selection Dialog for DogeDictate
Allows the user to select the interface language during installation
"""

import os
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QWidget, QApplication
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt

logger = logging.getLogger("DogeDictate.LanguageDialog")

class LanguageDialog(QDialog):
    """Dialog for selecting the interface language"""
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "pt": "Português",
        "fr": "Français",
        "es": "Español"
    }
    
    # Language flags
    LANGUAGE_FLAGS = {
        "en": "en.png",
        "pt": "pt.png",
        "fr": "fr.png",
        "es": "es.png"
    }
    
    def __init__(self, parent=None):
        """Initialize the language dialog"""
        super().__init__(parent)
        
        # Set dialog properties
        self.setWindowTitle("Select Language / Selecionar Idioma / Sélectionner la langue / Seleccionar idioma")
        self.setMinimumSize(400, 300)
        self.setModal(True)
        
        # Initialize UI
        self._init_ui()
        
        # Set default language
        self.selected_language = "en"
    
    def _init_ui(self):
        """Initialize the user interface"""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Add title and description
        title_label = QLabel("<h1>DogeDictate</h1>")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        description_label = QLabel("Please select your preferred language for the installation and application interface.")
        description_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(description_label)
        
        # Add language selection
        language_layout = QHBoxLayout()
        language_layout.setSpacing(10)
        
        language_label = QLabel("Language:")
        language_layout.addWidget(language_label)
        
        self.language_combo = QComboBox()
        self._populate_languages()
        language_layout.addWidget(self.language_combo)
        
        main_layout.addLayout(language_layout)
        
        # Add flag image
        self.flag_label = QLabel()
        self.flag_label.setAlignment(Qt.AlignCenter)
        self._update_flag("en")
        main_layout.addWidget(self.flag_label)
        
        # Add spacer
        main_layout.addStretch()
        
        # Add buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.setMinimumWidth(100)
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
    
    def _populate_languages(self):
        """Populate the language dropdown"""
        for code, name in self.SUPPORTED_LANGUAGES.items():
            self.language_combo.addItem(name, code)
    
    def _on_language_changed(self, index):
        """Handle language selection change"""
        language_code = self.language_combo.itemData(index)
        self.selected_language = language_code
        self._update_flag(language_code)
        self._update_translations(language_code)
    
    def _update_flag(self, language_code):
        """Update the flag image"""
        try:
            flag_file = self.LANGUAGE_FLAGS.get(language_code)
            if flag_file:
                # Try to find the flag image
                possible_paths = [
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "flags", flag_file),
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "resources", "flags", flag_file),
                    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "flags", flag_file)
                ]
                
                flag_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        flag_path = path
                        break
                
                if flag_path:
                    pixmap = QPixmap(flag_path)
                    self.flag_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.flag_label.setText(f"Flag for {language_code} not found")
            else:
                self.flag_label.clear()
        except Exception as e:
            logger.error(f"Error updating flag: {str(e)}")
            self.flag_label.clear()
    
    def _update_translations(self, language_code):
        """Update the UI translations based on the selected language"""
        translations = {
            "en": {
                "title": "Select Language",
                "description": "Please select your preferred language for the installation and application interface.",
                "language_label": "Language:",
                "ok": "OK",
                "cancel": "Cancel"
            },
            "pt": {
                "title": "Selecionar Idioma",
                "description": "Por favor, selecione o idioma preferido para a instalação e interface da aplicação.",
                "language_label": "Idioma:",
                "ok": "OK",
                "cancel": "Cancelar"
            },
            "fr": {
                "title": "Sélectionner la langue",
                "description": "Veuillez sélectionner votre langue préférée pour l'installation et l'interface de l'application.",
                "language_label": "Langue:",
                "ok": "OK",
                "cancel": "Annuler"
            },
            "es": {
                "title": "Seleccionar idioma",
                "description": "Por favor, seleccione su idioma preferido para la instalación y la interfaz de la aplicación.",
                "language_label": "Idioma:",
                "ok": "Aceptar",
                "cancel": "Cancelar"
            }
        }
        
        # Get translations for the selected language
        trans = translations.get(language_code, translations["en"])
        
        # Update UI elements
        self.setWindowTitle(trans["title"])
        self.findChild(QLabel, "", Qt.FindChildrenRecursively).setText(trans["description"])
        self.findChild(QLabel, "", Qt.FindChildrenRecursively).setText(trans["language_label"])
        self.ok_button.setText(trans["ok"])
        self.cancel_button.setText(trans["cancel"])
    
    def get_selected_language(self):
        """Get the selected language code"""
        return self.selected_language

def select_language():
    """Show the language selection dialog and return the selected language"""
    dialog = LanguageDialog()
    result = dialog.exec_()
    
    if result == QDialog.Accepted:
        return dialog.get_selected_language()
    else:
        return "en"  # Default to English if canceled

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    language = select_language()
    print(f"Selected language: {language}")
    sys.exit(0) 