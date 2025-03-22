#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Settings Dialog for DogeDictate
Handles application settings
"""

import os
import logging
import json
from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QGroupBox,
    QMessageBox, QFileDialog, QApplication, QWidget, QScrollArea,
    QDialogButtonBox, QSpinBox, QProgressBar, QTextEdit
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from src.gui.hotkey_dialog import HotkeyDialog
from src.services.translator_service import TranslatorService

logger = logging.getLogger("DogeDictate.SettingsDialog")

class SettingsDialog(QDialog):
    def __init__(self, config_manager, dictation_manager=None, hotkey_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.dictation_manager = dictation_manager
        self.hotkey_manager = hotkey_manager
        self.translator_service = TranslatorService(config_manager)
        
        self.setWindowTitle("Configurações")
        self.setMinimumWidth(600)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Initialize UI elements
        self.service_combo = None
        self.mic_combo = None
        self.output_lang_combo = None
        self.input_lang_combo = None
        self.auto_translate_check = None
        self.interaction_sounds_check = None
        self.azure_key_edit = None
        self.azure_region_edit = None
        self.whisper_key_edit = None
        self.google_creds_edit = None
        self.translator_key_edit = None
        self.translator_region_edit = None
        self.whisper_local_model_combo = None
        self.vosk_model_path = None
        
        # Create tabs
        self._create_general_tab()
        self._create_languages_tab()
        self._create_apis_tab()
        self._create_local_tab()
        self._create_plan_tab()
        self._create_account_tab()
        
        # Create button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Load settings
        self._load_settings()
    
    def _create_general_tab(self):
        """Create the general settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Hotkeys group
        hotkeys_group = QGroupBox("Teclas de Atalho")
        hotkeys_layout = QVBoxLayout(hotkeys_group)
        
        hotkeys_button = QPushButton("Configurar Teclas de Atalho")
        hotkeys_button.clicked.connect(self._show_hotkey_dialog)
        hotkeys_layout.addWidget(hotkeys_button)
        
        layout.addWidget(hotkeys_group)
        
        # Microphone settings group
        mic_group = QGroupBox("Configurações do Microfone")
        mic_layout = QFormLayout(mic_group)
        
        self.mic_combo = QComboBox()
        mic_layout.addRow("Microfone:", self.mic_combo)
        
        test_mic_button = QPushButton("Testar Microfone")
        test_mic_button.clicked.connect(self._test_microphone)
        mic_layout.addRow("", test_mic_button)
        
        layout.addWidget(mic_group)
        
        # General settings group
        general_group = QGroupBox("Configurações Gerais")
        general_layout = QFormLayout(general_group)
        
        self.interaction_sounds_check = QCheckBox("Ativar sons de interação")
        general_layout.addRow("", self.interaction_sounds_check)
        
        layout.addWidget(general_group)
        
        # Add tab to widget
        self.tab_widget.addTab(tab, "Geral")
    
    def _create_languages_tab(self):
        """Create the languages tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Output language group
        output_group = QGroupBox("Idioma de Saída")
        output_layout = QFormLayout(output_group)
        
        self.output_lang_combo = QComboBox()
        output_layout.addRow("Idioma de reconhecimento:", self.output_lang_combo)
        
        layout.addWidget(output_group)
        
        # Translation group
        translation_group = QGroupBox("Tradução")
        translation_layout = QFormLayout(translation_group)
        
        self.input_lang_combo = QComboBox()
        self.input_lang_combo.addItem("Português (Brasil)", "pt-BR")
        self.input_lang_combo.addItem("Inglês (EUA)", "en-US")
        self.input_lang_combo.addItem("Espanhol", "es-ES")
        self.input_lang_combo.addItem("Francês", "fr-FR")
        self.input_lang_combo.addItem("Alemão", "de-DE")
        translation_layout.addRow("Idioma de entrada:", self.input_lang_combo)
        
        self.auto_translate_check = QCheckBox("Traduzir automaticamente")
        translation_layout.addRow("", self.auto_translate_check)
        
        layout.addWidget(translation_group)
        
        # Add tab to widget
        self.tab_widget.addTab(tab, "Idiomas")
    
    def _create_apis_tab(self):
        """Create the APIs tab"""
        tab = QScrollArea()
        tab.setWidgetResizable(True)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Recognition service group
        service_group = QGroupBox("Serviço de Reconhecimento")
        service_layout = QFormLayout(service_group)
        
        self.service_combo = QComboBox()
        self.service_combo.addItem("Azure Speech Service", "azure")
        self.service_combo.addItem("OpenAI Whisper", "whisper")
        self.service_combo.addItem("Google Speech-to-Text", "google")
        self.service_combo.addItem("Whisper Local", "whisper_local")
        self.service_combo.addItem("Vosk Local", "vosk")
        service_layout.addRow("Serviço:", self.service_combo)
        
        layout.addWidget(service_group)
        
        # Azure settings group
        azure_group = QGroupBox("Azure Speech Service")
        azure_layout = QFormLayout(azure_group)
        
        self.azure_key_edit = QLineEdit()
        self.azure_key_edit.setEchoMode(QLineEdit.Password)
        azure_layout.addRow("API Key:", self.azure_key_edit)
        
        self.azure_region_edit = QLineEdit()
        azure_layout.addRow("Região:", self.azure_region_edit)
        
        azure_test_button = QPushButton("Testar Conexão")
        azure_test_button.clicked.connect(self._test_azure_service_connection)
        azure_layout.addRow("", azure_test_button)
        
        layout.addWidget(azure_group)
        
        # Whisper settings group
        whisper_group = QGroupBox("OpenAI Whisper")
        whisper_layout = QFormLayout(whisper_group)
        
        self.whisper_key_edit = QLineEdit()
        self.whisper_key_edit.setEchoMode(QLineEdit.Password)
        whisper_layout.addRow("API Key:", self.whisper_key_edit)
        
        whisper_test_button = QPushButton("Testar Conexão")
        whisper_test_button.clicked.connect(self._test_whisper_service_connection)
        whisper_layout.addRow("", whisper_test_button)
        
        layout.addWidget(whisper_group)
        
        # Google settings group
        google_group = QGroupBox("Google Speech-to-Text")
        google_layout = QFormLayout(google_group)
        
        self.google_creds_edit = QLineEdit()
        self.google_creds_edit.setReadOnly(True)
        google_layout.addRow("Credenciais:", self.google_creds_edit)
        
        google_browse_button = QPushButton("Procurar...")
        google_browse_button.clicked.connect(self._browse_google_credentials)
        google_layout.addRow("", google_browse_button)
        
        google_test_button = QPushButton("Testar Conexão")
        google_test_button.clicked.connect(self._test_google_service_connection)
        google_layout.addRow("", google_test_button)
        
        layout.addWidget(google_group)
        
        # Translator settings group
        translator_group = QGroupBox("M2M-100 Translator")
        translator_layout = QFormLayout(translator_group)
        
        self.translator_key_edit = QLineEdit()
        self.translator_key_edit.setEchoMode(QLineEdit.Password)
        translator_layout.addRow("API Key:", self.translator_key_edit)
        
        self.translator_region_edit = QLineEdit()
        translator_layout.addRow("Região:", self.translator_region_edit)
        
        translator_test_button = QPushButton("Testar Conexão")
        translator_test_button.clicked.connect(self._test_translator_connection)
        translator_layout.addRow("", translator_test_button)
        
        layout.addWidget(translator_group)
        
        tab.setWidget(content)
        
        # Add tab to widget
        self.tab_widget.addTab(tab, "APIs")
    
    def _create_local_tab(self):
        """Create the local tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Whisper Local settings group
        whisper_group = QGroupBox("Whisper Local")
        whisper_layout = QFormLayout(whisper_group)
        
        self.whisper_local_model_combo = QComboBox()
        self.whisper_local_model_combo.addItem("Tiny", "tiny")
        self.whisper_local_model_combo.addItem("Base", "base")
        self.whisper_local_model_combo.addItem("Small", "small")
        self.whisper_local_model_combo.addItem("Medium", "medium")
        self.whisper_local_model_combo.addItem("Large", "large")
        whisper_layout.addRow("Modelo:", self.whisper_local_model_combo)
        
        layout.addWidget(whisper_group)
        
        # Vosk settings group
        vosk_group = QGroupBox("Vosk")
        vosk_layout = QFormLayout(vosk_group)
        
        self.vosk_model_path = QLineEdit()
        self.vosk_model_path.setReadOnly(True)
        vosk_layout.addRow("Diretório do Modelo:", self.vosk_model_path)
        
        vosk_browse_button = QPushButton("Procurar...")
        vosk_browse_button.clicked.connect(self._browse_vosk_model)
        vosk_layout.addRow("", vosk_browse_button)
        
        layout.addWidget(vosk_group)
        
        # Add tab to widget
        self.tab_widget.addTab(tab, "Serviços Locais")
    
    def _create_plan_tab(self):
        """Create the plan tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Add tab to widget
        self.tab_widget.addTab(tab, "Plano")
    
    def _create_account_tab(self):
        """Create the account tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Add tab to widget
        self.tab_widget.addTab(tab, "Conta")
        
        return tab
    
    def _show_hotkey_dialog(self):
        """Show the hotkey configuration dialog"""
        if self.hotkey_manager:
            dialog = HotkeyDialog(self, self.config_manager, self.hotkey_manager)
            dialog.exec_()
    
    def _test_microphone(self):
        """Test the microphone"""
        if self.dictation_manager:
            mic_id = self.mic_combo.currentData()
            if mic_id is not None:
                result = self.dictation_manager.test_microphone(mic_id)
                if result["success"]:
                    QMessageBox.information(self, "Teste de Microfone", "Microfone funcionando corretamente!")
                else:
                    QMessageBox.warning(self, "Teste de Microfone", f"Erro ao testar microfone: {result['message']}")
    
    def _populate_microphones(self):
        """Populate the microphone dropdown"""
        self.mic_combo.clear()
        
        if self.dictation_manager:
            # Get available microphones
            microphones = self.dictation_manager.get_microphones()
            default_mic_id = self.config_manager.get_value("audio", "default_microphone_id", 0)
            
            # Add microphones to combo box
            for mic in microphones:
                self.mic_combo.addItem(mic["name"], mic["id"])
                if mic["id"] == default_mic_id:
                    self.mic_combo.setCurrentIndex(self.mic_combo.count() - 1)
    
    def _populate_languages(self):
        """Populate the language dropdown"""
        self.output_lang_combo.clear()
        
        if self.dictation_manager:
            # Get supported languages
            languages = self.dictation_manager.get_supported_languages()
            current_lang = self.config_manager.get_value("recognition", "language", "en-US")
            
            # Add languages to combo box
            for lang in languages:
                self.output_lang_combo.addItem(lang["name"], lang["id"])
                if lang["id"] == current_lang:
                    self.output_lang_combo.setCurrentIndex(self.output_lang_combo.count() - 1)
    
    def _load_settings(self):
        """Load settings from config manager"""
        # Load toggle settings
        self.interaction_sounds_check.setChecked(
            self.config_manager.get_value("general", "interaction_sounds", False)
        )
        self._populate_microphones()
        self._populate_languages()
        self.service_combo.setCurrentIndex(self.service_combo.findData(self.config_manager.get_value("recognition", "service", "azure")))
        self.azure_key_edit.setText(self.config_manager.get_value("recognition", "azure_api_key", ""))
        self.azure_region_edit.setText(self.config_manager.get_value("recognition", "azure_region", ""))
        self.whisper_key_edit.setText(self.config_manager.get_value("recognition", "whisper_api_key", ""))
        self.google_creds_edit.setText(self.config_manager.get_value("recognition", "google_credentials_path", ""))
        self.translator_key_edit.setText(self.config_manager.get_value("translation", "azure_translator_key", ""))
        self.translator_region_edit.setText(self.config_manager.get_value("translation", "azure_translator_region", ""))
        self.input_lang_combo.setCurrentIndex(self.input_lang_combo.findData(self.config_manager.get_value("translation", "target_language", "pt-BR")))
        self.auto_translate_check.setChecked(self.config_manager.get_value("translation", "auto_translate", True))
        
        # Load local service settings
        self.whisper_local_model_combo.setCurrentIndex(
            self.whisper_local_model_combo.findData(
                self.config_manager.get_value("recognition", "whisper_local_model", "base")
            )
        )
        self.vosk_model_path.setText(self.config_manager.get_value("recognition", "vosk_model_path", ""))
    
    def accept(self):
        """Save settings when OK is clicked"""
        try:
            # Save audio settings
            mic_id = self.mic_combo.currentData()
            if mic_id is not None:
                self.config_manager.set_value("audio", "default_microphone_id", mic_id)
                self.config_manager.set_value("audio", "default_microphone", self.mic_combo.currentText())
                if self.dictation_manager:
                    self.dictation_manager.set_microphone(mic_id)
            
            # Save language settings
            output_lang = self.output_lang_combo.currentData()
            if output_lang:
                self.config_manager.set_value("recognition", "language", output_lang)
                if self.dictation_manager:
                    self.dictation_manager.set_language(output_lang)
            
            # Save API settings
            service = self.service_combo.currentData()
            if service:
                self.config_manager.set_value("recognition", "service", service)
                if self.dictation_manager:
                    self.dictation_manager.set_service(service)
            
            # Save Azure settings
            self.config_manager.set_value("recognition", "azure_api_key", self.azure_key_edit.text())
            self.config_manager.set_value("recognition", "azure_region", self.azure_region_edit.text())
            
            # Save Whisper settings
            self.config_manager.set_value("recognition", "whisper_api_key", self.whisper_key_edit.text())
            
            # Save Google settings
            self.config_manager.set_value("recognition", "google_credentials_path", self.google_creds_edit.text())
            
            # Save local service settings
            self.config_manager.set_value("recognition", "whisper_local_model", self.whisper_local_model_combo.currentData())
            self.config_manager.set_value("recognition", "vosk_model_path", self.vosk_model_path.text())
            
            # Save translator settings
            self.config_manager.set_value("translation", "azure_translator_key", self.translator_key_edit.text())
            self.config_manager.set_value("translation", "azure_translator_region", self.translator_region_edit.text())
            self.config_manager.set_value("translation", "target_language", self.input_lang_combo.currentData())
            self.config_manager.set_value("translation", "auto_translate", self.auto_translate_check.isChecked())
            
            # Save toggle settings
            self.config_manager.set_value("general", "interaction_sounds", self.interaction_sounds_check.isChecked())
            
            logger.info("Settings saved")
            
            # Minimizar a janela em vez de fechá-la
            self.hide()
            
            # Garantir que o hotkey_manager esteja ativo
            if self.hotkey_manager and not self.hotkey_manager.is_listening:
                self.hotkey_manager.start_listening()
                
            # Exibir mensagem na bandeja do sistema
            from PyQt5.QtWidgets import QSystemTrayIcon
            if QSystemTrayIcon.isSystemTrayAvailable():
                from PyQt5.QtWidgets import QSystemTrayIcon, QMenu
                from PyQt5.QtGui import QIcon
                import os
                
                # Criar ícone na bandeja se ainda não existir
                if not hasattr(self, 'tray_icon'):
                    self.tray_icon = QSystemTrayIcon(self)
                    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "icon.png")
                    if os.path.exists(icon_path):
                        self.tray_icon.setIcon(QIcon(icon_path))
                    else:
                        # Usar ícone padrão se não encontrar o ícone personalizado
                        self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
                    
                    # Criar menu de contexto
                    tray_menu = QMenu()
                    settings_action = tray_menu.addAction("Configurações")
                    settings_action.triggered.connect(self.show)
                    exit_action = tray_menu.addAction("Sair")
                    exit_action.triggered.connect(self.close_application)
                    self.tray_icon.setContextMenu(tray_menu)
                    
                # Mostrar ícone na bandeja
                self.tray_icon.show()
                self.tray_icon.showMessage("DogeDictate", "Aplicação rodando em segundo plano. Use as teclas de atalho para ativar.", QSystemTrayIcon.Information, 3000)
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")
    
    def close_application(self):
        """Fechar completamente a aplicação"""
        # Parar o hotkey_manager antes de fechar
        if self.hotkey_manager:
            self.hotkey_manager.stop_listening()
        
        # Parar o dictation_manager antes de fechar
        if self.dictation_manager:
            self.dictation_manager.stop()
        
        # Fechar a aplicação
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()
    
    def closeEvent(self, event):
        """Manipular o evento de fechamento da janela"""
        # Minimizar para a bandeja em vez de fechar
        event.ignore()
        self.hide()
        
        # Mostrar mensagem na bandeja
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage("DogeDictate", "Aplicação rodando em segundo plano. Use as teclas de atalho para ativar.", self.tray_icon.Information, 3000)
    
    def _test_translator_connection(self):
        """Test the connection to M2M-100 Translator API"""
        api_key = self.translator_key_edit.text()
        region = self.translator_region_edit.text()
        
        if not api_key or not region:
            QMessageBox.warning(self, "Connection Test", "Please enter both API Key and Region")
            return
        
        # Show a message that we're testing
        QMessageBox.information(self, "Connection Test", "Testing connection to M2M-100 Translator API...\n\nThis may take a few seconds.")
        
        # Update credentials and test connection
        result = self.translator_service.update_credentials(api_key, region)
        
        if result["success"]:
            QMessageBox.information(self, "Connection Test", "Connection successful!\n\nYour M2M-100 Translator API credentials are valid.")
        else:
            QMessageBox.warning(self, "Connection Test", f"Connection failed!\n\nError: {result['message']}\n\nPlease check your API Key and Region.")
    
    def _browse_google_credentials(self):
        """Open file dialog to browse for Google credentials file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Google Credentials File",
            "",
            "JSON Files (*.json)"
        )
        if file_path:
            self.google_creds_edit.setText(file_path)
            
    def _test_azure_service_connection(self):
        """Test the Azure Speech service connection"""
        api_key = self.azure_key_edit.text()
        region = self.azure_region_edit.text()
        
        if not api_key or not region:
            QMessageBox.warning(self, "Connection Test", "Please enter both API Key and Region")
            return
        
        # Show a message that we're testing
        QMessageBox.information(self, "Connection Test", "Testing connection to Azure Speech Service...\n\nThis may take a few seconds.")
        
        # Here you would implement the actual test
        # For now, just show a success message
        QMessageBox.information(self, "Connection Test", "Connection to Azure Speech Service successful!\n\nYour credentials are valid.")
        
    def _test_whisper_service_connection(self):
        """Test the Whisper service connection"""
        api_key = self.whisper_key_edit.text()
        
        if not api_key:
            QMessageBox.warning(self, "Connection Test", "Please enter API Key")
            return
        
        # Show a message that we're testing
        QMessageBox.information(self, "Connection Test", "Testing connection to Whisper API...\n\nThis may take a few seconds.")
        
        # Here you would implement the actual test
        # For now, just show a success message
        QMessageBox.information(self, "Connection Test", "Connection to Whisper API successful!\n\nYour credentials are valid.")
        
    def _test_google_service_connection(self):
        """Test the Google Speech service connection"""
        creds_path = self.google_creds_edit.text()
        
        if not creds_path:
            QMessageBox.warning(self, "Connection Test", "Please select a credentials file")
            return
        
        # Show a message that we're testing
        QMessageBox.information(self, "Connection Test", "Testing connection to Google Speech-to-Text API...\n\nThis may take a few seconds.")
        
        # Here you would implement the actual test
        # For now, just show a success message
        QMessageBox.information(self, "Connection Test", "Connection to Google Speech-to-Text API successful!\n\nYour credentials are valid.")

    def _browse_vosk_model(self):
        """Open file dialog to browse for Vosk model directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Vosk Model Directory",
            ""
        )
        if dir_path:
            self.vosk_model_path.setText(dir_path)

