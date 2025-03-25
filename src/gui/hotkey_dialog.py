#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hotkey Dialog for DogeDictate
Provides interface for configuring keyboard shortcuts
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QLineEdit, QMessageBox, QWidget
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence

logger = logging.getLogger("DogeDictate.HotkeyDialog")

class HotkeyDialog(QDialog):
    """Dialog for configuring hotkeys"""
    
    def __init__(self, parent, config_manager, hotkey_manager):
        """Initialize the hotkey dialog"""
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.hotkey_manager = hotkey_manager
        
        # Set dialog properties
        self.setWindowTitle("Change Hotkeys")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        # Initialize UI
        self._init_ui()
        
        # Load current hotkeys
        self._load_hotkeys()
    
    def _init_ui(self):
        """Initialize the user interface"""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Add title and description
        main_layout.addWidget(QLabel("<h2>Change Hotkeys</h2>"))
        main_layout.addWidget(QLabel("Customize how you interact with DogeDictate"))
        main_layout.addSpacing(10)
        
        # Push to talk group
        ptt_group = QGroupBox("Push to Talk")
        ptt_layout = QVBoxLayout(ptt_group)
        
        # Push to talk hotkey
        self.ptt_edit = HotkeyEdit()
        ptt_layout.addWidget(self.ptt_edit)
        ptt_layout.addWidget(QLabel("Dictate text while holding this key"))
        
        # Add push to talk group to main layout
        main_layout.addWidget(ptt_group)
        
        # Hands-free group
        hf_group = QGroupBox("Hands-free Mode")
        hf_layout = QVBoxLayout(hf_group)
        
        # Hands-free hotkey
        self.hf_edit = HotkeyEdit()
        hf_layout.addWidget(self.hf_edit)
        hf_layout.addWidget(QLabel("Dictate hands-free by pressing once to start and again to stop"))
        
        # Add hands-free group to main layout
        main_layout.addWidget(hf_group)
        
        # Language hotkeys group
        lang_group = QGroupBox("Language Hotkeys")
        lang_layout = QVBoxLayout(lang_group)
        
        # Language hotkeys description
        lang_layout.addWidget(QLabel("Define hotkeys for specific languages"))
        
        # Language hotkey entries
        self.lang_hotkey_entries = []
        for i in range(4):  # Up to 4 language hotkeys
            entry = LanguageHotkeyEntry()
            self.lang_hotkey_entries.append(entry)
            lang_layout.addWidget(entry)
        
        # Add language hotkeys group to main layout
        main_layout.addWidget(lang_group)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        # Reset button
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset_defaults)
        
        # Save button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save_hotkeys)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        # Add buttons to layout
        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)
    
    def _load_hotkeys(self):
        """Load current hotkey settings"""
        # Load push to talk hotkey
        ptt_config = self.hotkey_manager.push_to_talk
        self.ptt_edit.set_hotkey(ptt_config.get("key", ""), ptt_config.get("modifiers", []))
        
        # Load hands-free hotkey
        hf_config = self.hotkey_manager.hands_free
        self.hf_edit.set_hotkey(hf_config.get("key", ""), hf_config.get("modifiers", []))
        
        # Load language hotkeys
        lang_hotkeys = self.hotkey_manager.language_hotkeys
        for i, entry in enumerate(self.lang_hotkey_entries):
            if i < len(lang_hotkeys):
                hotkey = lang_hotkeys[i]
                entry.set_hotkey(
                    hotkey.get("key", ""),
                    hotkey.get("modifiers", []),
                    hotkey.get("language", "")
                )
    
    def _save_hotkeys(self):
        """Save hotkey settings"""
        try:
            # Save push to talk hotkey
            ptt_key, ptt_modifiers = self.ptt_edit.get_hotkey()
            self.hotkey_manager.update_hotkey("push_to_talk", ptt_key, ptt_modifiers)
            
            # Save hands-free hotkey
            hf_key, hf_modifiers = self.hf_edit.get_hotkey()
            self.hotkey_manager.update_hotkey("toggle_dictation", hf_key, hf_modifiers)
            
            # Limpar hotkeys de linguagem existentes
            self.config_manager.set_value("hotkeys", "language_hotkeys", [])
            
            # Save language hotkeys
            language_hotkeys = []
            for i, entry in enumerate(self.lang_hotkey_entries):
                key, modifiers, language = entry.get_hotkey()
                if key and language:
                    # Adicionar hotkey à lista local primeiro
                    language_hotkeys.append({
                        "key": key,
                        "modifiers": modifiers,
                        "language": language
                    })
                    # Atualizar no hotkey_manager
                    self.hotkey_manager.update_language_hotkey(i, key, modifiers, language)
            
            # Garantir que os hotkeys estejam definidos diretamente no ConfigManager
            self.config_manager.set_value("hotkeys", "language_hotkeys", language_hotkeys)
            
            # Salvar configurações com força para garantir persistência
            self.config_manager.save_config(force=True)
            logger.info("Configurações salvas com força no arquivo de configuração")
            
            # Recarregar configurações no hotkey_manager
            self.hotkey_manager.reload_config()
            
            # Atualizar target languages nas regras de linguagem
            if hasattr(self.hotkey_manager, 'language_rules') and self.hotkey_manager.language_rules:
                self.hotkey_manager.language_rules.ensure_key_targets()
                logger.info("Language targets updated based on language hotkeys")
            else:
                logger.warning("Could not update language targets: language_rules not available")
            
            # Log para depuração
            logger.info("Hotkeys saved successfully")
            logger.info(f"Push to talk: key={ptt_key}, modifiers={ptt_modifiers}")
            logger.info(f"Hands-free: key={hf_key}, modifiers={hf_modifiers}")
            
            # Log language hotkeys
            for i, entry in enumerate(self.lang_hotkey_entries):
                key, modifiers, language = entry.get_hotkey()
                if key and language:
                    logger.info(f"Language hotkey {i}: key={key}, modifiers={modifiers}, language={language}")
            
            # Accept dialog
            self.accept()
        
        except Exception as e:
            logger.error(f"Error saving hotkeys: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.warning(self, "Error", f"Failed to save hotkeys: {str(e)}")
    
    def _reset_defaults(self):
        """Reset hotkeys to default values"""
        # Default push to talk: Caps Lock
        self.ptt_edit.set_hotkey("caps_lock", [])
        
        # Default hands-free: Shift+Space
        self.hf_edit.set_hotkey("space", ["shift"])
        
        # Default language hotkeys
        defaults = [
            {"key": "p", "modifiers": ["ctrl"], "language": "pt-BR"},
            {"key": "t", "modifiers": ["ctrl"], "language": "pt-PT"},
            {"key": "e", "modifiers": ["ctrl"], "language": "en-US"},
            {"key": "f", "modifiers": ["ctrl"], "language": "fr-FR"},
            {"key": "s", "modifiers": ["ctrl"], "language": "es-ES"}
        ]
        
        for i, entry in enumerate(self.lang_hotkey_entries):
            if i < len(defaults):
                hotkey = defaults[i]
                entry.set_hotkey(
                    hotkey.get("key", ""),
                    hotkey.get("modifiers", []),
                    hotkey.get("language", "")
                )


class HotkeyEdit(QWidget):
    """Custom widget for capturing hotkeys"""
    
    def __init__(self, parent=None):
        """Initialize the hotkey edit"""
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Create line edit
        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        self.line_edit.setPlaceholderText("Nenhum atalho definido")
        layout.addWidget(self.line_edit)
        
        # Create edit button
        self.edit_button = QPushButton("Definir")
        self.edit_button.setFixedWidth(80)
        self.edit_button.clicked.connect(self.start_recording)
        layout.addWidget(self.edit_button)
        
        self.key = ""
        self.modifiers = []
        self.is_recording = False
        
        # Map of allowed special keys
        self.key_map = {
            Qt.Key_Control: "ctrl",
            Qt.Key_Shift: "shift",
            Qt.Key_Alt: "alt",
            Qt.Key_Meta: "cmd",
            Qt.Key_CapsLock: "caps_lock",
            Qt.Key_Space: "space",
            Qt.Key_Tab: "tab",
            Qt.Key_Return: "return",
            Qt.Key_Enter: "enter",
            Qt.Key_Escape: "escape",
            Qt.Key_Backspace: "backspace",
            Qt.Key_Delete: "delete",
            Qt.Key_Insert: "insert",
            Qt.Key_Home: "home",
            Qt.Key_End: "end",
            Qt.Key_PageUp: "page_up",
            Qt.Key_PageDown: "page_down",
            Qt.Key_F1: "f1",
            Qt.Key_F2: "f2",
            Qt.Key_F3: "f3",
            Qt.Key_F4: "f4",
            Qt.Key_F5: "f5",
            Qt.Key_F6: "f6",
            Qt.Key_F7: "f7",
            Qt.Key_F8: "f8",
            Qt.Key_F9: "f9",
            Qt.Key_F10: "f10",
            Qt.Key_F11: "f11",
            Qt.Key_F12: "f12",
            Qt.Key_NumLock: "num_lock",
            Qt.Key_ScrollLock: "scroll_lock",
            Qt.Key_Pause: "pause",
            Qt.Key_Print: "print",
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",
            Qt.Key_Left: "left",
            Qt.Key_Right: "right"
        }

        # Mouse button mapping
        self.mouse_map = {
            Qt.LeftButton: "mouse_left",
            Qt.RightButton: "mouse_right",
            Qt.MiddleButton: "mouse_middle",
            Qt.BackButton: "mouse_back",
            Qt.ForwardButton: "mouse_forward"
        }

        # Style for recording state
        self.recording_style = """
            QLineEdit {
                background-color: #FFF3E0;
                color: #E65100;
                border: 2px solid #E65100;
            }
        """
        
        # Install event filter for both widgets
        self.installEventFilter(self)
        self.line_edit.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Filter events for the line edit"""
        if self.is_recording:
            if event.type() == QEvent.KeyPress:
                logger.debug(f"Key press event captured: {event.key()}")
                self.handle_key_press(event)
                return True
            elif event.type() == QEvent.MouseButtonPress:
                logger.debug(f"Mouse press event captured: {event.button()}")
                if obj is self or obj is self.line_edit:
                    self.handle_mouse_press(event)
                    return True
            elif event.type() == QEvent.FocusOut:
                # Cancelar a gravação se o foco for perdido
                logger.debug("Focus out event, stopping recording")
                self.stop_recording()
                return True
        return super().eventFilter(obj, event)
    
    def mousePressEvent(self, event):
        """Handle mouse press events directly"""
        if self.is_recording:
            logger.debug(f"Mouse press event in mousePressEvent: {event.button()}")
            self.handle_mouse_press(event)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def handle_mouse_press(self, event):
        """Handle mouse press events"""
        button = event.button()
        if button in self.mouse_map:
            # Get modifiers
            modifiers = event.modifiers()
            mod_list = []
            if modifiers & Qt.ControlModifier:
                mod_list.append("ctrl")
            if modifiers & Qt.ShiftModifier:
                mod_list.append("shift")
            if modifiers & Qt.AltModifier:
                mod_list.append("alt")
            if modifiers & Qt.MetaModifier:
                mod_list.append("cmd")
            
            # Set hotkey
            self.key = self.mouse_map[button]
            self.modifiers = mod_list
            
            # Log for debugging
            logger.info(f"Mouse button captured: {self.key}, modifiers: {self.modifiers}")
            
            self._finish_recording()
    
    def handle_key_press(self, event):
        """Handle key press events"""
        # Get key and modifiers
        key_code = event.key()
        modifiers = event.modifiers()
        
        # Escape key cancels recording
        if key_code == Qt.Key_Escape:
            logger.debug("Escape key pressed, canceling recording")
            self.stop_recording()
            return
        
        # Verificar se uma tecla modificadora foi pressionada sozinha
        # Para isso, verificamos se apenas um tipo de modificador está presente no evento
        # e se a key_code corresponde a essa tecla modificadora
        is_only_modifier = False
        if key_code == Qt.Key_Control:
            if modifiers == Qt.ControlModifier:
                self.key = "ctrl"
                self.modifiers = []
                is_only_modifier = True
                logger.info("Ctrl key captured as standalone key")
        elif key_code == Qt.Key_Shift:
            if modifiers == Qt.ShiftModifier:
                self.key = "shift"
                self.modifiers = []
                is_only_modifier = True
                logger.info("Shift key captured as standalone key")
        elif key_code == Qt.Key_Alt:
            if modifiers == Qt.AltModifier:
                self.key = "alt"
                self.modifiers = []
                is_only_modifier = True
                logger.info("Alt key captured as standalone key")
        elif key_code == Qt.Key_Meta:
            if modifiers == Qt.MetaModifier:
                self.key = "cmd"
                self.modifiers = []
                is_only_modifier = True
                logger.info("Meta/Win key captured as standalone key")
                
        # Se uma tecla modificadora foi capturada sozinha, finalizar a gravação
        if is_only_modifier:
            self._finish_recording()
            return
            
        # Skip if only modifier keys are pressed and we're waiting for a combination
        if key_code in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return
        
        # Handle regular keys (letters, numbers, etc.)
        if key_code >= Qt.Key_A and key_code <= Qt.Key_Z:
            key = chr(key_code).lower()
        elif key_code >= Qt.Key_0 and key_code <= Qt.Key_9:
            key = chr(key_code)
        # Only allow special keys from key_map
        elif key_code in self.key_map:
            key = self.key_map[key_code]
        else:
            # Log unknown key
            logger.debug(f"Unknown key code: {key_code}")
            return
            
        # Get modifiers
        mod_list = []
        if modifiers & Qt.ControlModifier:
            mod_list.append("ctrl")
        if modifiers & Qt.ShiftModifier:
            mod_list.append("shift")
        if modifiers & Qt.AltModifier:
            mod_list.append("alt")
        if modifiers & Qt.MetaModifier:
            mod_list.append("cmd")
        
        # Set hotkey
        self.key = key
        self.modifiers = mod_list
        
        # Log for debugging
        logger.info(f"Key captured: {self.key}, modifiers: {self.modifiers}")
        
        # Finish recording
        self._finish_recording()
    
    def start_recording(self):
        """Start recording a new hotkey"""
        # Limpar hotkey atual
        self.key = ""
        self.modifiers = []
        
        # Ativar o modo de gravação
        self.is_recording = True
        
        # Aplicar o estilo de gravação
        self.line_edit.setStyleSheet(self.recording_style)
        self.line_edit.setText("Pressione uma tecla ou botão do mouse...")
        
        # Dar foco ao campo de texto
        self.line_edit.setFocus()
        
        # Desativar o botão durante a gravação
        self.edit_button.setEnabled(False)
        
        # Garantir que o filtro de eventos esteja instalado
        self.installEventFilter(self)
        self.line_edit.installEventFilter(self)
        
        # Log para depuração
        logger.info("Started recording hotkey")
    
    def stop_recording(self):
        """Stop recording without saving"""
        # Desativar o modo de gravação
        self.is_recording = False
        
        # Remover o estilo de gravação
        self.line_edit.setStyleSheet("")
        
        # Atualizar o texto
        self._update_display()
        
        # Reativar o botão
        self.edit_button.setEnabled(True)
        
        # Remover o filtro de eventos para garantir que não continue capturando teclas
        self.removeEventFilter(self)
        self.line_edit.removeEventFilter(self)
        
        # Reinstalar o filtro de eventos para futuras gravações
        self.installEventFilter(self)
        self.line_edit.installEventFilter(self)
        
        # Log para depuração
        logger.info("Stopped recording without saving")
    
    def _finish_recording(self):
        """Finish recording and save the hotkey"""
        # Garantir que a gravação seja interrompida
        self.is_recording = False
        
        # Remover o estilo de gravação
        self.line_edit.setStyleSheet("")
        
        # Atualizar o texto
        self._update_display()
        
        # Remover o foco e reativar o botão
        self.line_edit.clearFocus()
        self.edit_button.setEnabled(True)
        
        # Remover o filtro de eventos para garantir que não continue capturando teclas
        self.removeEventFilter(self)
        self.line_edit.removeEventFilter(self)
        
        # Reinstalar o filtro de eventos para futuras gravações
        self.installEventFilter(self)
        self.line_edit.installEventFilter(self)
        
        # Log para depuração
        logger.info(f"Finished recording hotkey: {self.key}, modifiers: {self.modifiers}")
    
    def set_hotkey(self, key, modifiers):
        """Set the hotkey programmatically"""
        self.key = key
        self.modifiers = modifiers
        self._update_display()
    
    def get_hotkey(self):
        """Get the current hotkey"""
        return self.key, self.modifiers
    
    def _update_display(self):
        """Update the display text"""
        if not self.key:
            self.line_edit.setText("")
            return
        
        # Format modifiers
        mod_text = "+".join(mod.capitalize() for mod in self.modifiers)
        
        # Format key
        if self.key.startswith("mouse_"):
            key_text = self.key.replace("mouse_", "Mouse ").title()
        elif self.key in ["ctrl", "shift", "alt", "cmd"]:
            # Exibir teclas modificadoras de forma mais amigável
            key_map = {
                "ctrl": "Ctrl",
                "shift": "Shift",
                "alt": "Alt",
                "cmd": "Win"
            }
            key_text = key_map.get(self.key, self.key.upper())
        else:
            key_text = self.key.upper()
        
        # Combine
        if mod_text:
            self.line_edit.setText(f"{mod_text}+{key_text}")
        else:
            self.line_edit.setText(key_text)


class LanguageHotkeyEntry(QWidget):
    """Widget for configuring a language hotkey"""
    
    def __init__(self, parent=None):
        """Initialize the language hotkey entry"""
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Hotkey edit
        self.hotkey_edit = HotkeyEdit()
        layout.addWidget(self.hotkey_edit)
        
        # Language dropdown
        self.language_combo = QComboBox()
        self._populate_languages()
        layout.addWidget(self.language_combo)
        
        # Log for debugging
        logger.debug("LanguageHotkeyEntry initialized")
    
    def _populate_languages(self):
        """Populate the language dropdown"""
        languages = [
            ("en-US", "English (US)"),
            ("en-GB", "English (UK)"),
            ("pt-BR", "Portuguese (Brazil)"),
            ("pt-PT", "Portuguese (Portugal)"),
            ("es-ES", "Spanish (Spain)"),
            ("fr-FR", "French"),
            ("de-DE", "German"),
            ("it-IT", "Italian"),
            ("ja-JP", "Japanese"),
            ("zh-CN", "Chinese (Simplified)"),
            ("ru-RU", "Russian")
        ]
        
        for code, name in languages:
            self.language_combo.addItem(f"{name} ({code})", code)
    
    def set_hotkey(self, key, modifiers, language):
        """Set the hotkey and language"""
        self.hotkey_edit.set_hotkey(key, modifiers)
        
        # Set language
        index = self.language_combo.findData(language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
    
    def get_hotkey(self):
        """Get the current hotkey and language"""
        key, modifiers = self.hotkey_edit.get_hotkey()
        language = self.language_combo.currentData()
        return key, modifiers, language 