#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import logging.handlers
import platform
import time
import traceback
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap, QPalette, QColor, QIcon
from PyQt5.QtCore import Qt, QMetaType
import threading

# Ajustar os caminhos de importação

# Configurar caminhos de importação
import os
import sys
# Adicionar diretório pai ao PATH
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Importar componentes da aplicação usando caminhos absolutos
from src.core.config_manager import ConfigManager
from src.core.dictation_manager import DictationManager
from src.services.stats_service import StatsService
from src.core.hotkey_manager import HotkeyManager
from src.gui.settings.settings_dialog import SettingsDialog
from src.gui.main_window import MainWindow
from src.utils.i18n import init_i18n
from src.core.audio_log_filter import setup_dictation_log_filters
from src.core.language_rules import LanguageRulesManager

# Variáveis globais
app = None
main_window = None

# Adicione estas classes para filtrar logs específicos
class StatsLogFilter(logging.Filter):
    """Filtro para remover mensagens de estatísticas que poluem o log"""
    
    def __init__(self, name=''):
        super().__init__(name)
        self.stats_patterns = [
            "Loading statistics:",
            "Period statistics:",
            "API usage:",
            "Session history:",
            "Statistics loaded successfully"
        ]
    
    def filter(self, record):
        # Verificar se a mensagem contém algum dos padrões a serem filtrados
        if record.levelno == logging.INFO:  # Apenas filtrar mensagens de nível INFO
            message = record.getMessage()
            for pattern in self.stats_patterns:
                if pattern in message:
                    return False  # Não logar mensagens de estatísticas frequentes
        return True  # Logar todas as outras mensagens

# Configurar logging
def setup_logging(console_level=logging.INFO):
    """Setup logging configuration"""
    log_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "DogeDictate", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"dogedictate_{datetime.now().strftime('%Y%m%d')}.log")
    
    # Clear previous handlers
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Create file handler with UTF-8 encoding
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, 
        maxBytes=5*1024*1024, 
        backupCount=5, 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Create console handler that avoids Unicode issues
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    
    # Add the filter for suppressing statistics messages
    stats_filter = StatsLogFilter()
    console_handler.addFilter(stats_filter)
    
    # Replace the default stream handler
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.handlers.RotatingFileHandler):
            root_logger.removeHandler(handler)
    
    root_logger.addHandler(console_handler)
    
    # Set specific loggers level
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    
    # Log unhandled exceptions
    def exception_handler(exc_type, exc_value, exc_traceback):
        root_logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_handler
    
    # Log startup
    root_logger.info("Logging initialized")
    
    return logging.getLogger(__name__) 

def check_admin():
    """Check if app is running as admin"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False 

def setup_qt_vector_metatype():
    """Register QVector<int> metatype for Qt signal/slot system"""
    try:
        # Primeira tentativa: usar qRegisterMetaType
        from PyQt5.QtCore import qRegisterMetaType
        # Registrar QVector<int>
        qRegisterMetaType("QVector<int>")
        # Registrar QList<int>
        qRegisterMetaType("QList<int>")
        logger.info("Successfully registered Qt collection metatypes")
        return
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to register metatypes with qRegisterMetaType: {str(e)}")
        
    try:
        # Segunda tentativa: usar QMetaType.type()
        # QMetaType já foi importado no início do arquivo
        # Registrar QVector<int>
        QMetaType.type("QVector<int>")
        # Registrar QList<int>
        QMetaType.type("QList<int>")
        logger.info("Registered Qt collection metatypes using QMetaType.type")
        return
    except Exception as e:
        logger.warning(f"Failed to register metatypes with QMetaType.type: {str(e)}")
        
    try:
        # Terceira tentativa: usar técnica específica para versões mais recentes
        from PyQt5.QtCore import QVariant
        QVariant.nameToType("QVector<int>")
        QVariant.nameToType("QList<int>")
        logger.info("Registered Qt collection metatypes using QVariant.nameToType")
        return
    except Exception as e:
        logger.warning(f"Failed to register metatypes with QVariant.nameToType: {str(e)}")
        
    logger.warning("Could not register Qt metatypes. Some features may not work properly.")

def log_key_configurations(config_manager):
    """Log key configurations for debugging purposes"""
    try:
        # Log interface configurations
        interface_lang = config_manager.get_value("interface", "language", "en")
        start_minimized = config_manager.get_value("interface", "start_minimized", False)
        start_with_windows = config_manager.get_value("interface", "start_with_windows", False)
        logger.info(f"Interface settings: language={interface_lang}, start_minimized={start_minimized}, start_with_windows={start_with_windows}")
        
        # Log translation configurations
        target_lang = config_manager.get_value("translation", "target_language", "en-US")
        source_lang = config_manager.get_value("translation", "source_language", "en-US")
        logger.info(f"Translation settings: source={source_lang}, target={target_lang}")
        
        # Log hotkey configurations
        push_to_talk = config_manager.get_value("hotkeys", "push_to_talk", "")
        toggle_recording = config_manager.get_value("hotkeys", "toggle_recording", "")
        logger.info(f"Hotkey settings: push_to_talk={push_to_talk}, toggle_recording={toggle_recording}")
        
        # Log language hotkeys
        language_hotkeys = config_manager.get_value("language_hotkeys", {})
        logger.info(f"Language hotkeys: {language_hotkeys}")
        
        # Log key languages
        key_languages = config_manager.get_value("key_languages", {})
        logger.info(f"Key languages: {key_languages}")
        
    except Exception as e:
        logger.error(f"Error logging key configurations: {str(e)}")

def initialize_config():
    """Initialize the configuration manager"""
    logger.info("Initializing config manager...")
    config_manager = ConfigManager()
    
    # Se o config não estava carregado, cria o padrão
    if not config_manager.config:
        config_manager.config = config_manager._create_default_config()
        config_manager.dirty = True
        config_manager.save_config(force=True)
    
    # Log some key configs for debugging
    log_key_configurations(config_manager)
    
    return config_manager

def check_for_updates():
    """Check for updates in background"""
    try:
        logger.info("Checking for updates...")
        # TODO: Implement actual update checking logic
        time.sleep(5)  # Simulate network delay
        logger.info("Update check completed")
    except Exception as e:
        logger.error(f"Failed to check for updates: {str(e)}")

def validate_microphone_config():
    """Verifica se a configuração de microfone está correta"""
    try:
        # Obter configuração atual
        config_manager = ConfigManager()
        microphone_id = config_manager.get_value("audio", "microphone_id", 0)
        logger.info(f"Configuração atual de microfone ID: {microphone_id}")
        
        # Considerar a validação bem-sucedida por padrão
        return True
    except Exception as e:
        logger.error(f"Erro ao validar configuração de microfone: {str(e)}")
        return False

def main():
    """Main application function"""
    try:
        # Registrar QMetaTypes para sinais e slots
        setup_qt_vector_metatype()
        
        # Inicializar o gerenciador de configuração
        logger.info("Initializing config manager...")
        config_manager = initialize_config()
        
        # Verificar configurações
        interface_language = config_manager.get_value("interface", "language", "en")
        start_minimized = config_manager.get_value("interface", "start_minimized", False)
        start_with_windows = config_manager.get_value("general", "start_with_windows", False)
        logger.info(f"Interface settings: language={interface_language}, start_minimized={start_minimized}, start_with_windows={start_with_windows}")
        
        # Verificar configurações de tradução
        source_language = config_manager.get_value("translation", "source_language", "en-US")
        target_language = config_manager.get_value("translation", "target_language", "en-US")
        logger.info(f"Translation settings: source={source_language}, target={target_language}")
        
        # Verificar teclas de atalho
        push_to_talk = config_manager.get_value("hotkeys", "push_to_talk", {})
        toggle_recording = config_manager.get_value("hotkeys", "toggle_recording", "")
        logger.info(f"Hotkey settings: push_to_talk={push_to_talk}, toggle_recording={toggle_recording}")
        
        # Validar configuração de microfone
        logger.info("Validando configuração de microfone...")
        if not validate_microphone_config():
            logger.error("Falha na validação do microfone.")
            # Continuar mesmo com falha, já que a aplicação pode selecionar um microfone padrão
        
        # Initialize Qt application
        global app
        app = QApplication(sys.argv)
        app.setApplicationName("DogeDictate")
        
        # Try to load splash screen
        logger.info("Creating splash screen...")
        splash_pixmap = None
        try:
            # Tenta primeiro com caminho absoluto
            splash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "splash.png")
            logger.debug(f"Tentando carregar tela de splash do caminho: {splash_path}")
            if os.path.exists(splash_path):
                splash_pixmap = QPixmap(splash_path)
            else:
                logger.warning(f"Arquivo de splash não encontrado em: {splash_path}")
                
            # Se falhou, tenta com caminho relativo
            if splash_pixmap is None or splash_pixmap.isNull():
                splash_path = "resources/images/splash.png"
                logger.debug(f"Tentando carregar tela de splash do caminho alternativo: {splash_path}")
                if os.path.exists(splash_path):
                    splash_pixmap = QPixmap(splash_path)
                else:
                    logger.warning(f"Arquivo de splash não encontrado em: {splash_path}")
        except Exception as e:
            logger.error(f"Erro ao carregar a tela de splash: {str(e)}")
            
        # Cria e mostra a tela de splash se foi carregada com sucesso
        splash = None
        if splash_pixmap and not splash_pixmap.isNull():
            splash = QSplashScreen(splash_pixmap)
            splash.show()
            splash.showMessage("Carregando...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            app.processEvents()
        else:
            logger.warning("Não foi possível criar a tela de splash, iniciando sem ela.")
        
        # Set application style
        app.setStyle("fusion")
        
        # Configure dark palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)
        
        # Initialize internationalization
        logger.info("Initializing internationalization...")
        i18n = init_i18n(config_manager)
        
        # Set interface language
        interface_language = config_manager.get_value("interface", "language", "en")
        logger.info(f"Interface language set to: {interface_language}")
        i18n.set_language(interface_language)
        
        # Apply configured language
        configured_language = config_manager.get_value("translation", "target_language", "en-US")
        logger.info(f"Applied configured language: {configured_language}")
        
        # Start core services
        logger.info("Starting core services...")
        
        # Initialize dictation manager
        dictation_manager = DictationManager(config_manager)
        
        # Inicializar language_rules
        language_rules = LanguageRulesManager(config_manager)
        dictation_manager.language_rules = language_rules
        
        # Configurar filtro de logs para reduzir verbosidade durante gravação
        setup_dictation_log_filters()
        
        # Initialize hotkey manager with language_rules
        hotkey_manager = HotkeyManager(config_manager, dictation_manager, language_rules)
        
        # Add hotkey_manager reference to dictation_manager
        logger.info("Added hotkey_manager reference to dictation_manager")
        dictation_manager.hotkey_manager = hotkey_manager
        
        # Initialize settings dialog
        logger.info("Initializing settings dialog...")
        settings_dialog = SettingsDialog(config_manager, dictation_manager, hotkey_manager)
        
        # Initialize main window
        main_window = MainWindow(config_manager, dictation_manager, hotkey_manager)
        
        # Set settings dialog reference in main window
        main_window.settings_dialog = settings_dialog
        
        # Hide splash screen and show main window
        main_window.show()
        if splash:
            splash.finish(main_window)
        
        # Check if should start minimized
        start_minimized = config_manager.get_value("interface", "start_minimized", False)
        if start_minimized:
            logger.info("Iniciando minimizado...")
            main_window.hide()
            
        # Start hotkey listener
        logger.info("Starting hotkey listener...")
        hotkey_manager.start()
        
        # Check for updates in background
        threading.Thread(target=check_for_updates, daemon=True).start()
        
        logger.info("Application started successfully")
        
        # Run application
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Application failed to start: {str(e)}")
        sys.exit(1) 

if __name__ == "__main__":
    # Configurar logging
    logger = setup_logging()
    
    # Verificar se está sendo executado como administrador
    if check_admin():
        logger.warning("Running as administrator, this is not recommended")
    
    # Executar aplicação
    main() 