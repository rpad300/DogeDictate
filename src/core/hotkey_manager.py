#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hotkey Manager for DogeDictate
Handles keyboard shortcuts for dictation control
"""

import logging
import time
import threading
from pynput import keyboard
from pynput import mouse
from typing import Dict, List, Optional, Tuple, Any, Callable
import traceback
from .language_rules import LanguageRulesManager

logger = logging.getLogger("DogeDictate.HotkeyManager")

class HotkeyManager:
    """Manages hotkeys for controlling dictation"""
    
    # Mapping of key names between pynput and our config
    KEY_MAPPING = {
        "ctrl": keyboard.Key.ctrl,
        "shift": keyboard.Key.shift,
        "alt": keyboard.Key.alt,
        "cmd": keyboard.Key.cmd,
        "caps_lock": keyboard.Key.caps_lock,
        "space": keyboard.Key.space,
        # Mouse buttons
        "mouse_left": "mouse_left",
        "mouse_right": "mouse_right",
        "mouse_middle": "mouse_middle",
        "mouse_forward": "mouse_forward",
        "mouse_back": "mouse_back",
        # Add more special keys as needed
    }
    
    # Initialize logger at class level
    logger = logging.getLogger("DogeDictate.HotkeyManager")
    
    def __init__(self, config_manager, dictation_manager=None, language_rules=None):
        """Initialize the HotkeyManager
        
        Args:
            config_manager (ConfigManager): The configuration manager
            dictation_manager (DictationManager, optional): The dictation manager
            language_rules (LanguageRulesManager, optional): The language rules manager
        """
        try:
            # Initialize instance variables
            self.config_manager = config_manager
            self.dictation_manager = dictation_manager
            self.language_rules = language_rules
            
            # Set up the dictionary of currently pressed keys
            self.current_keys = set()
            
            # Load configuration from the config manager
            self.load_config()
            
            # Threading variables
            self.is_listening_value = False
            self.keyboard_listener = None
            self.mouse_listener = None
            
            # Set up signal handlers
            self.handlers = {}
            
            # Initialize listeners
            self.valid_hotkeys = []
            self.language_hotkeys_dict = {}  # Dictionary for quick lookup
            self._create_language_hotkeys_dict()
            self._register_valid_hotkeys()
            
            # Inicializar variáveis para debounce
            self.push_to_talk_active = False
            self.push_to_talk_debounce = 0.5  # Tempo em segundos para prevenir ativações duplicadas
            self.key_press_times = {}  # Armazenar o tempo do último pressionamento de cada tecla
            
            # Button timeout checker
            self.button_timeout_thread = None
            self.button_timeout_running = False
            
            self.logger.info("Hotkey manager initialized")
        except Exception as e:
            # Use a print statement if logger might not be initialized yet
            print(f"Error initializing hotkey manager: {str(e)}")
            print(traceback.format_exc())
    
    def _create_language_hotkeys_dict(self):
        """Create a dictionary of language hotkeys for quick lookup"""
        self.language_hotkeys_dict = {hotkey.get('key'): hotkey for hotkey in self.language_hotkeys}
        self.logger.debug(f"Created language_hotkeys_dict with {len(self.language_hotkeys_dict)} entries")
    
    def _register_valid_hotkeys(self):
        """Register all valid hotkeys for monitoring"""
        try:
            self.valid_hotkeys = []
            
            # Register push-to-talk hotkey
            if 'key' in self.push_to_talk and self.push_to_talk['key']:
                if self.push_to_talk['key'] == 'mouse_forward':
                    self.valid_hotkeys.append(('mouse', self.push_to_talk['key']))
                else:
                    self.valid_hotkeys.append(('keyboard', self.push_to_talk['key']))
                self.logger.info(f"Registered push-to-talk hotkey: {self.push_to_talk['key']} with modifiers: {self.push_to_talk.get('modifiers', [])}")
            
            # Register hands-free hotkey
            if 'key' in self.hands_free and self.hands_free['key']:
                self.valid_hotkeys.append(('keyboard', self.hands_free['key']))
                self.logger.info(f"Registered hands-free hotkey: {self.hands_free['key']} with modifiers: {self.hands_free.get('modifiers', [])}")
            
            # Register language hotkeys
            for i, hotkey in enumerate(self.language_hotkeys):
                if 'key' in hotkey and hotkey['key']:
                    if hotkey['key'].startswith('mouse_'):
                        self.valid_hotkeys.append(('mouse', hotkey['key']))
                    else:
                        self.valid_hotkeys.append(('keyboard', hotkey['key']))
                    self.logger.info(f"Registered language hotkey #{i}: {hotkey['key']} with modifiers: {hotkey.get('modifiers', [])} for language: {hotkey.get('language', 'unknown')}")
            
            # Register common modifiers
            for mod in ['ctrl', 'shift', 'alt']:
                self.valid_hotkeys.append(('keyboard', mod))
                self.logger.info(f"Registered modifier key: {mod}")
            
            # Register special keys
            self.valid_hotkeys.append(('keyboard', 'caps_lock'))
            self.logger.info(f"Registered special key: caps_lock")
            
            # Debug log
            self.logger.warning(f"Registered valid hotkeys: {self.valid_hotkeys}")
        except Exception as e:
            self.logger.error(f"Error registering valid hotkeys: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    @property
    def is_listening(self):
        """Check if the hotkey listener is active"""
        return self.is_listening_value and self.keyboard_listener and self.keyboard_listener.is_alive()
    
    def start_listening(self):
        """Start the hotkey listener (alias for start)"""
        self.start()
    
    def stop_listening(self):
        """Stop the hotkey listener (alias for stop)"""
        self.stop()
    
    def start(self):
        """Start the hotkey listener"""
        try:
            if not hasattr(self, 'keyboard_listener') or self.keyboard_listener is None:
                self.logger.info("Iniciando listener de teclado...")
                # Iniciar o listener de teclado
                self.keyboard_listener = keyboard.Listener(
                    on_press=self._on_key_press,
                    on_release=self._on_key_release,
                    # Não usamos suppress=True para evitar conflitos com outras aplicações
                    suppress=False
                )
                self.keyboard_listener.start()
                
                # Iniciar o listener de mouse para as teclas de mouse
                try:
                    self.mouse_listener = mouse.Listener(
                        on_click=self._on_mouse_click
                    )
                    self.mouse_listener.start()
                    self.logger.info("Mouse listener started")
                except Exception as e:
                    self.logger.error(f"Failed to start mouse listener: {str(e)}")
                    self.logger.error(traceback.format_exc())
                
                self.is_listening_value = True
                self.logger.info("Hotkey listener started")
                
                # Definir timeout thread como ativo
                self.button_timeout_running = True
                
                # Iniciar o thread de verificação de timeout de botões se necessário
                if not self.button_timeout_thread or not self.button_timeout_thread.is_alive():
                    self.button_timeout_thread = threading.Timer(5.0, self._check_button_timeouts)
                    self.button_timeout_thread.daemon = True
                    self.button_timeout_thread.start()
                    self.logger.debug("Button timeout checker started")
            else:
                self.logger.info("Hotkey listener already running")
        except Exception as e:
            self.logger.error(f"Failed to start hotkey listener: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.is_listening_value = False
    
    def _check_button_timeouts(self):
        """Verifica se algum botão está pressionado por muito tempo"""
        try:
            if not self.button_timeout_running:
                return
                
            current_time = time.time()
            keys_to_release = []
            
            # Verificar se alguma tecla está pressionada por muito tempo
            for key in self.current_keys:
                if key in self.key_press_times:
                    press_time = self.key_press_times[key]
                    duration = current_time - press_time
                    max_duration = 20.0  # 20 segundos por padrão
                    
                    # Se estiver pressionada por muito tempo, programar para liberar
                    if duration > max_duration:
                        self.logger.warning(f"Key {key} has been pressed for {duration:.1f}s, forcing release")
                        keys_to_release.append(key)
            
            # Liberar teclas presas
            for key in keys_to_release:
                self._force_key_release(key)
                
            # Reagendar a verificação
            if self.button_timeout_running:
                self.button_timeout_thread = threading.Timer(5.0, self._check_button_timeouts)
                self.button_timeout_thread.daemon = True
                self.button_timeout_thread.start()
                
        except Exception as e:
            self.logger.error(f"Error in button timeout checker: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # Tenta reagendar mesmo em caso de erro
            if self.button_timeout_running:
                threading.Timer(5.0, self._check_button_timeouts).start()
    
    def _force_key_release(self, key):
        """Força a liberação de uma tecla que está presa"""
        try:
            if key in self.current_keys:
                self.current_keys.remove(key)
                
            if key in self.key_press_times:
                del self.key_press_times[key]
                
            self.logger.info(f"Forced release of key: {key}")
            
            # Se for a tecla de push-to-talk, desativar o modo
            if key == self.push_to_talk_key and self.push_to_talk_active:
                self.push_to_talk_active = False
                self.logger.info("Forced deactivation of push-to-talk mode")
                
                # Notificar o dictation_manager para parar a gravação
                if self.dictation_manager:
                    self.logger.info("Notifying dictation manager to stop recording")
                    self.emit("stop_dictation")
        except Exception as e:
            self.logger.error(f"Error forcing key release: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def stop(self):
        """Stop the hotkey listener"""
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
                
                # Parar o listener de mouse se estiver ativo
                if hasattr(self, 'mouse_listener') and self.mouse_listener:
                    self.mouse_listener.stop()
                    self.mouse_listener = None
                
                # Parar o thread de verificação de timeout de botões
                self.button_timeout_running = False
                self.logger.info("Button timeout checker stopped")
                
                # Limpar estados
                self.current_keys = set()
                self.push_to_talk_active = False
                self.key_press_times.clear()
                
                self.is_listening_value = False
                self.logger.info("Hotkey listener stopped")
            except Exception as e:
                self.logger.error(f"Failed to stop hotkey listener: {str(e)}")
                self.logger.error(traceback.format_exc())
                self.is_listening_value = False
    
    def update_hotkey(self, hotkey_type, key, modifiers):
        """Update a hotkey configuration"""
        try:
            # Normalizar a entrada
            if not isinstance(modifiers, list):
                modifiers = []
            
            # Criar configuração normalizada
            hotkey_config = {"key": key, "modifiers": modifiers}
            
            if hotkey_type == "push_to_talk":
                self.push_to_talk = hotkey_config
                self.config_manager.set_value("hotkeys", "push_to_talk", self.push_to_talk)
                self.logger.info(f"Updated push-to-talk hotkey: key={key}, modifiers={modifiers}")
                result = True
            elif hotkey_type == "hands_free" or hotkey_type == "toggle_dictation":
                self.hands_free = hotkey_config
                self.config_manager.set_value("hotkeys", "toggle_dictation", self.hands_free)
                self.logger.info(f"Updated hands-free hotkey: key={key}, modifiers={modifiers}")
                result = True
            else:
                self.logger.error(f"Unknown hotkey type: {hotkey_type}")
                result = False
            
            if result:
                # Limpar o estado atual para evitar problemas
                self.current_keys = set()
                
                # Salvar configuração
                self.config_manager.save_config()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error updating hotkey configuration: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def update_language_hotkey(self, index, key, modifiers, language):
        """Update a language hotkey configuration"""
        try:
            # Obter a lista atual de hotkeys de linguagem
            language_hotkeys = self.config_manager.get_value("hotkeys", "language_hotkeys", [])
            
            # Verificar se language_hotkeys é uma lista válida
            if not isinstance(language_hotkeys, list):
                self.logger.error(f"Invalid language_hotkeys configuration: {language_hotkeys}, resetting to empty list")
                language_hotkeys = []
            
            # Criar a configuração da hotkey
            hotkey_config = {"key": key, "modifiers": modifiers, "language": language}
            
            # Atualizar ou adicionar a hotkey
            if 0 <= index < len(language_hotkeys):
                language_hotkeys[index] = hotkey_config
            else:
                language_hotkeys.append(hotkey_config)
            
            # Salvar a lista completa de hotkeys de linguagem
            result = self.config_manager.set_value("hotkeys", "language_hotkeys", language_hotkeys)
            
            # Atualizar a lista local
            if result:
                self.language_hotkeys = language_hotkeys
                self.logger.info(f"Updated language hotkey at index {index}: key={key}, modifiers={modifiers}, language={language}")
            
            # Salvar a configuração
            self.config_manager.save_config()
            
            # Limpar o dicionário de teclas de idioma pressionadas para evitar problemas
            self.language_pressed = {}
            
            # Log para depuração
            self.logger.info(f"Language hotkeys after update: {self.language_hotkeys}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error updating language hotkey configuration: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def reload_config(self):
        """Reload configuration from config manager"""
        try:
            # Load language hotkeys
            language_hotkeys = self.config_manager.get_value("hotkeys", "language_hotkeys", [])
            
            # Convert to list if dictionary
            if isinstance(language_hotkeys, dict):
                language_hotkeys = [language_hotkeys]
                
            self.language_hotkeys = language_hotkeys
            
            # Create dictionary for easier lookup
            self._create_language_hotkeys_dict()
            
            # Log language hotkeys
            self._log_language_hotkeys()
            
            # Set language keys from hotkeys
            self.language_keys = {}
            for lh in self.language_hotkeys:
                if "key" in lh and "language" in lh:
                    self.language_keys[lh["key"]] = lh["language"]
                    
            # Load push to talk and hands free hotkeys
            self.push_to_talk = self._get_hotkey_from_config("push_to_talk", {"key": "alt", "modifiers": []})
            self.hands_free = self._get_hotkey_from_config("toggle_dictation", {"key": "f9", "modifiers": []})
            
            # Extract key from push_to_talk for easier access
            self.push_to_talk_key = self.push_to_talk.get("key", "alt")
            
            # Atalho para conveniência: extrair a tecla principal para hands_free (toggle)
            self.toggle_key = self.hands_free.get("key", "f9")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error reloading configuration: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
            
    def _get_hotkey_from_config(self, hotkey_name, default_value):
        """Get a hotkey configuration from the config manager
        
        Args:
            hotkey_name (str): The name of the hotkey config to retrieve
            default_value (dict): Default value if not found
            
        Returns:
            dict: The hotkey configuration
        """
        try:
            # Primeiro tenta com o nome exato
            hotkey = self.config_manager.get_value("hotkeys", hotkey_name, default_value)
            
            # Se não encontrado e for toggle_dictation, tenta com hands_free (compatibilidade)
            if not hotkey and hotkey_name == "toggle_dictation":
                hotkey = self.config_manager.get_value("hotkeys", "hands_free", default_value)
                
            # Normaliza o formato
            return self._normalize_hotkey_format(hotkey)
        except Exception as e:
            logger.error(f"Error getting hotkey {hotkey_name} from config: {str(e)}")
            return self._normalize_hotkey_format(default_value)
    
    def _normalize_hotkey_format(self, hotkey):
        """Normalize hotkey format to dictionary with key and modifiers
        
        Args:
            hotkey: Hotkey configuration to normalize
            
        Returns:
            dict: Normalized hotkey configuration
        """
        try:
            # If hotkey is already a dictionary, ensure it has the required fields
            if isinstance(hotkey, dict):
                # Ensure 'key' field exists
                if 'key' not in hotkey:
                    hotkey['key'] = ''
                
                # Ensure 'modifiers' field exists and is a list
                if 'modifiers' not in hotkey or not isinstance(hotkey['modifiers'], list):
                    hotkey['modifiers'] = []
                
                return hotkey
            # If hotkey is a string, convert to dictionary
            elif isinstance(hotkey, str):
                return {'key': hotkey, 'modifiers': []}
            # If hotkey is None, return empty dictionary
            elif hotkey is None:
                return {'key': '', 'modifiers': []}
            else:
                self.logger.error(f"Invalid hotkey format: {hotkey}")
                return {'key': '', 'modifiers': []}
        except Exception as e:
            self.logger.error(f"Error normalizing hotkey format: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {'key': '', 'modifiers': []}
    
    def _convert_key(self, key):
        """Convert a key object to a string representation"""
        try:
            # Diagnóstico específico para a tecla Ctrl
            if isinstance(key, keyboard.Key) and key in [keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]:
                self.logger.debug(f"DIAGNÓSTICO _convert_key: Tecla CTRL detectada: {key}")
            
            # Mapeamento de teclas especiais
            special_keys = {
                keyboard.Key.alt: "alt",
                keyboard.Key.alt_l: "alt",
                keyboard.Key.alt_r: "alt",
                keyboard.Key.alt_gr: "alt_gr",
                keyboard.Key.backspace: "backspace",
                keyboard.Key.caps_lock: "caps_lock",
                keyboard.Key.cmd: "cmd",
                keyboard.Key.cmd_l: "cmd",
                keyboard.Key.cmd_r: "cmd",
                keyboard.Key.ctrl: "ctrl",
                keyboard.Key.ctrl_l: "ctrl",
                keyboard.Key.ctrl_r: "ctrl",
                keyboard.Key.delete: "delete",
                keyboard.Key.down: "down",
                keyboard.Key.end: "end",
                keyboard.Key.enter: "enter",
                keyboard.Key.esc: "esc",
                keyboard.Key.f1: "f1",
                keyboard.Key.home: "home",
                keyboard.Key.left: "left",
                keyboard.Key.page_down: "page_down",
                keyboard.Key.page_up: "page_up",
                keyboard.Key.right: "right",
                keyboard.Key.shift: "shift",
                keyboard.Key.shift_l: "shift",
                keyboard.Key.shift_r: "shift",
                keyboard.Key.space: "space",
                keyboard.Key.tab: "tab",
                keyboard.Key.up: "up"
            }
            
            # Verificar se é um botão do mouse
            if hasattr(key, 'button'):
                try:
                    return self._get_mouse_button_name(key.button)
                except Exception as e:
                    logger.error(f"Error handling mouse button: {str(e)}")
            
            # Verificar se é uma tecla especial conhecida
            if key in special_keys:
                result = special_keys[key]
                # Log mais detalhado para a tecla Ctrl
                if result == "ctrl":
                    self.logger.debug(f"DIAGNÓSTICO _convert_key: Tecla especial CTRL convertida para '{result}'")
                else:
                    self.logger.debug(f"Converted special key {key} to '{result}'")
                return result
            
            # Tentar obter o caractere da tecla
            try:
                result = key.char.lower()
                self.logger.debug(f"Converted character key {key} to '{result}'")
                return result
            except AttributeError:
                # Log unknown key for debugging
                self.logger.debug(f"Unknown key: {key}")
                return ""
        
        except Exception as e:
            self.logger.error(f"Error converting key: {str(e)}")
            self.logger.error(traceback.format_exc())
            return ""
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Handler for mouse click events
        
        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            button: The mouse button
            pressed: Whether the button was pressed or released
        """
        try:
            # Obter o nome do botão
            button_name = self._get_mouse_button_name(button)
            
            # Verificar se é mouse_forward
            is_forward_button = (
                button_name == 'mouse_forward' or
                button_name == 'mouse_x2' or
                'x2' in button_name or
                'forward' in button_name
            )
            
            # Se for forward button, usar sempre mouse_forward como nome padrão
            if is_forward_button:
                button_name = 'mouse_forward'
                self.logger.debug(f"Mouse forward button detectado e normalizado para 'mouse_forward'")
            
            # Verificar se é o botão de push-to-talk específico
            push_to_talk_key = None
            if self.push_to_talk and 'key' in self.push_to_talk:
                push_to_talk_key = self.push_to_talk['key']

            # Verificar se é uma language hotkey
            is_language_hotkey = button_name in self.language_hotkeys_dict
            
            # Se for pressionado, adicionar à lista de teclas pressionadas
            if pressed:
                if button_name not in self.current_keys:
                    self.current_keys.add(button_name)
                    self.logger.debug(f"Adicionado botão {button_name} à lista de teclas pressionadas")
                
                # Armazenar hora do pressionamento para debounce
                current_time = time.time()
                self.key_press_times[button_name] = current_time
            else:
                # Se for liberado, remover da lista de teclas pressionadas
                if button_name in self.current_keys:
                    self.current_keys.remove(button_name)
                    self.logger.debug(f"Removido botão {button_name} da lista de teclas pressionadas")
            
            # Verificar modificadores necessários para botões configurados
            required_modifiers = []
            
            if is_language_hotkey and 'modifiers' in self.language_hotkeys_dict[button_name]:
                required_modifiers = self.language_hotkeys_dict[button_name]['modifiers']
            elif button_name == push_to_talk_key and 'modifiers' in self.push_to_talk:
                required_modifiers = self.push_to_talk['modifiers']
            
            # Verificar se todos os modificadores necessários estão pressionados
            all_modifiers_pressed = True
            for modifier in required_modifiers:
                if modifier not in self.current_keys:
                    all_modifiers_pressed = False
                    self.logger.debug(f"Modificador {modifier} necessário para {button_name} não está pressionado")
                    break
            
            # Tratar todos os botões de mouse configurados como push-to-talk
            if (is_language_hotkey or (button_name == push_to_talk_key)) and all_modifiers_pressed:
                if pressed:
                    # Iniciar gravação com o idioma apropriado
                    if is_language_hotkey:
                        self.logger.info(f"Tecla de idioma pressionada: {button_name}")
                        self._force_language_hotkey_activation(button_name)
                    else:
                        self.logger.info(f"Push-to-talk pressionado: {button_name}")
                        self._force_push_to_talk_activation(button_name)
                else:
                    # Parar gravação ao soltar o botão
                    if is_language_hotkey:
                        self.logger.info(f"Tecla de idioma liberada: {button_name}")
                        self._force_language_hotkey_deactivation(button_name)
                    else:
                        self.logger.info(f"Push-to-talk liberado: {button_name}")
                        self._force_push_to_talk_deactivation(button_name)
            
        except Exception as e:
            self.logger.error(f"Error handling mouse click: {str(e)}")
            self.logger.error(traceback.format_exc())
            
    def _force_language_hotkey_activation(self, key_name):
        """Força a ativação de uma tecla de idioma com comportamento push-to-talk
        
        Args:
            key_name: The name of the language hotkey
        """
        try:
            # Parar qualquer gravação em andamento
            if self.dictation_manager:
                try:
                    is_recording = False
                    try:
                        is_recording = self.dictation_manager.is_recording
                    except Exception as e:
                        self.logger.error(f"Erro verificando gravação: {str(e)}")
                    
                    if is_recording:
                        self.logger.info("Parando gravação anterior antes de iniciar nova com idioma específico")
                        self.dictation_manager.stop_dictation()
                        time.sleep(0.1)
                except Exception as e:
                    self.logger.error(f"Erro parando gravação anterior: {str(e)}")
            
            # Definir idioma específico da tecla de idioma
            try:
                if key_name in self.language_hotkeys_dict:
                    language_settings = self.language_hotkeys_dict[key_name]
                    self.logger.info(f"Definindo idioma a partir da tecla {key_name}: {language_settings.get('language')}")
                    
                    if self.language_rules and self.dictation_manager:
                        self.language_rules.apply_language_settings(self.dictation_manager, "language_hotkey", language_settings)
                    else:
                        self.logger.error("Não foi possível definir idioma: gerenciador não disponível")
                else:
                    self.logger.error(f"Tecla de idioma não encontrada: {key_name}")
            except Exception as e:
                self.logger.error(f"Erro definindo idioma para tecla {key_name}: {str(e)}")
            
            # Iniciar gravação com o novo idioma
            if self.dictation_manager:
                try:
                    time.sleep(0.05)  # Pequena pausa para garantir que as configurações de idioma foram aplicadas
                    self.logger.info(f"Iniciando ditado com idioma da tecla {key_name}")
                    self.emit("start_dictation")
                except Exception as e:
                    self.logger.error(f"Erro iniciando ditado: {str(e)}")
            else:
                self.logger.error("Dictation manager não disponível")
            
        except Exception as e:
            self.logger.error(f"Erro na ativação de tecla de idioma {key_name}: {str(e)}")
            self.logger.error(traceback.format_exc())
            
    def _force_language_hotkey_deactivation(self, key_name):
        """Força a desativação de uma tecla de idioma com comportamento push-to-talk
        
        Args:
            key_name: The name of the language hotkey
        """
        try:
            # Parar a gravação
            if self.dictation_manager:
                try:
                    self.logger.info(f"Parando ditado (liberação de tecla de idioma {key_name})")
                    self.emit("stop_dictation")
                except Exception as e:
                    self.logger.error(f"Erro parando ditado: {str(e)}")
            else:
                self.logger.error("Dictation manager não disponível")
                
        except Exception as e:
            self.logger.error(f"Erro na desativação de tecla de idioma {key_name}: {str(e)}")
            self.logger.error(traceback.format_exc())
            
    def _on_key_press(self, key):
        """Handler for key press events"""
        try:
            # Converter a tecla para um nome mais amigável
            key_name = self._convert_key(key)
            
            # Ignorar teclas vazias ou inválidas
            if not key_name:
                return
                
            # Processar o evento internamente
            self._on_key_press_internal(key_name)
            
        except Exception as e:
            self.logger.error(f"Error handling key press: {str(e)}")
            self.logger.error(traceback.format_exc())
            
    def _on_key_press_internal(self, key_name):
        """Processamento interno de tecla pressionada"""
        try:
            # Verificar se a tecla é um modificador (ctrl, alt, shift)
            is_modifier = key_name in ['ctrl', 'alt', 'shift', 'cmd']
            
            # Apenas adicionar à lista de teclas pressionadas se for um modificador ou tecla configurada
            if is_modifier or (
                key_name == self.push_to_talk_key or 
                key_name == self.toggle_key or 
                key_name in self.language_hotkeys_dict
            ):
                # Adicionar tecla à lista de teclas pressionadas se ainda não estiver
                if key_name not in self.current_keys:
                    self.current_keys.add(key_name)
                    self.logger.debug(f"Adicionada tecla {key_name} à lista de teclas pressionadas")
                
                # Armazenar hora do pressionamento para debounce
                current_time = time.time()
                self.key_press_times[key_name] = current_time
            
            # Verificar se a tecla está configurada para alguma ação
            is_push_to_talk = key_name == self.push_to_talk_key
            is_toggle = key_name == self.toggle_key
            is_language_hotkey = key_name in self.language_hotkeys_dict
            
            # Verificar modificadores necessários para teclas configuradas
            required_modifiers = []
            
            if is_push_to_talk and 'modifiers' in self.push_to_talk:
                required_modifiers = self.push_to_talk['modifiers']
            elif is_toggle and 'modifiers' in self.hands_free:
                required_modifiers = self.hands_free['modifiers']
            elif is_language_hotkey and 'modifiers' in self.language_hotkeys_dict[key_name]:
                required_modifiers = self.language_hotkeys_dict[key_name]['modifiers']
            
            # Verificar se todos os modificadores necessários estão pressionados
            all_modifiers_pressed = True
            for modifier in required_modifiers:
                if modifier not in self.current_keys:
                    all_modifiers_pressed = False
                    self.logger.debug(f"Modificador {modifier} necessário para {key_name} não está pressionado")
                    break
            
            # Se a tecla for configurada e todos os modificadores necessários estiverem pressionados
            if is_push_to_talk and all_modifiers_pressed:
                # Tratamento especial para ctrl push-to-talk
                self.logger.info(f"Tecla push-to-talk pressionada: {key_name}")
                self._force_push_to_talk_activation(key_name)
            elif is_toggle and all_modifiers_pressed:
                self._handle_toggle_key(key_name)
            elif is_language_hotkey and all_modifiers_pressed:
                self.logger.info(f"Tecla de idioma pressionada (teclado): {key_name}")
                self._force_language_hotkey_activation(key_name)
            
        except Exception as e:
            self.logger.error(f"Error in _on_key_press_internal: {str(e)}")
            self.logger.error(traceback.format_exc())
            
    def _on_key_release(self, key):
        """Handler for key release events"""
        try:
            # Converter a tecla para um nome mais amigável
            key_name = self._convert_key(key)
            
            # Ignorar teclas vazias ou inválidas
            if not key_name:
                return
                
            # Processar o evento internamente
            self._on_key_release_internal(key_name)
            
        except Exception as e:
            self.logger.error(f"Error handling key release: {str(e)}")
            self.logger.error(traceback.format_exc())
            
    def _on_key_release_internal(self, key_name):
        """Processamento interno de tecla liberada"""
        try:
            # Remover da lista de teclas pressionadas
            if key_name in self.current_keys:
                self.current_keys.remove(key_name)
                self.logger.debug(f"Removed key {key_name} from current keys list")
            
            # Verificar se é o botão de push-to-talk
            is_push_to_talk = key_name == self.push_to_talk_key
            
            # Verificar se é uma tecla de idioma
            is_language_hotkey = key_name in self.language_hotkeys_dict
            
            # Verificar se os modificadores necessários estão (ou estavam) pressionados
            # para teclas de idioma e push-to-talk
            required_modifiers = []
            
            if is_push_to_talk and 'modifiers' in self.push_to_talk:
                required_modifiers = self.push_to_talk['modifiers']
            elif is_language_hotkey and 'modifiers' in self.language_hotkeys_dict[key_name]:
                required_modifiers = self.language_hotkeys_dict[key_name]['modifiers']
            
            # Se a tecla é modificador, verificar se é usada em alguma combinação ativa
            if key_name in ['ctrl', 'alt', 'shift', 'cmd']:
                self._check_key_combinations_on_modifier_release(key_name)
            
            # Para teclas com modificadores, verificar se todos modificadores estão (ou estavam) pressionados
            # Um modificador pode ter sido liberado logo antes da tecla principal
            all_modifiers_active = True
            missing_modifiers = []
            
            for modifier in required_modifiers:
                if modifier not in self.current_keys and modifier != key_name:
                    all_modifiers_active = False
                    missing_modifiers.append(modifier)
            
            if not all_modifiers_active and required_modifiers:
                self.logger.debug(f"Ignorando liberação de {key_name} porque faltam modificadores: {missing_modifiers}")
                return
            
            # Se for uma tecla de push-to-talk, desativar
            if is_push_to_talk:
                self.logger.info(f"Tecla push-to-talk liberada: {key_name}")
                self._force_push_to_talk_deactivation(key_name)
            # Se for uma tecla de idioma, encerrar o ditado de idioma
            elif is_language_hotkey:
                self.logger.info(f"Tecla de idioma liberada (teclado): {key_name}")
                self._force_language_hotkey_deactivation(key_name)
            
        except Exception as e:
            self.logger.error(f"Error in _on_key_release_internal: {str(e)}")
            self.logger.error(traceback.format_exc())
            
    def _check_key_combinations_on_modifier_release(self, modifier_key):
        """Verifica se alguma combinação de teclas estava ativa com este modificador"""
        try:
            # Verificar push-to-talk
            if self.push_to_talk_key != modifier_key and 'modifiers' in self.push_to_talk:
                if modifier_key in self.push_to_talk['modifiers'] and self.push_to_talk_key in self.current_keys:
                    self.logger.info(f"Liberando push-to-talk porque o modificador {modifier_key} foi liberado")
                    self._force_push_to_talk_deactivation(self.push_to_talk_key)
            
            # Verificar teclas de idioma
            for key, config in self.language_hotkeys_dict.items():
                if key != modifier_key and 'modifiers' in config:
                    if modifier_key in config['modifiers'] and key in self.current_keys:
                        self.logger.info(f"Liberando tecla de idioma {key} porque o modificador {modifier_key} foi liberado")
                        self._force_language_hotkey_deactivation(key)
        
        except Exception as e:
            self.logger.error(f"Error checking key combinations on modifier release: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _handle_push_to_talk(self, key_name):
        """Handler for push-to-talk key press
        
        Args:
            key_name: The name of the push-to-talk key
        """
        try:
            # Verificar se já está ativo
            if self.push_to_talk_active:
                self.logger.debug("Push-to-talk already active, ignoring")
                return
            
            # Ativar push-to-talk
            self.push_to_talk_active = True
            self.logger.info("Push-to-talk activated")
            
            # Verificar se devemos definir o idioma
            try:
                # Definir idioma de acordo com a tecla pressionada
                self._set_language_for_push_to_talk(key_name)
                
                # Iniciar a ditado se o dictation_manager existir
                if self.dictation_manager:
                    # Verificar se já está gravando para evitar iniciar novamente
                    is_recording = False
                    try:
                        is_recording = self.dictation_manager.is_recording
                    except Exception as e:
                        self.logger.error(f"Error checking if dictation is already recording: {str(e)}")
                    
                    if not is_recording:
                        self.logger.info("Starting dictation")
                        self.emit("start_dictation")
                    else:
                        self.logger.debug("Dictation already recording, not starting again")
                else:
                    self.logger.error("No dictation manager available")
            except Exception as e:
                self.logger.error(f"Error setting language or starting dictation: {str(e)}")
                self.logger.error(traceback.format_exc())
            
        except Exception as e:
            self.logger.error(f"Error handling push-to-talk: {str(e)}")
            self.logger.error(traceback.format_exc())
            
    def _handle_push_to_talk_release(self, key_name):
        """Handler for push-to-talk key release
        
        Args:
            key_name: The name of the push-to-talk key
        """
        try:
            # Verificar se está ativo
            if not self.push_to_talk_active:
                self.logger.debug("Push-to-talk not active, ignoring release")
                return
            
            # Desativar push-to-talk
            self.push_to_talk_active = False
            self.logger.info("Push-to-talk deactivated")
            
            # Parar a ditado se o dictation_manager existir
            if self.dictation_manager:
                # Verificar se está gravando antes de tentar parar
                is_recording = False
                try:
                    is_recording = self.dictation_manager.is_recording
                except Exception as e:
                    self.logger.error(f"Error checking if dictation is recording: {str(e)}")
                
                if is_recording:
                    self.logger.info("Stopping dictation")
                    self.emit("stop_dictation")
                else:
                    self.logger.debug("Dictation not recording, no need to stop")
            else:
                self.logger.error("No dictation manager available")
            
        except Exception as e:
            self.logger.error(f"Error handling push-to-talk release: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _handle_toggle_key(self, key_name):
        """Handler for toggle key press
        
        Args:
            key_name: The name of the toggle key
        """
        try:
            # Se o dictation_manager não estiver disponível, não fazer nada
            if not self.dictation_manager:
                self.logger.error("No dictation manager available")
                return
            
            # Verificar o estado atual da ditado hands-free
            is_recording = self.dictation_manager.is_recording
            
            # Alternar o estado
            if is_recording:
                self.logger.info("Stopping hands-free dictation")
                self.emit("stop_dictation")
            else:
                self.logger.info("Starting hands-free dictation")
                # Definir idioma padrão para hands-free
                self.language_rules.apply_language_settings(self.dictation_manager, "default")
                self.emit("start_dictation")
            
        except Exception as e:
            self.logger.error(f"Error handling toggle key: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _set_language_and_translation_for_key(self, key_name):
        """Set the language and translation settings based on the key pressed
        
        Args:
            key_name (str): The name of the key pressed
        """
        try:
            # If it's a language hotkey, use the language from the hotkey
            if key_name in self.language_hotkeys_dict:
                language = self.language_hotkeys_dict[key_name].get("language")
                self.logger.info(f"Setting language from hotkey {key_name}: {language}")
                self.language_rules.apply_language_settings(self.dictation_manager, "language_hotkey", 
                                                           self.language_hotkeys_dict[key_name])
            # If it's the push-to-talk key, use the language rules for push-to-talk
            elif key_name == self.push_to_talk_key:
                self.logger.info(f"Setting language for push-to-talk key: {key_name}")
                self.language_rules.apply_language_settings(self.dictation_manager, "push_to_talk")
            else:
                # Use default language settings
                self.logger.info(f"No specific language for key {key_name}, using default settings")
                self.language_rules.apply_language_settings(self.dictation_manager, "default")
        except Exception as e:
            self.logger.error(f"Error setting language for key {key_name}: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _set_language_for_push_to_talk(self, key_name=None):
        """Define o idioma com base na tecla de push-to-talk pressionada
        
        Esta função é um wrapper para _set_language_and_translation_for_key
        que é chamada quando uma tecla de push-to-talk é pressionada.
        
        Args:
            key_name (str, optional): Nome da tecla de push-to-talk pressionada. 
                                     Se não for fornecido, usa self.push_to_talk_key.
        """
        try:
            self.logger.info("Setting language for push-to-talk")
            
            # Se key_name não foi fornecido, usar o push_to_talk_key padrão
            if key_name is None:
                key_name = self.push_to_talk_key
                
            # Usar o método existente para definir o idioma
            self._set_language_and_translation_for_key(key_name)
            
        except Exception as e:
            self.logger.error(f"Error in _set_language_for_push_to_talk: {str(e)}")
            self.logger.error(traceback.format_exc())

    def load_config(self):
        """Carrega a configuração do gerenciador de configuração"""
        try:
            # Load language hotkeys
            self.language_hotkeys = self.config_manager.get_value("hotkeys", "language_hotkeys", [])
            
            # Convert to list if dictionary
            if isinstance(self.language_hotkeys, dict):
                self.language_hotkeys = [self.language_hotkeys]
                
            # Create language hotkeys dict
            self._create_language_hotkeys_dict()
            
            # Load push to talk and hands free hotkeys
            self.push_to_talk = self._get_hotkey_from_config("push_to_talk", {"key": "alt", "modifiers": []})
            self.hands_free = self._get_hotkey_from_config("toggle_dictation", {"key": "f9", "modifiers": []})
            
            # Extract key from push_to_talk for easier access
            self.push_to_talk_key = self.push_to_talk.get("key", "alt")
            
            # Atalho para conveniência: extrair a tecla principal para hands_free (toggle)
            self.toggle_key = self.hands_free.get("key", "f9")
            
            self.logger.info(f"Configuração carregada: push_to_talk={self.push_to_talk}, hands_free={self.hands_free}")
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def _get_mouse_button_name(self, button):
        """Converte um objeto de botão do mouse para um nome amigável
        
        Args:
            button: O objeto de botão do mouse
            
        Returns:
            str: O nome do botão
        """
        try:
            # Log detalhado para diagnóstico de todos os botões
            self.logger.info(f"Mouse button raw: {button}, type={type(button)}")
            
            # Tenta obter o nome do botão a partir do objeto
            if hasattr(button, 'name'):
                name = button.name
                # Converter para minúsculo e substituir aspas
                if isinstance(name, str):
                    name = name.lower().replace("'", "")
                    # Adicionar prefixo 'mouse_' para diferenciar dos botões do teclado
                    self.logger.info(f"Mouse button with name attribute: mouse_{name}")
                    
                    # Mapear nomes específicos para os botões X1 e X2
                    if name in ['x1', 'back', 'x_1', 'button4']:
                        return 'mouse_back'
                    elif name in ['x2', 'forward', 'x_2', 'button5']:
                        return 'mouse_forward'
                    
                    return f"mouse_{name}"
            
            # Tenta converter para string e examinar o conteúdo
            button_str = str(button).lower()
            self.logger.info(f"Mouse button string representation: {button_str}")
            
            # Verifica se é um botão conhecido
            if 'button.left' in button_str:
                return 'mouse_left'
            elif 'button.right' in button_str:
                return 'mouse_right'
            elif 'button.middle' in button_str:
                return 'mouse_middle'
            # Detectar botões adicionais por vários padrões comuns
            elif any(x in button_str for x in ['button.x1', 'button.back', 'back', 'button4', 'x1']):
                return 'mouse_back'
            elif any(x in button_str for x in ['button.x2', 'button.forward', 'forward', 'button5', 'x2']):
                return 'mouse_forward'
            
            # Se for um dos botões extras numerados
            if 'button(' in button_str:
                # Tenta extrair o número do botão
                try:
                    # Extrai o número entre parênteses, como "Button(4)"
                    num = int(button_str.split('(')[1].split(')')[0])
                    if num == 4 or num == 8:  # Valores comuns para o botão "back"
                        return 'mouse_back'
                    elif num == 5 or num == 9:  # Valores comuns para o botão "forward"
                        return 'mouse_forward'
                except:
                    pass
            
            # Se não conseguir identificar, retorna a representação em string
            mapped_button = f"mouse_{button_str.replace('button.', '')}"
            self.logger.info(f"Unrecognized mouse button, using mapped name: {mapped_button}")
            return mapped_button
            
        except Exception as e:
            self.logger.error(f"Error getting mouse button name: {str(e)}")
            self.logger.error(traceback.format_exc())
            return 'unknown_button'

    def emit(self, signal_name, *args, **kwargs):
        """Emit a signal to registered handlers
        
        Args:
            signal_name: The name of the signal to emit
            *args: Arguments to pass to the handlers
            **kwargs: Keyword arguments to pass to the handlers
        """
        try:
            # Se não houver dictation_manager, não fazer nada
            if not self.dictation_manager:
                self.logger.error(f"Cannot emit signal {signal_name}: no dictation_manager")
                return
            
            # Emitir o sinal para o dictation_manager
            if signal_name == "start_dictation":
                try:
                    self.dictation_manager.start_dictation()
                except Exception as e:
                    self.logger.error(f"Error in start_dictation: {str(e)}")
                    self.logger.error(traceback.format_exc())
            elif signal_name == "stop_dictation":
                try:
                    self.dictation_manager.stop_dictation()
                except Exception as e:
                    self.logger.error(f"Error in stop_dictation: {str(e)}")
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.error(f"Unknown signal: {signal_name}")
            
        except Exception as e:
            self.logger.error(f"Error emitting signal {signal_name}: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _force_push_to_talk_activation(self, key_name):
        """Força a ativação do push-to-talk, garantindo o estado correto
        
        Args:
            key_name: The name of the push-to-talk key
        """
        try:
            self.logger.info(f"DEBUG: _force_push_to_talk_activation chamado para tecla: {key_name}")
            
            # Verificar se a tecla já está iniciando o push-to-talk (prevenir ativações repetidas)
            # Mas permitir a ativação se ainda não estiver gravando
            if self.push_to_talk_active:
                is_recording = False
                try:
                    if self.dictation_manager:
                        is_recording = self.dictation_manager.is_recording
                except Exception as e:
                    self.logger.error(f"Erro verificando estado de gravação: {str(e)}")
                
                # Se já estiver gravando com push-to-talk ativo, não fazer nada
                if is_recording:
                    self.logger.info(f"Push-to-talk já está ativo e gravando para {key_name}, ignorando ativação repetida")
                    return
                else:
                    self.logger.info(f"Push-to-talk está ativo mas não está gravando, reiniciando para {key_name}")
            
            # Primeiramente, parar qualquer ditado em andamento para garantir estado limpo
            if self.dictation_manager:
                try:
                    # Verificar se está gravando
                    is_recording = False
                    try:
                        is_recording = self.dictation_manager.is_recording
                    except Exception as e:
                        self.logger.error(f"Erro verificando estado de gravação: {str(e)}")
                    
                    # Se estiver gravando, parar
                    if is_recording:
                        self.logger.info("Parando gravação anterior antes de iniciar nova")
                        self.dictation_manager.stop_dictation()
                        time.sleep(0.1)  # Pequena pausa para garantir que parou
                except Exception as e:
                    self.logger.error(f"Erro parando ditado existente: {str(e)}")
            
            # Ativar push-to-talk
            self.push_to_talk_active = True
            self.logger.info(f"Push-to-talk forçadamente ativado para tecla: {key_name}")
            
            # Definir idioma de acordo com a tecla pressionada
            # Usar o mesmo método que é usado para teclas de idioma para garantir comportamento idêntico
            try:
                # Verificar se o language_rules existe
                if not self.language_rules:
                    self.logger.error("Não foi possível definir idioma: language_rules não disponível")
                    return
                    
                # Verificar se o dictation_manager existe
                if not self.dictation_manager:
                    self.logger.error("Não foi possível definir idioma: dictation_manager não disponível")
                    return
                
                # Usar o método genérico para configurar idioma que funciona com todas as teclas
                self.logger.info(f"Configurando idioma para tecla push-to-talk: {key_name}")
                self._set_language_and_translation_for_key(key_name)
            except Exception as e:
                self.logger.error(f"Erro definindo idioma para push-to-talk: {str(e)}")
                self.logger.error(traceback.format_exc())
            
            # Iniciar a ditado se o dictation_manager existir
            if self.dictation_manager:
                try:
                    # Aguardar um momento para garantir configuração
                    time.sleep(0.05)
                    
                    # Verificar novamente se ainda não está gravando
                    is_recording = False
                    try:
                        is_recording = self.dictation_manager.is_recording
                    except Exception as e:
                        pass
                    
                    if not is_recording:
                        # Agora iniciar nova gravação
                        self.logger.info(f"Iniciando ditado com push-to-talk para tecla: {key_name}")
                        self.emit("start_dictation")
                    else:
                        self.logger.info("Já está gravando, não iniciando novamente")
                except Exception as e:
                    self.logger.error(f"Erro iniciando ditado: {str(e)}")
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.error("Dictation manager não disponível")
            
        except Exception as e:
            self.logger.error(f"Error in force push-to-talk activation: {str(e)}")
            self.logger.error(traceback.format_exc())
            
    def _force_push_to_talk_deactivation(self, key_name):
        """Força a desativação do push-to-talk, garantindo o estado correto
        
        Args:
            key_name: The name of the push-to-talk key
        """
        try:
            # Desativar push-to-talk
            was_active = self.push_to_talk_active
            self.push_to_talk_active = False
            self.logger.info("Push-to-talk forçadamente desativado")
            
            # Parar a ditado se o dictation_manager existir
            if self.dictation_manager:
                try:
                    # Sempre parar gravação quando push-to-talk é liberado
                    self.logger.info("Parando ditado (liberação de push-to-talk)")
                    self.emit("stop_dictation")
                except Exception as e:
                    self.logger.error(f"Erro parando ditado: {str(e)}")
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.error("Dictation manager não disponível")
            
        except Exception as e:
            self.logger.error(f"Error in force push-to-talk deactivation: {str(e)}")
            self.logger.error(traceback.format_exc())