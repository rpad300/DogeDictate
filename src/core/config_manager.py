#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Manager for DogeDictate
Handles loading, saving, and accessing configuration settings
"""

import os
import json
import logging
import shutil
from pathlib import Path
import time
import threading

logger = logging.getLogger("DogeDictate.ConfigManager")

class ConfigManager:
    """Manages application configuration settings"""
    
    DEFAULT_CONFIG = {
        "interface": {
            "language": "en",
            "theme": "light",
            "font_size": "medium"
        },
    "recording": {
        "min_recording_duration": 0.1,
        "post_recording_delay": 0.5,
        "debounce_time": 0.3
    },
        "recognition": {
            "service": "azure",
            "language": "en-US",
            "azure_api_key": "",
            "azure_region": "",
            "whisper_api_key": "",
            "google_credentials_file": "",
            "initial_silence_timeout_ms": "60000",
            "end_silence_timeout_ms": "30000",
            "segmentation_silence_timeout_ms": "5000"
        },
        "translation": {
            "service": "azure",
            "target_language": "pt-BR",
            "auto_translate": True,
            "azure_translator_key": "",
            "azure_translator_region": "",
            "azure_openai_key": "",
            "azure_openai_endpoint": ""
        },
        "audio": {
            "default_microphone_id": 0,
            "default_microphone": "",
            "sample_rate": 16000,
            "channels": 1
        },
        "general": {
            "interaction_sounds": False,
            "auto_start": False,
            "minimize_to_tray": True
        },
        "hotkeys": {
            "push_to_talk": {
                "key": "",
                "modifiers": []
            },
            "toggle_dictation": {
                "key": "",
                "modifiers": []
            },
            "language_hotkeys": {}
        },
        "statistics": {
            "general": {
                "total_words": 0,
                "translated_words": 0,
                "total_time": 0,
                "current_session": {
                    "start_time": "",
                    "duration": 0,
                    "words": 0
                }
            },
            "api_usage": {
                "azure_speech": 0,
                "whisper_api": 0,
                "google_speech": 0,
                "azure_translator": 0,
                "azure_openai": 0,
                "whisper_local": 0,
                "m2m100": 0
            },
            "session_history": []
        }
    }
    
    def __init__(self, config_path=None):
        """Initialize the config manager
        
        Args:
            config_path (str): Path to the config file
        """
        self.config = {}
        self.dirty = False  # Indica se o config foi modificado desde o último save
        self.last_saved = time.time()  # Timestamp do último salvamento
        self.min_save_interval = 3.0  # Intervalo mínimo entre salvamentos (segundos)
        self.scheduled_save = None  # Referência para o temporizador de salvamento agendado
        self.save_lock = threading.Lock()  # Lock para evitar condições de corrida
        
        # Determinar o caminho do arquivo de configuração
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = self._get_default_config_path()
        
        # Carregar a configuração
        self.load_config()
        
        # Limpar duplicatas na configuração
        self._cleanup_config()
    
    def _get_config_dir(self):
        """Get the configuration directory"""
        if os.name == "nt":  # Windows
            config_dir = os.path.join(os.environ["APPDATA"], "DogeDictate")
        else:  # macOS and Linux
            config_dir = os.path.join(str(Path.home()), ".dogedictate")
        
        return config_dir
    
    def _get_default_config_path(self):
        """Get the default configuration file path"""
        return os.path.join(self._get_config_dir(), "config.json")
    
    def load_config(self):
        """Load configuration from file or create default if not exists"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # Log loaded API configurations (without revealing the actual keys)
                logger.info(f"Configuration loaded from {self.config_path}")
                
                # Check if API keys are present
                if "recognition" in config:
                    azure_key = config["recognition"].get("azure_key", "")
                    azure_region = config["recognition"].get("azure_region", "")
                    whisper_key = config["recognition"].get("whisper_api_key", "")
                    logger.info(f"Loaded Azure key present: {bool(azure_key)}, Azure region: {azure_region}")
                    logger.info(f"Loaded Whisper key present: {bool(whisper_key)}")
                else:
                    logger.warning("Recognition section missing from loaded config")
                
                if "translation" in config:
                    translator_key = config["translation"].get("azure_translator_key", "")
                    translator_region = config["translation"].get("azure_translator_region", "")
                    logger.info(f"Loaded Translator key present: {bool(translator_key)}, Translator region: {translator_region}")
                else:
                    logger.warning("Translation section missing from loaded config")
                
                # Update with any missing default values
                self._update_with_defaults(config)
                
                # Ensure hotkeys are in the correct format
                self._fix_hotkey_format(config)
                
                self.config = config
                self.dirty = False
                self.last_saved = time.time()
                return True
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
                # Try to recover from backup if available
                backup_file = f"{self.config_path}.bak"
                if os.path.exists(backup_file):
                    try:
                        logger.info(f"Attempting to recover from backup: {backup_file}")
                        with open(backup_file, "r", encoding="utf-8") as f:
                            config = json.load(f)
                        # Save the recovered config
                        with open(self.config_path, "w", encoding="utf-8") as f:
                            json.dump(config, f, indent=4)
                        logger.info("Successfully recovered configuration from backup")
                        self._update_with_defaults(config)
                        self._fix_hotkey_format(config)
                        self.config = config
                        self.dirty = False
                        self.last_saved = time.time()
                        return True
                    except Exception as backup_error:
                        logger.error(f"Error recovering from backup: {str(backup_error)}")
                
                return False
        else:
            return False
    
    def _create_default_config(self):
        """Create and save default configuration"""
        config = self.DEFAULT_CONFIG.copy()
        self.save_config(config)
        logger.info("Created default configuration")
        return config
    
    def _update_with_defaults(self, config):
        """Update configuration with any missing default values"""
        # Recursive function to update nested dictionaries
        def update_dict(target, source):
            for key, value in source.items():
                if key not in target:
                    target[key] = value
                elif isinstance(value, dict) and isinstance(target[key], dict):
                    update_dict(target[key], value)
        
        # Update config with default values
        update_dict(config, self.DEFAULT_CONFIG)
        
        # Migrate old keys if needed
        self._migrate_old_keys(config)
        
        return config
    
    def _fix_hotkey_format(self, config):
        """Ensure hotkeys are in the correct format"""
        if "hotkeys" in config:
            # Fix push_to_talk
            if "push_to_talk" in config["hotkeys"]:
                if isinstance(config["hotkeys"]["push_to_talk"], str):
                    key = config["hotkeys"]["push_to_talk"]
                    config["hotkeys"]["push_to_talk"] = {
                        "key": key,
                        "modifiers": []
                    }
            
            # Fix toggle_dictation
            if "toggle_dictation" in config["hotkeys"]:
                if isinstance(config["hotkeys"]["toggle_dictation"], str):
                    key = config["hotkeys"]["toggle_dictation"]
                    config["hotkeys"]["toggle_dictation"] = {
                        "key": key,
                        "modifiers": []
                    }
            
            # Ensure language_hotkeys exists
            if "language_hotkeys" not in config["hotkeys"]:
                config["hotkeys"]["language_hotkeys"] = []
            
            # Fix language hotkeys format
            if isinstance(config["hotkeys"]["language_hotkeys"], dict):
                # Converter de dicionário para lista
                language_hotkeys_list = []
                for lang, hotkey in config["hotkeys"]["language_hotkeys"].items():
                    if isinstance(hotkey, str):
                        language_hotkeys_list.append({
                            "key": hotkey,
                            "modifiers": [],
                            "language": lang
                        })
                    elif isinstance(hotkey, dict):
                        hotkey_dict = hotkey.copy()
                        hotkey_dict["language"] = lang
                        language_hotkeys_list.append(hotkey_dict)
                config["hotkeys"]["language_hotkeys"] = language_hotkeys_list
    
    def _migrate_old_keys(self, config):
        """Migrate old configuration keys to new format"""
        # Example: Migrate from old_key to new_key
        if "recognition" in config:
            # Migrate whisper_key to whisper_api_key
            if "whisper_key" in config["recognition"] and "whisper_api_key" not in config["recognition"]:
                config["recognition"]["whisper_api_key"] = config["recognition"]["whisper_key"]
                del config["recognition"]["whisper_key"]
                
            # Migrate azure_key to azure_api_key
            if "azure_key" in config["recognition"] and "azure_api_key" not in config["recognition"]:
                config["recognition"]["azure_api_key"] = config["recognition"]["azure_key"]
                del config["recognition"]["azure_key"]
                logger.info("Migrated recognition.azure_key to recognition.azure_api_key")
        
        # Migrate input_language to target_language
        if "translation" in config:
            if "input_language" in config["translation"] and "target_language" not in config["translation"]:
                config["translation"]["target_language"] = config["translation"]["input_language"]
                del config["translation"]["input_language"]
                logger.info("Migrated translation.input_language to translation.target_language")
        
        # Add more migrations as needed
        
        return config
    
    def _cleanup_config(self):
        """Limpa duplicatas e entradas problemáticas na configuração"""
        try:
            # Verificar tamanho atual do config para detectar se é grande demais
            config_size = len(json.dumps(self.config, ensure_ascii=False))
            if config_size > 5000:  # Arquivo maior que 5KB
                logger.warning(f"Config file is large ({config_size} bytes), cleaning up...")
                
                # Limpar duplicatas específicas comuns
                self._cleanup_microphones()
                
                # Salvar configuração limpa
                self.save_config(force=True)
                
                # Reportar redução de tamanho
                new_size = len(json.dumps(self.config, ensure_ascii=False))
                logger.info(f"Config file cleaned: {config_size} -> {new_size} bytes")
        except Exception as e:
            logger.error(f"Error during config cleanup: {str(e)}")
            
    def _cleanup_microphones(self):
        """Limpa duplicatas na lista de microfones"""
        try:
            # Verifica se existe a seção de microfones
            if "microphones" not in self.config:
                return
                
            # Mapeia os microfones por nome para detectar duplicatas
            mic_map = {}
            duplicates = 0
            
            # Lista original
            mics_original = self.config.get("microphones", [])
            
            # Lista filtrada
            mics_filtered = []
            
            for mic in mics_original:
                mic_name = mic.get("name", "")
                mic_id = mic.get("id")
                
                # Chave única para este microfone
                key = f"{mic_name}_{mic_id}"
                
                if key not in mic_map:
                    mic_map[key] = mic
                    mics_filtered.append(mic)
                else:
                    duplicates += 1
            
            # Atualiza a lista de microfones se houve redução
            if duplicates > 0:
                self.config["microphones"] = mics_filtered
                logger.info(f"Removed {duplicates} duplicate microphones")
                self.dirty = True
        except Exception as e:
            logger.error(f"Error cleaning up microphones: {str(e)}")
            
    def save_config(self, force=False):
        """Save the configuration to the config file
        
        Args:
            force (bool): Force saving even if not dirty or before min interval
        
        Returns:
            bool: True if saved, False otherwise
        """
        with self.save_lock:
            # Cancelar qualquer salvamento agendado pendente
            if self.scheduled_save:
                self.scheduled_save.cancel()
                self.scheduled_save = None
            
            # Verificar se precisamos salvar
            current_time = time.time()
            time_since_last_save = current_time - self.last_saved
            
            if not force and not self.dirty:
                return False  # Nada para salvar
                
            if not force and time_since_last_save < self.min_save_interval:
                # Agendar o salvamento para mais tarde
                delay = self.min_save_interval - time_since_last_save
                self.scheduled_save = threading.Timer(delay, self._delayed_save)
                self.scheduled_save.daemon = True
                self.scheduled_save.start()
                return False
                
            # Executar o salvamento real
            return self._perform_save()
            
    def _delayed_save(self):
        """Método chamado pelo timer para realizar salvamento adiado"""
        with self.save_lock:
            self.scheduled_save = None
            self._perform_save()
            
    def _perform_save(self):
        """Realiza o salvamento real da configuração"""
        try:
            # Garantir que o diretório exista
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Salvamento atômico (criar arquivo temporário primeiro)
            temp_path = f"{self.config_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
                
            # Renomear o arquivo temporário para o destino final
            if os.path.exists(self.config_path):
                # Em Windows, precisamos remover o arquivo de destino primeiro
                try:
                    os.remove(self.config_path)
                except:
                    pass
                    
            os.rename(temp_path, self.config_path)
            
            # Atualizar o estado
            self.last_saved = time.time()
            self.dirty = False
            
            logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_config(self):
        """Get the entire configuration"""
        return self.config
    
    def get_value(self, section, key, default=None):
        """Get a value from the configuration"""
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return default
    
    def set_value(self, section, key, value):
        """Set a value in the configuration"""
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
    
    def set_and_save_value(self, section, key, value):
        """Set a value and save the configuration"""
        self.set_value(section, key, value)
        return self.save_config()
    
    def backup_config(self):
        """Create a backup of the configuration file"""
        try:
            if os.path.exists(self.config_path):
                backup_file = f"{self.config_path}.bak"
                shutil.copy2(self.config_path, backup_file)
                logger.info(f"Configuration backup created: {backup_file}")
                return True
            else:
                logger.warning("No configuration file to backup")
                return False
        except Exception as e:
            logger.error(f"Error creating configuration backup: {str(e)}")
            return False
    
    def verify_api_configurations(self):
        """Verify API configurations and return status"""
        try:
            # Check Azure Speech Services
            azure_api_key = self.get_value("recognition", "azure_api_key", "")
            azure_region = self.get_value("recognition", "azure_region", "")
            azure_configured = bool(azure_api_key and azure_region)
            
            # Check Whisper API
            whisper_api_key = self.get_value("recognition", "whisper_api_key", "")
            whisper_configured = bool(whisper_api_key)
            
            # Check Google Speech-to-Text
            google_credentials_path = self.get_value("recognition", "google_credentials_path", "")
            google_configured = bool(google_credentials_path and os.path.exists(google_credentials_path))
            
            # Check Azure Translator
            azure_translator_key = self.get_value("translation", "azure_translator_key", "")
            azure_translator_region = self.get_value("translation", "azure_translator_region", "")
            azure_translator_configured = bool(azure_translator_key and azure_translator_region)
            
            # Check Azure OpenAI
            azure_openai_key = self.get_value("translation", "azure_openai_key", "")
            azure_openai_endpoint = self.get_value("translation", "azure_openai_endpoint", "")
            azure_openai_configured = bool(azure_openai_key and azure_openai_endpoint)
            
            return {
                "azure_speech": azure_configured,
                "whisper_api": whisper_configured,
                "google_speech": google_configured,
                "azure_translator": azure_translator_configured,
                "azure_openai": azure_openai_configured
            }
        except Exception as e:
            logger.error(f"Error verifying API configurations: {str(e)}")
            return {
                "azure_speech": False,
                "whisper_api": False,
                "google_speech": False,
                "azure_translator": False,
                "azure_openai": False
            } 