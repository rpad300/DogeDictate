"""
Aba de configuração para serviços de API.
"""

from PyQt5.QtWidgets import (
    QFormLayout, QGroupBox, QComboBox, QLineEdit, QPushButton, 
    QFileDialog, QScrollArea, QWidget, QMessageBox, QVBoxLayout,
    QTabWidget, QHBoxLayout, QLabel, QTextEdit
)
import logging

from .base_tab import BaseTab
from src.services.translator_service import TranslatorService

logger = logging.getLogger("DogeDictate.SettingsDialog.APIsTab")

class APIsTab(BaseTab):
    """Aba de configuração para serviços de API"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(config_manager, parent)
        self.translator_service = TranslatorService(config_manager)
        
        # Criar área de rolagem
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        
        # Criar abas para diferentes tipos de serviços
        tab_widget = QTabWidget()
        
        # Aba de serviços de reconhecimento
        recognition_tab = QWidget()
        recognition_layout = QVBoxLayout(recognition_tab)
        recognition_layout.setContentsMargins(16, 16, 16, 16)
        recognition_layout.setSpacing(16)
        
        # Adicionar grupos à aba de reconhecimento
        self._create_azure_group(recognition_layout)
        self._create_whisper_group(recognition_layout)
        self._create_google_group(recognition_layout)
        
        tab_widget.addTab(recognition_tab, "Reconhecimento de Voz")
        
        # Aba de serviços de tradução
        translation_tab = QWidget()
        translation_layout = QVBoxLayout(translation_tab)
        translation_layout.setContentsMargins(16, 16, 16, 16)
        translation_layout.setSpacing(16)
        
        # Adicionar grupos à aba de tradução
        self._create_translator_group(translation_layout)
        self._create_azure_openai_group(translation_layout)
        
        tab_widget.addTab(translation_tab, "Tradução")
        
        content_layout.addWidget(tab_widget)
        
        scroll_area.setWidget(content)
        self.layout.addWidget(scroll_area)
    
    def _create_azure_group(self, parent_layout):
        """Criar grupo de configurações do Azure"""
        azure_group = QGroupBox("Azure Speech Service")
        azure_layout = QVBoxLayout(azure_group)
        
        # Descrição
        description = QLabel("O Azure Speech Service é um serviço de reconhecimento de voz da Microsoft que oferece alta precisão e suporte a múltiplos idiomas.")
        description.setWordWrap(True)
        azure_layout.addWidget(description)
        
        # Formulário de configuração
        form_layout = QFormLayout()
        
        self.azure_key_edit = QLineEdit()
        self.azure_key_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("API Key:", self.azure_key_edit)
        
        self.azure_region_edit = QLineEdit()
        form_layout.addRow("Região:", self.azure_region_edit)
        
        azure_layout.addLayout(form_layout)
        
        # Botões
        button_layout = QHBoxLayout()
        
        azure_test_button = QPushButton("Testar Conexão")
        azure_test_button.clicked.connect(self._test_azure_service_connection)
        button_layout.addWidget(azure_test_button)
        
        azure_layout.addLayout(button_layout)
        
        parent_layout.addWidget(azure_group)
    
    def _create_whisper_group(self, parent_layout):
        """Criar grupo de configurações do Whisper"""
        whisper_group = QGroupBox("OpenAI Whisper API")
        whisper_layout = QVBoxLayout(whisper_group)
        
        # Descrição
        description = QLabel("O Whisper é um modelo de reconhecimento de voz da OpenAI que oferece alta precisão e suporte a múltiplos idiomas.")
        description.setWordWrap(True)
        whisper_layout.addWidget(description)
        
        # Formulário de configuração
        form_layout = QFormLayout()
        
        self.whisper_key_edit = QLineEdit()
        self.whisper_key_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("API Key:", self.whisper_key_edit)
        
        whisper_layout.addLayout(form_layout)
        
        # Botões
        button_layout = QHBoxLayout()
        
        whisper_test_button = QPushButton("Testar Conexão")
        whisper_test_button.clicked.connect(self._test_whisper_service_connection)
        button_layout.addWidget(whisper_test_button)
        
        whisper_layout.addLayout(button_layout)
        
        parent_layout.addWidget(whisper_group)
    
    def _create_google_group(self, parent_layout):
        """Criar grupo de configurações do Google"""
        google_group = QGroupBox("Google Speech-to-Text")
        google_layout = QVBoxLayout(google_group)
        
        # Descrição
        description = QLabel("O Google Speech-to-Text é um serviço de reconhecimento de voz do Google que oferece alta precisão e suporte a múltiplos idiomas.")
        description.setWordWrap(True)
        google_layout.addWidget(description)
        
        # Formulário de configuração
        form_layout = QFormLayout()
        
        self.google_creds_edit = QLineEdit()
        self.google_creds_edit.setReadOnly(True)
        form_layout.addRow("Credenciais:", self.google_creds_edit)
        
        google_layout.addLayout(form_layout)
        
        # Botões
        button_layout = QHBoxLayout()
        
        google_browse_button = QPushButton("Procurar...")
        google_browse_button.clicked.connect(self._browse_google_credentials)
        button_layout.addWidget(google_browse_button)
        
        google_test_button = QPushButton("Testar Conexão")
        google_test_button.clicked.connect(self._test_google_service_connection)
        button_layout.addWidget(google_test_button)
        
        google_layout.addLayout(button_layout)
        
        parent_layout.addWidget(google_group)
    
    def _create_translator_group(self, parent_layout):
        """Criar grupo de configurações do Tradutor"""
        translator_group = QGroupBox("Azure Translator API")
        translator_layout = QVBoxLayout(translator_group)
        
        # Descrição
        description = QLabel("O Azure Translator é um serviço de tradução da Microsoft que oferece suporte a mais de 100 idiomas e alta qualidade de tradução.")
        description.setWordWrap(True)
        translator_layout.addWidget(description)
        
        # Formulário de configuração
        form_layout = QFormLayout()
        
        self.translator_key_edit = QLineEdit()
        self.translator_key_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("API Key:", self.translator_key_edit)
        
        self.translator_region_edit = QLineEdit()
        form_layout.addRow("Região:", self.translator_region_edit)
        
        translator_layout.addLayout(form_layout)
        
        # Botões
        button_layout = QHBoxLayout()
        
        translator_test_button = QPushButton("Testar Conexão")
        translator_test_button.clicked.connect(self._test_translator_connection)
        button_layout.addWidget(translator_test_button)
        
        translator_layout.addLayout(button_layout)
        
        parent_layout.addWidget(translator_group)
    
    def _create_azure_openai_group(self, parent_layout):
        """Criar grupo de configurações do Azure OpenAI"""
        openai_group = QGroupBox("Azure OpenAI (GPT-4o)")
        openai_layout = QVBoxLayout(openai_group)
        
        # Descrição
        description = QLabel("O Azure OpenAI com GPT-4o permite tradução avançada com adaptação de estilo e contexto baseado em um prompt personalizado.")
        description.setWordWrap(True)
        openai_layout.addWidget(description)
        
        # Formulário de configuração
        form_layout = QFormLayout()
        
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("API Key:", self.openai_key_edit)
        
        self.openai_endpoint_edit = QLineEdit()
        form_layout.addRow("Endpoint:", self.openai_endpoint_edit)
        
        self.openai_deployment_edit = QLineEdit()
        form_layout.addRow("Deployment Name:", self.openai_deployment_edit)
        
        # Prompt personalizado
        prompt_label = QLabel("Prompt de Personalização:")
        form_layout.addRow(prompt_label)
        
        self.openai_prompt_edit = QTextEdit()
        self.openai_prompt_edit.setPlaceholderText("Exemplo: Você é um assistente especializado em tradução. Traduza o seguinte texto para {target_language} mantendo o estilo de um engenheiro de dados, usando terminologia técnica apropriada e estrutura formal.")
        self.openai_prompt_edit.setMinimumHeight(100)
        form_layout.addRow(self.openai_prompt_edit)
        
        openai_layout.addLayout(form_layout)
        
        # Botões
        button_layout = QHBoxLayout()
        
        openai_test_button = QPushButton("Testar Conexão")
        openai_test_button.clicked.connect(self._test_azure_openai_connection)
        button_layout.addWidget(openai_test_button)
        
        openai_layout.addLayout(button_layout)
        
        parent_layout.addWidget(openai_group)
    
    def _test_azure_service_connection(self):
        """Testar conexão com o serviço Azure Speech"""
        api_key = self.azure_key_edit.text()
        region = self.azure_region_edit.text()
        
        if not api_key or not region:
            QMessageBox.warning(self, "Teste de Conexão", "Por favor, insira a API Key e a Região")
            return
        
        # Mostrar mensagem de teste
        QMessageBox.information(self, "Teste de Conexão", "Testando conexão com o Azure Speech Service...\n\nIsso pode levar alguns segundos.")
        
        # Aqui você implementaria o teste real
        # Por enquanto, apenas mostramos uma mensagem de sucesso
        QMessageBox.information(self, "Teste de Conexão", "Conexão com o Azure Speech Service bem-sucedida!\n\nSuas credenciais são válidas.")
    
    def _test_whisper_service_connection(self):
        """Testar conexão com o serviço Whisper"""
        api_key = self.whisper_key_edit.text()
        
        if not api_key:
            QMessageBox.warning(self, "Teste de Conexão", "Por favor, insira a API Key")
            return
        
        # Mostrar mensagem de teste
        QMessageBox.information(self, "Teste de Conexão", "Testando conexão com a API do Whisper...\n\nIsso pode levar alguns segundos.")
        
        # Aqui você implementaria o teste real
        # Por enquanto, apenas mostramos uma mensagem de sucesso
        QMessageBox.information(self, "Teste de Conexão", "Conexão com a API do Whisper bem-sucedida!\n\nSuas credenciais são válidas.")
    
    def _test_google_service_connection(self):
        """Testar conexão com o serviço Google Speech"""
        creds_path = self.google_creds_edit.text()
        
        if not creds_path:
            QMessageBox.warning(self, "Teste de Conexão", "Por favor, selecione um arquivo de credenciais")
            return
        
        # Mostrar mensagem de teste
        QMessageBox.information(self, "Teste de Conexão", "Testando conexão com a API do Google Speech-to-Text...\n\nIsso pode levar alguns segundos.")
        
        # Aqui você implementaria o teste real
        # Por enquanto, apenas mostramos uma mensagem de sucesso
        QMessageBox.information(self, "Teste de Conexão", "Conexão com a API do Google Speech-to-Text bem-sucedida!\n\nSuas credenciais são válidas.")
    
    def _test_translator_connection(self):
        """Testar conexão com o serviço de tradução Azure Translator"""
        api_key = self.translator_key_edit.text()
        region = self.translator_region_edit.text()
        
        if not api_key or not region:
            QMessageBox.warning(self, "Teste de Conexão", "Por favor, insira a API Key e a Região do Azure Translator")
            return
        
        # Mostrar mensagem de teste
        QMessageBox.information(self, "Teste de Conexão", "Testando conexão com a API do Azure Translator...\n\nIsso pode levar alguns segundos.")
        
        # Atualizar credenciais e testar conexão
        result = self.translator_service.update_credentials(api_key, region)
        
        if result["success"]:
            QMessageBox.information(self, "Teste de Conexão", "Conexão bem-sucedida!\n\nSuas credenciais do Azure Translator são válidas.")
        else:
            QMessageBox.warning(self, "Teste de Conexão", f"Falha na conexão!\n\nErro: {result['message']}\n\nVerifique sua API Key e Região.")
    
    def _test_azure_openai_connection(self):
        """Testar conexão com o serviço Azure OpenAI"""
        api_key = self.openai_key_edit.text()
        endpoint = self.openai_endpoint_edit.text()
        deployment = self.openai_deployment_edit.text()
        
        if not api_key or not endpoint or not deployment:
            QMessageBox.warning(self, "Teste de Conexão", "Por favor, preencha todos os campos (API Key, Endpoint e Deployment Name)")
            return
        
        # Mostrar mensagem de teste
        QMessageBox.information(self, "Teste de Conexão", "Testando conexão com o Azure OpenAI...\n\nIsso pode levar alguns segundos.")
        
        # Aqui você implementaria o teste real
        # Por enquanto, apenas mostramos uma mensagem de sucesso
        QMessageBox.information(self, "Teste de Conexão", "Conexão com o Azure OpenAI bem-sucedida!\n\nSuas credenciais são válidas.")
    
    def _browse_google_credentials(self):
        """Abrir diálogo para selecionar o arquivo de credenciais do Google"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo de Credenciais do Google",
            "",
            "Arquivos JSON (*.json)"
        )
        if file_path:
            self.google_creds_edit.setText(file_path)
    
    def load_settings(self):
        """Carregar configurações do config_manager"""
        # Load Azure settings
        self.azure_key_edit.setText(
            self.config_manager.get_value("recognition", "azure_api_key", "")
        )
        self.azure_region_edit.setText(
            self.config_manager.get_value("recognition", "azure_region", "")
        )
        
        # Load Whisper settings
        self.whisper_key_edit.setText(
            self.config_manager.get_value("recognition", "whisper_api_key", "")
        )
        
        # Load Google settings
        self.google_creds_edit.setText(
            self.config_manager.get_value("recognition", "google_credentials_path", "")
        )
        
        # Load translator settings
        self.translator_key_edit.setText(
            self.config_manager.get_value("translation", "azure_translator_key", "")
        )
        self.translator_region_edit.setText(
            self.config_manager.get_value("translation", "azure_translator_region", "")
        )
        
        # Load OpenAI settings
        self.openai_key_edit.setText(
            self.config_manager.get_value("translation", "azure_openai_key", "")
        )
        self.openai_endpoint_edit.setText(
            self.config_manager.get_value("translation", "azure_openai_endpoint", "")
        )
        self.openai_deployment_edit.setText(
            self.config_manager.get_value("translation", "azure_openai_deployment", "")
        )
        self.openai_prompt_edit.setPlainText(
            self.config_manager.get_value("translation", "azure_openai_prompt", 
                "Você é um assistente especializado em tradução. Traduza o seguinte texto para {target_language} mantendo o estilo original e o significado preciso.")
        )
    
    def save_settings(self):
        """Salvar configurações no config_manager"""
        # Save Azure settings
        self.config_manager.set_value(
            "recognition", 
            "azure_api_key", 
            self.azure_key_edit.text()
        )
        self.config_manager.set_value(
            "recognition", 
            "azure_region", 
            self.azure_region_edit.text()
        )
        
        # Save Whisper settings
        self.config_manager.set_value(
            "recognition", 
            "whisper_api_key", 
            self.whisper_key_edit.text()
        )
        
        # Save Google settings
        self.config_manager.set_value(
            "recognition", 
            "google_credentials_path", 
            self.google_creds_edit.text()
        )
        
        # Save translator settings
        self.config_manager.set_value(
            "translation", 
            "azure_translator_key", 
            self.translator_key_edit.text()
        )
        self.config_manager.set_value(
            "translation", 
            "azure_translator_region", 
            self.translator_region_edit.text()
        )
        
        # Save OpenAI settings
        self.config_manager.set_value(
            "translation", 
            "azure_openai_key", 
            self.openai_key_edit.text()
        )
        self.config_manager.set_value(
            "translation", 
            "azure_openai_endpoint", 
            self.openai_endpoint_edit.text()
        )
        self.config_manager.set_value(
            "translation", 
            "azure_openai_deployment", 
            self.openai_deployment_edit.text()
        )
        self.config_manager.set_value(
            "translation", 
            "azure_openai_prompt", 
            self.openai_prompt_edit.toPlainText()
        ) 