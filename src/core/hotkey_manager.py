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
            
            # Initialize callback for UI updates
            self.update_ui_callback = None
            
            self.logger.info("Hotkey manager initialized")
        except Exception as e:
            # Use a print statement if logger might not be initialized yet
            print(f"Error initializing hotkey manager: {str(e)}")
            print(traceback.format_exc())
    
    def _create_language_hotkeys_dict(self):
        """Create a dictionary for faster hotkey lookup"""
        self.language_hotkeys_dict = {}
        
        # Log para depuração
        self.logger.debug("Criando dicionário de hotkeys de idioma")
        
        # Adicionar mouse_forward como uma language hotkey especial
        self.language_hotkeys_dict["mouse_forward"] = {
            "key": "mouse_forward",
            "modifiers": [],
            "language": "pt-PT",  # Sempre usar português para reconhecimento
            "target_language": self.config_manager.get_value("language_rules", "output_language", "en-US")  # Usar o idioma de saída configurado
        }
        self.logger.info(f"Mouse forward configurado como language hotkey especial com target_language: {self.language_hotkeys_dict['mouse_forward']['target_language']}")
        
        for hotkey in self.language_hotkeys:
            # Verificar se a configuração da hotkey é válida
            if "key" in hotkey and "language" in hotkey:
                key = hotkey["key"]
                
                # Verificar se é uma tecla modificadora
                is_modifier = key in ['ctrl', 'alt', 'shift', 'cmd']
                if is_modifier:
                    self.logger.info(f"Tecla modificadora {key} configurada como hotkey de idioma para {hotkey['language']}")
                    # Para teclas modificadoras, garantir que não haja modificadores
                    hotkey_copy = hotkey.copy()
                    hotkey_copy["modifiers"] = []
                    self.language_hotkeys_dict[key] = hotkey_copy
                else:
                    # Para teclas normais, usar a configuração normal
                    self.language_hotkeys_dict[key] = hotkey
            else:
                self.logger.warning(f"Configuração de hotkey inválida: {hotkey}")
        
        # Log do dicionário criado
        self.logger.debug(f"Dicionário de hotkeys de idioma: {self.language_hotkeys_dict}")
    
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
                
                # Salvar configuração com força para garantir persistência
                self.config_manager.save_config(force=True)
                self.logger.info(f"Configuração de {hotkey_type} salva com força")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error updating hotkey configuration: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def update_language_hotkey(self, index, key, modifiers, language):
        """Atualizar uma hotkey de idioma"""
        try:
            # Log para depuração
            self.logger.info(f"Atualizando hotkey de idioma {index}: key={key}, modifiers={modifiers}, language={language}")
            
            # Verificar se é uma tecla modificadora
            is_modifier = key in ['ctrl', 'alt', 'shift', 'cmd']
            if is_modifier:
                self.logger.info(f"Tecla modificadora {key} sendo configurada como hotkey de idioma")
                # Garantir que a configuração de modificador esteja correta para teclas modificadoras
                modifiers = [] # Teclas modificadoras não devem ter modificadores quando usadas como hotkey principal
            
            # Configuração da hotkey
            hotkey_config = {
                "key": key,
                "modifiers": modifiers,
                "language": language
            }
            
            # Verificar se já existe uma hotkey para o índice especificado
            needs_create = True
            if index < len(self.language_hotkeys):
                self.language_hotkeys[index] = hotkey_config
                needs_create = False
                
            # Se precisar criar, adicionar à lista
            if needs_create:
                self.language_hotkeys.append(hotkey_config)
                
            # Salvar na configuração
            self.config_manager.set_value("hotkeys", "language_hotkeys", self.language_hotkeys)
            
            # Forçar o salvamento imediato da configuração
            self.config_manager.save_config(force=True)
            self.logger.info("Configuração de hotkeys salva com força")
            
            # Atualizar dicionário para referência rápida
            self._create_language_hotkeys_dict()
            
            # Log da atualização concluída
            self.logger.info(f"Hotkey de idioma {index} atualizada com sucesso")
            self._log_language_hotkeys()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar hotkey de idioma: {str(e)}")
            import traceback
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
                self.logger.info(f"Mouse forward button detectado e normalizado para 'mouse_forward'")
            
            # Lista concreta de nomes de botões do mouse para verificação
            mouse_button_names = [
                'mouse_left', 'mouse_right', 'mouse_middle', 
                'mouse_forward', 'mouse_back', 'mouse_button3', 
                'mouse_button4', 'mouse_button5'
            ]
            
            # Verificar se é um botão válido do mouse
            if not any(name in button_name for name in ['mouse_', 'button']):
                self.logger.warning(f"Botão de mouse inválido: {button_name}, ignorando")
                return
                
            # Verificar se é o botão de push-to-talk específico
            push_to_talk_key = None
            if self.push_to_talk and 'key' in self.push_to_talk:
                push_to_talk_key = self.push_to_talk['key']

            # Verificar se é uma language hotkey
            is_language_hotkey = False
            for hotkey in self.language_hotkeys:
                if 'key' in hotkey and hotkey['key'] == button_name:
                    is_language_hotkey = True
                    break
                    
            # Log para debugging
            self.logger.info(f"Mouse {'Press' if pressed else 'Release'}: {button_name}")
            self.logger.info(f"  - Is push-to-talk: {button_name == push_to_talk_key}")
            self.logger.info(f"  - Is language hotkey: {is_language_hotkey or button_name == 'mouse_forward'}")
            
            # Handle button press
            if pressed:
                # Adicionar uma chave especial para o mouse para evitar confusão com teclas
                mouse_key = f"MOUSE_EVENT_{button_name}"
                self.current_keys.add(mouse_key)
                self.logger.info(f"Added {button_name} to current keys as {mouse_key}")
                
                # Evitar confusão com a tecla ctrl - marcar explicitamente como mouse button
                if is_forward_button:
                    self.logger.info("Mouse forward button pressed - this is NOT a keyboard ctrl key")
                
                # Se for o botão de push-to-talk ou mouse_forward, iniciar ditado
                if button_name == push_to_talk_key or button_name == "mouse_forward":
                    self.logger.info(f"Push-to-talk/Language hotkey: mouse button {button_name} pressed")
                    # Armazenar hora do pressionamento para debounce
                    current_time = time.time()
                    self.key_press_times[button_name] = current_time
                    
                    # Se for mouse_forward, tratar como language hotkey
                    if button_name == "mouse_forward":
                        self._force_language_hotkey_activation(button_name)
                    else:
                        self._force_push_to_talk_activation(button_name)
                
                # Se for uma hotkey de idioma, forçar ativação
                elif is_language_hotkey:
                    self.logger.info(f"Language hotkey: mouse button {button_name} pressed")
                    self._force_language_hotkey_activation(button_name)
            else:
                # Handle button release
                mouse_key = f"MOUSE_EVENT_{button_name}"
                if mouse_key in self.current_keys:
                    self.current_keys.remove(mouse_key)
                    self.logger.info(f"Removed {button_name} from current keys")
                
                # Se for o botão de push-to-talk ou mouse_forward, parar ditado
                if button_name == push_to_talk_key or button_name == "mouse_forward":
                    self.logger.info(f"Push-to-talk/Language hotkey: mouse button {button_name} released")
                    
                    # Se for mouse_forward, tratar como language hotkey
                    if button_name == "mouse_forward":
                        self._force_language_hotkey_deactivation(button_name)
                    else:
                        self._force_push_to_talk_deactivation(button_name)
                
                # Se for uma hotkey de idioma, forçar desativação
                elif is_language_hotkey:
                    self.logger.info(f"Language hotkey: mouse button {button_name} released")
                    self._force_language_hotkey_deactivation(button_name)
            
        except Exception as e:
            self.logger.error(f"Error handling mouse click: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _force_language_hotkey_activation(self, key_name):
        """Force the activation of a language hotkey, with the same behavior as push-to-talk"""
        try:
            if not self.dictation_manager:
                self.logger.warning("Dictation manager not set, cannot force language hotkey activation")
                return

            if not self.language_rules:
                self.logger.warning("Language rules not set, cannot force language hotkey activation")
                return

            # Verificar se a tecla é uma language hotkey
            if key_name not in self.language_hotkeys_dict and key_name != "mouse_forward":
                self.logger.debug(f"Key {key_name} is not a language hotkey")
                return
                
            # Obter configuração da hotkey
            if key_name == "mouse_forward":
                # Para mouse_forward, atualizar a configuração com o idioma de saída atual
                target_language = self.config_manager.get_value("language_rules", "output_language", "en-US")
                self.language_hotkeys_dict["mouse_forward"]["target_language"] = target_language
                self.logger.info(f"Atualizando target_language do mouse_forward para: {target_language}")
                
            hotkey_config = self.language_hotkeys_dict[key_name]
            self.logger.info(f"Found language hotkey config: {hotkey_config}")

            # Tratar language hotkeys como push-to-talk (inicia a gravação)
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

            # Obter o idioma de reconhecimento da tecla
            recognition_language = hotkey_config.get("language", "pt-PT")
            
            # Para o mouse_forward, sempre usar o idioma de saída configurado
            if key_name == "mouse_forward":
                target_language = hotkey_config.get("target_language", self.config_manager.get_value("language_rules", "output_language", "en-US"))
                self.logger.info(f"Usando idioma de saída configurado para mouse_forward: {target_language}")
            else:
                # Verificar se há um idioma de destino específico para esta tecla
                key_targets = self.config_manager.get_value("language_rules", "key_targets", {})
                if isinstance(key_targets, dict) and key_name in key_targets:
                    target_language = key_targets[key_name]
                    self.logger.info(f"Using target language from key_targets: {target_language}")
                else:
                    # Se não tiver target específico, usar o mesmo idioma de reconhecimento
                    target_language = hotkey_config.get("target_language", recognition_language)
                    self.logger.info(f"No specific target language found, using: {target_language}")
            
            # Criar configuração completa para aplicar
            complete_config = hotkey_config.copy()
            complete_config["target_language"] = target_language
            
            # Aplicar as regras de idioma
            self.logger.info(f"Applying language settings for key {key_name}: {recognition_language} -> {target_language}")
            self.language_rules.apply_language_settings(self.dictation_manager, "language_hotkey", complete_config)
            
            # Preparar mensagem de notificação
            try:
                recognition_lang_name = self._get_language_display_name(recognition_language)
                target_lang_name = self._get_language_display_name(target_language)
                
                if recognition_language == target_language:
                    msg = f"Ditando em {recognition_lang_name}"
                else:
                    msg = f"Ditando em {recognition_lang_name} (tradução para {target_lang_name})"
                
                self.logger.info(f"Notificação de idioma: {msg}")
                
                # Mostrar notificação se o método existir
                if hasattr(self.dictation_manager, 'show_notification'):
                    self.dictation_manager.show_notification(msg, "info", 2000)
            except Exception as notification_error:
                self.logger.warning(f"Error showing language notification: {str(notification_error)}")
            
            # Atualizar a interface do usuário (se o callback estiver disponível)
            if hasattr(self, 'update_ui_callback') and self.update_ui_callback:
                self.update_ui_callback()
                
            # Iniciar a ditado - COMPORTAMENTO IGUAL AO PUSH-TO-TALK
            self.push_to_talk_active = True  # Marcar como ativo mesmo para teclas de idioma
            if self.dictation_manager:
                # Verificar se já está gravando
                is_recording = False
                try:
                    is_recording = self.dictation_manager.is_recording
                except Exception as e:
                    pass
                
                if not is_recording:
                    # Aguardar um momento para garantir configuração
                    time.sleep(0.05)
                    self.logger.info(f"Iniciando ditado com language hotkey: {key_name}")
                    self.emit("start_dictation")
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error forcing language hotkey activation: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _force_language_hotkey_deactivation(self, key_name):
        """Força a desativação de uma hotkey de idioma com mesmo comportamento do push-to-talk"""
        try:
            self.logger.info(f"Forçando desativação da hotkey de idioma: {key_name}")
            
            # Verificar se a tecla está configurada como hotkey de idioma
            if key_name in self.language_hotkeys_dict:
                # Desativar push-to-talk (mesmo para teclas de idioma)
                was_active = self.push_to_talk_active
                self.push_to_talk_active = False
                self.logger.info(f"Desativando modo de ditado para language hotkey: {key_name}")
                
                # Parar o ditado se o dictation_manager existir
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
                            self.logger.info(f"Parando ditado (liberação de tecla de idioma {key_name})")
                            self.emit("stop_dictation")
                    except Exception as e:
                        self.logger.error(f"Erro parando ditado: {str(e)}")
                        self.logger.error(traceback.format_exc())
                else:
                    self.logger.warning(f"Dictation manager não disponível")
            else:
                self.logger.warning(f"Tecla {key_name} não está configurada como hotkey de idioma")
                
        except Exception as e:
            self.logger.error(f"Erro ao forçar desativação de hotkey de idioma: {str(e)}")
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
        """Handle key press internally"""
        try:
            # Log para depuração
            self.logger.debug(f"Key pressed (internal): {key_name}")
            
            # Se a tecla não for uma tecla conhecida, ignorar
            if not key_name:
                return
            
            # Verificar se a tecla já foi processada (já está no conjunto de teclas pressionadas)
            # Isso previne que teclas mantidas pressionadas gerem múltiplos eventos
            if key_name in self.current_keys:
                # Se for uma tecla modificadora como Ctrl, verificar tempo desde último processamento
                if key_name in ['ctrl', 'alt', 'shift', 'cmd']:
                    current_time = time.time()
                    last_press = self.key_press_times.get(key_name, 0)
                    
                    # Reduzir o tempo de debounce para 0.5 segundos
                    if current_time - last_press < 0.5:
                        self.logger.debug(f"Tecla {key_name} já está pressionada, ignorando evento repetido")
                        return
                    else:
                        # Se passou mais de 0.5 segundos, atualizar o timestamp mas não reprocessar
                        self.key_press_times[key_name] = current_time
                        self.logger.debug(f"Tecla {key_name} mantida pressionada por 0.5 segundos, atualizando timestamp")
                        return
                else:
                    # Para teclas normais, ignorar completamente se já estiver pressionada
                    self.logger.debug(f"Tecla {key_name} já está pressionada, ignorando evento repetido")
                    return
                
            # Armazenar hora do pressionamento
            current_time = time.time()
            self.key_press_times[key_name] = current_time
            
            # Adicionar à lista de teclas pressionadas
            self.current_keys.add(key_name)
            
            # Verificar se é uma tecla de idioma
            is_language_hotkey = key_name in self.language_hotkeys_dict
            
            # Log para debug
            if is_language_hotkey:
                self.logger.info(f"Tecla de idioma pressionada (teclado): {key_name}")
                self._force_language_hotkey_activation(key_name)
            
            # Verificar se é a tecla push-to-talk
            if key_name == self.push_to_talk_key:
                self.logger.info(f"Push-to-talk pressionado: {key_name}")
                self._force_push_to_talk_activation(key_name)
            
            # Verificar se é a tecla toggle (hands-free)
            if key_name == self.toggle_key:
                self.logger.info(f"Toggle pressionado: {key_name}")
                self._handle_toggle_key(key_name)
            
            # Verificar se é uma tecla modificadora
            is_modifier = key_name in ['ctrl', 'shift', 'alt', 'cmd']
            if is_modifier:
                # Se for a tecla control, verificar se é uma language hotkey
                if key_name == 'ctrl' and key_name in self.language_hotkeys_dict:
                    self.logger.debug(f"Ctrl pressionado como hotkey de idioma")
                else:
                    self.logger.debug(f"Tecla modificadora pressionada: {key_name}")
        
        except Exception as e:
            self.logger.error(f"Error in key press handler: {str(e)}")
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
                # Parar o ditado ao liberar tecla de idioma, comportamento igual ao push-to-talk
                self.logger.info(f"Parando ditado (liberação de tecla de idioma {key_name})")
                self.push_to_talk_active = False
                self.emit("stop_dictation")
            
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
    
    def _force_push_to_talk_activation(self, key_name):
        """Força a ativação do push-to-talk, garantindo o estado correto
        
        Args:
            key_name (str): O nome da tecla que foi pressionada
        """
        try:
            # Se a tecla não for o push-to-talk configurado, ignorar
            if key_name != self.push_to_talk_key and key_name != "mouse_forward":
                self.logger.info(f"Tecla {key_name} não é push-to-talk, ignorando...")
                return
            
            # Verificar se já está ativo
            if self.push_to_talk_active:
                self.logger.debug("Push-to-talk already active, ignoring")
                return
            
            # Verificar se a tecla é válida para push-to-talk
            if not key_name:
                self.logger.warning("Invalid push-to-talk key, ignoring")
                return
            
            # Ativar push-to-talk
            self.push_to_talk_active = True
            self.logger.info(f"Ativação forçada de push-to-talk com tecla: {key_name}")
            
            # Definir idioma de acordo com a tecla pressionada
            # Usar o método de ativação forçada que garante usar pt-PT
            self._force_push_to_talk_activation(key_name)
            
        except Exception as e:
            self.logger.error(f"Error in _force_push_to_talk_activation: {str(e)}")
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
            self.logger.info(f"Configurando idioma para a tecla: {key_name}")
            
            # Garantir que usamos sempre o idioma pt-PT para reconhecimento, independente da tecla
            recognition_language = "pt-PT"
            self.logger.info(f"Forçando idioma de reconhecimento para: {recognition_language}")
            
            # Se for uma language hotkey (exemplo: ctrl, shift, mouse_forward), usar as configurações da hotkey
            if key_name in self.language_hotkeys_dict or key_name == "mouse_forward":
                # Para mouse_forward, usar configuração específica de tradução
                if key_name == "mouse_forward":
                    # Obter o idioma de saída da configuração
                    target_language = self.config_manager.get_value("language_rules", "output_language", "en-US")
                    self.logger.info(f"Mouse forward usando idioma de saída configurado: {target_language}")
                else:
                    # Para outras language hotkeys, usar configuração normal
                    hotkey_config = self.language_hotkeys_dict[key_name]
                    
                    # Verificar se há um idioma de destino específico para esta tecla em language_rules.key_targets
                    key_targets = self.config_manager.get_value("language_rules", "key_targets", {})
                    if isinstance(key_targets, dict) and key_name in key_targets:
                        target_language = key_targets[key_name]
                        self.logger.info(f"Tecla {key_name} tem idioma alvo configurado: {target_language}")
                    else:
                        # Se não houver configuração específica em key_targets, usar o mesmo idioma da hotkey
                        target_language = hotkey_config.get("language", recognition_language)
                        self.logger.info(f"Tecla {key_name} não tem idioma alvo específico, usando: {target_language}")
                
                # Log para diagnóstico
                self.logger.info(f"Configurando language hotkey {key_name}: {recognition_language} → {target_language}")
                    
                # Configurar a aplicação para usar esses idiomas
                if self.dictation_manager and hasattr(self.dictation_manager, 'set_language'):
                    self.dictation_manager.set_language(recognition_language)
                    self.logger.info(f"Idioma de reconhecimento definido como: {recognition_language}")
                
                if self.dictation_manager and hasattr(self.dictation_manager, 'set_target_language'):
                    self.dictation_manager.set_target_language(target_language)
                    self.logger.info(f"Idioma de destino definido como: {target_language}")
                
                # Ativar tradução automática se os idiomas forem diferentes
                auto_translate = recognition_language != target_language
                if self.dictation_manager and hasattr(self.dictation_manager, 'set_auto_translate'):
                    self.dictation_manager.set_auto_translate(auto_translate)
                    self.logger.info(f"Auto-tradução definida como: {auto_translate}")
                
                # Mostrar notificação de idioma
                source_name = self._get_language_display_name(recognition_language)
                target_name = self._get_language_display_name(target_language)
                
                if recognition_language == target_language:
                    message = f"Ditando em {source_name}"
                else:
                    message = f"Ditando em {source_name} → Traduzindo para {target_name}"
                
                self.logger.info(f"Language hotkey {key_name}: {message}")
                self.emit("show_notification", message, "info", 2000)
                
                return
                
            # Se chegar aqui, usar configurações padrão
            self.logger.info(f"Nenhuma configuração específica para tecla {key_name}, usando pt-PT")
            
            # Usar configuração pt-PT como padrão
            if self.dictation_manager and hasattr(self.dictation_manager, 'set_language'):
                self.dictation_manager.set_language(recognition_language)
                self.logger.info(f"Idioma de reconhecimento padrão definido como: {recognition_language}")
            
        except Exception as e:
            self.logger.error(f"Error setting language for key {key_name}: {str(e)}")
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
            elif signal_name == "show_notification":
                try:
                    # Verificar se o dictation_manager tem o método show_notification
                    if hasattr(self.dictation_manager, 'show_notification'):
                        self.dictation_manager.show_notification(*args, **kwargs)
                    else:
                        self.logger.warning(f"dictation_manager não tem método show_notification: {args}")
                except Exception as e:
                    self.logger.error(f"Error in show_notification: {str(e)}")
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.error(f"Unknown signal: {signal_name}")
            
        except Exception as e:
            self.logger.error(f"Error emitting signal {signal_name}: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _get_language_display_name(self, language_code):
        """Get a human-readable display name for a language code
        
        Args:
            language_code (str): The language code (e.g., 'en-US', 'pt-BR')
            
        Returns:
            str: A human-readable language name
        """
        language_names = {
            'en-US': 'English (US)',
            'en-GB': 'English (UK)',
            'pt-BR': 'Portuguese (Brazil)',
            'pt-PT': 'Portuguese (Portugal)',
            'es-ES': 'Spanish',
            'fr-FR': 'French',
            'de-DE': 'German',
            'it-IT': 'Italian',
            'ja-JP': 'Japanese',
            'zh-CN': 'Chinese',
            'ru-RU': 'Russian'
        }
        
        return language_names.get(language_code, language_code)

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
            
            # Verificar se a tecla é ctrl
            if key_name == "ctrl":
                self.logger.warning(f"Push-to-talk with CTRL key detected: {key_name}")
            
            # Ativar push-to-talk
            self.push_to_talk_active = True
            self.logger.info(f"Push-to-talk activated with key: {key_name}")
            
            # Usar o método de ativação forçada que garante usar pt-PT
            self._force_push_to_talk_activation(key_name)
            
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
                self.logger.error("No dictation manager available")
            
        except Exception as e:
            self.logger.error(f"Error handling push-to-talk release: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _get_mouse_button_name(self, button):
        """Get the name of a mouse button
        
        Args:
            button: The mouse button object from pynput
            
        Returns:
            str: The name of the mouse button
        """
        try:
            # Verificar se o objeto button tem atributos específicos
            if hasattr(button, 'name'):
                # Normalizar nome do botão
                button_name = str(button.name).lower()
                
                # Mapear nomes específicos de botões
                if button_name == 'left':
                    return 'mouse_left'
                elif button_name == 'right':
                    return 'mouse_right'
                elif button_name == 'middle':
                    return 'mouse_middle'
                elif 'button8' in button_name or 'x2' in button_name or 'forward' in button_name:
                    return 'mouse_forward'
                elif 'button9' in button_name or 'x1' in button_name or 'back' in button_name:
                    return 'mouse_back'
                else:
                    # Para qualquer outro botão, adicionar prefixo "mouse_"
                    if not button_name.startswith('mouse_'):
                        return f'mouse_{button_name}'
                    return button_name
            
            # Se não tiver nome, verificar pelo número do botão
            if hasattr(button, 'value'):
                button_value = int(button.value)
                # Mapear valores comuns de botões
                button_map = {
                    0: 'mouse_left',
                    1: 'mouse_right',
                    2: 'mouse_middle',
                    4: 'mouse_back',  # Corrigido: botão 4 é back
                    5: 'mouse_forward'  # Corrigido: botão 5 é forward
                }
                
                if button_value in button_map:
                    return button_map[button_value]
                else:
                    return f'mouse_button{button_value}'
            
            # Última tentativa - converter para string
            button_str = str(button).lower()
            if 'button.button' in button_str:
                # Extrair número do botão
                try:
                    # Tenta extrair o número do botão da string 'Button.button#'
                    button_num = int(button_str.split('.')[-1].replace('button', ''))
                    if button_num == 8:
                        return 'mouse_forward'
                    elif button_num == 9:
                        return 'mouse_back'
                    else:
                        return f'mouse_button{button_num}'
                except:
                    pass
            
            # Se chegar aqui, usar a string e adicionar prefixo
            if not button_str.startswith('mouse_'):
                return f'mouse_{button_str}'
            return button_str
            
        except Exception as e:
            self.logger.error(f"Error getting mouse button name: {str(e)}")
            self.logger.error(traceback.format_exc())
            return "mouse_unknown"