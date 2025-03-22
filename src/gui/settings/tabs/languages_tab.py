"""
Aba de configuração para idiomas.
"""

from PyQt5.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QCheckBox, QLabel
)
import logging

from .base_tab import BaseTab
from src.i18n import get_instance as get_i18n, _

logger = logging.getLogger("DogeDictate.SettingsDialog.LanguagesTab")

class LanguagesTab(BaseTab):
    """Aba de configuração para idiomas"""
    
    def __init__(self, config_manager, dictation_manager=None, parent=None):
        super().__init__(config_manager, parent)
        self.dictation_manager = dictation_manager
        
        # Recognition language group (previously output language)
        self._create_recognition_group()
        
        # Translation group
        self._create_translation_group()
    
    def _create_recognition_group(self):
        """Criar grupo de configurações de idioma de reconhecimento"""
        recognition_group = QGroupBox(_("recognition_language_group", "Recognition Language"))
        recognition_layout = QFormLayout(recognition_group)
        
        # Adicionar descrição
        description_label = QLabel(_("recognition_language_description", 
            "Select the language that will be used to recognize your speech from the microphone."))
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #666; font-style: italic;")
        recognition_layout.addRow(description_label)
        
        self.recognition_lang_combo = QComboBox()
        recognition_layout.addRow(_("recognition_language", "Recognition Language:"), self.recognition_lang_combo)
        
        self.layout.addWidget(recognition_group)
    
    def _create_translation_group(self):
        """Criar grupo de configurações de tradução"""
        translation_group = QGroupBox(_("translation_group", "Translation"))
        translation_layout = QFormLayout(translation_group)
        
        # Adicionar descrição
        description_label = QLabel(_("translation_description", 
            "Configure automatic translation of recognized speech to another language."))
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #666; font-style: italic;")
        translation_layout.addRow(description_label)
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItem("Português (Brasil)", "pt-BR")
        self.target_lang_combo.addItem("Inglês (EUA)", "en-US")
        self.target_lang_combo.addItem("Espanhol", "es-ES")
        self.target_lang_combo.addItem("Francês", "fr-FR")
        self.target_lang_combo.addItem("Alemão", "de-DE")
        translation_layout.addRow(_("target_language", "Target Language:"), self.target_lang_combo)
        
        self.auto_translate_check = QCheckBox(_("auto_translate", "Translate automatically"))
        translation_layout.addRow("", self.auto_translate_check)
        
        self.layout.addWidget(translation_group)
    
    def _populate_languages(self):
        """Preencher o combo de idiomas de reconhecimento"""
        self.recognition_lang_combo.clear()
        
        if self.dictation_manager:
            # Get supported languages
            languages = self.dictation_manager.get_supported_languages()
            current_lang = self.config_manager.get_value("recognition", "language", "en-US")
            
            # Add languages to combo box
            for lang in languages:
                self.recognition_lang_combo.addItem(lang["name"], lang["id"])
                if lang["id"] == current_lang:
                    self.recognition_lang_combo.setCurrentIndex(self.recognition_lang_combo.count() - 1)
    
    def load_settings(self):
        """Carregar configurações do config_manager"""
        # Populate languages
        self._populate_languages()
        
        # Load translation settings
        target_language = self.config_manager.get_value("translation", "target_language", "en-US")
        index = self.target_lang_combo.findData(target_language)
        if index >= 0:
            self.target_lang_combo.setCurrentIndex(index)
        
        self.auto_translate_check.setChecked(
            self.config_manager.get_value("translation", "auto_translate", True)
        )
    
    def save_settings(self):
        """Salvar configurações no config_manager"""
        # Save language settings
        recognition_lang = self.recognition_lang_combo.currentData()
        if recognition_lang:
            self.config_manager.set_value("recognition", "language", recognition_lang)
            if self.dictation_manager:
                self.dictation_manager.set_language(recognition_lang)
        
        # Save translation settings
        self.config_manager.set_value(
            "translation", 
            "target_language", 
            self.target_lang_combo.currentData()
        )
        self.config_manager.set_value(
            "translation", 
            "auto_translate", 
            self.auto_translate_check.isChecked()
        ) 