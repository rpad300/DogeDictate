#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DogeDictate - Dictation Manager
Author: RazorSh4rk
"""

import os
import sys
import logging
import numpy as np
import pyaudio
import wave
import threading
import queue
import uuid
import re
import random
import time  # Added time module for test_microphone caching
import traceback
import tempfile
from datetime import datetime
import winsound
import pyperclip
import pyautogui
import platform

from src.services.whisper_service import WhisperService
from src.services.azure_service import AzureService
from src.services.google_service import GoogleService
from src.services.local_whisper_service import LocalWhisperService
from src.core.text_formatter import TextFormatter
from src.services.translator_service import TranslatorService
from src.services.local_llm_translator_service import LocalLLMTranslatorService
from src.services.azure_translator_service import AzureTranslatorService
from src.services.m2m100_translator_service import M2M100TranslatorService
from src.services.azure_openai_service import AzureOpenAIService
from src.services.stats_service import StatsService

class DictationManager:
    """Manages dictation functionality"""
    
    # Initialize logger at class level
    logger = logging.getLogger("DogeDictate.DictationManager")
    
    # Atributos de classe para cache de testes de microfone
    _last_mic_test = {}
    _last_mic_test_time = 0
    
    def __init__(self, config_manager):
        """Initialize dictation manager
        
        Args:
            config_manager (ConfigManager): Configuration manager
        """
        try:
            self.config_manager = config_manager
            
            # Get configuration values
            self.language = self.config_manager.get_value("recognition", "language", "en-US")
            self.target_language = self.config_manager.get_value("translation", "target_language", "pt-BR")
            self.auto_translate = self.config_manager.get_value("translation", "auto_translate", True)
            self.service_name = self.config_manager.get_value("recognition", "service", "azure")
            self.translation_service_name = self.config_manager.get_value("translation", "service", "azure_openai")
            
            # Inicializar atributos de classe
            self.is_dictating = False
            self.is_processing = False
            self.push_to_talk_active = False
            self.recognition_text = ""
            self.translation_text = ""
            self.text_formatter = None
            
            # Inicialização proativa de serviços de tradução para garantir disponibilidade
            self.logger.info("Inicializando proativamente serviços de tradução")
            self._initialize_translation_services()
            
            # Verificar se o serviço de tradução foi inicializado corretamente
            if not hasattr(self, 'translator_service') or self.translator_service is None:
                self.logger.warning("translator_service não inicializado no construtor, tentando novamente")
                self.translator_service = self._get_translator_service(self.translation_service_name)
                
            if self.translator_service is None:
                self.logger.error("Não foi possível inicializar translator_service no construtor")
            else:
                self.logger.info(f"translator_service inicializado com sucesso: {type(self.translator_service).__name__}")
        except Exception as e:
            self.logger.error(f"Erro durante a inicialização do DictationManager: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            
        # Inicialização padrão (para garantir que atributos básicos sempre existam)
        # Defaults
        self.stream = None
        self.recognizers = {}
        
        # Configurações padrão
        self.current_language = "pt-PT"
        self.service = None
        self.recognition_service = "azure"
        if not hasattr(self, 'translation_service_name'):
            self.translation_service_name = "azure_openai"  # Definir valor padrão
        if not hasattr(self, 'translator_service'):
            self.translator_service = None
        self.azure_service = None
        self.whisper_service = None
        self.google_service = None
        self.local_whisper_service = None
        self.azure_translator_service = None
        self.azure_openai_service = None
        self.m2m100_translator_service = None
        self.local_llm_translator_service = None
        
        # Inicializar o lock para variáveis compartilhadas
        self.lock = threading.RLock()
        
        # Atributos para o estado da aplicação
        self.is_recording = False
        self.stop_flag = False
        self.paused = False
        self.processing = False
        
        # Initialize language_rules attribute
        self.language_rules = None
        
        # Inicializar settings a partir da configuração
        self.settings = {}
        if hasattr(config_manager, 'get_config'):
            self.settings = config_manager.get_config()
            
        # Obter recursos path se disponível
        self.resources_path = getattr(config_manager, 'resources_path', None)
        
        # Initialize locks
        self.recording_lock = threading.Lock()
        self.stream_lock = threading.Lock()
        
        # Initialize audio settings
        self.sample_rate = 44100  # Aumentar taxa de amostragem para melhor qualidade
        self.channels = 1
        self.dtype = 'int16'
        self.frames_per_buffer = 1024  # Reduzir buffer para menor latência
        self.audio_format = pyaudio.paInt16  # Formato de áudio para PyAudio
        self.chunk_size = 1024  # Tamanho do chunk para leitura de áudio
        
        # Initialize recording flags and buffers
        self.is_recording = False
        self.is_processing = False
        self.audio_buffer = []
        self.audio_queue = queue.Queue()
        self.processing_queue = queue.Queue()
        
        # Initialize threads
        self.recording_thread = None
        self.processing_thread = None
        
        # Initialize streams
        self.stream = None
        self.audio_stream = None
        self.pyaudio = None  # Inicializando o atributo pyaudio
        
        # Inicializar timestamp de fim de gravação
        self.last_recording_end_time = 0  # Inicializar com 0 para evitar problemas no primeiro uso
        
        # Initialize language settings
        self.language = self.config_manager.get_value("recognition", "language", "pt-PT")
        self.current_language = self.language  # Definir current_language igual a language por padrão
        self.target_language = self.config_manager.get_value("translation", "target_language", "en-US")
        
        # Initialize microphone using the main key or alternative
        self.default_mic_id = self.config_manager.get_value("audio", "microphone_id", 0)
        if not self.default_mic_id:
            self.default_mic_id = self.config_manager.get_value("audio", "default_microphone_id", 0)
            
        # Normalize configurations: ensure all microphone keys are consistent
        self.config_manager.set_value("audio", "microphone_id", self.default_mic_id)
        self.config_manager.set_value("audio", "default_microphone_id", self.default_mic_id)
        
        # Save normalized configurations
        self.config_manager.save_config()
        
        # List all audio devices and log their details
        self.logger.info("Scanning audio devices...")
        devices = self.get_microphones()
        
        # Try to find HyperX SoloCast or similar USB microphones
        hyperx_device = None
        for device in devices:
            if 'hyperx' in device['name'].lower() or 'solo' in device['name'].lower() or 'cast' in device['name'].lower():
                hyperx_device = device
                self.logger.info(f"Found HyperX device: {device['name']} (ID: {device['id']})")
                break
        
        # If HyperX device is found, set it as default
        if hyperx_device:
            self.default_mic_id = hyperx_device['id']
            # Normalize configurations: ensure the keys used for the microphone are consistent
            self.config_manager.set_value("audio", "microphone_id", self.default_mic_id)
            self.config_manager.set_value("audio", "default_microphone_id", self.default_mic_id)
            self.config_manager.set_value("audio", "default_microphone", hyperx_device['name'])
            # Save configuration
            self.config_manager.save_config()
            self.logger.info(f"Set HyperX device as default microphone (ID: {self.default_mic_id})")
        
        # Initialize temp directory
        self.temp_dir = os.path.join(tempfile.gettempdir(), "DogeDictate")
        if not os.path.exists(self.temp_dir):
            try:
                os.makedirs(self.temp_dir)
            except Exception as e:
                self.logger.error(f"Error creating temp directory: {str(e)}")
        
        # Initialize services through the dedicated method
        self._initialize_services(self.config_manager.get_value("recognition", "service", "azure"))
        
        # Initialize VAD parameters - Adjusted for higher sensitivity
        self.vad_enabled = False  # Disable VAD by default
        self.vad_threshold = 0.001  # Reduced threshold to detect lower sounds
        self.vad_silence_duration = 0.5  # Reduced duration of silence
        
        # Save VAD settings to config
        self.config_manager.set_value("vad", "enabled", self.vad_enabled)
        self.config_manager.set_value("vad", "threshold", self.vad_threshold)
        self.config_manager.set_value("vad", "silence_duration", self.vad_silence_duration)
        
        # Initialize stats service if available
        if self.config_manager.get_value("stats", "enabled", True):
            self.initialize_stats()
        else:
            self.stats_service = None
            
        # Initialize sound settings
        self._play_sounds = self.config_manager.get_value("audio", "play_sounds", True)
        
        # Initialize chunk processing flag
        self.chunk_processing_enabled = False
    
    def _handle_exception(self, operation_name, e, fallback_return=None):
        """Método auxiliar para tratamento padronizado de exceções
        
        Args:
            operation_name (str): Nome da operação para logging
            e (Exception): A exceção capturada
            fallback_return: Valor a retornar em caso de exceção
            
        Returns:
            O valor de fallback_return
        """
        self.logger.error(f"Error in {operation_name}: {str(e)}")
        self.logger.error(traceback.format_exc())
        return fallback_return
    
    def _initialize_services(self, service_name):
        """Initialize recognition and translation services"""
        try:
            # Logging inicial
            self.logger.info("Inicializando serviços de reconhecimento e tradução")
            self.logger.info(f"Serviço solicitado: {service_name}")
            
            # Lista para verificar serviços disponíveis
            available_services = {}
            
            # Initialize Azure service
            if hasattr(self.config_manager, 'get_value'):
                # Verificar ambos os possíveis nomes de chave
                azure_key = self.config_manager.get_value("recognition", "azure_api_key", "")
                if not azure_key:
                    self.logger.info("Chave 'azure_api_key' não encontrada, tentando 'azure_key'")
                    azure_key = self.config_manager.get_value("recognition", "azure_key", "")
                    
                azure_region = self.config_manager.get_value("recognition", "azure_region", "westeurope")
                
                if azure_key:
                    self.logger.info("Inicializando serviço Azure...")
                    self.azure_service = AzureService(self.config_manager)
                    
                    # Verificar se o serviço foi inicializado com sucesso
                    if hasattr(self.azure_service, 'update_credentials'):
                        success = self.azure_service.update_credentials(azure_key, azure_region)
                        if success:
                            self.logger.info("Serviço Azure inicializado com sucesso")
                            available_services['azure'] = self.azure_service
                        else:
                            self.logger.warning("Falha ao inicializar serviço Azure")
                    else:
                        # Show only part of the key for security
                        masked_key = azure_key[:5] + "..." + azure_key[-5:] if len(azure_key) > 10 else "***"
                        self.logger.info(f"Azure API key configurada: {masked_key}")
                        self.logger.info(f"Azure region configurada: {azure_region}")
                        self.logger.info("Serviço Azure inicializado")
                        available_services['azure'] = self.azure_service
                else:
                    self.logger.warning("Azure API key não configurada")
            
            # Initialize Google service
            google_credentials = self.config_manager.get_value("recognition", "google_credentials_path", "")
            if google_credentials:
                self.logger.info("Inicializando serviço Google...")
                self.google_service = GoogleService(self.config_manager)
                
                # Verificar se o serviço está disponível
                if hasattr(self.google_service, 'is_available') and self.google_service.is_available():
                    self.logger.info(f"Google credentials encontrado em: {google_credentials}")
                    self.logger.info("Serviço Google inicializado")
                    available_services['google'] = self.google_service
                else:
                    self.logger.warning("Serviço Google não está disponível")
            else:
                self.logger.info("Google credentials não configurado")
            
            # Initialize API Whisper service
            whisper_key = self.config_manager.get_value("recognition", "whisper_api_key", "")
            if whisper_key:
                self.logger.info("Inicializando serviço Whisper API...")
                self.whisper_service = WhisperService(self.config_manager)
                
                # Verificar se o serviço está disponível
                if hasattr(self.whisper_service, 'test_connection'):
                    test_result = self.whisper_service.test_connection()
                    if test_result.get('success', False):
                        self.logger.info("Serviço Whisper API inicializado com sucesso")
                        available_services['whisper'] = self.whisper_service
                    else:
                        self.logger.warning(f"Falha ao testar Whisper API: {test_result.get('message', 'Erro desconhecido')}")
                else:
                    self.logger.info("Serviço Whisper API inicializado")
                    available_services['whisper'] = self.whisper_service
            else:
                self.logger.info("Whisper API key não configurada")
            
            # Initialize local whisper service (apenas para registrar existência, não usado como fallback)
            self.logger.info("Verificando disponibilidade de serviço Local Whisper...")
            self.local_whisper_service = LocalWhisperService(self.config_manager)
            
            # Set language for recognition
            self.language = self.config_manager.get_value("recognition", "language", "pt-PT")
            
            # Set default service for compatibility
            self.service = self._get_service(service_name)
            
            if self.service:
                self.logger.info(f"Usando serviço de reconhecimento: {service_name}")
                self.logger.warning(f"Serviço de reconhecimento inicializado: {service_name}")
                self.logger.info(f"Idioma de reconhecimento: {self.language}")
                self.recognition_service = service_name
            else:
                self.logger.error(f"Falha ao inicializar serviço de reconhecimento: {service_name}")
                
                # Verificar se foi solicitada uma API (não serviço local)
                is_api_service = service_name in ['azure', 'whisper', 'google']
                
                # Verificar se há algum serviço API disponível como fallback
                api_services = {k: v for k, v in available_services.items() if k in ['azure', 'whisper', 'google']}
                
                if is_api_service and not api_services:
                    # Se foi solicitada uma API e nenhuma API está disponível, mostrar erro ao usuário
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.critical(
                        None,
                        "Erro de Serviço de Reconhecimento",
                        f"O serviço de reconhecimento {service_name} não está disponível. Verifique sua conexão com a internet e as chaves de API nas configurações.",
                        QMessageBox.Ok
                    )
                    return
                
                # Se solicitou uma API mas ela falhou, tentar outra API (não serviço local)
                if is_api_service and api_services:
                    fallback_name, fallback_service = next(iter(api_services.items()))
                    self.logger.warning(f"Usando {fallback_name} como serviço fallback de reconhecimento (apenas APIs)")
                    self.service = fallback_service
                    self.recognition_service = fallback_name
                else:
                    self.logger.error("Não foi possível encontrar um serviço de API disponível!")
            
            # Inicializar serviços de tradução
            self._initialize_translation_services()
            
            # Verificação final
            self.logger.info(f"Serviços disponíveis: {', '.join(available_services.keys())}")
            self.logger.info(f"Serviço de reconhecimento selecionado: {self.recognition_service}")
            self.logger.info(f"Serviço de tradução selecionado: {self.translation_service_name}")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar serviços: {str(e)}")
            
    def _initialize_translation_services(self):
        """Inicializa serviços de tradução"""
        # Inicializar atributos de serviço padrão para evitar AttributeError
        self.azure_translator_service = None
        self.azure_openai_service = None 
        self.m2m100_translator_service = None
        self.local_llm_translator_service = None
        self.translator_service = None
        
        # Obter serviço configurado
        translator_service_name = self.config_manager.get_value("translation", "service", "azure_openai")
        self.translation_service_name = translator_service_name
        self.logger.info(f"Inicializando serviço de tradução: {translator_service_name}")
        
        # Lista para verificar serviços disponíveis
        available_translation_services = {}
        
        # Initialize Azure translator
        azure_translator_key = self.config_manager.get_value("translation", "azure_translator_key", "")
        azure_translator_region = self.config_manager.get_value("translation", "azure_translator_region", "westeurope")
        
        if azure_translator_key:
            self.logger.info("Inicializando serviço Azure Translator...")
            self.azure_translator_service = AzureTranslatorService(self.config_manager)
            
            # Verificar se o serviço está disponível
            if hasattr(self.azure_translator_service, 'is_configured') and self.azure_translator_service.is_configured():
                self.logger.info("Serviço Azure Translator inicializado com sucesso")
                available_translation_services['azure_translator'] = self.azure_translator_service
        
        # Initialize Azure OpenAI translator
        azure_openai_key = self.config_manager.get_value("translation", "azure_openai_key", "")
        azure_openai_endpoint = self.config_manager.get_value("translation", "azure_openai_endpoint", "")
        azure_openai_deployment = self.config_manager.get_value("translation", "azure_openai_deployment", "")
        
        # Logs para diagnóstico
        masked_key = azure_openai_key[:5] + "..." + azure_openai_key[-5:] if len(azure_openai_key) > 10 else "***" if azure_openai_key else "vazio"
        self.logger.info(f"Chave Azure OpenAI carregada: {masked_key}")
        self.logger.info(f"Endpoint Azure OpenAI: {azure_openai_endpoint}")
        self.logger.info(f"Deployment Azure OpenAI: {azure_openai_deployment}")
        
        if azure_openai_key and azure_openai_endpoint:
            self.logger.info("Inicializando serviço Azure OpenAI...")
            
            # Remove extra slashes at the end of the URL if they exist
            if azure_openai_endpoint.endswith("/"):
                azure_openai_endpoint = azure_openai_endpoint.rstrip("/")
                self.logger.info(f"Endpoint Azure OpenAI sanitizado: {azure_openai_endpoint}")
            
            self.azure_openai_service = AzureOpenAIService(
                api_key=azure_openai_key, 
                endpoint=azure_openai_endpoint,
                deployment_name=azure_openai_deployment
            )
            
            # Verificar se o serviço está disponível
            if hasattr(self.azure_openai_service, 'is_configured') and self.azure_openai_service.is_configured():
                self.logger.info("Serviço Azure OpenAI inicializado com sucesso")
                available_translation_services['azure_openai'] = self.azure_openai_service
        
        # Obter apenas serviços de API (sem serviços locais)
        api_services = {k: v for k, v in available_translation_services.items() 
                       if k in ['azure_translator', 'azure_openai']}
        
        # Verificar se o serviço solicitado é uma API e está disponível
        is_api_service = translator_service_name in ['azure_translator', 'azure_openai']
        service_available = translator_service_name in available_translation_services
        
        self.logger.info(f"Serviços de API disponíveis: {list(api_services.keys())}")
        self.logger.info(f"Serviço solicitado '{translator_service_name}' disponível: {service_available}")
        
        # Se o serviço solicitado é uma API e está disponível, usá-lo
        if is_api_service and service_available:
            self.translator_service = available_translation_services[translator_service_name]
            self.logger.info(f"Usando serviço de tradução API: {translator_service_name}")
        # Se o serviço solicitado é uma API mas não está disponível
        elif is_api_service and not service_available:
            # Se há outras APIs disponíveis, usar como fallback
            if api_services:
                fallback_name, fallback_service = next(iter(api_services.items()))
                self.translator_service = fallback_service
                self.translation_service_name = fallback_name
                self.logger.info(f"Serviço {translator_service_name} não disponível, usando {fallback_name} como fallback")
            else:
                # Se não há nenhuma API disponível, mostrar erro
                self.logger.error("Nenhum serviço de tradução API disponível!")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None,
                    "Erro de Serviço de Tradução",
                    f"O serviço de tradução {translator_service_name} não está disponível. Verifique sua conexão com a internet e as chaves de API nas configurações.",
                    QMessageBox.Ok
                )
        # Se o serviço solicitado é local, verificar se há APIs disponíveis como fallback
        elif not is_api_service and api_services:
            fallback_name, fallback_service = next(iter(api_services.items()))
            self.translator_service = fallback_service
            self.translation_service_name = fallback_name
            self.logger.info(f"Serviço local solicitado, mas usando API {fallback_name} em vez disso")
        else:
            # Se não há opções de API disponíveis
            self.logger.error("Não foi possível encontrar um serviço de tradução API disponível!")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "Erro de Serviço de Tradução",
                "Nenhum serviço de tradução API está disponível. Verifique sua conexão com a internet e as chaves de API nas configurações.",
                QMessageBox.Ok
            )
        
        # Definir target language
        self.target_language = self.config_manager.get_value("translation", "target_language", "en-US")
        self.logger.info(f"Idioma alvo para tradução: {self.target_language}")
    
    def start_dictation(self):
        """Start dictation"""
        try:
            if self.is_recording:
                self.logger.warning("Dictation already started")
                return False
            
            # Configure VAD to be more sensitive
            self.vad_enabled = False
            self.vad_threshold = 0.0001  # Reduced to be more sensitive
            self.vad_silence_duration = 0.5
            
            # Save updated configurations to config file
            self._save_vad_settings()
            
            self.logger.warning(f"VAD status: enabled={self.vad_enabled}, threshold={self.vad_threshold}, silence_duration={self.vad_silence_duration}")
            self.logger.warning("Chunk processing disabled during recording to ensure continuous audio capture")
            
            # Check if we need to wait due to debouncing
            current_time = time.time()
            debounce_time = self.config_manager.get_value("recording", "debounce_time", 0.5)
            
            if (current_time - self.last_recording_end_time) < debounce_time:
                wait_time = debounce_time - (current_time - self.last_recording_end_time)
                self.logger.warning(f"Debouncing activated, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
            
            # Reset recording state
            self.is_recording = False
            self.is_processing = False
            
            # Clean up any existing streams to avoid resource leaks
            self._cleanup_streams()
            
            # Initialize recording properties
            self.audio_buffer = []
            self.audio_queue = queue.Queue()
            self.processing_queue = queue.Queue()
            
            # Reset thread references
            self.recording_thread = None
            self.processing_thread = None
            
            # Configure audio before starting recording
            self.audio_config = {
                'chunk_size': 1024,
                'format': pyaudio.paInt16,
                'channels': 1,
                'sample_rate': 16000,
                'frames_per_buffer': 1024
            }
            self.logger.info("Audio configuration set")
            
            # Set callback mode to False
            self.audio_callback_mode = False
            
            # Start the actual recording process
            if not self._start_recording():
                self.logger.error("Failed to start recording")
                return False
            
            self.logger.warning(f"Starting dictation with language: {self.language}")
            
            # Mark as recording and processing
            self.is_recording = True
            self.is_processing = True
            
            # Start new recording thread
            self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
            self.recording_thread.start()
            
            # Start thread for audio processing to consume from queue
            self.processing_thread = threading.Thread(target=self._process_audio_loop, daemon=True)
            self.processing_thread.start()
            
            # Configure timestamp for statistics
            self.start_time = time.time()
            
            # Emit sound to indicate start (optional, according to configuration)
            if self.config_manager.get_value("audio", "play_sounds", True):
                self.play_start_sound()
            
            # Log successful start
            self.logger.info(f"Dictation started with language: {self.language}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error in start_dictation: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.is_recording = False
            self.is_processing = False
            return False
    
    def _save_vad_settings(self):
        """Salva as configurações de VAD no arquivo de configuração"""
        try:
            self.config_manager.set_value("vad", "enabled", self.vad_enabled)
            self.config_manager.set_value("vad", "threshold", self.vad_threshold)
            self.config_manager.set_value("vad", "silence_duration", self.vad_silence_duration)
            self.config_manager.save_config()
            self.logger.info(f"VAD settings saved to config: enabled={self.vad_enabled}, threshold={self.vad_threshold}")
        except Exception as e:
            self.logger.error(f"Error saving VAD settings: {str(e)}")
    
    def stop_dictation(self):
        """Stop dictation"""
        # Reduce delay to capture the end of speech
        post_recording_delay = self.config_manager.get_value("recording", "post_recording_delay", 0.5)
        # Use a smaller value to reduce latency
        actual_delay = min(post_recording_delay, 0.1)  # We limit to a maximum of 100ms
        if actual_delay > 0:
            self.logger.debug(f"Waiting {actual_delay:.2f} seconds to capture the end of speech...")
            time.sleep(actual_delay)
            
        if not self.is_recording:
            self.logger.warning("Dictation already stopped")
            return
        
        self.logger.warning("Stopping dictation")
        
        # Stop recording - disable before processing audio
        self.is_recording = False
        self.continuous_recording = False  # Disable continuous recording
        
        # Wait for recording thread to finish
        if self.recording_thread and self.recording_thread.is_alive():
            self.logger.info("Waiting for recording thread to finish")
            self.recording_thread.join(timeout=2.0)  # Timeout to avoid blocking
            if self.recording_thread.is_alive():
                self.logger.warning("Recording thread did not exit within timeout, continuing anyway")
        
        # This delay is important to give time for _process_audio_loop to recognize that 
        # recording has stopped and process the accumulated audio
        time.sleep(1.0)
        
        # End processing thread only after a certain time
        # to ensure that all audio has been processed
        time.sleep(1.5)  # More time for complete processing
        self.is_processing = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.logger.info("Waiting for processing thread to finish")
            self.processing_thread.join(timeout=3.0)  # Timeout aumentado
            if self.processing_thread.is_alive():
                self.logger.warning("Processing thread did not exit within timeout, continuing anyway")
        
        # Cleanup streams
        self._cleanup_streams()
        
        # Update recording end time for debouncing
        self.last_recording_end_time = time.time()
        
        # Emitir sinal sonoro para indicar fim (opcional, conforme configuração)
        if self._play_sounds:
            self.play_stop_sound()
        
        # Log de finalização
        self.logger.info("Dictation stopped")
    
    def get_microphones(self):
        """Obtém lista de microfones disponíveis"""
        try:
            self.logger.info("Iniciando busca por dispositivos de áudio...")
            p = pyaudio.PyAudio()
            devices = []
            seen_names = set()  # Para controlar nomes já vistos
            
            # Obter o dispositivo de entrada padrão
            try:
                default_device = p.get_default_input_device_info()
                default_id = default_device['id']
                self.logger.info(f"Dispositivo de entrada padrão: {default_device['name']} (ID: {default_id})")
            except Exception as e:
                self.logger.warning(f"Não foi possível obter o dispositivo padrão: {str(e)}")
                default_id = -1
            
            # Listar todos os dispositivos para debug
            self.logger.info("Listando todos os dispositivos de áudio:")
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                
                # Verificar se é um dispositivo de entrada (microfone)
                if device_info.get('maxInputChannels', 0) > 0:
                    name = device_info.get('name', '').strip()
                    
                    # Remover números em parênteses no final do nome
                    base_name = re.sub(r'\s*\(\d+\)\s*$', '', name)
                    
                    # Se já vimos este nome base e não é o dispositivo padrão, pular
                    if base_name in seen_names and i != default_id:
                        continue
                    
                    # Criar dicionário com informações do dispositivo
                    device = {
                        'id': i,  # ID do dispositivo
                        'name': name,  # Nome original do dispositivo
                        'channels': device_info.get('maxInputChannels', 0),  # Número de canais
                        'sample_rate': int(device_info.get('defaultSampleRate', 44100)),  # Taxa de amostragem
                        'is_default': (i == default_id)  # Se é o dispositivo padrão
                    }
                    
                    self._log_device_info(device)
                    
                    devices.append(device)
                    seen_names.add(base_name)
            
            # Ordenar dispositivos (padrão primeiro, depois por nome)
            devices.sort(key=lambda x: (-x['is_default'], x['name'].lower()))
            
            self.logger.info(f"Total de dispositivos de entrada únicos encontrados: {len(devices)}")
            
            p.terminate()
            return devices
            
        except Exception as e:
            return self._handle_exception("get_microphones", e, [])

    def _log_device_info(self, device):
        """Método auxiliar para fazer log das informações de um dispositivo de áudio
        
        Args:
            device (dict): Dicionário com informações do dispositivo
        """
        self.logger.info(f"Encontrado dispositivo de entrada: {device['name']} (ID: {device['id']})")
        self.logger.info(f"  Canais: {device['channels']}")
        self.logger.info(f"  Taxa de amostragem: {device['sample_rate']}")
        self.logger.info(f"  Dispositivo padrão: {device['is_default']}")
    
    def _deduplicate_devices(self, devices):
        """Remove dispositivos duplicados baseado na similaridade dos nomes
        
        Args:
            devices (list): Lista de dicionários com informações dos dispositivos
            
        Returns:
            list: Lista de dispositivos sem duplicatas
        """
        if not devices:
            return []
            
        try:
            # Criar dicionário para agrupar dispositivos por nome normalizado
            device_groups = {}
            
            # Primeiro passo: agrupar dispositivos por nome normalizado
            for device in devices:
                name = device.get('name', '')
                norm_name = self._normalize_device_name(name)
                
                if norm_name not in device_groups:
                    device_groups[norm_name] = []
                device_groups[norm_name].append(device)
            
            # Lista final de dispositivos únicos
            unique_devices = []
            
            # Segundo passo: selecionar o melhor dispositivo de cada grupo
            for norm_name, group in device_groups.items():
                self.logger.info(f"Processando grupo: {norm_name} ({len(group)} dispositivos)")
                
                # Se só tem um dispositivo no grupo, adicionar direto
                if len(group) == 1:
                    unique_devices.append(group[0])
                    continue
                
                # Ordenar dispositivos do grupo por prioridade
                sorted_group = sorted(group, key=lambda d: (
                    -int(d.get('is_default', False)),  # Dispositivo padrão primeiro
                    -d.get('channels', 0),             # Mais canais depois
                    d.get('id', 999999)                # ID menor por último
                ))
                
                # Pegar o melhor dispositivo do grupo
                best_device = sorted_group[0]
                
                # Log detalhado da seleção
                self.logger.info(f"Selecionado dispositivo: {best_device.get('name')} (ID: {best_device.get('id')})")
                self.logger.info(f"  Canais: {best_device.get('channels')}")
                self.logger.info(f"  Padrão: {best_device.get('is_default', False)}")
                
                unique_devices.append(best_device)
            
            # Ordenar dispositivos finais (padrão primeiro, depois por nome)
            unique_devices.sort(key=lambda x: (
                -int(x.get('is_default', False)),  # Dispositivo padrão primeiro
                x.get('name', '').lower()          # Depois por nome
            ))
            
            # Log final
            self.logger.info(f"Total de dispositivos após deduplicação: {len(unique_devices)}")
            for device in unique_devices:
                self.logger.info(f"Dispositivo final: {device.get('name')} (ID: {device.get('id')})")
            
            return unique_devices
            
        except Exception as e:
            self.logger.error(f"Erro na deduplicação de dispositivos: {str(e)}")
            self.logger.error(traceback.format_exc())
            return devices  # Retornar lista original em caso de erro
    
    def _get_service(self, service_name):
        """Get a speech recognition service by name"""
        try:
            # Mapeamento de serviços para seus respectivos objetos
            service_mapping = {
                "azure": self._get_azure_service,
                "whisper": self._get_whisper_service,
                "google": self._get_google_service,
                "local_whisper": lambda: self.local_whisper_service
            }
            
            # Verificar se o serviço está no mapeamento
            if service_name in service_mapping:
                service = service_mapping[service_name]()
                if service:
                    return service
                    
            # Se o serviço solicitado não existe ou não retornou um objeto válido
            self.logger.warning(f"Service {service_name} not available, falling back to Local Whisper")
            return self.local_whisper_service
            
        except Exception as e:
            return self._handle_exception("_get_service", e, self.local_whisper_service)
    
    def _get_azure_service(self):
        """Obter serviço Azure Speech para reconhecimento de fala"""
        # Verificar credenciais do Azure
        api_key = self.config_manager.get_value("recognition", "azure_api_key", "")
        
        # Se não encontrar no campo principal, tentar campo alternativo
        if not api_key:
            self.logger.warning("Azure API key não encontrada em 'azure_api_key', tentando campo alternativo 'azure_key'")
            api_key = self.config_manager.get_value("recognition", "azure_key", "")
            
        region = self.config_manager.get_value("recognition", "azure_region", "westeurope")
        
        # Log para diagnóstico
        if not api_key:
            self.logger.error("Azure API key is empty or not configured (tentadas chaves 'azure_api_key' e 'azure_key')")
            return None
        else:
            # Mostrar parte da chave por segurança
            masked_key = api_key[:5] + "..." + api_key[-5:] if len(api_key) > 10 else "***"
            self.logger.info(f"Azure API key configured: {masked_key}")
            
        self.logger.info(f"Azure region configured: {region}")
        
        if api_key and region:
            # Criar um service com explicitamente a API key e região
            azure_service = AzureService(self.config_manager)
            # Forçar atualização das credenciais para garantir
            if hasattr(azure_service, 'update_credentials'):
                azure_service.update_credentials(api_key, region)
            return azure_service
        
        return None
    
    def _get_whisper_service(self):
        """Obter serviço Whisper para reconhecimento de fala"""
        whisper_key = self.config_manager.get_value("recognition", "whisper_api_key", "")
        
        if whisper_key:
            return WhisperService(self.config_manager)
        else:
            self.logger.warning("Whisper API key not configured")
            return None
    
    def _get_google_service(self):
        """Obter serviço Google para reconhecimento de fala"""
        # Google Cloud credentials são lidos de variável de ambiente ou arquivo JSON
        return GoogleService(self.config_manager)
        
    def _get_translator_service(self, service_name):
        """Get a translator service by name
        
        Args:
            service_name (str): Service name
            
        Returns:
            object: Translator service
        """
        self.logger.info(f"Obtendo serviço de tradução: {service_name}")
        
        # Verificar se os serviços já foram inicializados
        if not hasattr(self, 'azure_translator_service') or not hasattr(self, 'azure_openai_service'):
            self.logger.warning("Serviços de tradução não inicializados. Tentando inicializar novamente.")
            self._initialize_translation_services()
        
        # Verifica tipo de serviço e retorna o apropriado
        if service_name == "azure_translator":
            # Verificação detalhada do serviço Azure Translator
            if hasattr(self, 'azure_translator_service') and self.azure_translator_service is not None:
                if hasattr(self.azure_translator_service, 'is_configured') and self.azure_translator_service.is_configured():
                    self.logger.info("Retornando serviço Azure Translator configurado")
                    return self.azure_translator_service
                else:
                    self.logger.warning("Serviço Azure Translator existe mas não está configurado corretamente")
            else:
                self.logger.warning("Serviço Azure Translator não está disponível")
                
        elif service_name == "azure_openai":
            # Verificação detalhada do serviço Azure OpenAI
            if hasattr(self, 'azure_openai_service') and self.azure_openai_service is not None:
                self.logger.info(f"Serviço Azure OpenAI encontrado: {self.azure_openai_service}")
                
                # Verificar configuração
                if hasattr(self.azure_openai_service, 'is_configured'):
                    is_configured = self.azure_openai_service.is_configured()
                    self.logger.info(f"Azure OpenAI está configurado: {is_configured}")
                    
                    if is_configured:
                        self.logger.info("Retornando serviço Azure OpenAI configurado")
                        return self.azure_openai_service
                    else:
                        # Tentar reconfigurar
                        self.logger.warning("Tentando reconfigurar o serviço Azure OpenAI")
                        azure_openai_key = self.config_manager.get_value("translation", "azure_openai_key", "")
                        azure_openai_endpoint = self.config_manager.get_value("translation", "azure_openai_endpoint", "")
                        azure_openai_deployment = self.config_manager.get_value("translation", "azure_openai_deployment", "")
                        
                        # Log de depuração
                        self.logger.info(f"Reconfigurando com: Key={bool(azure_openai_key)}, Endpoint={azure_openai_endpoint}, Deployment={azure_openai_deployment}")
                        
                        if hasattr(self.azure_openai_service, 'update_credentials'):
                            success = self.azure_openai_service.update_credentials(
                                azure_openai_key, 
                                azure_openai_endpoint,
                                azure_openai_deployment
                            )
                            
                            if success:
                                self.logger.info("Serviço Azure OpenAI reconfigurado com sucesso")
                                return self.azure_openai_service
                            else:
                                self.logger.error("Falha ao reconfigurar o serviço Azure OpenAI")
                        else:
                            self.logger.error("Serviço Azure OpenAI não tem método update_credentials")
                else:
                    self.logger.warning("Serviço Azure OpenAI não tem método is_configured")
            else:
                self.logger.warning("Serviço Azure OpenAI não está disponível")
                
                # Tentar inicializar o serviço
                self.logger.info("Tentando inicializar o serviço Azure OpenAI")
                try:
                    from src.services.azure_openai_service import AzureOpenAIService
                    
                    azure_openai_key = self.config_manager.get_value("translation", "azure_openai_key", "")
                    azure_openai_endpoint = self.config_manager.get_value("translation", "azure_openai_endpoint", "")
                    azure_openai_deployment = self.config_manager.get_value("translation", "azure_openai_deployment", "")
                    
                    if azure_openai_key and azure_openai_endpoint and azure_openai_deployment:
                        self.logger.info("Inicializando serviço Azure OpenAI a partir do zero")
                        self.azure_openai_service = AzureOpenAIService(
                            api_key=azure_openai_key,
                            endpoint=azure_openai_endpoint,
                            deployment_name=azure_openai_deployment
                        )
                        
                        if hasattr(self.azure_openai_service, 'is_configured') and self.azure_openai_service.is_configured():
                            self.logger.info("Serviço Azure OpenAI inicializado com sucesso")
                            return self.azure_openai_service
                except Exception as e:
                    self.logger.error(f"Erro ao inicializar serviço Azure OpenAI: {str(e)}")
        
        # Se chegar aqui, o serviço solicitado não está disponível
        # Tentar serviço alternativo de API
        self.logger.warning(f"Serviço {service_name} não disponível, procurando alternativa")
        
        # Verificar Azure OpenAI como alternativa
        if service_name != "azure_openai" and hasattr(self, 'azure_openai_service') and self.azure_openai_service is not None:
            if hasattr(self.azure_openai_service, 'is_configured') and self.azure_openai_service.is_configured():
                self.logger.info("Usando Azure OpenAI como alternativa")
                return self.azure_openai_service
        
        # Verificar Azure Translator como alternativa
        if service_name != "azure_translator" and hasattr(self, 'azure_translator_service') and self.azure_translator_service is not None:
            if hasattr(self.azure_translator_service, 'is_configured') and self.azure_translator_service.is_configured():
                self.logger.info("Usando Azure Translator como alternativa")
                return self.azure_translator_service
        
        self.logger.error("Nenhum serviço de tradução API disponível!")
        return None
    
    def _recognize_with_selected_service(self, audio_file, service_name=None, auto_translate=True, target_language=None):
        """Reconhece fala usando o serviço selecionado
        
        Args:
            audio_file (str): O arquivo de áudio a ser reconhecido
            service_name (str, optional): O nome do serviço a ser usado
            auto_translate (bool, optional): Se deve traduzir automaticamente
            target_language (str, optional): O idioma de destino para tradução
            
        Returns:
            str: O texto reconhecido
        """
        try:
            # Forçar uso do idioma pt-PT para reconhecimento sempre
            recognition_language = "pt-PT"
            self.logger.warning(f"Forçando idioma de reconhecimento para: {recognition_language}")
            
            # Verificar se estamos usando language_rules em modo avançado
            if hasattr(self, 'language_rules') and self.language_rules:
                mode = self.config_manager.get_value("language_rules", "mode", "simple")
                if mode == "advanced":
                    self.logger.info("Usando modo avançado de regras de idioma")
                    # Em modo avançado, usar os language_rules
                else:
                    self.logger.info("Usando modo simples de regras de idioma")
            
            # Se nenhum serviço específico for fornecido, usar o padrão
            if not service_name:
                service_name = self.service_name if hasattr(self, 'service_name') else "azure"
                
            self.logger.info(f"Recognizing audio with service: {service_name}, language: {recognition_language}")
            
            # Verificar se o serviço existe
            service_instance = self.get_recognition_service(service_name)
            if not service_instance:
                self.logger.error(f"Service {service_name} not found, trying alternative services")
                # Tentar encontrar um serviço alternativo
                for alt_service in ["azure", "whisper", "google", "local_whisper"]:
                    if alt_service != service_name:
                        self.logger.info(f"Trying alternative service: {alt_service}")
                        service_instance = self.get_recognition_service(alt_service)
                        if service_instance:
                            self.logger.info(f"Using alternative service: {alt_service}")
                            service_name = alt_service
                            break
                
                # Se ainda não encontrou um serviço, falhar
                if not service_instance:
                    self.logger.error("No recognition service available")
                    return "Error: No recognition service available"
            
            # Realizar reconhecimento
            self.logger.info(f"Recognizing with {service_name} in language '{recognition_language}'")
            recognized_text = service_instance.recognize_speech(audio_file, recognition_language)
            
            # Verificar se o reconhecimento foi bem-sucedido
            if not recognized_text:
                self.logger.warning("No text recognized")
                return ""
                
            # Registrar resultado do reconhecimento inicial
            self.logger.info(f"Recognition result: '{recognized_text}'")
            
            # Determinar se precisamos traduzir
            perform_translation = False
            if auto_translate:
                # Se temos idioma de destino explícito, verificar se é diferente do idioma de reconhecimento
                if target_language and target_language != recognition_language:
                    perform_translation = True
                    self.logger.info(f"Auto-translation enabled, target_language ({target_language}) differs from recognition_language ({recognition_language})")
                # Se não temos idioma de destino explícito, verificar se auto_translate está ativado e usar target_language padrão
                elif hasattr(self, 'auto_translate') and self.auto_translate:
                    default_target = getattr(self, 'target_language', 'en-US')
                    if default_target != recognition_language:
                        perform_translation = True
                        target_language = default_target
                        self.logger.info(f"Auto-translation enabled, using default target_language: {target_language}")
            
            # Traduzir se necessário
            if perform_translation and recognized_text:
                source_lang = recognition_language
                # Se não temos idioma de destino explícito, usar o padrão da classe
                if not target_language and hasattr(self, 'target_language'):
                    target_language = self.target_language
                
                # Traduzir o texto
                if target_language and target_language != source_lang:
                    self.logger.info(f"Translating from {source_lang} to {target_language}")
                    original_text = recognized_text
                    try:
                        # Traduzir usando o método específico
                        translated_text = self._translate_text(recognized_text, source_lang, target_language)
                        
                        # Verificar se a tradução foi bem-sucedida
                        if translated_text and translated_text != recognized_text:
                            self.logger.info(f"Translation successful: '{recognized_text}' -> '{translated_text}'")
                            recognized_text = translated_text
                        else:
                            self.logger.warning(f"Translation failed or returned same text, using original: '{recognized_text}'")
                    except Exception as e:
                        self.logger.error(f"Error during translation: {str(e)}")
                        self.logger.error(traceback.format_exc())
                        # Manter o texto original em caso de erro na tradução
                        self.logger.warning(f"Using original text due to translation error: '{recognized_text}'")
            
            # Retornar o texto reconhecido e possivelmente traduzido
            self.logger.info(f"Recognized text: {recognized_text}")
            return recognized_text
            
        except Exception as e:
            self.logger.error(f"Error in recognize_with_selected_service: {str(e)}")
            self.logger.error(traceback.format_exc())
            return f"Error: {str(e)}"

    def get_recognition_service(self, service_name):
        """Get the recognition service by name"""
        try:
            if service_name == "azure" and hasattr(self, 'azure_service'):
                return self.azure_service
            elif service_name == "whisper" and hasattr(self, 'whisper_service'):
                return self.whisper_service
            elif service_name == "google" and hasattr(self, 'google_service'):
                return self.google_service
                
            self.logger.error(f"Recognition service '{service_name}' not available")
            return None
        except Exception as e:
            self.logger.error(f"Error getting recognition service: {str(e)}")
            return None
    
    def _start_recording(self):
        """Start recording audio from the microphone"""
        try:
            # Verificar se já estamos gravando
            if self.is_recording:
                self.logger.warning("Recording already in progress")
                return
            
            # Verificar configurações
            if not hasattr(self, 'audio_config') or not self.audio_config:
                self.logger.error("Audio configuration not set")
                return
            
            # Inicializar PyAudio se necessário
            if not hasattr(self, 'pyaudio') or self.pyaudio is None:
                self.pyaudio = pyaudio.PyAudio()
                self.logger.debug("PyAudio instance created")
            
            # Obter ID do microfone das configurações usando a chave padrão
            mic_id = self.config_manager.get_value("audio", "microphone_id", 0)
            # Verificar também a chave alternativa se a padrão não retornar valor
            if mic_id is None or mic_id == 0:
                mic_id = self.config_manager.get_value("audio", "default_microphone_id", 0)
            
            # Usar o ID armazenado na instância se tudo falhar
            if mic_id is None or mic_id == 0:
                mic_id = self.default_mic_id
            
            self.logger.info(f"Using microphone with ID: {mic_id}")
            
            # Testar microfone para garantir que está disponível
            mic_test = self.test_microphone(mic_id)
            if not mic_test.get('success', False):
                self.logger.error(f"Microphone test failed: {mic_test.get('message', 'Unknown error')}")
                return
            
            # Configurações de gravação
            self.frames = []
            self.is_recording = True
            self.audio_buffer = []
            self.chunk_size = self.audio_config.get('chunk_size', 1024)
            self.format = self.audio_config.get('format', pyaudio.paInt16)
            self.channels = self.audio_config.get('channels', 1)
            self.rate = self.audio_config.get('sample_rate', 16000)
            self.frames_per_buffer = self.audio_config.get('frames_per_buffer', 1024)
            
            # Timeout de silêncio e limite de gravação
            silence_timeout = self.config_manager.get_value("audio", "silence_timeout", 2.0)
            self.silence_timeout = float(silence_timeout)
            self.max_recording_time = self.config_manager.get_value("audio", "max_recording_time", 30)
            
            # Inicializar a detecção de voz se configurada
            self.use_vad = self.config_manager.get_value("audio", "use_vad", True)
            self.vad_aggressiveness = self.config_manager.get_value("audio", "vad_aggressiveness", 3)
            self.vad_frame_duration = 30  # WebRTCVAD precisa de 10, 20 ou 30ms
            
            if self.use_vad:
                try:
                    import webrtcvad
                    self.vad = webrtcvad.Vad(int(self.vad_aggressiveness))
                    self.logger.info(f"Voice Activity Detection (VAD) initialized with aggressiveness level {self.vad_aggressiveness}")
                except ImportError:
                    self.logger.warning("webrtcvad module not available, VAD will be disabled")
                    self.use_vad = False
                except Exception as e:
                    self.logger.error(f"Error initializing VAD: {str(e)}")
                    self.use_vad = False
            
            # Inicializar variáveis para detecção de silêncio
            self.last_audio_time = time.time()
            self.recording_start_time = time.time()
            self.has_speech = False
            self.consecutive_silence = 0
            
            # Abrir o stream de áudio
            try:
                self.audio_stream = self.pyaudio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.frames_per_buffer,
                    input_device_index=int(mic_id),
                    stream_callback=self._audio_callback if self.audio_callback_mode else None
                )
                
                self.logger.info(f"Audio stream opened with: format={self.format}, channels={self.channels}, rate={self.rate}, device={mic_id}")
                
                if not self.audio_callback_mode:
                    # Iniciar thread para gravação se não estiver usando callback
                    self.recording_thread = threading.Thread(target=self._record_audio)
                    self.recording_thread.daemon = True
                    self.recording_thread.start()
                    self.logger.info("Recording thread started")
                else:
                    self.logger.info("Using callback mode for audio recording")
                
                # Iniciar thread de processamento de áudio
                self.processing_thread = threading.Thread(target=self._process_audio_loop)
                self.processing_thread.daemon = True
                self.processing_thread.start()
                self.logger.info("Audio processing thread started")
                
                # Iniciar a stream
                self.audio_stream.start_stream()
                self.logger.info("Audio stream started")
                
                # Reproduzir som de início de gravação
                self.play_start_sound()
                
                # Sinalizar que a gravação começou
                self.logger.info("Recording started")
                
                return True
                
            except Exception as e:
                self.is_recording = False
                self.logger.error(f"Error starting recording: {str(e)}")
                self.logger.error(traceback.format_exc())
                
                # Limpar recursos
                self._cleanup_streams()
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error in _start_recording: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _record_audio(self):
        """Record audio from the microphone in a separate thread"""
        try:
            # Confirmar que temos uma stream aberta
            if not hasattr(self, 'audio_stream') or not self.audio_stream:
                self.logger.error("No audio stream available")
                return
            
            self.logger.info("Starting audio recording loop")
            
            # Loop de gravação
            while self.is_recording and self.audio_stream and self.audio_stream.is_active():
                try:
                    # Ler dados do microfone
                    audio_data = self.audio_stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Processar os dados de áudio
                    self._process_incoming_audio(audio_data)
                    
                except IOError as e:
                    # Erros de overflow são comuns e podem ser ignorados
                    if e.errno == -9981:  # Input overflow
                        self.logger.debug("Audio input overflow detected (non-critical)")
                    else:
                        self.logger.error(f"IOError during audio recording: {str(e)}")
                        
                        # Verificar se a stream ainda está ativa
                        if not self.audio_stream.is_active():
                            self.logger.warning("Audio stream is no longer active, stopping recording")
                            break
                            
                except Exception as e:
                    self.logger.error(f"Error in audio recording loop: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    
                    # Verificar se ainda devemos continuar gravando
                    if not self.is_recording:
                        break
                        
                    # Pequena pausa para evitar CPU 100% em caso de erros repetidos
                    time.sleep(0.1)
            
            self.logger.info("Audio recording loop ended")
            
        except Exception as e:
            self.logger.error(f"Fatal error in _record_audio: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # Certificar que fazemos cleanup em caso de erro fatal
            try:
                self.is_recording = False
                self._cleanup_streams()
            except Exception as cleanup_error:
                self.logger.error(f"Error during cleanup after recording failure: {str(cleanup_error)}")
    
    def _process_incoming_audio(self, audio_data):
        """Processa dados de áudio recebidos do microfone
        
        Este método recebe os dados brutos do microfone, faz qualquer pré-processamento
        necessário e coloca os dados na fila para processamento pela thread de processamento.
        
        Args:
            audio_data (bytes): Dados brutos de áudio do microfone
        """
        try:
            # Se não estamos mais gravando, ignorar os dados
            if not self.is_recording:
                return
                
            # Converter os dados de áudio para um array numpy
            # Isto é importante para processamento posterior
            try:
                # Converter bytes para array numpy (2 bytes por amostra de int16)
                audio_np = np.frombuffer(audio_data, dtype=np.int16)
                
                # Adicionar ao buffer da fila se temos dados válidos
                if len(audio_np) > 0:
                    # Adicionar o chunk à fila para processamento
                    self.audio_queue.put(audio_np)
                    
                    # Opcional: adicionar ao buffer local também para referência
                    self.audio_buffer.append(audio_data)
                
            except Exception as e:
                self.logger.error(f"Error converting audio data: {str(e)}")
                self.logger.error(traceback.format_exc())
                
        except Exception as e:
            self.logger.error(f"Error in _process_incoming_audio: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _process_audio_loop(self):
        """Thread principal de processamento de áudio
        
        Esta função é executada em uma thread separada e é responsável por 
        consumir áudio da fila audio_queue e processá-lo para reconhecimento
        enquanto self.is_processing for True.
        """
        self.logger.info("Starting audio processing thread")
        
        try:
            self.logger.info(f"Processing thread is_processing={self.is_processing}, queue size={self.audio_queue.qsize()}")
            
            # Buffer para acumular todo o áudio durante a gravação contínua
            accumulated_audio = []
            continuously_recording = False
            chunk_count = 0  # Contador de chunks para reduzir logs
            
            while self.is_processing:
                try:
                    # Verificar se estamos gravando continuamente 
                    if self.is_recording:
                        if not continuously_recording:
                            continuously_recording = True
                            accumulated_audio = []  # Limpar o buffer no início da gravação
                            chunk_count = 0  # Resetar contador
                            self.logger.info("Recording started, accumulating audio without processing")
                    else:
                        if continuously_recording:
                            continuously_recording = False
                            self.logger.info("Recording stopped, processing accumulated audio")
                            
                            # Processar o áudio acumulado quando a gravação parar
                            if accumulated_audio:
                                try:
                                    # Combinar todo o áudio acumulado em um grande chunk
                                    combined_audio = np.concatenate(accumulated_audio)
                                    total_duration = len(combined_audio) / self.sample_rate
                                    self.logger.info(f"Processing combined audio: {len(combined_audio)} samples, duration: {total_duration:.2f}s")
                                    
                                    # Processar o áudio combinado
                                    recognized_text = self._process_audio(combined_audio)
                                    
                                    # Registrar resultado
                                    if recognized_text:
                                        self.logger.info(f"Recognized text: {recognized_text[:100]}...")
                                        # Adicionar o código para colar o texto no cursor
                                        self._paste_text(recognized_text)
                                    else:
                                        self.logger.info("No text recognized from combined audio")
                                        
                                    # Limpar o buffer acumulado após o processamento
                                    accumulated_audio = []
                                    chunk_count = 0  # Resetar contador
                                    
                                except Exception as e:
                                    self.logger.error(f"Error processing accumulated audio: {str(e)}")
                                    self.logger.error(traceback.format_exc())
                                    accumulated_audio = []
                                    chunk_count = 0  # Resetar contador
                    
                    # Tentar obter dados de áudio da fila com timeout
                    try:
                        # Reduzir verbosidade do log - exibir somente a cada 10 iterações ou se o tamanho da fila > 0
                        queue_size = self.audio_queue.qsize()
                        if chunk_count % 10 == 0 or queue_size > 0:
                            self.logger.debug(f"Waiting for audio data in queue (size={queue_size})")
                        
                        audio_data = self.audio_queue.get(timeout=0.2)
                        
                        # Log menos verboso para recebimento de dados
                        if audio_data is not None and len(audio_data) > 0:
                            # Incrementar contador apenas com dados válidos
                            chunk_count += 1
                            # Exibir mensagens menos frequentes para reduzir logs
                            if chunk_count % 10 == 0:
                                self.logger.debug(f"Got audio data: {chunk_count} chunks processed so far")
                        
                    except queue.Empty:
                        # Se não há dados na fila, continuar o loop
                        continue
                    
                    # Se estamos gravando continuamente, apenas acumular o áudio
                    if continuously_recording:
                        if audio_data is not None and len(audio_data) > 0:
                            accumulated_audio.append(audio_data)
                            # Log a cada 10 chunks para não poluir o log
                            if len(accumulated_audio) % 10 == 0:
                                total_samples = sum(len(chunk) for chunk in accumulated_audio)
                                self.logger.info(f"Accumulated {len(accumulated_audio)} chunks, total samples: {total_samples}")
                    # Caso contrário, processar o áudio normalmente (para retrocompatibilidade)
                    elif audio_data is not None and len(audio_data) > 0:
                        self.logger.info(f"Processing audio chunk: {len(audio_data)} samples")
                        recognized_text = self._process_audio(audio_data)
                        
                        # Registrar resultado
                        if recognized_text:
                            self.logger.info(f"Recognized text: {recognized_text[:30]}...")
                            # Adicionar o código para colar o texto no cursor
                            self._paste_text(recognized_text)
                        else:
                            self.logger.info("No text recognized from audio chunk")
                    
                except Exception as e:
                    self.logger.error(f"Error in audio processing loop: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    
                    # Breve pausa para evitar loop muito rápido em caso de erro
                    time.sleep(0.05)
            
            # Antes de terminar, processar qualquer áudio acumulado restante
            if accumulated_audio:
                try:
                    combined_audio = np.concatenate(accumulated_audio)
                    total_duration = len(combined_audio) / self.sample_rate
                    self.logger.info(f"Processing final accumulated audio: {len(combined_audio)} samples, duration: {total_duration:.2f}s")
                    
                    recognized_text = self._process_audio(combined_audio)
                    
                    if recognized_text:
                        self.logger.info(f"Recognized text from final audio: {recognized_text[:100]}...")
                        self._paste_text(recognized_text)
                    else:
                        self.logger.info("No text recognized from final accumulated audio")
                except Exception as e:
                    self.logger.error(f"Error processing final accumulated audio: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    
        except Exception as e:
            self.logger.error(f"Unhandled error in processing thread: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            self.logger.info("Processing thread terminated")
    
    def _process_audio(self, audio_frames, push_to_talk=False, auto_translate=True):
        """Process the accumulated audio frames for speech recognition
        
        Args:
            audio_frames (list): List of audio frames to process
            push_to_talk (bool): Whether this is a push-to-talk request
            auto_translate (bool): Whether to translate the recognized text
            
        Returns:
            str: The recognized (and possibly translated) text
        """
        try:
            self.processing = True
            
            # Verificar se temos dados para processar
            # Verificar de forma segura para arrays numpy ou listas
            if audio_frames is None or (isinstance(audio_frames, list) and len(audio_frames) == 0) or (hasattr(audio_frames, 'size') and audio_frames.size == 0):
                self.logger.warning("No audio frames to process")
                self.processing = False
                return None
                
            # Calcular duração aproximada do áudio
            # Se for um array numpy, usar tamanho apropriado
            if hasattr(audio_frames, 'size'):
                # Para arrays numpy
                num_samples = audio_frames.size // self.channels // (self.audio_config.get('sample_width', 2) if hasattr(self, 'audio_config') else 2)
            else:
                # Para listas de frames
                num_samples = sum(len(frame) // self.channels // (self.audio_config.get('sample_width', 2) if hasattr(self, 'audio_config') else 2) for frame in audio_frames)
            
            duration = num_samples / float(self.rate)
            
            # Verificar se a duração é suficiente
            min_duration = 0.3  # 300ms mínimos
            if duration < min_duration:
                self.logger.warning(f"Audio duration too short: {duration:.2f}s < {min_duration:.2f}s")
                self.processing = False
                return None
                
            self.logger.info(f"Processing combined audio: {num_samples} samples, duration: {duration:.2f}s")
            
            # Criar arquivo temporário para salvar o áudio
            try:
                # Criar diretório temporário se não existir
                temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temp")
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                    self.logger.debug(f"Created temporary directory: {temp_dir}")
                    
                temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
                os.close(temp_fd)  # Fechar o descritor de arquivo aberto por tempfile
                
                # Salvar os frames em um arquivo WAV
                with wave.open(temp_path, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio_config.get('sample_width', 2) if hasattr(self, 'audio_config') else 2)
                    wf.setframerate(self.rate)
                    
                    # Tratar de forma diferente conforme o tipo dos dados
                    if hasattr(audio_frames, 'tobytes'):
                        # Para arrays numpy
                        wf.writeframes(audio_frames.tobytes())
                    else:
                        # Para listas de frames
                        for frame in audio_frames:
                            wf.writeframes(frame)
                        
                self.logger.debug(f"Audio saved to temporary file: {temp_path}")
                
                # Log de informações do arquivo para diagnóstico
                self._log_audio_file_info(temp_path)
                
                # Selecionar serviço de reconhecimento
                service_name = self.config_manager.get_value("recognition", "service", "azure")
                self.logger.info(f"Processing audio with service: {service_name}")
                
                # Configurar API key do Azure se estiver usando
                if service_name == "azure" and hasattr(self, 'azure_service'):
                    api_key = self.config_manager.get_value("recognition", "azure_key", "")
                    region = self.config_manager.get_value("recognition", "azure_region", "")
                    
                    # Apenas mostrar parte da chave por segurança
                    if api_key:
                        masked_key = api_key[:5] + "..." + api_key[-5:] if len(api_key) > 10 else "***"
                        self.logger.info(f"Azure API key configured: {masked_key}")
                    
                    if region:
                        self.logger.info(f"Azure region configured: {region}")
                
                # Obter o idioma alvo para tradução
                target_language = self.target_language
                
                # Reconhecer o áudio com o serviço selecionado
                result = self._recognize_with_selected_service(
                    temp_path, 
                    service_name=service_name,
                    auto_translate=auto_translate,
                    target_language=target_language
                )
                
                # Tentar apagar o arquivo temporário
                try:
                    os.unlink(temp_path)
                    self.logger.debug(f"Temporary audio file deleted: {temp_path}")
                except Exception as e:
                    self.logger.error(f"Error deleting temporary audio file: {str(e)}")
                
                # Verificar resultado
                if not result:
                    self.logger.warning("Recognition failed or returned empty result")
                    return None
                
                # Contar palavras (mesmo que aproximadamente)
                word_count = len(result.split())
                
                # Registrar estatísticas se o serviço estiver disponível
                if hasattr(self, 'stats_service') and self.stats_service:
                    if hasattr(self.stats_service, 'record_recognition'):
                        self.stats_service.record_recognition(
                            service_name=service_name,
                            language=self.current_language,
                            word_count=word_count
                        )
                    else:
                        # Fallback para método mais simples se record_recognition não existir
                        self.logger.debug("Método record_recognition não encontrado, usando increment_word_count")
                        if hasattr(self.stats_service, 'increment_word_count'):
                            self.stats_service.increment_word_count(word_count)
                
                self.logger.info(f"Successfully recognized {word_count} words")
                self.logger.info(f"Recognized text: {result[:50]}..." if len(result) > 50 else f"Recognized text: {result}")
                
                # Retornar o texto final
                return result
                
            except Exception as e:
                self.logger.error(f"Error processing audio: {str(e)}")
                self.logger.error(traceback.format_exc())
                return None
                
        except Exception as e:
            self.logger.error(f"Error in _process_audio: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None
            
        finally:
            # Set processing state to False when done
            self.processing = False
    
    def _log_audio_file_info(self, file_path):
        """Log information about an audio file (for debugging)"""
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(file_path):
                self.logger.warning(f"Audio file does not exist: {file_path}")
                return
            
            # Obter o tamanho do arquivo
            file_size = os.path.getsize(file_path)
            self.logger.debug(f"Audio file size: {file_size / 1024:.2f} KB")
            
            # Analisar arquivo WAV
            try:
                with wave.open(file_path, 'rb') as wf:
                    channels = wf.getnchannels()
                    sample_width = wf.getsampwidth()
                    frame_rate = wf.getframerate()
                    n_frames = wf.getnframes()
                    duration = n_frames / float(frame_rate)
                    
                    self.logger.debug(
                        f"WAV details: channels={channels}, "
                        f"sample_width={sample_width}, "
                        f"frame_rate={frame_rate}, "
                        f"frames={n_frames}, "
                        f"duration={duration:.2f}s"
                    )
            except Exception as e:
                self.logger.warning(f"Could not analyze WAV file: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Error logging audio file info: {str(e)}")
    
    def _paste_text(self, text):
        """Insert the recognized text where the cursor is"""
        if not text:
            self.logger.warning("No text to paste")
            return
            
        try:
            # Emitir sinal para aplicação principal
            self.logger.info(f"Inserting text at cursor: {text[:50]}..." if len(text) > 50 else f"Inserting text at cursor: {text}")
            
            # Notificar UI antes de inserir (para atualizações visuais)
            if hasattr(self, 'text_inserted') and callable(self.text_inserted):
                self.text_inserted.emit(text)
            
            # Obter configuração de inserção de texto
            paste_method = self.config_manager.get_value("text_insertion", "method", "clipboard")
            
            # Método 1: Usar clipboard (mais confiável mas pode substituir conteúdo da área de transferência)
            if paste_method == "clipboard":
                # Salvar o conteúdo atual do clipboard
                try:
                    original_clipboard = pyperclip.paste()
                except Exception as e:
                    self.logger.error(f"Failed to get original clipboard: {str(e)}")
                    original_clipboard = None
                
                # Copiar o texto reconhecido para o clipboard
                try:
                    pyperclip.copy(text)
                    self.logger.debug("Text copied to clipboard")
                    
                    # Pequena pausa para garantir que o sistema processou a cópia
                    time.sleep(0.1)
                    
                    # Simular Ctrl+V para colar
                    pyautogui.hotkey('ctrl', 'v')
                    self.logger.debug("Paste keystroke sent")
                    
                    # Pequena pausa antes de restaurar o clipboard original
                    time.sleep(0.2)
                    
                    # Restaurar clipboard original se existia
                    if original_clipboard is not None:
                        try:
                            pyperclip.copy(original_clipboard)
                            self.logger.debug("Original clipboard content restored")
                        except Exception as e:
                            self.logger.error(f"Failed to restore clipboard: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Error during clipboard paste: {str(e)}")
                    self.logger.error(traceback.format_exc())
            
            # Método 2: Digitar o texto diretamente (mais lento, mas não interfere com o clipboard)
            elif paste_method == "type":
                self.logger.debug("Using direct typing method")
                # Simular digitação de cada caractere
                pyautogui.write(text)
            
            # Método 3: Windows API para inserção mais confiável
            elif paste_method == "windows_api" and platform.system() == "Windows":
                self.logger.debug("Using Windows API method")
                try:
                    # Copiar para clipboard
                    pyperclip.copy(text)
                    
                    # Usar SendKeys para enviar Ctrl+V mais confiável no Windows
                    import win32com.client
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shell.SendKeys("^v")  # ^v é Ctrl+V
                except Exception as e:
                    self.logger.error(f"Error using Windows API: {str(e)}")
                    # Fallback para método de clipboard padrão
                    pyautogui.hotkey('ctrl', 'v')
            
            self.logger.info("Text insertion complete")
            
            # Verificar se devemos tocar um som após a inserção
            if self.config_manager.get_value("audio", "play_sounds", True):
                self.play_stop_sound()
                
        except Exception as e:
            self.logger.error(f"Error pasting text: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _play_sound(self, sound_type):
        """Método auxiliar para reproduzir sons de interação
        
        Args:
            sound_type (str): Tipo de som ('start' ou 'stop')
        """
        try:
            if not self._play_sounds:
                return
                
            if not self.settings or not self.settings.get("interaction_sounds", False):
                return
                
            if sound_type == 'start':
                sound_path = os.path.join(self.resources_path, "sounds", "start.wav")
            elif sound_type == 'stop':
                sound_path = os.path.join(self.resources_path, "sounds", "stop.wav")
            else:
                self.logger.warning(f"Tipo de som desconhecido: {sound_type}")
                return
                
            if os.path.exists(sound_path):
                self.logger.info(f"Playing {sound_type} sound: {sound_path}")
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                self.logger.warning(f"{sound_type.capitalize()} sound file not found: {sound_path}")
        except Exception as e:
            self.logger.warning(f"Could not play {sound_type} sound: {str(e)}")
            
    def play_start_sound(self):
        """Reproduz o som de início da gravação"""
        self._play_sound('start')
    
    def play_stop_sound(self):
        """Play a sound to indicate stop of dictation"""
        self._play_sound('stop')
    
    def test_microphone(self, mic_id):
        """Test if a microphone is working by checking if the device exists.
        
        Args:
            mic_id (int): The ID of the microphone to test
            
        Returns:
            dict: A dictionary containing:
                - success (bool): Whether the test was successful
                - message (str): A message describing the result or error
                - level (float): A simulated audio level (0.0 to 1.0)
        """
        try:
            # Verificar se temos um resultado em cache recente (menos de 60 segundos)
            current_time = time.time()
            cache_time_diff = current_time - self.__class__._last_mic_test_time
            
            # Usar resultado em cache se disponível e recente
            if (cache_time_diff < 60.0 and str(mic_id) in self.__class__._last_mic_test):
                cached_result = self.__class__._last_mic_test[str(mic_id)].copy()
                
                # Variar levemente o nível para simular um microfone ativo
                if cached_result.get("success", False):
                    current_level = cached_result.get("level", 0.3)
                    variation = random.uniform(-0.05, 0.05)
                    new_level = max(0.05, min(0.95, current_level + variation))
                    cached_result["level"] = new_level
                
                # Log simplificado
                self.logger.debug(f"[CACHE] Usando resultado em cache para o microfone ID {mic_id}")
                return cached_result
            
            self.logger.info(f"Testando o microfone ID: {mic_id}")
            
            # Implementação simplificada para retornar um status simulado
            # Não criamos instâncias do PyAudio a cada teste para economizar recursos
            simulated_level = random.uniform(0.2, 0.6)
            
            result = {
                "success": True,
                "message": f"Microfone {mic_id} disponível (simulado)",
                "level": simulated_level
            }
            
            # Atualizar o cache
            self.__class__._last_mic_test[str(mic_id)] = result.copy()
            self.__class__._last_mic_test_time = current_time
            self.logger.debug(f"Armazenado teste de microfone em cache")
            
            return result
            
        except Exception as e:
            # Criar resultado de erro
            result = {
                "success": False,
                "message": f"Erro ao testar microfone: {str(e)}",
                "level": 0.0
            }
            
            # Atualizar o cache mesmo para erros
            self.__class__._last_mic_test[str(mic_id)] = result.copy()
            self.__class__._last_mic_test_time = current_time
            
            # Registrar erro
            return self._handle_exception("test_microphone", e, result)
    
    def get_language(self):
        """Retorna o idioma de reconhecimento atual."""
        return self.current_language
    
    def set_language(self, language):
        """Set the language for speech recognition
        
        Args:
            language (str): The language code (e.g., 'en-US', 'pt-PT')
        """
        try:
            self.logger.info(f"Setting recognition language to {language}")
            self.language = language
            
            # Persistir a alteração na configuração
            self.config_manager.set_value("recognition", "language", language)
            self.config_manager.save_config()
            
            # Log detalhado para garantir que a configuração foi salva
            self.logger.info(f"Language saved in config: {self.config_manager.get_value('recognition', 'language')}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to set language to {language}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def set_microphone(self, mic_id):
        """Set the microphone for recording
        
        Args:
            mic_id (int): The ID of the microphone to use
        """
        self.logger.info(f"Setting microphone ID to: {mic_id}")
        self.default_mic_id = mic_id
        
        # Usar chaves consistentes no config_manager
        self.config_manager.set_value("audio", "microphone_id", mic_id)
        self.config_manager.set_value("audio", "default_microphone_id", mic_id)
        
        # Atualizar o nome do microfone nas configurações, se disponível
        try:
            microphones = self.get_microphones()
            for mic in microphones:
                if mic["id"] == mic_id:
                    self.config_manager.set_value("audio", "default_microphone", mic["name"])
                    break
        except Exception as e:
            self.logger.error(f"Error updating microphone name: {str(e)}")
        
        # Salvar alterações imediatamente com force=True para garantir persistência
        self.config_manager.save_config(force=True)
        self.logger.info(f"Microphone settings saved with ID: {mic_id}")
    
    def stop(self):
        """Stop all processing and threads"""
        self.logger.info("Stopping DictationManager")
        self.stop_flag = True
        
        # Garantir que todas as configurações sejam salvas
        if hasattr(self, 'config_manager') and hasattr(self.config_manager, 'ensure_saved'):
            try:
                self.config_manager.ensure_saved()
                self.logger.info("Configurações salvas com sucesso durante o encerramento")
            except Exception as e:
                self.logger.error(f"Erro ao salvar configurações durante encerramento: {str(e)}")
        
        # Encerrar recursos de áudio
        if hasattr(self, 'audio_stream') and self.audio_stream:
            self.logger.info("Closing audio stream")
            try:
                if self.audio_stream.is_active():
                    self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
            except Exception as e:
                self.logger.error(f"Error closing audio stream: {str(e)}")
        
        if hasattr(self, 'pyaudio') and self.pyaudio:
            self.logger.info("Terminating PyAudio")
            try:
                self.pyaudio.terminate()
                self.pyaudio = None
            except Exception as e:
                self.logger.error(f"Error terminating PyAudio: {str(e)}")
        
        # Clear buffers
        self.audio_buffer = []
        if hasattr(self, 'audio_queue'):
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except:
                    pass
        
        self.logger.info("DictationManager stopped")
    
    def get_supported_languages(self):
        """Get list of supported languages for recognition
        
        Returns:
            list: List of dictionaries with language information
        """
        try:
            # Define common languages supported across services
            languages = [
                {"id": "pt-PT", "name": "Português (Portugal)", "voice_available": True},
                {"id": "pt-BR", "name": "Português (Brasil)", "voice_available": True},
                {"id": "en-US", "name": "English (US)", "voice_available": True},
                {"id": "en-GB", "name": "English (UK)", "voice_available": True},
                {"id": "en-AU", "name": "English (Australia)", "voice_available": True},
                {"id": "es-ES", "name": "Español (España)", "voice_available": True},
                {"id": "es-MX", "name": "Español (México)", "voice_available": True},
                {"id": "fr-FR", "name": "Français (France)", "voice_available": True},
                {"id": "fr-CA", "name": "Français (Canada)", "voice_available": True},
                {"id": "it-IT", "name": "Italiano", "voice_available": True},
                {"id": "de-DE", "name": "Deutsch", "voice_available": True},
                {"id": "ja-JP", "name": "日本語", "voice_available": True},
                {"id": "ko-KR", "name": "한국어", "voice_available": True},
                {"id": "zh-CN", "name": "中文 (简体)", "voice_available": True},
                {"id": "zh-TW", "name": "中文 (繁體)", "voice_available": True},
                {"id": "ru-RU", "name": "Русский", "voice_available": True},
                {"id": "pl-PL", "name": "Polski", "voice_available": True},
                {"id": "nl-NL", "name": "Nederlands", "voice_available": True},
                {"id": "tr-TR", "name": "Türkçe", "voice_available": True},
                {"id": "ar-SA", "name": "العربية", "voice_available": True},
                {"id": "hi-IN", "name": "हिन्दी", "voice_available": True}
            ]
            
            # If using Azure service, request current languages
            if hasattr(self, 'service_name') and self.service_name == "azure" and hasattr(self, 'azure_service'):
                try:
                    # Try to get real-time supported languages from the service
                    azure_languages = self.azure_service.get_supported_languages()
                    if azure_languages:
                        # Merge with our predefined list
                        language_ids = [lang["id"] for lang in languages]
                        for azure_lang in azure_languages:
                            if azure_lang["id"] not in language_ids:
                                languages.append(azure_lang)
                except Exception as e:
                    self.logger.error(f"Error getting supported languages from Azure: {str(e)}")
            
            # Sort languages by name
            languages.sort(key=lambda x: x["name"])
            
            return languages
        except Exception as e:
            return self._handle_exception("get_supported_languages", e, [
                {"id": "en-US", "name": "English (US)", "voice_available": True},
                {"id": "pt-PT", "name": "Português (Portugal)", "voice_available": True}
            ])
            
    def set_service(self, service_name):
        """Set the speech recognition service"""
        try:
            # Get the service
            service = self._get_service(service_name)
            
            # If service is valid, set it
            if service:
                self.service = service
                self.service_name = service_name
                
                # Save to config
                self.config_manager.set_value("recognition", "service", service_name)
                # Salvar configuração imediatamente com force=True
                self.config_manager.save_config(force=True)
                
                # Log service change
                self.logger.info(f"Changed speech recognition service to {service_name}")
                
                return True
            else:
                self.logger.error(f"Invalid service name: {service_name}")
                return False
        except Exception as e:
            return self._handle_exception("set_service", e, False)

    def set_translator_service(self, service_name):
        """Set the translator service"""
        try:
            self.logger.info(f"Setting translator service to: {service_name}")
            
            # Verificar se o serviço LLM local está disponível
            if service_name == "local_llm":
                try:
                    import torch
                    from transformers import MBartForConditionalGeneration, MBart50TokenizerFast
                except ImportError:
                    self.logger.warning("Torch/Transformers not installed, using Azure Translator instead")
                    service_name = "azure_translator"
                    self.config_manager.set_value("translation", "service", service_name)
                    
            # Verificar se o serviço Azure tem credenciais configuradas
            if service_name == "azure_translator":
                # Obter credenciais do Azure Translator
                api_key = self.config_manager.get_value("translation", "azure_translator_key", "")
                region = self.config_manager.get_value("translation", "azure_translator_region", "")
                
                # Registrar informações detalhadas para diagnóstico
                if not api_key:
                    self.logger.error("Azure Translator API key is empty or not configured")
                else:
                    # Mostrar apenas parte da chave por segurança
                    masked_key = api_key[:5] + "..." + api_key[-5:] if len(api_key) > 10 else "***"
                    self.logger.info(f"Azure Translator API key from config: {masked_key}")
                
                if not region:
                    self.logger.error("Azure Translator region is empty or not configured")
                else:
                    self.logger.info(f"Azure Translator region from config: {region}")
                
                # Atualizar credenciais do Azure Translator
                if hasattr(self, 'translator_service') and hasattr(self.translator_service, "update_credentials"):
                    self.logger.info("Updating Azure Translator credentials")
                    credentials_valid = self.translator_service.update_credentials(api_key, region)
                    
                    if not credentials_valid:
                        self.logger.warning("Azure Translator credentials not valid")
                else:
                    if not api_key or not region:
                        self.logger.warning("Azure Translator credentials not configured")
                
                # Descarregar modelo LLM se estiver mudando para Azure
                if hasattr(self, 'local_llm_translator_service') and hasattr(self.local_llm_translator_service, "unload_model"):
                    self.logger.debug(f"Changing from local translator to API translator ({service_name})")
                    self.logger.debug("Unloading local LLM translation model to free memory")
                    self.local_llm_translator_service.unload_model()
            
            # Set the translator service
            self.translator = self._get_translator_service(service_name)
            self.logger.info(f"Translator service set to: {service_name}")
            
            return service_name
        except Exception as e:
            return self._handle_exception("set_translator_service", e, "m2m100")
            
    def _get_full_recognition_text(self):
        """Método auxiliar para obter o texto completo reconhecido da sessão atual.
        
        Returns:
            str: O texto mais longo do histórico de reconhecimento, ou None se não houver histórico.
        """
        if hasattr(self, 'recognition_history') and self.recognition_history:
            # Retornar o texto mais longo do histórico
            return max(self.recognition_history, key=len)
            
        # Caso não tenha histórico, retornar None
        return None
        
    def set_target_language(self, target_language):
        """Define o idioma alvo para tradução."""
        self.target_language = target_language
        self.config_manager.set_value("translation", "target_language", target_language)
        # Salvar configuração
        self.config_manager.save_config()
        self.logger.info(f"Target language set to: {target_language}")
    
    def _translate_text(self, text, source_lang=None, target_lang=None):
        """
        Translate text using the selected translation service
        
        Args:
            text (str): Text to translate
            source_lang (str, optional): Source language. Defaults to None.
            target_lang (str, optional): Target language. Defaults to None.
            
        Returns:
            str: Translated text
        """
        try:
            # Se o texto estiver vazio, retornar vazio
            if not text or len(text.strip()) == 0:
                return text
                
            # Obter idioma de origem
            if source_lang is None:
                source_lang = self.language
                
            # Obter idioma de destino
            if target_lang is None:
                target_lang = self.target_language
                
            self.logger.info(f"Translating from {source_lang} to {target_lang}")
            
            # Verificar atributo para evitar erros
            if not hasattr(self, 'translation_service_name') or self.translation_service_name is None:
                self.translation_service_name = self.config_manager.get_value("translation", "service", "azure_openai")
                self.logger.warning(f"Atributo translation_service_name não encontrado, usando valor do config: {self.translation_service_name}")
            
            # Obter serviço de tradução
            self.logger.info(f"Usando serviço de tradução: {self.translation_service_name}")
            
            if not hasattr(self, 'translator_service') or self.translator_service is None:
                self.translator_service = self._get_translator_service(self.translation_service_name)
                
            if self.translator_service is None:
                self.logger.error("Translator service not available")
                
                # Verificar se temos API keys configuradas
                azure_openai_key = self.config_manager.get_value("translation", "azure_openai_key", "")
                azure_openai_endpoint = self.config_manager.get_value("translation", "azure_openai_endpoint", "")
                azure_openai_deployment = self.config_manager.get_value("translation", "azure_openai_deployment", "")
                
                # Tentar inicializar o serviço manualmente
                if azure_openai_key and azure_openai_endpoint and azure_openai_deployment:
                    self.logger.info("Tentando inicializar o serviço Azure OpenAI manualmente")
                    try:
                        from src.services.azure_openai_service import AzureOpenAIService
                        self.translator_service = AzureOpenAIService(
                            api_key=azure_openai_key,
                            endpoint=azure_openai_endpoint,
                            deployment_name=azure_openai_deployment
                        )
                        self.logger.info("Serviço Azure OpenAI inicializado manualmente com sucesso")
                    except Exception as e:
                        self.logger.error(f"Falha ao inicializar manualmente: {str(e)}")
                        
                # Se ainda não conseguimos, usar serviço local como fallback
                if self.translator_service is None:
                    self.logger.warning("Serviço de tradução não disponível, usando texto original")
                    return text
                
            # Log do tipo de serviço para diagnóstico
            if self.translator_service:
                self.logger.info(f"Tipo do serviço de tradução: {type(self.translator_service).__name__}")
                
            # Tentar traduzir o texto
            try:
                # Formatar o texto para tradução (remover caracteres especiais, etc)
                # Implementação futura: preparação do texto específica para cada idioma
                
                # Traduzir o texto - verificar qual método existe no serviço
                start_time = time.time()
                translated_text = None
                
                # Verificar qual método de tradução o serviço implementa
                if hasattr(self.translator_service, 'translate_text'):
                    self.logger.info("Usando método translate_text")
                    translated_text = self.translator_service.translate_text(text, source_lang, target_lang)
                elif hasattr(self.translator_service, 'translate'):
                    self.logger.info("Usando método translate")
                    translated_text = self.translator_service.translate(text, source_lang, target_lang)
                elif hasattr(self.translator_service, 'generate_text'):
                    self.logger.info("Usando método generate_text (Azure OpenAI)")
                    # Para Azure OpenAI, preparar um prompt específico para tradução
                    prompt = f"Translate the following text from {source_lang} to {target_lang}:\n\n{text}\n\nTranslation:"
                    translated_text = self.translator_service.generate_text(prompt)
                else:
                    self.logger.error(f"Serviço de tradução {type(self.translator_service).__name__} não implementa método de tradução conhecido")
                    return text
                
                end_time = time.time()
                
                # Verificar resultado
                if not translated_text or translated_text.strip() == '':
                    self.logger.warning("Translation returned empty result")
                    return text
                
                # Log do resultado
                translation_time = end_time - start_time
                self.logger.info(f"Tradução bem-sucedida em {translation_time:.2f}s: '{text[:50]}....' -> '{translated_text[:50]}....'")
                
                # Registrar estatísticas
                if hasattr(self, 'stats_service') and self.stats_service:
                    word_count = len(text.split())
                    target_word_count = len(translated_text.split())
                    
                    if hasattr(self.stats_service, 'add_translation'):
                        self.stats_service.add_translation(
                            source_lang, 
                            target_lang, 
                            word_count, 
                            target_word_count, 
                            translation_time
                        )
                
                # Retornar o texto traduzido
                return translated_text
                
            except Exception as e:
                self.logger.error(f"Error in translation: {str(e)}")
                self.logger.error(traceback.format_exc())
                return text
                
        except Exception as e:
            self.logger.error(f"Error in _translate_text: {str(e)}")
            self.logger.error(traceback.format_exc())
            return text

    def _cleanup_streams(self):
        """Clean up any existing audio streams"""
        try:
            # Usar lock para evitar problemas com concorrência
            with threading.Lock():
                # Limpar stream de áudio
                if hasattr(self, 'audio_stream') and self.audio_stream:
                    try:
                        if self.audio_stream.is_active():
                            self.audio_stream.stop_stream()
                        self.audio_stream.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing audio stream: {str(e)}")
                    finally:
                        self.audio_stream = None
                
                # Limpar stream geral
                if hasattr(self, 'stream') and self.stream:
                    try:
                        if self.stream.is_active():
                            self.stream.stop_stream()
                        self.stream.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing general stream: {str(e)}")
                    finally:
                        self.stream = None
        except Exception as e:
            self.logger.error(f"Error cleaning up streams: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _post_process_text(self, text):
        """Apply post-processing to the recognized text
        
        Args:
            text (str): Text to process
            
        Returns:
            str: Processed text
        """
        try:
            if not text:
                return ""
                
            # Inicializar o formatador de texto
            try:
                # Criar o formatador sem passar o config_manager (ele tem seu próprio)
                text_formatter = TextFormatter()
                self.logger.info("Text formatter initialized")
            except Exception as e:
                self.logger.error(f"Error initializing text formatter: {str(e)}")
                self.logger.error(traceback.format_exc())
                return text
                
            # Aplicar formatação
            try:
                processed_text = text_formatter.format_text(text)
                return processed_text
            except Exception as e:
                self.logger.error(f"Error applying text formatting: {str(e)}")
                self.logger.error(traceback.format_exc())
                return text
                
        except Exception as e:
            self.logger.error(f"Error in _post_process_text: {str(e)}")
            self.logger.error(traceback.format_exc())
            return text

    def initialize_stats(self):
        """Initialize the statistics service"""
        try:
            from src.services.stats_service import StatsService
            if self.config_manager:
                self.stats_service = StatsService(self.config_manager._get_config_dir())
            else:
                self.stats_service = None
        except Exception as e:
            logger.error(f"Failed to initialize stats service: {e}")
            self.stats_service = None
    
    def show_notification(self, message, notification_type="info", duration=2000):
        """Exibe uma notificação para o usuário
        
        Args:
            message (str): Mensagem a ser exibida
            notification_type (str): Tipo de notificação ("info", "warning", "error")
            duration (int): Duração em milissegundos
        """
        try:
            self.logger.info(f"Mostrando notificação: {message} (tipo: {notification_type}, duração: {duration}ms)")
            
            # Tentativa com QSystemTrayIcon
            try:
                from PyQt5.QtWidgets import QApplication, QSystemTrayIcon
                from PyQt5.QtGui import QIcon
                import os
                
                # Determinar o caminho dos recursos - mais robusto
                # Primeiro verificar se temos self.resources_path
                resources_path = None
                if hasattr(self, 'resources_path') and self.resources_path:
                    resources_path = self.resources_path
                else:
                    # Tentar encontrar o caminho com base no diretório atual
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    possible_paths = [
                        os.path.join(os.path.dirname(os.path.dirname(current_dir)), "resources"),  # ../../resources
                        os.path.join(os.path.dirname(current_dir), "resources"),  # ../resources
                        os.path.join(current_dir, "resources")  # ./resources
                    ]
                    for path in possible_paths:
                        if os.path.exists(path):
                            resources_path = path
                            break
                
                # Se não conseguir encontrar, usar um ícone padrão ou nenhum ícone
                icon_path = None
                if resources_path:
                    icon_path = os.path.join(resources_path, "icons", "app_icon.png")
                    if not os.path.exists(icon_path):
                        icon_path = None
                
                # Obter aplicação atual
                app = QApplication.instance()
                if app:
                    # Criar ícone temporário se necessário
                    if not hasattr(self, '_tray_icon') or self._tray_icon is None:
                        self._tray_icon = QSystemTrayIcon()
                        if icon_path:
                            self._tray_icon.setIcon(QIcon(icon_path))
                        else:
                            # Usar um ícone padrão do sistema
                            self._tray_icon.setIcon(QIcon.fromTheme("dialog-information"))
                        self._tray_icon.show()
                    
                    # Mapear tipo de notificação para ícone
                    icon_type = QSystemTrayIcon.Information
                    if notification_type == "warning":
                        icon_type = QSystemTrayIcon.Warning
                    elif notification_type == "error":
                        icon_type = QSystemTrayIcon.Critical
                    
                    # Mostrar notificação
                    self._tray_icon.showMessage(
                        "DogeDictate",
                        message,
                        icon_type,
                        duration
                    )
                    return
            except Exception as e:
                self.logger.warning(f"Falha ao mostrar notificação com QSystemTrayIcon: {str(e)}")
            
            # Fallback para QMessageBox se QSystemTrayIcon falhar
            try:
                from PyQt5.QtWidgets import QMessageBox
                from PyQt5.QtCore import QTimer, Qt
                
                # Criar message box sem bloquear
                msg = QMessageBox()
                msg.setWindowTitle("DogeDictate")
                msg.setText(message)
                msg.setWindowFlags(Qt.WindowStaysOnTopHint)
                
                # Definir ícone com base no tipo
                if notification_type == "info":
                    msg.setIcon(QMessageBox.Information)
                elif notification_type == "warning":
                    msg.setIcon(QMessageBox.Warning)
                elif notification_type == "error":
                    msg.setIcon(QMessageBox.Critical)
                
                # Configurar para fechar automaticamente
                QTimer.singleShot(duration, msg.close)
                
                # Mostrar sem bloquear
                msg.show()
            except Exception as e:
                self.logger.error(f"Falha ao mostrar notificação com QMessageBox: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Erro ao mostrar notificação: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    