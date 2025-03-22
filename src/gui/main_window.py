#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window for DogeDictate
Provides the main settings interface
"""

import os
import sys
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QComboBox, QCheckBox, QGroupBox,
    QLineEdit, QFileDialog, QMessageBox, QProgressBar, QScrollArea,
    QFrame, QSpacerItem, QSizePolicy, QStackedWidget, QSystemTrayIcon, QMenu, QDialog
)
from PyQt5.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QPixmap, QFont, QPalette, QColor
from PyQt5.QtWidgets import QApplication
import traceback
import time

from src.gui.hotkey_dialog import HotkeyDialog
from src.gui.floating_bar import FloatingBar
from src.gui.settings_dialog import SettingsDialog
from src.gui.styles import MAIN_WINDOW_STYLE, create_toggle_style, Colors

logger = logging.getLogger("DogeDictate.MainWindow")

class SettingsGroup(QGroupBox):
    """Custom GroupBox for settings sections"""
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(24, 24, 24, 24)

class SettingItem(QWidget):
    """Custom widget for individual settings"""
    def __init__(self, title, description=None, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side (labels)
        self.label_layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.label_layout.addWidget(self.title_label)
        
        if description:
            self.description_label = QLabel(description)
            self.description_label.setProperty("type", "description")
            self.label_layout.addWidget(self.description_label)
        
        self.layout.addLayout(self.label_layout)
        self.layout.addStretch()

    def add_widget(self, widget):
        """Add a widget to the right side of the setting item"""
        self.layout.addWidget(widget)

    def add_widget_layout(self, layout):
        """Add a layout to the right side of the setting item"""
        self.layout.addLayout(layout)

class ToggleSettingItem(SettingItem):
    """Setting item with a toggle switch"""
    def __init__(self, title, description=None, parent=None):
        super().__init__(title, description, parent)
        self.toggle = QCheckBox()
        self.toggle.setStyleSheet(create_toggle_style())
        self.layout.addWidget(self.toggle)

class ButtonSettingItem(SettingItem):
    """Setting item with a button"""
    def __init__(self, title, button_text, button_type="primary", description=None, parent=None):
        super().__init__(title, description, parent)
        self.button = QPushButton(button_text)
        self.button.setProperty("type", button_type)
        self.layout.addWidget(self.button)

class MainWindow(QMainWindow):
    """Main window for DogeDictate application"""
    
    def __init__(self, config_manager, dictation_manager, hotkey_manager):
        """Initialize the main window"""
        try:
            super().__init__()
            logger.info("Inicializando a janela principal...")
            
            # Store references
            self.config_manager = config_manager
            self.dictation_manager = dictation_manager
            self.hotkey_manager = hotkey_manager
            self.floating_bar = None
            self.settings_dialog = None
            
            # Initialize UI
            self._setup_ui()
            
            # Setup signal connections
            self._connect_signals()
            
            logger.info("Janela principal inicializada com sucesso")
        except Exception as e:
            logger.critical(f"Erro fatal ao inicializar a janela principal: {str(e)}")
            logger.critical(f"Detalhes da exceção: {traceback.format_exc()}")
            # Tentar mostrar uma mensagem na interface
            try:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(None, "Erro de Inicialização", 
                                   f"Falha ao inicializar a interface: {str(e)}\n\nVerifique os logs para mais detalhes.")
            except:
                pass  # Se não puder mostrar a mensagem, apenas continue
    
    def _setup_ui(self):
        """Setup the UI components"""
        try:
            logger.info("Configurando interface de usuário...")
            # Inicializar a interface do usuário básica
            self._init_ui()
            
            # Inicializar a barra flutuante
            self._init_floating_bar()
            
            # Carregar configurações
            self._load_settings()
            
            # Configurar o ícone da bandeja do sistema
            self._setup_tray_icon()
            
            logger.info("Interface de usuário configurada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao configurar a interface: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _init_ui(self):
        """Initialize the user interface"""
        logger.info("Inicializando elementos básicos da interface...")
        self.setWindowTitle("DogeDictate")
        self.setMinimumSize(800, 600)
        
        # Aplicar estilo
        self.setStyleSheet(MAIN_WINDOW_STYLE)
        
        # Definir ícone da aplicação
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                               "resources", "icons", "app_icon.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                logger.info(f"Ícone da aplicação carregado de: {icon_path}")
            else:
                logger.warning(f"Ícone da aplicação não encontrado em: {icon_path}")
        except Exception as e:
            logger.warning(f"Erro ao carregar ícone da aplicação: {str(e)}")
        
        # Criar layout principal
        main_layout = QVBoxLayout()
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Adicionar texto simples para teste
        test_label = QLabel("DogeDictate está iniciando...", self)
        test_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(test_label)
        
        # Botão para abrir configurações
        settings_button = QPushButton("Abrir Configurações", self)
        settings_button.clicked.connect(self._open_settings)
        main_layout.addWidget(settings_button)
        
        logger.info("Elementos básicos da interface inicializados")
    
    def _open_settings(self):
        """Open settings dialog"""
        try:
            if self.settings_dialog is None:
                self.settings_dialog = SettingsDialog(self.config_manager, self.dictation_manager, self.hotkey_manager, self)
            
            self.settings_dialog.show()
            logger.info("Dialog de configurações aberto")
        except Exception as e:
            logger.error(f"Erro ao abrir dialog de configurações: {str(e)}")
            QMessageBox.warning(self, "Erro", f"Não foi possível abrir as configurações: {str(e)}")
    
    def _init_floating_bar(self):
        """Initialize the floating bar"""
        try:
            logger.info("Inicializando barra flutuante...")
            self.floating_bar = FloatingBar(self.config_manager, self.dictation_manager, self)
            self.floating_bar.hide()  # Hide initially
            logger.info("Barra flutuante inicializada")
        except Exception as e:
            logger.error(f"Erro ao inicializar barra flutuante: {str(e)}")
            self.floating_bar = None
    
    def _setup_tray_icon(self):
        """Setup the system tray icon"""
        try:
            logger.info("Configurando ícone da bandeja do sistema...")
            # Criar menu da bandeja
            tray_menu = QMenu()
            
            # Ação para mostrar/esconder a janela principal
            show_action = tray_menu.addAction("Mostrar/Esconder")
            show_action.triggered.connect(self._toggle_window)
            
            # Ação para abrir configurações
            settings_action = tray_menu.addAction("Configurações")
            settings_action.triggered.connect(self._open_settings)
            
            # Separador
            tray_menu.addSeparator()
            
            # Ação para sair
            quit_action = tray_menu.addAction("Sair")
            quit_action.triggered.connect(self.quit_application)
            
            # Criar ícone da bandeja
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                               "resources", "icons", "app_icon.png")
            
            if not os.path.exists(icon_path):
                logger.warning(f"Ícone da bandeja não encontrado em: {icon_path}")
                icon_path = None
            
            # Usar ícone padrão se o ícone personalizado não estiver disponível
            self.tray_icon = QSystemTrayIcon(self)
            
            if icon_path and os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
            
            # Conectar sinal de ativação
            self.tray_icon.activated.connect(self._tray_icon_activated)
            
            logger.info("Ícone da bandeja configurado")
        except Exception as e:
            logger.error(f"Erro ao configurar ícone da bandeja: {str(e)}")
            
    def _toggle_window(self):
        """Toggle the visibility of the main window"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
    
    def _load_settings(self):
        """Load settings from config manager"""
        # Initialize attributes that might be accessed before they're created
        self.mic_combo = None
        self.service_combo = None
        self.language_label = None
        
        # Load service settings
        self.current_service = self.config_manager.get_value("recognition", "service", "azure")
        
        # Load toggle settings
        self.improve_model = self.config_manager.get_value("general", "improve_model", False)
        self.context_recognition = self.config_manager.get_value("general", "context_recognition", False)
        self.interaction_sounds = self.config_manager.get_value("general", "interaction_sounds", False)
        self.mute_during_dictation = self.config_manager.get_value("general", "mute_during_dictation", False)
        self.auto_learn_words = self.config_manager.get_value("general", "auto_learn_words", False)
        self.start_on_login = self.config_manager.get_value("general", "start_on_login", False)
        self.show_in_taskbar = self.config_manager.get_value("general", "show_in_taskbar", True)
        self.show_floating_bar = self.config_manager.get_value("general", "show_floating_bar", True)
        
        # Load language settings
        self.current_language = self.config_manager.get_value("recognition", "language", "en-US")

    def _save_settings(self):
        """Save settings to config manager"""
        try:
            # Save service settings
            if hasattr(self, 'service_combo') and self.service_combo is not None:
                service_index = self.service_combo.currentIndex()
                if service_index == 0:
                    self.config_manager.set_value("recognition", "service", "whisper")
                    if hasattr(self, 'whisper_key') and self.whisper_key is not None:
                        self.config_manager.set_value(
                            "recognition", "whisper_api_key", self.whisper_key.text()
                        )
                elif service_index == 1:
                    self.config_manager.set_value("recognition", "service", "azure")
                    if hasattr(self, 'azure_key') and self.azure_key is not None:
                        self.config_manager.set_value(
                            "recognition", "azure_api_key", self.azure_key.text()
                        )
                    if hasattr(self, 'azure_region') and self.azure_region is not None:
                        self.config_manager.set_value(
                            "recognition", "azure_region", self.azure_region.text()
                        )
                elif service_index == 2:
                    self.config_manager.set_value("recognition", "service", "google")
                    if hasattr(self, 'google_cred') and self.google_cred is not None:
                        self.config_manager.set_value(
                            "recognition", "google_credentials_path", self.google_cred.text()
                        )
            
            # Save toggle settings
            if hasattr(self, 'interaction_sounds_toggle') and self.interaction_sounds_toggle is not None:
                self.config_manager.set_value(
                    "general", "interaction_sounds", self.interaction_sounds_toggle.isChecked()
                )
            if hasattr(self, 'mute_audio_toggle') and self.mute_audio_toggle is not None:
                self.config_manager.set_value(
                    "general", "mute_audio", self.mute_audio_toggle.isChecked()
                )
            if hasattr(self, 'auto_learn_toggle') and self.auto_learn_toggle is not None:
                self.config_manager.set_value(
                    "general", "auto_learn", self.auto_learn_toggle.isChecked()
                )
            
            # Save language settings
            if hasattr(self, 'lang_combo') and self.lang_combo is not None:
                lang_index = self.lang_combo.currentIndex()
                if lang_index == 0:
                    self.config_manager.set_value("languages", "default_language", "en-US")
                elif lang_index == 1:
                    self.config_manager.set_value("languages", "default_language", "pt-BR")
                elif lang_index == 2:
                    self.config_manager.set_value("languages", "default_language", "es-ES")
            
            # Save microphone settings
            if hasattr(self, 'mic_combo') and self.mic_combo is not None:
                mic_id = self.mic_combo.currentData()
                if mic_id is not None:
                    self.config_manager.set_value("audio", "default_microphone_id", mic_id)
            
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")
    
    def _populate_microphones(self):
        """Populate the microphone dropdown"""
        self.mic_combo.clear()
        
        # Get available microphones
        microphones = self.dictation_manager.get_microphones()
        default_mic_id = self.config_manager.get_value("audio", "default_microphone", None)
        
        # Add microphones to combo box
        for mic in microphones:
            self.mic_combo.addItem(mic["name"], mic["id"])
            if mic["id"] == default_mic_id:
                self.mic_status.setText(f"Mic in use: {mic['name']}")

    def _populate_languages(self):
        """Populate the language dropdowns and checkboxes"""
        # Implementation of _populate_languages method
        pass
    
    def _get_language_name(self, language_code):
        """Get the display name for a language code"""
        language_map = {
            "en-US": "English (US)",
            "en-GB": "English (UK)",
            "pt-BR": "Portuguese (Brazil)",
            "es-ES": "Spanish (Spain)",
            "fr-FR": "French",
            "de-DE": "German",
            "it-IT": "Italian",
            "ja-JP": "Japanese",
            "zh-CN": "Chinese (Simplified)",
            "ru-RU": "Russian"
        }
        return language_map.get(language_code, language_code)
    
    def _on_service_changed(self, index):
        """Handle service selection change"""
        # Implementation of _on_service_changed method
        pass
    
    def _on_microphone_changed(self, index):
        """Handle microphone selection change"""
        # Implementation of _on_microphone_changed method
        pass
    
    def _browse_google_credentials(self):
        """Open file dialog to select Google credentials file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Google Credentials File",
            "",
            "JSON Files (*.json)"
        )
        
        if file_path:
            self.google_cred.setText(file_path)

    def _test_service_connection(self, service):
        """Test the connection to the selected speech recognition service"""
        try:
            if service == "whisper":
                api_key = self.whisper_key.text()
                if not api_key:
                    QMessageBox.warning(self, "Missing API Key", "Please enter your Whisper API key first.")
                    return
                self.dictation_manager.services["whisper"].update_api_key(api_key)
                result = self.dictation_manager.services["whisper"].test_connection()
            elif service == "azure":
                api_key = self.azure_key.text()
                region = self.azure_region.text()
                if not api_key:
                    QMessageBox.warning(self, "Missing API Key", "Please enter your Azure API key first.")
                    return
                if not region:
                    QMessageBox.warning(self, "Missing Region", "Please enter your Azure region first.")
                    return
                self.dictation_manager.services["azure"].update_credentials(api_key, region)
                result = self.dictation_manager.services["azure"].test_connection()
            elif service == "google":
                cred_path = self.google_cred.text()
                if not cred_path:
                    QMessageBox.warning(self, "Missing Credentials", "Please select your Google credentials file first.")
                    return
                self.dictation_manager.services["google"].update_credentials_path(cred_path)
                result = self.dictation_manager.services["google"].test_connection()
            else:
                QMessageBox.warning(self, "Invalid Service", "Invalid service selected.")
                return

            if result["success"]:
                QMessageBox.information(self, "Connection Test", "✅ " + result["message"])
            else:
                QMessageBox.warning(self, "Connection Test", "❌ " + result["message"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while testing the connection: {str(e)}")

    def _test_microphone(self):
        """Test the microphone connection"""
        result = self.dictation_manager.test_microphone()
        if result["success"]:
            QMessageBox.information(self, "Microphone Test", "Microphone is working correctly!")
        else:
            QMessageBox.warning(self, "Microphone Test", f"Microphone test failed: {result['message']}")
        self._update_home_status()

    def _test_service(self):
        """Test the speech recognition service connection"""
        result = self.dictation_manager.test_service()
        if result["success"]:
            QMessageBox.information(self, "Service Test", "Speech recognition service is working correctly!")
        else:
            QMessageBox.warning(self, "Service Test", f"Service test failed: {result['message']}")
        self._update_home_status()

    def _show_hotkey_dialog(self):
        """Show the hotkey configuration dialog"""
        dialog = HotkeyDialog(self, self.config_manager, self.hotkey_manager)
        dialog.exec_()

    def _toggle_floating_bar(self, state):
        """Toggle the floating bar visibility"""
        if state == Qt.Checked:
            self._show_floating_bar()
        else:
            self._hide_floating_bar()
        self.config_manager.set_value("general", "show_floating_bar", state == Qt.Checked)

    def _show_floating_bar(self):
        """Show the floating bar"""
        if not self.floating_bar:
            self.floating_bar = FloatingBar(self.dictation_manager)
        self.floating_bar.show()

    def _hide_floating_bar(self):
        """Hide the floating bar"""
        if self.floating_bar:
            self.floating_bar.hide()

    def _delete_history(self):
        """Delete transcription history"""
        # Implementation of _delete_history method
        pass
    
    def _open_privacy_policy(self):
        """Open the privacy policy in a web browser"""
        # Implementation of _open_privacy_policy method
        pass
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.config_manager.get_value("general", "show_in_taskbar", True):
            # Normal close
            self.quit_application()
        else:
            # Minimize to tray
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "DogeDictate",
                "DogeDictate is still running in the background.",
                QSystemTrayIcon.Information,
                2000
            )
    
    def _tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
    
    def quit_application(self):
        """Quit the application"""
        try:
            # Stop dictation if active
            if hasattr(self.dictation_manager, 'stop_dictation'):
                self.dictation_manager.stop_dictation()
            
            # Descarregar modelos e liberar memória
            if hasattr(self.dictation_manager, 'stop'):
                logger.info("Descarregando modelos e liberando memória")
                self.dictation_manager.stop()
            
            # Stop hotkey listener
            if hasattr(self.hotkey_manager, 'stop'):
                self.hotkey_manager.stop()
            
            # Hide floating bar if visible
            if hasattr(self, 'floating_bar') and self.floating_bar is not None:
                self.floating_bar.hide()
            
            # Save settings
            try:
                self._save_settings()
            except Exception as e:
                logger.error(f"Error saving settings on quit: {str(e)}")
            
            # Forçar coleta de lixo
            try:
                import gc
                gc.collect()
                logger.info("Garbage collection performed before quit")
                
                # Limpar cache CUDA se disponível
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.info("CUDA cache cleared before quit")
            except Exception as e:
                logger.error(f"Error during final cleanup: {str(e)}")
            
            # Quit application
            logger.info("Quitting application")
            QApplication.quit()
        except Exception as e:
            logger.error(f"Error quitting application: {str(e)}")
            # Force quit
            QApplication.quit()

    def _update_mic_level(self):
        """Update microphone level indicator"""
        try:
            # Verificar se a barra flutuante existe
            if hasattr(self, 'floating_bar') and self.floating_bar is not None:
                # Só atualizar a cada 2 segundos para reduzir drasticamente o número de testes
                current_time = time.time()
                if not hasattr(self, 'last_mic_update_time'):
                    self.last_mic_update_time = 0
                    
                if current_time - self.last_mic_update_time > 2.0:  # Limitar a uma vez a cada 2 segundos
                    self.last_mic_update_time = current_time
                    # Atualizar nível do microfone na barra flutuante
                    self.floating_bar.update_mic_level()
        except Exception as e:
            # Não logar erro a cada atualização para não encher o log
            pass

    def _test_whisper_connection(self):
        """Test the connection to the Whisper API"""
        # Implementation of _test_whisper_connection method
        pass
    
    def _test_azure_connection(self):
        """Test the connection to Azure Speech Services"""
        # Implementation of _test_azure_connection method
        pass
    
    def _test_google_connection(self):
        """Test the connection to Google Speech-to-Text"""
        # Implementation of _test_google_connection method
        pass

    def _update_service_settings(self, index):
        """Update service settings when service is changed"""
        self.service_stack.setCurrentIndex(index)

    def _update_mic_status(self, index):
        """Update microphone status when selection changes"""
        if index >= 0:
            mic_name = self.mic_combo.currentText()
            self.mic_status.setText(f"Mic in use: {mic_name}")

    def _handle_navigation(self, page_id):
        """Handle navigation between pages"""
        # Update button states
        for button_id, button in self.nav_buttons.items():
            button.setChecked(button_id == page_id)
        
        # Show the selected page
        if page_id == "home":
            self.stacked_widget.setCurrentWidget(self.home_page)
            self._update_home_status()
        elif page_id == "dictionary":
            self.stacked_widget.setCurrentWidget(self.dictionary_page)
        elif page_id == "history":
            self.stacked_widget.setCurrentWidget(self.history_page)
        elif page_id == "settings":
            self.stacked_widget.setCurrentWidget(self.settings_page)

    def _update_home_status(self):
        """Update the status information on the home page"""
        try:
            # Update microphone status
            if hasattr(self, 'mic_status'):
                mic_name = self.dictation_manager.get_current_microphone_name()
                self.mic_status.setText(f"Microfone: {mic_name}")
            
            # Update service status
            if hasattr(self, 'service_status'):
                service_name = self.dictation_manager.get_service_name()
                self.service_status.setText(f"Serviço: {service_name}")
            
            # Update language status
            if hasattr(self, 'language_status'):
                language_name = self._get_language_name(self.dictation_manager.get_language())
                self.language_status.setText(f"Idioma: {language_name}")
            
            # Update hotkey status
            if hasattr(self, 'hotkey_status') and self.hotkey_manager:
                ptt_hotkey = self.hotkey_manager.get_hotkey_display("push_to_talk")
                hf_hotkey = self.hotkey_manager.get_hotkey_display("hands_free")
                self.hotkey_status.setText(f"Atalhos: PTT: {ptt_hotkey}, HF: {hf_hotkey}")
        except Exception as e:
            logger.error(f"Error updating home status: {str(e)}")

    def _update_ui_from_settings(self):
        """Update UI elements based on current settings"""
        # Update dictation manager settings
        current_language = self.config_manager.get_value("recognition", "language", "en-US")
        current_service = self.config_manager.get_value("recognition", "service", "azure")
        
        # Update dictation manager
        self.dictation_manager.set_language(current_language)
        self.dictation_manager.set_service(current_service)
        
        # Update floating bar visibility if it exists
        show_floating_bar = self.config_manager.get_value("general", "show_floating_bar", True)
        if hasattr(self, 'floating_bar') and self.floating_bar is not None:
            if show_floating_bar:
                self.floating_bar.show()
            else:
                self.floating_bar.hide()
        
        # Log settings update
        logger.info("UI updated from settings")

    def _connect_signals(self):
        """Connect signals to slots"""
        try:
            logger.info("Conectando sinais...")
            
            # Conectar sinais do dictation_manager
            if hasattr(self.dictation_manager, 'dictation_started'):
                self.dictation_manager.dictation_started.connect(self._on_dictation_started)
                
            if hasattr(self.dictation_manager, 'dictation_stopped'):
                self.dictation_manager.dictation_stopped.connect(self._on_dictation_stopped)
                
            if hasattr(self.dictation_manager, 'text_inserted'):
                self.dictation_manager.text_inserted.connect(self._on_text_inserted)
            
            # Não configurar timer para atualização do microfone - teste único no início
            
            logger.info("Sinais conectados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar sinais: {str(e)}")
    
    def _on_dictation_started(self):
        """Handle dictation started event"""
        logger.info("Dictation started")
        # Update UI to show dictation is active
        
    def _on_dictation_stopped(self):
        """Handle dictation stopped event"""
        logger.info("Dictation stopped")
        # Update UI to show dictation is inactive
        
    def _on_text_inserted(self, text):
        """Handle text inserted event"""
        logger.info(f"Text inserted: {text}")
        # Update UI to show the inserted text
        
    def _on_hotkey_triggered(self, hotkey_id):
        """Handle hotkey triggered event"""
        logger.info(f"Hotkey triggered: {hotkey_id}")
        # Handle different hotkeys

    def showEvent(self, event):
        """Called when the window is shown"""
        super().showEvent(event)

    def _show_settings_dialog(self):
        """Show the settings dialog"""
        if not self.settings_dialog:
            self.settings_dialog = SettingsDialog(self.config_manager, self.dictation_manager, self.hotkey_manager, self)
            self.settings_dialog.finished.connect(self._on_settings_dialog_finished)
        
        self.settings_dialog.show()
