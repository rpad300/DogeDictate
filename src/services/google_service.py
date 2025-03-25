#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Service for DogeDictate
Handles speech recognition using Google Speech-to-Text
"""

import os
import logging
import tempfile
import time
from google.cloud import speech
from google.oauth2 import service_account

logger = logging.getLogger("DogeDictate.GoogleService")

class GoogleService:
    """Service for speech recognition using Google Speech-to-Text"""
    
    def __init__(self, config_manager):
        """Initialize the Google Speech-to-Text service"""
        self.config_manager = config_manager
        self.credentials_path = self.config_manager.get_value("recognition", "google_credentials_path", "")
        self.client = None
        
        # Log detalhado para diagnóstico
        if self.credentials_path and os.path.exists(self.credentials_path):
            logger.info(f"Google Speech inicializado: Credentials path={self.credentials_path}")
            # Verificar se as credenciais são válidas, mas não inicializar o cliente ainda (lazy loading)
        else:
            if not self.credentials_path:
                logger.warning("Google Speech não configurado: Caminho de credenciais não definido")
            elif not os.path.exists(self.credentials_path):
                logger.warning(f"Google Speech não configurado: Arquivo de credenciais não encontrado em {self.credentials_path}")
    
    def is_available(self):
        """Check if the service is available"""
        try:
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                return False
                
            # Verificar se é possível inicializar o cliente
            if self.client is None:
                return self._initialize_client()
            return True
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade do Google Speech: {str(e)}")
            return False
            
    def _initialize_client(self):
        """Initialize the Google Speech-to-Text client"""
        try:
            # Verificar se o caminho de credenciais existe
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                logger.error(f"Arquivo de credenciais do Google não encontrado: {self.credentials_path}")
                return False
                
            # Configurar variável de ambiente para credenciais
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            
            # Importar módulo apenas quando necessário
            from google.cloud import speech
            
            # Inicializar cliente
            start_time = time.time()
            self.client = speech.SpeechClient()
            load_time = time.time() - start_time
            
            logger.info(f"Cliente Google Speech inicializado em {load_time:.2f}s")
            return True
        except ImportError:
            logger.error("Módulo google-cloud-speech não instalado. Instale com: pip install google-cloud-speech")
            return False
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente Google Speech: {str(e)}")
            return False
    
    def recognize_speech(self, audio_data, language=None):
        """
        Recognize speech from audio data
        
        Args:
            audio_data (bytes or str): Audio data in bytes format or path to audio file
            language (str, optional): Language code (e.g., "en-US"). Defaults to None.
            
        Returns:
            str: Recognized text
        """
        # Verificar disponibilidade do serviço
        if not self.is_available():
            logger.error("Serviço Google Speech não está disponível")
            return ""
            
        # Log detalhado
        logger.info(f"Iniciando reconhecimento com Google Speech, idioma: {language}")
        
        try:
            # Importar módulos do Google apenas quando necessário
            from google.cloud import speech
            
            # Inicializar cliente se ainda não estiver inicializado
            if self.client is None:
                if not self._initialize_client():
                    return ""
            
            # Validar idioma
            if language is None:
                language = "pt-BR"  # Default to Portuguese
            
            # Converter código de idioma para formato esperado pelo Google (sem região)
            google_language = language.split('-')[0] if '-' in language else language
                
            # Processar o áudio
            if isinstance(audio_data, str) and os.path.exists(audio_data):
                # É um caminho para arquivo
                with open(audio_data, "rb") as audio_file:
                    content = audio_file.read()
            else:
                # É conteúdo binário
                content = audio_data
                
            # Configurar requisição para o Google
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=google_language,
                enable_automatic_punctuation=True
            )
            
            # Realizar reconhecimento
            start_time = time.time()
            response = self.client.recognize(config=config, audio=audio)
            recognition_time = time.time() - start_time
            
            # Processar resultado
            result = ""
            for res in response.results:
                result += res.alternatives[0].transcript + " "
                
            logger.info(f"Reconhecimento Google Speech concluído em {recognition_time:.2f}s: '{result}'")
            return result.strip()
            
        except Exception as e:
            logger.error(f"Erro no reconhecimento com Google Speech: {str(e)}")
            return ""
    
    def update_credentials(self, credentials_path):
        """
        Update credentials for Google Speech service
        
        Args:
            credentials_path (str): Path to Google credentials JSON file
            
        Returns:
            bool: True if update is successful, False otherwise
        """
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(credentials_path):
                logger.error(f"Arquivo de credenciais não encontrado: {credentials_path}")
                return False
                
            # Atualizar caminho
            self.credentials_path = credentials_path
            
            # Atualizar variável de ambiente
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            
            # Resetar cliente para forçar reinicialização na próxima chamada
            self.client = None
            
            logger.info(f"Credenciais do Google Speech atualizadas: {credentials_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar credenciais do Google Speech: {str(e)}")
            return False
    
    def test_connection(self):
        """Test the connection to Google Speech-to-Text"""
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            return {
                "success": False,
                "message": "Google Speech-to-Text credentials not configured or file not found"
            }
        
        try:
            # Initialize client if not already done
            if not self.client:
                self._initialize_client()
            
            # If client initialization failed, return error
            if not self.client:
                return {
                    "success": False,
                    "message": "Failed to initialize Google Speech-to-Text client"
                }
            
            # List available operations (this will fail if credentials are invalid)
            self.client.operations.list()
            
            # If we get here, the credentials are valid
            return {
                "success": True,
                "message": "Successfully connected to Google Speech-to-Text"
            }
        
        except Exception as e:
            logger.error(f"Google Speech-to-Text connection test failed: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to connect to Google Speech-to-Text: {str(e)}"
            }
    
    def update_credentials_path(self, credentials_path):
        """Update the Google Speech-to-Text credentials path"""
        if not os.path.exists(credentials_path):
            return {
                "success": False,
                "message": f"Credentials file not found: {credentials_path}"
            }
        
        self.credentials_path = credentials_path
        self.config_manager.set_value("recognition", "google_credentials_path", credentials_path)
        
        # Re-initialize client with new credentials
        self._initialize_client()
        
        return self.test_connection() 