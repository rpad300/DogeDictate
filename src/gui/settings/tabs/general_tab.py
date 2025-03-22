"""
Aba de configuração geral.
"""

from PyQt5.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QCheckBox, QPushButton, QMessageBox,
    QRadioButton, QButtonGroup, QVBoxLayout, QHBoxLayout, QLabel
)
from PyQt5.QtCore import Qt
import logging

from .base_tab import BaseTab
from src.gui.hotkey_dialog import HotkeyDialog
from src.i18n import get_instance as get_i18n, _

logger = logging.getLogger("DogeDictate.SettingsDialog.GeneralTab")

class GeneralTab(BaseTab):
    """Aba de configuração geral"""
    
    def __init__(self, config_manager, dictation_manager=None, hotkey_manager=None, parent=None):
        super().__init__(config_manager, parent)
        self.dictation_manager = dictation_manager
        self.hotkey_manager = hotkey_manager
        
        # Hotkeys group
        self._create_hotkeys_group()
        
        # Service selection group
        self._create_service_selection_group()
        
        # Microphone settings group
        self._create_mic_group()
        
        # General settings group
        self._create_general_group()
    
    def _create_hotkeys_group(self):
        """Criar grupo de configurações de teclas de atalho"""
        hotkeys_group = QGroupBox(_("hotkeys_group", "Teclas de Atalho"))
        hotkeys_layout = QFormLayout(hotkeys_group)
        
        hotkeys_button = QPushButton(_("configure_hotkeys", "Configurar Teclas de Atalho"))
        hotkeys_button.clicked.connect(self._show_hotkey_dialog)
        hotkeys_layout.addRow("", hotkeys_button)
        
        self.layout.addWidget(hotkeys_group)
    
    def _create_service_selection_group(self):
        """Criar grupo de seleção de serviços"""
        service_group = QGroupBox("Seleção de Serviços")
        service_layout = QVBoxLayout(service_group)
        
        # Serviço de reconhecimento
        recognition_label = QLabel("<b>Serviço de Reconhecimento de Voz:</b>")
        service_layout.addWidget(recognition_label)
        
        # Opções de API
        api_layout = QHBoxLayout()
        
        self.recognition_api_group = QButtonGroup(self)
        
        self.azure_radio = QRadioButton("Azure")
        self.recognition_api_group.addButton(self.azure_radio, 1)
        api_layout.addWidget(self.azure_radio)
        
        self.whisper_radio = QRadioButton("Whisper API")
        self.recognition_api_group.addButton(self.whisper_radio, 2)
        api_layout.addWidget(self.whisper_radio)
        
        self.google_radio = QRadioButton("Google")
        self.recognition_api_group.addButton(self.google_radio, 3)
        api_layout.addWidget(self.google_radio)
        
        service_layout.addLayout(api_layout)
        
        # Opções locais
        local_layout = QHBoxLayout()
        
        self.whisper_local_radio = QRadioButton("Whisper Local")
        self.recognition_api_group.addButton(self.whisper_local_radio, 4)
        local_layout.addWidget(self.whisper_local_radio)
        
        service_layout.addLayout(local_layout)
        
        # Serviço de tradução
        translation_label = QLabel("<b>Serviço de Tradução:</b>")
        service_layout.addWidget(translation_label)
        
        # Opções de tradução
        translation_layout = QHBoxLayout()
        
        self.translation_api_group = QButtonGroup(self)
        
        self.azure_translator_radio = QRadioButton("Azure Translator")
        self.translation_api_group.addButton(self.azure_translator_radio, 1)
        translation_layout.addWidget(self.azure_translator_radio)
        
        self.m2m100_local_radio = QRadioButton("M2M-100 Local")
        self.translation_api_group.addButton(self.m2m100_local_radio, 2)
        translation_layout.addWidget(self.m2m100_local_radio)
        
        self.azure_openai_radio = QRadioButton("Azure OpenAI (GPT-4o)")
        self.translation_api_group.addButton(self.azure_openai_radio, 3)
        translation_layout.addWidget(self.azure_openai_radio)
        
        service_layout.addLayout(translation_layout)
        
        self.layout.addWidget(service_group)
    
    def _create_mic_group(self):
        """Criar grupo de configurações de microfone"""
        mic_group = QGroupBox("Configurações do Microfone")
        mic_layout = QFormLayout(mic_group)
        
        self.mic_combo = QComboBox()
        mic_layout.addRow("Microfone:", self.mic_combo)
        
        test_mic_button = QPushButton("Testar Microfone")
        test_mic_button.clicked.connect(self._test_microphone)
        mic_layout.addRow("", test_mic_button)
        
        self.layout.addWidget(mic_group)
    
    def _create_general_group(self):
        """Criar grupo de configurações gerais"""
        general_group = QGroupBox(_("general_settings", "General Settings"))
        general_layout = QFormLayout(general_group)
        
        # Idioma da interface
        self.interface_lang_combo = QComboBox()
        self.interface_lang_combo.addItem("English", "en")
        self.interface_lang_combo.addItem("Português", "pt")
        self.interface_lang_combo.addItem("Français", "fr")
        self.interface_lang_combo.addItem("Español", "es")
        general_layout.addRow(_("interface_language", "Interface Language:"), self.interface_lang_combo)
        
        # Aviso sobre reinicialização
        language_note = QLabel(_("language_restart_note", "* Changing the language requires restarting the application"))
        language_note.setStyleSheet("color: #888; font-style: italic; font-size: 9pt;")
        general_layout.addRow("", language_note)
        
        # Botão para reiniciar a aplicação
        restart_button = QPushButton(_("restart_application", "Restart Application"))
        restart_button.setStyleSheet("background-color: #f0ad4e; color: white;")
        restart_button.clicked.connect(self._restart_application)
        restart_button.setToolTip(_("restart_tooltip", "Restarts the application to apply language changes"))
        restart_layout = QHBoxLayout()
        restart_layout.addWidget(restart_button)
        restart_layout.addStretch()
        general_layout.addRow("", restart_layout)
        
        # Tema
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(_("theme_light", "Light"), "light")
        self.theme_combo.addItem(_("theme_dark", "Dark"), "dark")
        self.theme_combo.addItem(_("theme_system", "System"), "system")
        general_layout.addRow(_("theme", "Theme:"), self.theme_combo)
        
        # Tamanho da fonte
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItem(_("font_size_small", "Small"), "small")
        self.font_size_combo.addItem(_("font_size_medium", "Medium"), "medium")
        self.font_size_combo.addItem(_("font_size_large", "Large"), "large")
        general_layout.addRow(_("font_size", "Font Size:"), self.font_size_combo)
        
        # Opções de configuração
        self.interaction_sounds_check = QCheckBox(_("enable_interaction_sounds", "Enable interaction sounds"))
        general_layout.addRow("", self.interaction_sounds_check)
        
        self.auto_start_check = QCheckBox(_("auto_start", "Start with Windows"))
        general_layout.addRow("", self.auto_start_check)
        
        self.minimize_to_tray_check = QCheckBox(_("minimize_to_tray", "Minimize to tray when closing"))
        general_layout.addRow("", self.minimize_to_tray_check)
        
        self.layout.addWidget(general_group)
    
    def _show_hotkey_dialog(self):
        """Mostrar diálogo de configuração de teclas de atalho"""
        if self.hotkey_manager:
            dialog = HotkeyDialog(self, self.config_manager, self.hotkey_manager)
            dialog.exec_()
    
    def _test_microphone(self):
        """Testar microfone"""
        if not self.dictation_manager:
            QMessageBox.warning(self, "Teste de Microfone", "Gerenciador de ditado não está disponível.")
            return
            
        mic_id = self.mic_combo.currentData()
        if mic_id is None:
            QMessageBox.warning(self, "Teste de Microfone", "Nenhum microfone selecionado.")
            return
            
        try:
            # Ensure mic_id is properly converted to integer if it's not already
            mic_id = int(mic_id) if not isinstance(mic_id, int) else mic_id
            result = self.dictation_manager.test_microphone(mic_id)
            
            if result and "success" in result:
                if result["success"]:
                    QMessageBox.information(self, "Teste de Microfone", "Microfone funcionando corretamente!")
                else:
                    QMessageBox.warning(self, "Teste de Microfone", f"Erro ao testar microfone: {result.get('message', 'Erro desconhecido')}")
            else:
                QMessageBox.warning(self, "Teste de Microfone", "Resultado de teste de microfone inválido.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao testar microfone: {str(e)}")
    
    def _populate_microphones(self):
        """Preencher o combo de microfones"""
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
    
    def _set_recognition_service(self, service):
        """Definir o serviço de reconhecimento selecionado"""
        if service == "azure":
            self.azure_radio.setChecked(True)
        elif service == "whisper":
            self.whisper_radio.setChecked(True)
        elif service == "google":
            self.google_radio.setChecked(True)
        elif service == "whisper_local":
            self.whisper_local_radio.setChecked(True)
        else:
            # Padrão para Azure
            self.azure_radio.setChecked(True)
    
    def _get_recognition_service(self):
        """Obter o serviço de reconhecimento selecionado"""
        if self.azure_radio.isChecked():
            return "azure"
        elif self.whisper_radio.isChecked():
            return "whisper"
        elif self.google_radio.isChecked():
            return "google"
        elif self.whisper_local_radio.isChecked():
            return "whisper_local"
        else:
            return "azure"  # Padrão
    
    def _set_translation_service(self, service):
        """Definir o serviço de tradução selecionado"""
        if service == "azure":
            self.azure_translator_radio.setChecked(True)
        elif service == "m2m100":
            self.m2m100_local_radio.setChecked(True)
        elif service == "azure_openai":
            self.azure_openai_radio.setChecked(True)
        else:
            # Padrão para Azure
            self.azure_translator_radio.setChecked(True)
    
    def _get_translation_service(self):
        """Obter o serviço de tradução selecionado"""
        if self.azure_translator_radio.isChecked():
            return "azure"
        elif self.m2m100_local_radio.isChecked():
            return "m2m100"
        elif self.azure_openai_radio.isChecked():
            return "azure_openai"
        else:
            return "azure"  # Padrão
    
    def load_settings(self):
        """Carregar configurações do config_manager"""
        # Populate microphones
        self._populate_microphones()
        
        # Load service selection
        recognition_service = self.config_manager.get_value("recognition", "service", "azure")
        self._set_recognition_service(recognition_service)
        
        translation_service = self.config_manager.get_value("translation", "service", "azure")
        self._set_translation_service(translation_service)
        
        # Load interface settings
        interface_lang = self.config_manager.get_value("interface", "language", "en")
        index = self.interface_lang_combo.findData(interface_lang)
        if index >= 0:
            self.interface_lang_combo.setCurrentIndex(index)
        
        theme = self.config_manager.get_value("interface", "theme", "light")
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        font_size = self.config_manager.get_value("interface", "font_size", "medium")
        index = self.font_size_combo.findData(font_size)
        if index >= 0:
            self.font_size_combo.setCurrentIndex(index)
        
        # Load toggle settings
        self.interaction_sounds_check.setChecked(
            self.config_manager.get_value("general", "interaction_sounds", False)
        )
        self.auto_start_check.setChecked(
            self.config_manager.get_value("general", "auto_start", False)
        )
        self.minimize_to_tray_check.setChecked(
            self.config_manager.get_value("general", "minimize_to_tray", True)
        )
    
    def save_settings(self):
        """Salvar configurações no config_manager"""
        # Save microphone settings
        mic_id = self.mic_combo.currentData()
        if mic_id is not None:
            self.config_manager.set_value("audio", "default_microphone_id", mic_id)
            self.config_manager.set_value("audio", "default_microphone", self.mic_combo.currentText())
            if self.dictation_manager:
                self.dictation_manager.set_microphone(mic_id)
        
        # Save service selection
        recognition_service = self._get_recognition_service()
        self.config_manager.set_value("recognition", "service", recognition_service)
        if self.dictation_manager:
            self.dictation_manager.set_service(recognition_service)
        
        translation_service = self._get_translation_service()
        self.config_manager.set_value("translation", "service", translation_service)
        
        # Save interface settings
        self.config_manager.set_value(
            "interface", 
            "language", 
            self.interface_lang_combo.currentData()
        )
        self.config_manager.set_value(
            "interface", 
            "theme", 
            self.theme_combo.currentData()
        )
        self.config_manager.set_value(
            "interface", 
            "font_size", 
            self.font_size_combo.currentData()
        )
        
        # Save toggle settings
        self.config_manager.set_value(
            "general", 
            "interaction_sounds", 
            self.interaction_sounds_check.isChecked()
        )
        self.config_manager.set_value(
            "general", 
            "auto_start", 
            self.auto_start_check.isChecked()
        )
        self.config_manager.set_value(
            "general", 
            "minimize_to_tray", 
            self.minimize_to_tray_check.isChecked()
        )
    
    def _restart_application(self):
        """Reiniciar a aplicação para aplicar as alterações de idioma"""
        from PyQt5.QtWidgets import QMessageBox
        import sys
        import os
        import subprocess
        
        # Obter o idioma atual
        from src.i18n import get_instance as get_i18n
        i18n = get_i18n()
        
        # Salvar configurações antes de reiniciar
        self.save_settings()
        
        # Confirmar reinicialização
        reply = QMessageBox.question(
            self,
            _("restart_title", "Restart Application"),
            _("restart_confirm", "Do you want to restart the application now to apply language changes?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Obter o caminho do executável atual
                if getattr(sys, 'frozen', False):
                    # Se for um executável congelado (PyInstaller)
                    application_path = sys.executable
                else:
                    # Se for um script Python
                    application_path = sys.argv[0]
                
                # Iniciar uma nova instância da aplicação
                if sys.platform.startswith('win'):
                    # Windows
                    subprocess.Popen([application_path] + sys.argv[1:], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    # Linux/Mac
                    subprocess.Popen([application_path] + sys.argv[1:], start_new_session=True)
                
                # Fechar a aplicação atual
                from PyQt5.QtWidgets import QApplication
                QApplication.instance().quit()
            
            except Exception as e:
                logger.error(f"Erro ao reiniciar a aplicação: {str(e)}")
                QMessageBox.warning(
                    self,
                    _("error_title", "Error"),
                    _("restart_error", "Could not restart the application automatically. Please close and open the application manually.\n\nError: {error}").format(error=str(e))
                ) 