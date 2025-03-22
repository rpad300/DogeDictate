#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Floating Bar for DogeDictate
Displays dictation status and controls
"""

import logging
import time
import traceback

# Imports do PyQt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QProgressBar, QApplication
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QSize
from PyQt5.QtGui import QColor, QPalette, QFont, QIcon, QPixmap

# Imports próprios
from src.gui.styles import FLOATING_BAR_STYLE

class FloatingBar(QWidget):
    """Barra flutuante para controle da ditação"""
    
    # Configurar logger no nível da classe
    logger = logging.getLogger("DogeDictate.FloatingBar")
    
    def __init__(self, config_manager, dictation_manager, parent=None):
        """Initialize the floating bar"""
        super().__init__(None, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        
        self.config_manager = config_manager
        self.dictation_manager = dictation_manager
        self.parent = parent
        self.dragging = False
        self.drag_position = None
        
        # Set window properties
        self.setWindowTitle("DogeDictate")
        self.setMinimumSize(220, 60)
        self.setMaximumHeight(60)
        
        # Apply style
        self.setStyleSheet(FLOATING_BAR_STYLE)
        
        # Initialize UI
        self._init_ui()
        
        # Position the bar
        self._position_bar()
        
        # Start update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(500)  # Update every 500ms for less CPU usage
        
        # Audio level animation
        self.audio_level = 0
        self.target_audio_level = 0
        self.last_audio_check = 0
        self.initial_mic_test_done = False
        
        # Realizar um teste de microfone único ao iniciar
        self.logger.info("Realizando teste único de microfone durante a inicialização")
        self._do_microphone_test()
    
    def _init_ui(self):
        """Initialize the user interface"""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(5)
        
        # Top row with status and language
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 12))
        self.status_indicator.setStyleSheet("color: gray;")
        top_layout.addWidget(self.status_indicator)
        
        # Language indicator
        self.language_label = QLabel("en-US")
        self.language_label.setFont(QFont("Arial", 10))
        top_layout.addWidget(self.language_label)
        
        # Spacer
        top_layout.addStretch()
        
        # Pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setFixedSize(60, 24)
        self.pause_button.clicked.connect(self._toggle_pause)
        top_layout.addWidget(self.pause_button)
        
        # Close button
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(24, 24)
        self.close_button.clicked.connect(self.hide)
        top_layout.addWidget(self.close_button)
        
        # Add top layout to main layout
        main_layout.addLayout(top_layout)
        
        # Audio level progress bar
        self.audio_level_bar = QProgressBar()
        self.audio_level_bar.setRange(0, 100)
        self.audio_level_bar.setValue(0)
        self.audio_level_bar.setTextVisible(False)
        self.audio_level_bar.setFixedHeight(6)
        main_layout.addWidget(self.audio_level_bar)
    
    def _position_bar(self):
        """Position the floating bar on the screen"""
        # Position at the top center of the screen
        desktop = self.screen().availableGeometry()
        self.move(
            (desktop.width() - self.width()) // 2,
            10  # 10 pixels from the top
        )
    
    def _do_microphone_test(self):
        """Realizar um teste de microfone único"""
        try:
            if hasattr(self.dictation_manager, 'test_microphone'):
                # Obter o ID do microfone atual da configuração
                mic_id = self.dictation_manager.config_manager.get_value("audio", "microphone_id", 0)
                
                self.logger.debug("Realizando teste de microfone")
                
                # Get real audio level from microphone
                mic_test = self.dictation_manager.test_microphone(mic_id)
                if isinstance(mic_test, dict) and 'level' in mic_test:
                    self.target_audio_level = min(int(mic_test["level"] * 100), 100)
                    self.logger.debug(f"Nível de áudio detectado: {self.target_audio_level}")
                else:
                    self.target_audio_level = 0
                    self.logger.warning("Teste de microfone não retornou nível de áudio")
                
                # Atualizar flag de teste inicial
                self.initial_mic_test_done = True
                
            else:
                self.logger.error("DictationManager não possui método test_microphone")
        except Exception as e:
            # Em caso de erro, não atualizar o nível de áudio
            self.target_audio_level = 0
            # Registrar o erro no log
            self.logger.error(f"Erro ao testar microfone: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _update_status(self):
        """Update the status display"""
        try:
            # Update dictation status
            if hasattr(self.dictation_manager, 'is_dictating'):
                is_dictating = self.dictation_manager.is_dictating
                self.status_indicator.setStyleSheet(
                    "color: #34A853;" if is_dictating else "color: gray;"
                )
            
            # Update language
            if hasattr(self.dictation_manager, 'current_language'):
                self.language_label.setText(self.dictation_manager.current_language)
            
            # Não fazer mais testes de microfone, usar apenas o nível já estabelecido
            # ou ajustar animação se necessário
            
            # Animate audio level
            if self.audio_level < self.target_audio_level:
                self.audio_level = min(self.audio_level + 5, self.target_audio_level)
            elif self.audio_level > self.target_audio_level:
                self.audio_level = max(self.audio_level - 5, self.target_audio_level)
            
            # Update progress bar
            self.audio_level_bar.setValue(self.audio_level)
            
            # Update pause button text
            if hasattr(self.dictation_manager, 'is_dictating'):
                self.pause_button.setText("Pause" if self.dictation_manager.is_dictating else "Start")
                
        except Exception as e:
            # Capturar qualquer erro para evitar que a interface trave
            self.logger.error(f"Erro na atualização da interface: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _toggle_pause(self):
        """Toggle dictation pause state"""
        if hasattr(self.dictation_manager, 'is_dictating'):
            if self.dictation_manager.is_dictating:
                self.dictation_manager.stop_dictation()
            else:
                # Fazer um teste de microfone antes de iniciar a ditação
                self._do_microphone_test()
                self.dictation_manager.start_dictation()
    
    def mousePressEvent(self, event):
        """Handle mouse press events for dragging"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging"""
        if event.buttons() & Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events for dragging"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
    
    def showEvent(self, event):
        """Handle show event"""
        # Update position when shown
        self._position_bar()
        super().showEvent(event)
    
    def closeEvent(self, event):
        """Handle close event"""
        # Stop the update timer
        self.update_timer.stop()
        super().closeEvent(event)

    def update_mic_level(self):
        """Update the microphone level directly"""
        # Não fazer nada - testes de microfone estão desativados
        # O teste inicial já foi feito durante a inicialização
        pass 