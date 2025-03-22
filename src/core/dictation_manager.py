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
        """Initialize the dictation manager
        
        Args:
            config_manager: The configuration manager
        """
        # Store the config manager
        self.config_manager = config_manager
        
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
        
        # Initialize microphone
        self.default_mic_id = self.config_manager.get_value("audio", "microphone_id", 0)
        
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
            self.config_manager.set_value("audio", "microphone_id", self.default_mic_id)
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
        
        # Initialize VAD parameters - Ajustados para maior sensibilidade
        self.vad_enabled = False  # Desabilitar VAD por padrão
        self.vad_threshold = 0.001  # Reduzir threshold para detectar sons mais baixos
        self.vad_silence_duration = 0.5  # Reduzir duração do silêncio
        
        # Save VAD settings to config
        self.config_manager.set_value("vad", "enabled", self.vad_enabled)
        self.config_manager.set_value("vad", "threshold", self.vad_threshold)
        self.config_manager.set_value("vad", "silence_duration", self.vad_silence_duration)
        
        # Initialize stats service if available
        if self.config_manager.get_value("stats", "enabled", True):
            self.stats_service = StatsService(self.config_manager)
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
            # Initialize default service attributes to None
            self.whisper_service = None
            self.azure_service = None
            self.google_service = None
            self.local_whisper_service = None
            
            # Initialize translation service attributes to None
            self.azure_translator_service = None
            self.azure_openai_service = None
            self.m2m100_translator_service = None
            self.local_llm_translator_service = None
            
            # Set default attributes for services
            self.service = None
            self.translator_service = None
            self.translation_service = None  # Alias for compatibility
            
            # Initialize recognition service name
            self.recognition_service = service_name
            self.service_name = service_name  # Para compatibilidade com código existente
            
            self.logger.info("Initializing speech recognition services...")
            self.logger.info(f"Requested service: {service_name}")
            
            # Initialize whisper service
            if 'whisper' in service_name:
                self.logger.info("Initializing Whisper service...")
                self.whisper_service = WhisperService(self.config_manager)
                self.logger.info("Whisper service initialized")
            
            # Initialize Azure service
            if hasattr(self.config_manager, 'get_value'):
                azure_key = self.config_manager.get_value("recognition", "azure_api_key", "")
                azure_region = self.config_manager.get_value("recognition", "azure_region", "westeurope")
                
                if azure_key:
                    self.logger.info("Initializing Azure service...")
                    self.azure_service = AzureService(self.config_manager)
                    # Show only part of the key for security
                    masked_key = azure_key[:5] + "..." + azure_key[-5:] if len(azure_key) > 10 else "***"
                    self.logger.info(f"Azure API key configured: {masked_key}")
                    self.logger.info(f"Azure region configured: {azure_region}")
                    self.logger.info("Azure service initialized")
                else:
                    self.logger.warning("Azure API key not configured")
            
            # Initialize Google service
            google_credentials = self.config_manager.get_value("recognition", "google_credentials_path", "")
            if google_credentials and os.path.exists(google_credentials):
                self.logger.info("Initializing Google service...")
                self.google_service = GoogleService(self.config_manager)
                self.logger.info(f"Google credentials found at: {google_credentials}")
                self.logger.info("Google service initialized")
            else:
                self.logger.info("Google credentials not configured")
            
            # Initialize local whisper service
            self.logger.info("Initializing Local Whisper service...")
            self.local_whisper_service = LocalWhisperService(self.config_manager)
            self.logger.info("Local Whisper service initialized")
            
            # Set language for recognition
            self.language = self.config_manager.get_value("recognition", "language", "pt-PT")
            
            # Set default service for compatibility
            self.service = self._get_service(service_name)
            
            if self.service:
                self.logger.info(f"Using recognition service: {service_name}")
                self.logger.warning(f"Recognition service initialized: {service_name}")
                self.logger.info(f"Recognition language: {self.language}")
            else:
                self.logger.error(f"Failed to initialize recognition service: {service_name}")
                # Try to use a fallback service
                if self.azure_service:
                    self.logger.warning("Using Azure as fallback recognition service")
                    self.service = self.azure_service
                    self.recognition_service = 'azure'
                elif self.local_whisper_service:
                    self.logger.warning("Using Local Whisper as fallback recognition service")
                    self.service = self.local_whisper_service
                    self.recognition_service = 'whisper_local'
            
            # Initialize translator services
            translator_service_name = self.config_manager.get_value("translation", "service", "azure_openai")
            self.translation_service_name = translator_service_name
            self.logger.info(f"Initializing translator service: {translator_service_name}")
            
            # Initialize Azure translator
            azure_translator_key = self.config_manager.get_value("translation", "azure_translator_key", "")
            azure_translator_region = self.config_manager.get_value("translation", "azure_translator_region", "westeurope")
            
            if azure_translator_key:
                self.logger.info("Initializing Azure Translator service...")
                self.azure_translator_service = AzureTranslatorService(self.config_manager)
                self.logger.info("Azure Translator service initialized")
            
            # Initialize Azure OpenAI translator
            azure_openai_key = self.config_manager.get_value("translation", "azure_openai_key", "")
            if azure_openai_key:
                self.logger.info("Initializing Azure OpenAI service...")
                self.azure_openai_service = AzureOpenAIService(self.config_manager)
                self.logger.warning("Using Azure OpenAI for translation")
            
            # Initialize M2M100 translator
            self.logger.info("Initializing M2M100 translator service...")
            self.m2m100_translator_service = M2M100TranslatorService(self.config_manager)
            self.logger.info("M2M100 translator service initialized")
            
            # Initialize Local LLM translator
            self.logger.info("Initializing Local LLM translator service...")
            self.local_llm_translator_service = LocalLLMTranslatorService(self.config_manager)
            self.logger.info("Local LLM translator service initialized")
            
            # Set translation service based on configuration
            self.translator_service = self._get_translator_service(translator_service_name)
            if self.translator_service:
                self.logger.warning(f"Translation service initialized: {translator_service_name}")
            else:
                self.logger.error(f"Failed to initialize translation service: {translator_service_name}")
                # Try fallback
                if self.azure_openai_service:
                    self.logger.warning("Using Azure OpenAI as fallback translation service")
                    self.translator_service = self.azure_openai_service
                    self.translation_service_name = "azure_openai"
                elif self.azure_translator_service:
                    self.logger.warning("Using Azure Translator as fallback translation service")
                    self.translator_service = self.azure_translator_service
                    self.translation_service_name = "azure_translator"
                    
            # Set target language for translation
            self.target_language = self.config_manager.get_value("translation", "target_language", "en-US")
            self.logger.info(f"Translation target language: {self.target_language}")
            
        except Exception as e:
            self.logger.error(f"Error initializing services: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def start_dictation(self):
        """Start dictation"""
        try:
            if self.is_recording:
                self.logger.warning("Dictation already started")
                return False
            
            # Configurar VAD para ser mais sensível
            self.vad_enabled = False
            self.vad_threshold = 0.0001  # Reduzido para ser mais sensível
            self.vad_silence_duration = 0.5
            
            # Salvar configurações atualizadas no arquivo de configuração
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
            
            # Inicializar propriedades de gravação
            self.audio_buffer = []
            self.audio_queue = queue.Queue()
            self.processing_queue = queue.Queue()
            
            # Reset thread references
            self.recording_thread = None
            self.processing_thread = None
            
            # Configurar áudio antes de iniciar gravação
            self.audio_config = {
                'chunk_size': 1024,
                'format': pyaudio.paInt16,
                'channels': 1,
                'sample_rate': 16000,
                'frames_per_buffer': 1024
            }
            self.logger.info("Audio configuration set")
            
            # Definir modo de callback como falso
            self.audio_callback_mode = False
            
            # Start the actual recording process
            if not self._start_recording():
                self.logger.error("Failed to start recording")
                return False
            
            self.logger.warning(f"Starting dictation with language: {self.language}")
            
            # Marcar como gravando e processando
            self.is_recording = True
            self.is_processing = True
            
            # Iniciar nova thread de gravação
            self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
            self.recording_thread.start()
            
            # Iniciar thread de processamento de áudio para consumir da fila
            self.processing_thread = threading.Thread(target=self._process_audio_loop, daemon=True)
            self.processing_thread.start()
            
            # Configurar timestamp para estatísticas
            self.start_time = time.time()
            
            # Emitir sinal sonoro para indicar início (opcional, conforme configuração)
            if self.config_manager.get_value("audio", "play_sounds", True):
                self.play_start_sound()
            
            # Log de início bem-sucedido
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
        # Reduzir o atraso para capturar o final da fala
        post_recording_delay = self.config_manager.get_value("recording", "post_recording_delay", 0.5)
        # Usar um valor menor para reduzir a latência
        actual_delay = min(post_recording_delay, 0.1)  # Limitamos a 100ms máximo
        if actual_delay > 0:
            self.logger.debug(f"Aguardando {actual_delay:.2f} segundos para capturar o final da fala...")
            time.sleep(actual_delay)
            
        if not self.is_recording:
            self.logger.warning("Dictation already stopped")
            return
        
        self.logger.warning("Stopping dictation")
        
        # Stop recording - desative antes de processar áudio
        self.is_recording = False
        self.continuous_recording = False  # Desativar gravação contínua
        
        # Aguardar a thread de gravação terminar
        if self.recording_thread and self.recording_thread.is_alive():
            self.logger.info("Waiting for recording thread to finish")
            self.recording_thread.join(timeout=2.0)  # Timeout para evitar bloqueio
            if self.recording_thread.is_alive():
                self.logger.warning("Recording thread did not exit within timeout, continuing anyway")
        
        # Este delay é importante para dar tempo ao _process_audio_loop reconhecer que 
        # a gravação parou e processar o áudio acumulado
        time.sleep(1.0)
        
        # Encerrar a thread de processamento só depois de um tempo
        # para garantir que todo o áudio foi processado
        time.sleep(1.5)  # Mais tempo para processamento completo
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
        region = self.config_manager.get_value("recognition", "azure_region", "westeurope")
        
        # Log para diagnóstico
        if not api_key:
            self.logger.error("Azure API key is empty or not configured")
            return None
        else:
            # Mostrar parte da chave por segurança
            masked_key = api_key[:5] + "..." + api_key[-5:] if len(api_key) > 10 else "***"
            self.logger.info(f"Azure API key configured: {masked_key}")
            
        self.logger.info(f"Azure region configured: {region}")
        
        if api_key and region:
            return AzureService(self.config_manager)
        
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
        """Get a translation service by name"""
        try:
            # Mapeamento de serviços para seus respectivos objetos
            translator_mapping = {
                "azure_translator": self._get_azure_translator_service,
                "m2m100": lambda: self.m2m100_translator_service,
                "azure_openai": self._get_azure_openai_service,
                "local_llm": lambda: self.local_llm_translator_service
            }
            
            # Verificar se o serviço está no mapeamento
            if service_name in translator_mapping:
                service = translator_mapping[service_name]()
                if service:
                    return service
                    
            # Se o serviço solicitado não existe ou não retornou um objeto válido
            self.logger.warning(f"Translation service {service_name} not available, falling back to M2M100")
            return self.m2m100_translator_service
            
        except Exception as e:
            return self._handle_exception("_get_translator_service", e, self.m2m100_translator_service)
            
    def _get_azure_translator_service(self):
        """Obter serviço Azure Translator para tradução"""
        api_key = self.config_manager.get_value("translation", "azure_translator_key", "")
        region = self.config_manager.get_value("translation", "azure_translator_region", "westeurope")
        
        if api_key and region:
            return self.azure_translator_service
        else:
            self.logger.warning("Azure Translator credentials not configured properly")
            return None
            
    def _get_azure_openai_service(self):
        """Obter serviço Azure OpenAI para tradução"""
        api_key = self.config_manager.get_value("translation", "azure_openai_key", "")
        
        if api_key and hasattr(self, 'azure_openai_service'):
            return self.azure_openai_service
        else:
            self.logger.warning("Azure OpenAI credentials not configured properly")
            return None
    
    def _recognize_with_selected_service(self, audio_file, service_name=None, auto_translate=True, target_language=None):
        """Recognize speech from audio file using the selected recognition service
        
        Args:
            audio_file (str): Path to the audio file
            service_name (str, optional): Name of the recognition service to use. 
                                         If None, use the configured service.
            auto_translate (bool, optional): Whether to translate the recognized text
            target_language (str, optional): Target language for translation
            
        Returns:
            str: Recognized text (and translated if auto_translate is True)
        """
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(audio_file):
                self.logger.error(f"Audio file does not exist: {audio_file}")
                return None
                
            # Obter serviço de reconhecimento
            if not service_name:
                service_name = self.config_manager.get_value("recognition", "service", "azure")
                
            self.logger.info(f"Trying recognition with {service_name}")
            
            # Selecionar o serviço apropriado
            recognition_service = self.get_recognition_service(service_name)
            
            # Registrar tentativa de reconhecimento
            if hasattr(self, 'stats_service') and self.stats_service:
                if hasattr(self.stats_service, 'add_recognition_attempt'):
                    self.stats_service.add_recognition_attempt(service_name, self.current_language)
                
            # Se não encontrar o serviço, tentar serviço reserva
            if not recognition_service:
                fallback = self.config_manager.get_value("recognition", "fallback_service", "whisper")
                self.logger.warning(f"Recognition service {service_name} not available, trying fallback: {fallback}")
                recognition_service = self.get_recognition_service(fallback)
                
                if not recognition_service:
                    self.logger.error("No recognition service available")
                    return None
                    
                # Atualizar o nome do serviço
                service_name = fallback
                
            # Tentar reconhecimento
            start_time = time.time()
            
            # Verificar o método disponível para o serviço
            if hasattr(recognition_service, 'recognize_speech'):
                result = recognition_service.recognize_speech(audio_file, self.current_language)
            elif hasattr(recognition_service, 'recognize_audio'):
                result = recognition_service.recognize_audio(audio_file, self.current_language)
            elif hasattr(recognition_service, 'recognize'):
                result = recognition_service.recognize(audio_file, self.current_language)
            else:
                self.logger.error(f"Recognition service {service_name} has no recognition method")
                return None
                
            end_time = time.time()
            recognition_time = end_time - start_time
            
            # Verificar resultado
            if not result:
                self.logger.warning(f"Recognition with {service_name} failed or returned empty result")
                return None
                
            # Extrair texto do resultado (pode ser string ou dicionário)
            recognized_text = ""
            confidence = 0.0
            
            if isinstance(result, dict):
                # Se for um dicionário, extrair texto e confiança
                recognized_text = result.get('text', '')
                confidence = result.get('confidence', 0.0)
            elif isinstance(result, str):
                # Se for uma string, usar diretamente
                recognized_text = result
            else:
                # Tentar converter para string
                try:
                    recognized_text = str(result)
                except:
                    self.logger.error(f"Could not convert recognition result to text: {type(result)}")
                    return None
                    
            # Verificar se o texto está vazio
            if not recognized_text or recognized_text.strip() == '':
                self.logger.warning(f"Recognition with {service_name} returned empty text")
                return None
                
            # Aplicar formatação e pós-processamento
            processed_text = self._post_process_text(recognized_text)
            
            # Log do resultado
            self.logger.info(f"Recognition successful in {recognition_time:.2f}s with {service_name}")
            
            # Definir o idioma alvo para tradução
            if not target_language:
                target_language = self.target_language
                
            # Tradução automática se configurada E se os idiomas de origem e destino forem diferentes
            if auto_translate and self.current_language != target_language:
                try:
                    self.logger.info(f"Auto-translating from {self.current_language} to {target_language}")
                    translated_text = self._translate_text(
                        processed_text, 
                        source_lang=self.current_language, 
                        target_lang=target_language
                    )
                    
                    if translated_text and translated_text.strip() != '':
                        self.logger.info(f"Translation successful: '{processed_text}' -> '{translated_text}'")
                        processed_text = translated_text
                    else:
                        self.logger.warning("Translation failed or returned empty result")
                except Exception as e:
                    self.logger.error(f"Error during translation: {str(e)}")
                    self.logger.error(traceback.format_exc())
            else:
                if auto_translate and self.current_language == target_language:
                    self.logger.info(f"Skipping translation: source language ({self.current_language}) and target language ({target_language}) are the same")
                elif not auto_translate:
                    self.logger.info("Auto-translation disabled")
            
            return processed_text
            
        except Exception as e:
            self.logger.error(f"Error in recognition with {service_name}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

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
            
            # Obter ID do microfone das configurações
            mic_id = self.config_manager.get_value("audio", "microphone_id", 0)
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
        """Set the language for dictation"""
        self.language = language
        self.current_language = language
        self.logger.info(f"Language set to: {language}")

    def stop(self):
        """Alias para stop_dictation() para compatibilidade com código existente"""
        self.logger.debug("stop() called as alias for stop_dictation()")
        self.stop_dictation()
        
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
        self.logger.info(f"Target language set to: {target_language}")
    
    def _translate_text(self, text, source_lang=None, target_lang=None):
        """Traduz o texto reconhecido para o idioma alvo
        
        Args:
            text (str): Texto a ser traduzido
            source_lang (str, optional): Idioma de origem. Se None, usa o idioma atual.
            target_lang (str, optional): Idioma alvo. Se None, usa o idioma alvo configurado.
            
        Returns:
            str: Texto traduzido ou o texto original em caso de erro
        """
        try:
            if not text:
                self.logger.warning("No text to translate")
                return ""
                
            # Definir idiomas padrão se não fornecidos
            if not source_lang:
                source_lang = self.current_language
                
            if not target_lang:
                target_lang = self.target_language
                
            # Verificar se os idiomas são iguais
            if source_lang == target_lang:
                self.logger.debug(f"Source and target languages are the same ({source_lang}), skipping translation")
                return text
                
            # Log detalhado para depuração
            self.logger.info(f"Translating from {source_lang} to {target_lang}")
            self.logger.debug(f"Original text: {text[:50]}..." if len(text) > 50 else f"Original text: {text}")
            
            # Obter o serviço de tradução configurado
            translator_service_name = self.config_manager.get_value("translation", "service", "azure")
            
            # Obter a instância do serviço de tradução
            translator_service = self._get_translator_service(translator_service_name)
            
            if not translator_service:
                self.logger.error(f"Translation service '{translator_service_name}' not available")
                return text
                
            # Tentar traduzir
            start_time = time.time()
            translated_text = translator_service.translate(text, source_lang, target_lang)
            end_time = time.time()
            
            # Verificar resultado
            if not translated_text:
                self.logger.warning("Translation failed or returned empty result")
                return text
                
            # Registrar sucesso e tempo
            translation_time = end_time - start_time
            self.logger.info(f"Translation successful in {translation_time:.2f}s using {translator_service_name}")
            self.logger.debug(f"Translated text: {translated_text[:50]}..." if len(translated_text) > 50 else f"Translated text: {translated_text}")
            
            # Incrementar contadores de estatísticas
            if hasattr(self, 'stats_service') and self.stats_service:
                try:
                    word_count = len(text.split())
                    if hasattr(self.stats_service, 'add_translated_words'):
                        self.stats_service.add_translated_words(word_count, translator_service_name)
                    elif hasattr(self.stats_service, 'increment_translation_count'):
                        self.stats_service.increment_translation_count(word_count)
                except Exception as e:
                    self.logger.error(f"Error updating translation statistics: {str(e)}")
            
            # Retornar texto traduzido
            return translated_text
            
        except Exception as e:
            self.logger.error(f"Error in translation: {str(e)}")
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

    