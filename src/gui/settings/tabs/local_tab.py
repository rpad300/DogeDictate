"""
Aba de configuração para serviços locais.
"""

from PyQt5.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QLineEdit, QPushButton, QFileDialog,
    QProgressBar, QLabel, QMessageBox, QHBoxLayout, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import logging
import os

from .base_tab import BaseTab

logger = logging.getLogger("DogeDictate.SettingsDialog.LocalTab")

class ModelDownloadThread(QThread):
    """Thread para download de modelos"""
    progress_updated = pyqtSignal(int)
    download_complete = pyqtSignal(bool, str)
    
    def __init__(self, model_type, model_name, download_path):
        super().__init__()
        self.model_type = model_type
        self.model_name = model_name
        self.download_path = download_path
    
    def run(self):
        """Executar o download do modelo"""
        try:
            # Simulação de download (aqui você implementaria o download real)
            for i in range(101):
                self.progress_updated.emit(i)
                self.msleep(50)  # Simular progresso
            
            # Simular sucesso
            self.download_complete.emit(True, "Download concluído com sucesso!")
        except Exception as e:
            logger.error(f"Error downloading model: {str(e)}")
            self.download_complete.emit(False, f"Erro no download: {str(e)}")

class LocalTab(BaseTab):
    """Aba de configuração para serviços locais"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(config_manager, parent)
        
        # Whisper Local settings group
        self._create_whisper_group()
        
        # M100 settings group
        self._create_m100_group()
        
        # Download status
        self.download_thread = None
        self.current_download_progress = None
    
    def _create_whisper_group(self):
        """Criar grupo de configurações do Whisper Local"""
        whisper_group = QGroupBox("Whisper Local")
        whisper_layout = QFormLayout(whisper_group)
        
        # Modelo
        self.whisper_local_model_combo = QComboBox()
        self.whisper_local_model_combo.addItem("Tiny", "tiny")
        self.whisper_local_model_combo.addItem("Base", "base")
        self.whisper_local_model_combo.addItem("Small", "small")
        self.whisper_local_model_combo.addItem("Medium", "medium")
        self.whisper_local_model_combo.addItem("Large", "large")
        whisper_layout.addRow("Modelo:", self.whisper_local_model_combo)
        
        # Status do modelo
        self.whisper_status_label = QLabel("Status: Não instalado")
        whisper_layout.addRow("", self.whisper_status_label)
        
        # Botões de ação
        button_layout = QHBoxLayout()
        
        self.whisper_download_button = QPushButton("Baixar Modelo")
        self.whisper_download_button.clicked.connect(self._download_whisper_model)
        button_layout.addWidget(self.whisper_download_button)
        
        self.whisper_remove_button = QPushButton("Remover Modelo")
        self.whisper_remove_button.clicked.connect(self._remove_whisper_model)
        button_layout.addWidget(self.whisper_remove_button)
        
        whisper_layout.addRow("", button_layout)
        
        # Barra de progresso
        self.whisper_progress = QProgressBar()
        self.whisper_progress.setVisible(False)
        whisper_layout.addRow("Progresso:", self.whisper_progress)
        
        # Opção para usar GPU
        self.whisper_gpu_check = QCheckBox("Usar GPU (requer CUDA)")
        whisper_layout.addRow("", self.whisper_gpu_check)
        
        self.layout.addWidget(whisper_group)
    
    def _create_m100_group(self):
        """Criar grupo de configurações do M100"""
        m100_group = QGroupBox("M100 (Tradução Local)")
        m100_layout = QFormLayout(m100_group)
        
        # Modelo
        self.m100_model_combo = QComboBox()
        self.m100_model_combo.addItem("Small (418M)", "small")
        self.m100_model_combo.addItem("Medium (1.2B)", "medium")
        self.m100_model_combo.addItem("Large (12B)", "large")
        m100_layout.addRow("Modelo:", self.m100_model_combo)
        
        # Diretório do modelo
        self.m100_model_path = QLineEdit()
        self.m100_model_path.setReadOnly(True)
        m100_layout.addRow("Diretório:", self.m100_model_path)
        
        # Status do modelo
        self.m100_status_label = QLabel("Status: Não instalado")
        m100_layout.addRow("", self.m100_status_label)
        
        # Botões de ação
        button_layout = QHBoxLayout()
        
        self.m100_browse_button = QPushButton("Procurar...")
        self.m100_browse_button.clicked.connect(self._browse_m100_model)
        button_layout.addWidget(self.m100_browse_button)
        
        self.m100_download_button = QPushButton("Baixar Modelo")
        self.m100_download_button.clicked.connect(self._download_m100_model)
        button_layout.addWidget(self.m100_download_button)
        
        self.m100_remove_button = QPushButton("Remover Modelo")
        self.m100_remove_button.clicked.connect(self._remove_m100_model)
        button_layout.addWidget(self.m100_remove_button)
        
        m100_layout.addRow("", button_layout)
        
        # Barra de progresso
        self.m100_progress = QProgressBar()
        self.m100_progress.setVisible(False)
        m100_layout.addRow("Progresso:", self.m100_progress)
        
        # Opção para usar GPU
        self.m100_gpu_check = QCheckBox("Usar GPU (requer CUDA)")
        m100_layout.addRow("", self.m100_gpu_check)
        
        self.layout.addWidget(m100_group)
    
    def _browse_m100_model(self):
        """Abrir diálogo para selecionar o diretório do modelo M100"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select M100 Model Directory",
            ""
        )
        if dir_path:
            self.m100_model_path.setText(dir_path)
            self._check_m100_model_status()
    
    def _download_whisper_model(self):
        """Iniciar download do modelo Whisper"""
        model = self.whisper_local_model_combo.currentData()
        download_path = os.path.join(
            os.path.expanduser("~"),
            ".dogedictate",
            "models",
            "whisper"
        )
        
        # Criar diretório se não existir
        os.makedirs(download_path, exist_ok=True)
        
        # Iniciar download
        self.whisper_progress.setVisible(True)
        self.whisper_download_button.setEnabled(False)
        self.current_download_progress = self.whisper_progress
        
        self.download_thread = ModelDownloadThread("whisper", model, download_path)
        self.download_thread.progress_updated.connect(self._update_download_progress)
        self.download_thread.download_complete.connect(self._whisper_download_complete)
        self.download_thread.start()
    
    def _download_m100_model(self):
        """Iniciar download do modelo M100"""
        model = self.m100_model_combo.currentData()
        download_path = os.path.join(
            os.path.expanduser("~"),
            ".dogedictate",
            "models",
            "m100"
        )
        
        # Criar diretório se não existir
        os.makedirs(download_path, exist_ok=True)
        
        # Iniciar download
        self.m100_progress.setVisible(True)
        self.m100_download_button.setEnabled(False)
        self.current_download_progress = self.m100_progress
        
        self.download_thread = ModelDownloadThread("m100", model, download_path)
        self.download_thread.progress_updated.connect(self._update_download_progress)
        self.download_thread.download_complete.connect(self._m100_download_complete)
        self.download_thread.start()
    
    def _update_download_progress(self, value):
        """Atualizar barra de progresso do download"""
        if self.current_download_progress:
            self.current_download_progress.setValue(value)
    
    def _whisper_download_complete(self, success, message):
        """Callback para quando o download do Whisper terminar"""
        self.whisper_progress.setVisible(False)
        self.whisper_download_button.setEnabled(True)
        
        if success:
            self.whisper_status_label.setText("Status: Instalado")
            model = self.whisper_local_model_combo.currentData()
            model_path = os.path.join(
                os.path.expanduser("~"),
                ".dogedictate",
                "models",
                "whisper",
                model
            )
            self.config_manager.set_value("recognition", "whisper_local_model_path", model_path)
        
        QMessageBox.information(self, "Download de Modelo", message)
        self._check_whisper_model_status()
    
    def _m100_download_complete(self, success, message):
        """Callback para quando o download do M100 terminar"""
        self.m100_progress.setVisible(False)
        self.m100_download_button.setEnabled(True)
        
        if success:
            self.m100_status_label.setText("Status: Instalado")
            model = self.m100_model_combo.currentData()
            model_path = os.path.join(
                os.path.expanduser("~"),
                ".dogedictate",
                "models",
                "m100",
                model
            )
            self.m100_model_path.setText(model_path)
            self.config_manager.set_value("translation", "m100_model_path", model_path)
        
        QMessageBox.information(self, "Download de Modelo", message)
        self._check_m100_model_status()
    
    def _remove_whisper_model(self):
        """Remover modelo Whisper"""
        model = self.whisper_local_model_combo.currentData()
        model_path = os.path.join(
            os.path.expanduser("~"),
            ".dogedictate",
            "models",
            "whisper",
            model
        )
        
        reply = QMessageBox.question(
            self,
            "Remover Modelo",
            f"Tem certeza que deseja remover o modelo Whisper {model}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Aqui você implementaria a remoção real do modelo
            # Por enquanto, apenas simulamos
            self.config_manager.set_value("recognition", "whisper_local_model_path", "")
            self.whisper_status_label.setText("Status: Não instalado")
            QMessageBox.information(self, "Remover Modelo", "Modelo removido com sucesso!")
    
    def _remove_m100_model(self):
        """Remover modelo M100"""
        model = self.m100_model_combo.currentData()
        model_path = self.m100_model_path.text()
        
        if not model_path:
            QMessageBox.warning(self, "Remover Modelo", "Nenhum modelo instalado para remover.")
            return
        
        reply = QMessageBox.question(
            self,
            "Remover Modelo",
            f"Tem certeza que deseja remover o modelo M100 {model}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Aqui você implementaria a remoção real do modelo
            # Por enquanto, apenas simulamos
            self.config_manager.set_value("translation", "m100_model_path", "")
            self.m100_model_path.setText("")
            self.m100_status_label.setText("Status: Não instalado")
            QMessageBox.information(self, "Remover Modelo", "Modelo removido com sucesso!")
    
    def _check_whisper_model_status(self):
        """Verificar status do modelo Whisper"""
        model = self.whisper_local_model_combo.currentData()
        model_path = self.config_manager.get_value("recognition", "whisper_local_model_path", "")
        
        if model_path and os.path.exists(model_path):
            self.whisper_status_label.setText("Status: Instalado")
            self.whisper_remove_button.setEnabled(True)
        else:
            self.whisper_status_label.setText("Status: Não instalado")
            self.whisper_remove_button.setEnabled(False)
    
    def _check_m100_model_status(self):
        """Verificar status do modelo M100"""
        model_path = self.m100_model_path.text()
        
        if model_path and os.path.exists(model_path):
            self.m100_status_label.setText("Status: Instalado")
            self.m100_remove_button.setEnabled(True)
        else:
            self.m100_status_label.setText("Status: Não instalado")
            self.m100_remove_button.setEnabled(False)
    
    def load_settings(self):
        """Carregar configurações do config_manager"""
        # Load Whisper Local settings
        self.whisper_local_model_combo.setCurrentIndex(
            self.whisper_local_model_combo.findData(
                self.config_manager.get_value("recognition", "whisper_local_model", "base")
            )
        )
        self.whisper_gpu_check.setChecked(
            self.config_manager.get_value("recognition", "whisper_local_use_gpu", False)
        )
        
        # Load M100 settings
        self.m100_model_combo.setCurrentIndex(
            self.m100_model_combo.findData(
                self.config_manager.get_value("translation", "m100_model", "small")
            )
        )
        self.m100_model_path.setText(
            self.config_manager.get_value("translation", "m100_model_path", "")
        )
        self.m100_gpu_check.setChecked(
            self.config_manager.get_value("translation", "m100_use_gpu", False)
        )
        
        # Check model status
        self._check_whisper_model_status()
        self._check_m100_model_status()
    
    def save_settings(self):
        """Salvar configurações no config_manager"""
        # Save Whisper Local settings
        self.config_manager.set_value(
            "recognition", 
            "whisper_local_model", 
            self.whisper_local_model_combo.currentData()
        )
        self.config_manager.set_value(
            "recognition", 
            "whisper_local_use_gpu", 
            self.whisper_gpu_check.isChecked()
        )
        
        # Save M100 settings
        self.config_manager.set_value(
            "translation", 
            "m100_model", 
            self.m100_model_combo.currentData()
        )
        self.config_manager.set_value(
            "translation", 
            "m100_model_path", 
            self.m100_model_path.text()
        )
        self.config_manager.set_value(
            "translation", 
            "m100_use_gpu", 
            self.m100_gpu_check.isChecked()
        ) 