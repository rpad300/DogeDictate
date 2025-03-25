#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Azure Service for DogeDictate
Handles speech recognition using Azure Speech Services
"""

import os
import logging
import azure.cognitiveservices.speech as speechsdk
import time
import tempfile
import shutil
import uuid
import sys
import subprocess
import platform
import re
import threading
import traceback
import numpy as np
import wave
import io

logger = logging.getLogger("DogeDictate.AzureService")

class AzureService:
    """Service for speech recognition using Azure Speech Services"""
    
    def __init__(self, config_manager):
        """Initialize the Azure service"""
        self.config_manager = config_manager
        
        # Carregar chave da API e região
        self.api_key = self.config_manager.get_value("recognition", "azure_api_key", "")
        if not self.api_key:
            # Log para diagnóstico
            logger.warning("API key não encontrada em 'azure_api_key', tentando campo alternativo 'azure_key'")
            self.api_key = self.config_manager.get_value("recognition", "azure_key", "")
        
        self.region = self.config_manager.get_value("recognition", "azure_region", "")
        
        # Log detalhado para diagnóstico
        if self.api_key:
            masked_key = self.api_key[:5] + "..." + self.api_key[-5:] if len(self.api_key) > 10 else "***"
            logger.info(f"Azure API key carregada: {masked_key}")
        else:
            logger.error("Não foi possível encontrar uma chave Azure API válida na configuração")
        
        if self.region:
            logger.info(f"Azure region configurada: {self.region}")
        else:
            logger.error("Region Azure não encontrada na configuração")
        
        self.speech_config = None
        self.custom_temp_dir = None
        self.max_retries = 3
        self.retry_delay = 0.5  # segundos
        
        # Adicionar contadores para controle de reinicialização periódica
        self.recognition_count = 0
        self.last_reset_time = time.time()
        self.max_recognitions_before_reset = 50  # Reiniciar após 50 reconhecimentos
        self.reset_time_threshold = 1800  # Ou após 30 minutos (1800 segundos)
        
        # Criar e configurar diretório temporário personalizado
        self._setup_custom_temp_dir()
        
        # Initialize speech config if credentials are available
        if self.api_key and self.region:
            self._initialize_speech_config()
        
        # Executa limpeza de arquivos temporários antigos durante a inicialização
        self._cleanup_old_files()
    
    def _setup_custom_temp_dir(self):
        """Configura um diretório temporário personalizado para o aplicativo"""
        try:
            # Determinar o diretório raiz do aplicativo
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Criar diretório temp dentro do aplicativo
            temp_dir = os.path.join(app_dir, "temp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                logger.info(f"Created custom temporary directory: {temp_dir}")
            
            # Verificar permissões de escrita
            test_file = os.path.join(temp_dir, f"test_{uuid.uuid4().hex}.tmp")
            with open(test_file, 'w') as f:
                f.write("Test")
            os.remove(test_file)
            
            self.custom_temp_dir = temp_dir
            logger.info(f"Using custom temporary directory: {self.custom_temp_dir}")
            
        except Exception as e:
            logger.error(f"Failed to setup custom temporary directory: {str(e)}")
            self.custom_temp_dir = None
    
    def get_supported_languages(self):
        """Get list of supported languages for Azure Speech Recognition

        Returns:
            list: List of dictionaries with language information
        """
        try:
            # Define common languages supported by Azure Speech Service
            # This is a static list as the API doesn't provide a method to get this dynamically
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
            
            # Log how many languages are supported
            logger.info(f"Returning {len(languages)} supported languages for Azure Speech Service")
            
            return languages
            
        except Exception as e:
            logger.error(f"Error getting supported languages: {str(e)}")
            return []
    
    def update_credentials(self, api_key, region):
        """
        Atualizar credenciais do serviço Azure Speech
        
        Args:
            api_key (str): Chave de API do Azure Speech
            region (str): Região do Azure Speech
            
        Returns:
            bool: True se as credenciais foram atualizadas com sucesso, False caso contrário
        """
        try:
            # Atualizar credenciais
            self.api_key = api_key
            self.region = region
            
            # Log detalhado
            masked_key = self.api_key[:5] + "..." + self.api_key[-5:] if len(self.api_key) > 10 else "***"
            logger.info(f"Atualizando credenciais do Azure Speech: Key={masked_key}, Region={region}")
            
            # Reinicializar configuração de fala
            return self._initialize_speech_config()
        except Exception as e:
            logger.error(f"Erro ao atualizar credenciais do Azure Speech: {str(e)}")
            return False
    
    def _initialize_speech_config(self):
        """Initialize the Azure Speech Services configuration"""
        try:
            # Verificar se as credenciais estão configuradas
            if not self.api_key or not self.region:
                logger.error("Cannot initialize Azure Speech Services: API key or region not configured")
                self.speech_config = None
                return False
            
            # Log detalhado para diagnóstico
            masked_key = self.api_key[:5] + "..." + self.api_key[-5:] if len(self.api_key) > 10 else "***"
            logger.info(f"Inicializando Azure Speech com: API Key={masked_key}, Region={self.region}")
            
            # Verificar versão do SDK e atualizar se necessário
            self._check_sdk_version()
            
            # Criar configuração de fala
            self.speech_config = speechsdk.SpeechConfig(subscription=self.api_key, region=self.region)
            
            # Configurar propriedades adicionais
            log_file = os.path.join(self.custom_temp_dir, "azure_speech.log") if self.custom_temp_dir else "azure_speech.log"
            self.speech_config.set_property(speechsdk.PropertyId.Speech_LogFilename, log_file)
            
            logger.info(f"Azure Speech Services initialized successfully with region: {self.region}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Azure Speech Services: {str(e)}")
            self.speech_config = None
            return False
    
    def _check_sdk_version(self):
        """Verifica e atualiza a versão do SDK do Azure se necessário"""
        try:
            import pkg_resources
            
            # Obter versão atual do SDK
            current_version = pkg_resources.get_distribution("azure-cognitiveservices-speech").version
            logger.info(f"Current Azure Speech SDK version: {current_version}")
            
            # Verificar se é a versão mais recente (opcional)
            # Esta verificação pode ser desativada em ambientes de produção
            try:
                import subprocess
                import json
                
                # Obter informações da versão mais recente do PyPI
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "index", "versions", "azure-cognitiveservices-speech", "--json"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if result.stdout:
                    data = json.loads(result.stdout)
                    latest_version = data.get("versions", [])[0] if data.get("versions") else current_version
                    
                    if latest_version != current_version:
                        logger.warning(f"A newer version of Azure Speech SDK is available: {latest_version}")
                        # Atualização automática desativada para evitar problemas de compatibilidade
                        # Apenas registra a informação para atualização manual
            except Exception as e:
                logger.warning(f"Failed to check for SDK updates: {str(e)}")
                
        except Exception as e:
            logger.warning(f"Failed to check SDK version: {str(e)}")
    
    def _sanitize_path(self, path):
        """Sanitiza o caminho para evitar problemas com caracteres especiais"""
        if not path:
            return path
            
        # Converter para caminho absoluto
        abs_path = os.path.abspath(path)
        
        # No Windows, usar caminho curto (8.3) para evitar espaços e caracteres especiais
        if platform.system() == "Windows":
            try:
                import ctypes
                buffer_size = 260  # MAX_PATH
                buffer = ctypes.create_unicode_buffer(buffer_size)
                get_short_path_name = ctypes.windll.kernel32.GetShortPathNameW
                result = get_short_path_name(abs_path, buffer, buffer_size)
                
                if result != 0:
                    return buffer.value
            except Exception as e:
                logger.warning(f"Failed to get short path name: {str(e)}")
                
        return abs_path
    
    def _create_temp_file(self, audio_data):
        """Cria um arquivo temporário com os dados de áudio.
        
        Args:
            audio_data (bytes): Dados de áudio
            
        Returns:
            str: Caminho para o arquivo temporário
        """
        try:
            # Gerar nome único para o arquivo
            timestamp = int(time.time())
            random_id = uuid.uuid4().hex[:16]
            temp_filename = f"azure_audio_{timestamp}_{random_id}.wav"
            
            # Usar diretório temporário personalizado se disponível
            if self.custom_temp_dir and os.path.exists(self.custom_temp_dir):
                temp_file_path = os.path.join(self.custom_temp_dir, temp_filename)
            else:
                # Fallback para diretório temporário do sistema
                temp_file_path = os.path.join(tempfile.gettempdir(), temp_filename)
            
            # Converter dados de áudio para formato WAV adequado se necessário
            # Se os dados já estiverem em formato WAV, verificar se tem cabeçalho correto
            if audio_data[:4] != b'RIFF' or audio_data[8:12] != b'WAVE':
                logger.warning("Audio data does not have valid WAV headers, creating proper WAV file")
                # Converter os dados para array numpy
                try:
                    samples = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Garantir que o arquivo WAV seja gravado corretamente com wave.open
                    with wave.open(temp_file_path, 'wb') as wf:
                        wf.setnchannels(1)  # mono
                        wf.setsampwidth(2)  # 16-bit = 2 bytes
                        wf.setframerate(16000)  # 16kHz é o esperado pelo Azure
                        wf.writeframes(samples.tobytes())  # Usar tobytes() para garantir formato correto
                        
                    # Log importante para debug
                    logger.warning(f"Created new WAV file from raw audio data: {temp_file_path}")
                    logger.warning(f"Original audio data size: {len(audio_data)}, samples: {len(samples)}")
                except Exception as wave_error:
                    logger.error(f"Error creating WAV file: {str(wave_error)}")
                    # Tente uma abordagem alternativa mais simples
                    with open(temp_file_path, 'wb') as f:
                        f.write(audio_data)
                    logger.warning("Fell back to direct file write without WAV conversion")
            else:
                # Se já estiver em formato WAV, escrever diretamente
                with open(temp_file_path, 'wb') as f:
                    f.write(audio_data)
                logger.warning(f"Wrote existing WAV file directly: {temp_file_path}")
            
            # Validar se o arquivo foi criado corretamente
            if os.path.exists(temp_file_path):
                file_size = os.path.getsize(temp_file_path)
                logger.warning(f"Temporary file created: {temp_file_path}, size: {file_size} bytes")
                
                # Verificar se o tamanho é razoável
                if file_size < 1000:
                    logger.warning(f"Warning: Temporary file size is suspiciously small: {file_size} bytes")
                
                # Validação adicional - tentar abrir e ler o arquivo WAV
                try:
                    with wave.open(temp_file_path, 'rb') as wf:
                        channels = wf.getnchannels()
                        sample_width = wf.getsampwidth()
                        frame_rate = wf.getframerate()
                        n_frames = wf.getnframes()
                        
                        logger.warning(f"WAV file validated - channels: {channels}, sample width: {sample_width}, "
                                     f"rate: {frame_rate}, frames: {n_frames}")
                        
                        # Se o arquivo estiver vazio ou tiver parâmetros inválidos, tente recriar
                        if n_frames == 0 or channels == 0 or sample_width == 0 or frame_rate == 0:
                            logger.warning("Invalid WAV file parameters detected, attempting to recreate")
                            # Tentar recriar o arquivo com um exemplo mínimo válido se necessário
                            if len(audio_data) < 1000:
                                # Criar um sinal de teste mínimo se os dados forem muito pequenos
                                duration_sec = 1.0  # 1 segundo
                                test_samples = np.linspace(0, duration_sec, int(16000 * duration_sec))
                                test_audio = np.sin(2 * np.pi * 440 * test_samples)  # 440 Hz tone
                                test_audio = (test_audio * 32767).astype(np.int16)
                                
                                with wave.open(temp_file_path, 'wb') as wf_new:
                                    wf_new.setnchannels(1)
                                    wf_new.setsampwidth(2)
                                    wf_new.setframerate(16000)
                                    wf_new.writeframes(test_audio.tobytes())
                                
                                logger.warning("Created test tone WAV file as fallback")
                except Exception as wave_error:
                    logger.error(f"Error validating WAV file: {str(wave_error)}")
            else:
                logger.error(f"Failed to create temporary file at {temp_file_path}")
            
            return temp_file_path
            
        except Exception as e:
            logger.error(f"Error creating temporary file: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def _remove_temp_file(self, temp_file):
        """Remove the temporary WAV file
        
        Args:
            temp_file (str): Path to the temporary file
        """
        import os
        import time
        
        # Tenta remover o arquivo com mais tentativas
        max_attempts = 5  # Increased from 3 to 5
        for attempt in range(max_attempts):
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.warning(f"Arquivo temporário removido com sucesso: {temp_file}")
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    logger.warning(f"Tentativa {attempt+1} falhou ao remover arquivo temporário: {str(e)}")
                    time.sleep(1.0)  # Increased from 0.5 to 1.0 seconds
                else:
                    logger.warning(f"Erro ao remover arquivo temporário: {str(e)}")
                    logger.warning(f"Registrando arquivo para remoção tardia: {temp_file}")
                    self._register_for_delayed_removal(temp_file)
                    return False
                    
    def _register_for_delayed_removal(self, temp_file):
        """Register a file for delayed removal
        
        Args:
            temp_file (str): Path to the file to remove later
        """
        import threading
        import time
        import os
        
        def delayed_remove():
            # Espera um tempo maior antes de tentar remover
            for attempt in range(8):  # Increased from 5 to 8 attempts
                delay = 2 + attempt  # Progressively longer delays: 2, 3, 4, 5, 6, 7, 8, 9 seconds
                time.sleep(delay)
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        logger.warning(f"Arquivo temporário removido com sucesso (remoção tardia): {temp_file}")
                        return
                    else:
                        # File doesn't exist anymore, consider it removed
                        return
                except Exception as e:
                    logger.warning(f"Tentativa {attempt+1}: Ainda não foi possível remover o arquivo: {str(e)}")
            
            # Se ainda não conseguiu remover, adiciona à lista de arquivos a serem limpos na próxima execução
            self._add_to_cleanup_list(temp_file)
        
        # Inicia thread para remoção tardia
        threading.Thread(target=delayed_remove, daemon=True).start()
        
    def _add_to_cleanup_list(self, temp_file):
        """Adiciona um arquivo temporário à lista de arquivos a serem limpos posteriormente
        
        Args:
            temp_file (str): Caminho para o arquivo temporário
        """
        if not temp_file or not os.path.exists(temp_file):
            return
            
        import json
        
        temp_dir = self.custom_temp_dir or tempfile.gettempdir()
        cleanup_file = os.path.join(temp_dir, "cleanup_list.json")
        
        cleanup_list = []
        if os.path.exists(cleanup_file):
            try:
                with open(cleanup_file, 'r') as f:
                    cleanup_list = json.load(f)
            except:
                cleanup_list = []
        
        # Adiciona arquivo à lista se ainda não estiver
        if temp_file not in cleanup_list:
            cleanup_list.append(temp_file)
        
        # Salva lista atualizada
        try:
            with open(cleanup_file, 'w') as f:
                json.dump(cleanup_list, f)
        except Exception as e:
            logger.error(f"Erro ao salvar lista de limpeza: {str(e)}")
            
    def _get_temp_directory(self):
        """Retorna o diretório temporário para armazenar arquivos de áudio
        
        Returns:
            str: Caminho para o diretório temporário
        """
        if self.custom_temp_dir and os.path.exists(self.custom_temp_dir):
            return self.custom_temp_dir
        else:
            return tempfile.gettempdir()
            
    def _cleanup_old_files(self):
        """Clean up old temporary files registered for deletion
        """
        import os
        import json
        import glob
        import time
        
        temp_dir = self._get_temp_directory()
        cleanup_file = os.path.join(temp_dir, "cleanup_list.json")
        
        # Limpa arquivos registrados para remoção
        if os.path.exists(cleanup_file):
            try:
                with open(cleanup_file, 'r') as f:
                    cleanup_list = json.load(f)
                
                remaining_files = []
                for file_path in cleanup_list:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.warning(f"Arquivo temporário removido durante limpeza: {file_path}")
                        else:
                            logger.warning(f"Arquivo temporário já não existe: {file_path}")
                    except Exception as e:
                        logger.warning(f"Não foi possível remover arquivo durante limpeza: {file_path} - {str(e)}")
                        remaining_files.append(file_path)
                
                # Atualiza a lista com arquivos que ainda não puderam ser removidos
                with open(cleanup_file, 'w') as f:
                    json.dump(remaining_files, f)
            except Exception as e:
                logger.error(f"Erro durante processo de limpeza: {str(e)}")
        
        # Limpa arquivos temporários antigos (mais de 1 dia)
        try:
            current_time = time.time()
            one_day_ago = current_time - (24 * 60 * 60)
            
            # Busca todos os arquivos WAV no diretório temporário
            for temp_file in glob.glob(os.path.join(temp_dir, "azure_audio_*.wav")):
                try:
                    # Verifica a data de modificação
                    file_mod_time = os.path.getmtime(temp_file)
                    if file_mod_time < one_day_ago:
                        os.remove(temp_file)
                        logger.warning(f"Arquivo temporário antigo removido: {temp_file}")
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo temporário antigo: {temp_file} - {str(e)}")
        except Exception as e:
            logger.error(f"Erro durante limpeza de arquivos antigos: {str(e)}")
    
    def recognize_speech(self, audio_data, language=None):
        """
        Recognize speech from audio data
        
        Args:
            audio_data (bytes or str): Audio data in bytes format or path to audio file
            language (str): Language code (e.g., "en-US")
            
        Returns:
            str: Recognized text
        """
        if not self.api_key or not self.region:
            logger.error("Azure credentials not configured")
            return ""
        
        # Use o idioma fornecido ou o padrão se não especificado
        if language is None:
            language = self.config_manager.get_value("recognition", "language", "pt-PT")
        
        # Verificar se é necessário reiniciar os recursos
        self._check_and_reset_resources()
        
        temp_filename = None
        
        try:
            # Medir o tempo de processamento
            start_time = time.time()
            
            # Incrementar o contador de reconhecimentos
            self.recognition_count += 1
            
            # Verifique se audio_data é um caminho para arquivo ou dados binários
            is_file_path = isinstance(audio_data, str) and os.path.exists(audio_data)
            
            if is_file_path:
                # É um caminho para arquivo, verificar o tamanho
                file_size = os.path.getsize(audio_data)
                if file_size < 2000:  # Menos de 2KB
                    logger.warning(f"Audio file is too small: {file_size} bytes")
                    # Tentar criar um arquivo WAV válido mínimo
                    self._create_minimum_valid_wav(audio_data)
                    
                temp_filename = audio_data
                logger.warning(f"Using existing audio file: {temp_filename}, size: {file_size} bytes")
                
                # Verificar se é um arquivo WAV válido
                try:
                    with wave.open(temp_filename, 'rb') as wf:
                        n_channels = wf.getnchannels()
                        sample_width = wf.getsampwidth()
                        frame_rate = wf.getframerate()
                        n_frames = wf.getnframes()
                        duration = n_frames / frame_rate
                        
                        logger.warning(f"WAV file info: channels={n_channels}, width={sample_width}, " +
                                    f"rate={frame_rate}, frames={n_frames}, duration={duration:.2f}s")
                        
                        # Verificar se o arquivo tem conteúdo suficiente
                        if n_frames < 8000:  # Menos de 0.5 segundo a 16kHz
                            logger.warning(f"WAV file has very few frames: {n_frames}, padding with silence")
                            self._pad_wav_file(temp_filename)
                except Exception as wav_error:
                    logger.error(f"Error checking WAV file: {str(wav_error)}")
                    # Se não for um WAV válido, criar um novo
                    with open(temp_filename, 'rb') as f:
                        file_content = f.read()
                    temp_filename = self._create_temp_file(file_content)
            else:
                # São dados binários, verificar o tamanho
                audio_size = len(audio_data) if audio_data else 0
                if audio_size < 2000:  # Menos de 2KB
                    logger.warning(f"Audio data too small ({audio_size} bytes), might not be enough for recognition")
                    # Adicionar dados mínimos se necessário para satisfazer os requisitos do Azure
                    audio_data = self._ensure_minimum_audio_size(audio_data)
                
                # Aplicar pré-processamento para melhorar a qualidade do áudio
                logger.warning("Aplicando pré-processamento avançado para melhorar qualidade do áudio")
                processed_audio = self._preprocess_audio(audio_data)
                
                # Criar arquivo temporário
                temp_filename = self._create_temp_file(processed_audio)
            
            # Verifica a validade do caminho
            sanitized_path = self._sanitize_path(temp_filename)
            
            # Verificar novamente se o arquivo existe e tem conteúdo
            if not os.path.exists(sanitized_path):
                logger.error(f"Temporary file does not exist: {sanitized_path}")
                return ""
                
            file_size = os.path.getsize(sanitized_path)
            logger.warning(f"Final audio file size: {file_size} bytes")
            
            # Tentar múltiplas abordagens para reconhecimento
            recognized_text = ""
            
            # Abordagem 1: Contexto isolado
            logger.warning("Trying recognition in isolated context...")
            recognized_text = self._recognize_in_isolated_context(sanitized_path, language)
            
            # Abordagem 2: Método direto
            if not recognized_text:
                logger.warning("Isolated context failed, trying direct method...")
                try:
                    direct_config = speechsdk.SpeechConfig(subscription=self.api_key, region=self.region)
                    direct_config.speech_recognition_language = language
                    direct_config.enable_dictation()  # Melhor para reconhecimento de fala natural
                    
                    audio_config = speechsdk.audio.AudioConfig(filename=sanitized_path)
                    recognizer = speechsdk.SpeechRecognizer(speech_config=direct_config, audio_config=audio_config)
                    
                    # Realizar reconhecimento direto
                    result = recognizer.recognize_once()
                    
                    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                        recognized_text = result.text
                        logger.warning(f"Direct recognition successful: '{recognized_text}'")
                    else:
                        logger.warning(f"Direct recognition failed with reason: {result.reason}")
                        
                except Exception as direct_error:
                    logger.error(f"Direct recognition error: {str(direct_error)}")
            
            # Abordagem 3: Reconhecimento contínuo
            if not recognized_text:
                logger.warning("Direct method failed, trying continuous recognition...")
                try:
                    # Criar novo reconhecedor com configuração para reconhecimento contínuo
                    continuous_config = speechsdk.SpeechConfig(subscription=self.api_key, region=self.region)
                    continuous_config.speech_recognition_language = language
                    continuous_config.enable_dictation()
                    
                    audio_config = speechsdk.audio.AudioConfig(filename=sanitized_path)
                    recognizer = speechsdk.SpeechRecognizer(speech_config=continuous_config, audio_config=audio_config)
                    
                    # Usar eventos para capturar resultados
                    done = False
                    all_results = []
                    
                    def handle_final_result(evt):
                        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                            all_results.append(evt.result.text)
                    
                    def stop_cb(evt):
                        nonlocal done
                        done = True
                    
                    # Conectar manipuladores de eventos
                    recognizer.recognized.connect(handle_final_result)
                    recognizer.session_stopped.connect(stop_cb)
                    recognizer.canceled.connect(stop_cb)
                    
                    # Iniciar reconhecimento contínuo
                    recognizer.start_continuous_recognition()
                    
                    # Esperar até que o processamento termine (máximo 10 segundos)
                    for _ in range(20):  # 20 x 0.5s = 10s
                        if done:
                            break
                        time.sleep(0.5)
                    
                    # Parar reconhecimento
                    recognizer.stop_continuous_recognition()
                    
                    # Combinar resultados
                    if all_results:
                        recognized_text = " ".join(all_results)
                        logger.warning(f"Continuous recognition successful: '{recognized_text}'")
                    
                except Exception as continuous_error:
                    logger.error(f"Continuous recognition error: {str(continuous_error)}")
            
            # Aplicar pós-processamento ao texto reconhecido
            if recognized_text:
                processed_text = self._postprocess_text(recognized_text)
                
                # Se o texto foi modificado pelo pós-processamento, registrar
                if processed_text != recognized_text:
                    logger.warning(f"Text corrected by post-processing: '{recognized_text}' -> '{processed_text}'")
                
                recognized_text = processed_text
            
            # Registrar tempo total
            end_time = time.time()
            logger.warning(f"Total recognition time: {end_time - start_time:.3f} seconds")
            
            # Forçar coleta de lixo para garantir que todos os recursos sejam liberados
            import gc
            gc.collect()
            
            return recognized_text
            
        except Exception as e:
            logger.error(f"General error in speech recognition: {str(e)}")
            logger.error(traceback.format_exc())
            return ""
        finally:
            # Cleanup: remove o arquivo temporário apenas se foi criado por este método
            # e não é o arquivo de entrada original
            if temp_filename and not is_file_path and os.path.exists(temp_filename):
                try:
                    self._remove_temp_file(temp_filename)
                except Exception as cleanup_error:
                    logger.warning(f"Error cleaning up temp file: {str(cleanup_error)}")

    def _ensure_minimum_audio_size(self, audio_data):
        """Garante que os dados de áudio tenham um tamanho mínimo
        
        Args:
            audio_data (bytes): Dados de áudio originais
            
        Returns:
            bytes: Dados de áudio com tamanho mínimo garantido
        """
        if not audio_data:
            logger.warning("Audio data is empty, creating minimal audio data")
            # Criar 1 segundo de silêncio a 16kHz, 16 bits, mono
            silence = np.zeros(16000, dtype=np.int16)
            return silence.tobytes()
            
        # Se os dados já são maiores que o mínimo, retornar sem modificar
        if len(audio_data) >= 2000:
            return audio_data
            
        try:
            # Converter bytes para array numpy
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calcular quantas amostras precisamos adicionar para ter pelo menos 1 segundo
            samples_needed = max(0, 16000 - len(samples))
            
            if samples_needed > 0:
                # Adicionar silêncio ao final
                silence = np.zeros(samples_needed, dtype=np.int16)
                padded_samples = np.concatenate([samples, silence])
                logger.warning(f"Padded audio data from {len(samples)} to {len(padded_samples)} samples")
                return padded_samples.tobytes()
            else:
                return audio_data
                
        except Exception as e:
            logger.error(f"Error ensuring minimum audio size: {str(e)}")
            # Em caso de erro, retornar os dados originais
            return audio_data
            
    def _pad_wav_file(self, wav_path, min_duration_sec=1.0):
        """Adiciona silêncio ao final de um arquivo WAV para garantir duração mínima
        
        Args:
            wav_path (str): Caminho para o arquivo WAV
            min_duration_sec (float): Duração mínima desejada em segundos
        """
        try:
            # Ler o arquivo WAV original
            with wave.open(wav_path, 'rb') as wf:
                n_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frame_rate = wf.getframerate()
                n_frames = wf.getnframes()
                original_data = wf.readframes(n_frames)
                
                # Calcular duração atual e quantos frames precisamos adicionar
                current_duration = n_frames / frame_rate
                frames_needed = int((min_duration_sec - current_duration) * frame_rate)
                
                if frames_needed <= 0:
                    logger.info(f"WAV file already has sufficient duration: {current_duration:.2f}s")
                    return
                    
                # Criar silêncio para adicionar
                silence = np.zeros(frames_needed * n_channels, dtype=np.int16)
                silence_data = silence.tobytes()
                
                # Escrever novo arquivo WAV com o silêncio adicionado
                with wave.open(wav_path, 'wb') as new_wf:
                    new_wf.setnchannels(n_channels)
                    new_wf.setsampwidth(sample_width)
                    new_wf.setframerate(frame_rate)
                    new_wf.writeframes(original_data)
                    new_wf.writeframes(silence_data)
                    
                # Verificar o tamanho do novo arquivo    
                new_size = os.path.getsize(wav_path)
                logger.warning(f"Padded WAV file from {current_duration:.2f}s to {min_duration_sec:.2f}s, new size: {new_size} bytes")
                
        except Exception as e:
            logger.error(f"Error padding WAV file: {str(e)}")
            
    def _create_minimum_valid_wav(self, output_path, duration_sec=1.0):
        """Cria um arquivo WAV mínimo válido com um tom de teste
        
        Args:
            output_path (str): Caminho onde salvar o arquivo WAV
            duration_sec (float): Duração do arquivo em segundos
        """
        try:
            # Parâmetros para o arquivo WAV
            sample_rate = 16000
            n_channels = 1
            sample_width = 2  # 16 bits
            
            # Criar um tom de teste (440 Hz)
            t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
            audio = np.sin(2 * np.pi * 440 * t)
            audio = (audio * 32767).astype(np.int16)
            
            # Escrever arquivo WAV
            with wave.open(output_path, 'wb') as wf:
                wf.setnchannels(n_channels)
                wf.setsampwidth(sample_width)
                wf.setframerate(sample_rate)
                wf.writeframes(audio.tobytes())
                
            logger.warning(f"Created minimum valid WAV file at {output_path}, size: {os.path.getsize(output_path)} bytes")
            
        except Exception as e:
            logger.error(f"Error creating minimum valid WAV file: {str(e)}")
    
    def _check_and_reset_resources(self):
        """Verifica se é necessário reiniciar os recursos do Azure Speech para evitar problemas de memória"""
        current_time = time.time()
        time_since_last_reset = current_time - self.last_reset_time
        
        # Reiniciar se excedeu o número máximo de reconhecimentos ou o tempo limite
        if (self.recognition_count >= self.max_recognitions_before_reset or 
            time_since_last_reset >= self.reset_time_threshold):
            
            logger.warning(f"Reiniciando recursos do Azure Speech após {self.recognition_count} reconhecimentos " +
                          f"ou {time_since_last_reset:.1f} segundos desde o último reset")
            
            # Forçar coleta de lixo para liberar recursos
            import gc
            gc.collect()
            
            # Reinicializar o speech config
            self._initialize_speech_config()
            
            # Limpar diretório temporário
            self._cleanup_temp_dir()
            
            # Resetar contadores
            self.recognition_count = 0
            self.last_reset_time = current_time
            
            logger.warning("Recursos do Azure Speech reiniciados com sucesso")

    def _cleanup_temp_dir(self):
        """Limpa arquivos temporários antigos para evitar acúmulo de lixo"""
        try:
            if not self.custom_temp_dir or not os.path.exists(self.custom_temp_dir):
                return
                
            # Obter lista de arquivos no diretório temporário
            files = os.listdir(self.custom_temp_dir)
            current_time = time.time()
            count_removed = 0
            
            # Remover arquivos temporários com mais de 1 hora
            for file in files:
                if file.startswith("azure_audio_") and file.endswith(".wav"):
                    file_path = os.path.join(self.custom_temp_dir, file)
                    try:
                        # Verificar idade do arquivo
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > 3600:  # 1 hora em segundos
                            os.unlink(file_path)
                            count_removed += 1
                    except Exception as e:
                        logger.warning(f"Erro ao remover arquivo temporário antigo {file}: {str(e)}")
            
            if count_removed > 0:
                logger.warning(f"Removidos {count_removed} arquivos temporários antigos")
                
        except Exception as e:
            logger.warning(f"Erro ao limpar diretório temporário: {str(e)}")

    def _preprocess_audio(self, audio_bytes, sample_width=2, channels=1, rate=16000):
        """Pré-processa o áudio para melhorar a qualidade de reconhecimento.
        
        Args:
            audio_bytes (bytes): Dados do áudio em bytes
            sample_width (int): Largura da amostra em bytes (geralmente 2 para 16-bit)
            channels (int): Número de canais (1 para mono, 2 para estéreo)
            rate (int): Taxa de amostragem em Hz
            
        Returns:
            bytes: Áudio processado em bytes
        """
        start_time = time.time()
        logger.info("Iniciando pré-processamento de áudio SUPER AGRESSIVO")
        
        try:
            # Converter bytes para numpy array
            if not audio_bytes:
                logger.error("Dados de áudio vazios recebidos para pré-processamento")
                return audio_bytes
                
            # Converter para numpy array
            samples = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Obter estatísticas originais
            original_rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
            original_peak = np.max(np.abs(samples))
            original_duration = len(samples) / rate
            
            logger.info(f"Estatísticas do áudio original: Duração={original_duration:.2f}s, RMS={original_rms:.2f}, Pico={original_peak}")
            
            # Verificar clipping no áudio original
            max_value = 2**(8 * sample_width - 1) - 1  # Valor máximo para áudio (e.g., 32767 para 16-bit)
            clip_threshold = 0.95 * max_value  # 95% do máximo para detectar clipping
            clipped_samples = np.sum(np.abs(samples) > clip_threshold)
            clipped_percentage = 100 * clipped_samples / len(samples) if len(samples) > 0 else 0
            
            logger.info(f"Verificação de clipping: {clipped_percentage:.2f}% das amostras acima de {clip_threshold}")
            
            # Detecção e remoção de silêncio - VERSÃO SUPER AGRESSIVA
            # Usar um tamanho de segmento muito menor para detecção mais precisa
            segment_duration_ms = 5  # 5ms por segmento para detecção mais precisa
            samples_per_segment = int(rate * segment_duration_ms / 1000)
            
            # Definir um threshold dinâmico mais baixo para detectar mais fala
            # Usar um valor menor para captar até mesmo fala muito baixa
            silence_threshold = max(100, min(1000, original_rms * 0.1))  # Threshold mais baixo (10% do RMS)
            logger.info(f"Threshold de silêncio definido para {silence_threshold} - VALOR BAIXO")
            
            # Dividir em segmentos e analisar cada um
            num_segments = len(samples) // samples_per_segment if samples_per_segment > 0 else 0
            segment_volumes = []
            is_silent = []
            
            for i in range(num_segments):
                start = i * samples_per_segment
                end = start + samples_per_segment
                segment = samples[start:end]
                segment_rms = np.sqrt(np.mean(segment.astype(np.float32)**2))
                segment_volumes.append(segment_rms)
                is_silent.append(segment_rms < silence_threshold)
            
            # Contar segmentos não silenciosos
            non_silent_segments = sum(not s for s in is_silent)
            non_silent_percentage = 100 * non_silent_segments / num_segments if num_segments > 0 else 0
            
            logger.info(f"Análise de segmentos: Total={num_segments}, " +
                      f"Não-silenciosos={non_silent_segments} ({non_silent_percentage:.1f}%)")
            
            # Detectar e remover silêncio prolongado no início - MAIS AGRESSIVO
            start_index = 0
            if num_segments > 0:
                # Encontrar o primeiro segmento não silencioso
                for i in range(num_segments):
                    if not is_silent[i]:
                        # Voltar menos para cortar mais do início silencioso
                        start_index = max(0, i * samples_per_segment - int(0.05 * rate))  # Apenas 50ms antes
                    break
            
                # Se todo o áudio for silencioso, aplicar um ganho muito maior
                if start_index == 0 and all(is_silent):
                    logger.warning("Todo o áudio parece ser silencioso. Aplicando ganho de emergência MUITO ALTO.")
                    # Aplicar um ganho de emergência extremamente alto
                    samples = (samples.astype(np.float32) * 20.0).astype(np.int16)
                    # Limitar para evitar clipping
                    samples = np.clip(samples, -max_value, max_value)
                
            # Detectar e remover silêncio prolongado no fim - MAIS AGRESSIVO
            end_index = len(samples)
            if num_segments > 0:
                # Encontrar o último segmento não silencioso
                for i in range(num_segments - 1, -1, -1):
                    if not is_silent[i]:
                        # Estender menos para cortar mais do final silencioso
                        end_index = min(len(samples), (i + 1) * samples_per_segment + int(0.05 * rate))  # Apenas 50ms depois
                    break
            
            # Verificar se temos fala suficiente após remover silêncio
            if end_index - start_index < 0.3 * rate:  # Menos de 0.3 segundos de fala (reduzido)
                logger.warning("Áudio tem muito pouca fala detectada após remoção de silêncio. AINDA APLICANDO CORTES.")
                # Mesmo com pouca fala, vamos cortar silêncio excessivo
                if start_index > 0.5 * rate:  # Se o início for mais de 0.5s
                    start_index = max(0, int(0.1 * rate))  # Manter apenas 100ms do início
                if len(samples) - end_index > 0.5 * rate:  # Se o final for mais de 0.5s
                    end_index = min(len(samples), len(samples) - int(0.1 * rate))  # Manter apenas 100ms do final
            else:
                logger.info(f"Removendo silêncio: {start_index/rate:.2f}s do início e {(len(samples)-end_index)/rate:.2f}s do fim")
            
            # Aplicar corte para remover silêncio excessivo
            samples = samples[start_index:end_index]
            
            # GANHO AGRESSIVO: Sempre aplicar um ganho mínimo, mesmo se o áudio já tiver fala detectada
            # Isto ajuda a prevenir problemas de silêncio inicial detectado pelo Azure
            min_gain = 2.0  # Ganho mínimo aplicado sempre
            
            # Se o áudio tiver poucos segmentos não silenciosos, aumentar o ganho ainda mais
            if non_silent_percentage < 50:
                # Aplicar ganho inversamente proporcional à quantidade de fala detectada
                gain_factor = max(8.0, 20.0 * (50 / max(1, non_silent_percentage)))
                gain_factor = min(gain_factor, 30.0)  # Limitar o ganho máximo a 30x (aumentado)
                
                logger.info(f"Áudio com pouca fala ({non_silent_percentage:.1f}%). Aplicando ganho SUPER ALTO de {gain_factor:.1f}x")
            else:
                # Mesmo com fala suficiente, aplicar um ganho considerável
                gain_factor = min_gain
                logger.info(f"Aplicando ganho mínimo de {gain_factor:.1f}x para garantir detecção")
                
            # Aplicar ganho com cuidado para evitar clipping
            samples = np.clip(
                (samples.astype(np.float32) * gain_factor).astype(np.int16),
                -max_value, max_value
            )
            
            # Aplicar filtragem de passagem de banda para focar nas frequências da voz humana
            if len(samples) > 0:
                try:
                    from scipy import signal
                    
                    # Definir frequências para a voz humana (300-3400 Hz)
                    nyquist = 0.5 * rate
                    low = 300.0 / nyquist
                    high = 3400.0 / nyquist
                    
                    # Criar e aplicar o filtro
                    b, a = signal.butter(4, [low, high], btype='band')
                    samples = signal.filtfilt(b, a, samples.astype(np.float32)).astype(np.int16)
                    
                    logger.info("Filtro passa-banda aplicado (300-3400 Hz)")
                except Exception as filter_err:
                    logger.warning(f"Erro ao aplicar filtro passa-banda: {str(filter_err)}")
            
            # Normalizar volume - abordagem SUPER agressiva
            if len(samples) > 0:
                # Normalizar para 80% do máximo (aumentado de 70%)
                target_level = 0.8 * max_value
                current_max = np.max(np.abs(samples))
                
                if current_max > 0:
                    # Normalizar para aumentar o volume
                    gain = target_level / current_max
                    
                    # Limitar o ganho máximo para evitar amplificar muito ruído
                    # Aumentado para permitir ganhos maiores
                    max_gain = 10.0  # Dobrado de 5.0
                    
                    # Se o áudio tiver pouca fala, permitir ganho ainda maior
                    if non_silent_percentage < 30:
                        max_gain = 20.0  # Dobrado de 10.0
                    
                    if gain > max_gain:
                        logger.warning(f"Ganho limitado de {gain:.1f}x para {max_gain:.1f}x para evitar excesso de ruído")
                        gain = max_gain
                    
                    # Aplicar ganho com normalização
                    samples = np.clip(
                        (samples.astype(np.float32) * gain).astype(np.int16),
                        -max_value, max_value
                    )
                    
                    logger.info(f"Ganho de normalização aplicado: {gain:.2f}x")
            
            # Adicionar menos silêncio ao início e fim (apenas o suficiente para evitar cortes bruscos)
            silence_padding = np.zeros(int(0.05 * rate), dtype=np.int16)  # Reduzido para 50ms (era 100ms)
            samples = np.concatenate([silence_padding, samples, silence_padding])
            
            # Adicionar um pequeno "tic" no início do áudio (ruído controlado)
            # Isto pode ajudar o Azure a detectar o início do áudio e evitar timeout de silêncio inicial
            tick_length = int(0.01 * rate)  # 10ms
            tick_amplitude = 0.1 * max_value  # 10% do máximo
            tick = np.sin(np.linspace(0, np.pi, tick_length)) * tick_amplitude
            tick = tick.astype(np.int16)
            
            # Inserir o "tic" no início do áudio (após o padding de silêncio)
            if len(silence_padding) > 0 and len(tick) > 0:
                start_pos = len(silence_padding)
                end_pos = start_pos + len(tick)
                if end_pos <= len(samples):
                    samples[start_pos:end_pos] = tick
                    logger.info("Adicionado marcador sonoro no início para ajudar detecção")
            
            # Estatísticas finais após processamento
            final_rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
            final_peak = np.max(np.abs(samples))
            final_duration = len(samples) / rate
            
            # Verificar clipping no áudio final
            clipped_samples_final = np.sum(np.abs(samples) > clip_threshold)
            clipped_percentage_final = 100 * clipped_samples_final / len(samples) if len(samples) > 0 else 0
            
            logger.info(f"Estatísticas do áudio processado: " +
                      f"Duração={final_duration:.2f}s, RMS={final_rms:.2f}, " +
                      f"Pico={final_peak}, Clipping={clipped_percentage_final:.2f}%")
            
            # Verificar se o pré-processamento melhorou o áudio
            improvement = f"Volume: {final_rms/original_rms:.1f}x, " + \
                          f"Duração: {final_duration/original_duration:.1f}x"
            logger.info(f"Melhoria geral após pré-processamento: {improvement}")
            
            # Converter numpy array de volta para bytes
            processed_audio = samples.tobytes()
            
            end_time = time.time()
            logger.info(f"Pré-processamento de áudio SUPER AGRESSIVO concluído em {end_time - start_time:.2f}s")
            
            return processed_audio
            
        except Exception as e:
            logger.error(f"Erro no pré-processamento de áudio: {str(e)}")
            logger.error(traceback.format_exc())
            # Em caso de erro, retornar o áudio original
            return audio_bytes

    def _postprocess_text(self, text):
        """Aplica pós-processamento ao texto reconhecido para melhorar a qualidade.
        
        Args:
            text (str): Texto reconhecido original
            
        Returns:
            str: Texto processado
        """
        if not text:
            return ""
        
        try:
            # Remover espaços extras
            processed_text = " ".join(text.split())
            
            # Remover pontuação dupla
            processed_text = re.sub(r'([.,!?])\1+', r'\1', processed_text)
            
            # Corrigir espaços antes de pontuação
            processed_text = re.sub(r'\s+([.,!?:;])', r'\1', processed_text)
            
            # Garantir que a primeira letra da frase seja maiúscula
            if processed_text and len(processed_text) > 0:
                processed_text = processed_text[0].upper() + processed_text[1:]
            
            # Remover aspas que possam estar incorretas
            processed_text = processed_text.replace('"', "").replace("'", "")
            
            # Remover texto entre colchetes ou parênteses (geralmente metadados)
            processed_text = re.sub(r'\[.*?\]|\(.*?\)', '', processed_text)
            
            # Corrigir termos específicos e abreviaturas comuns
            common_corrections = {
                "nao": "não",
                "e ": "é ",
                " e ": " é ",
                "tbm": "também",
                "vc": "você",
                "pq": "porque",
                "msm": "mesmo"
            }
            
            # Aplicar correções
            for wrong, correct in common_corrections.items():
                # Usar regex para encontrar a palavra inteira
                processed_text = re.sub(fr'\b{wrong}\b', correct, processed_text, flags=re.IGNORECASE)
            
            # Se o processamento removeu muito texto, manter o original
            if text and len(processed_text) < len(text) * 0.7:
                logger.warning(f"Pós-processamento removeu muito texto. Mantendo original.")
                return text
                
            return processed_text
            
        except Exception as e:
            logger.error(f"Erro no pós-processamento de texto: {str(e)}")
            # Em caso de erro, retornar o texto original
            return text
            
    def _create_default_config(self, language="pt-PT"):
        """Cria uma configuração padrão para reconhecimento de fala
        
        Args:
            language (str): Código do idioma a ser usado para reconhecimento
            
        Returns:
            speechsdk.SpeechConfig: Configuração para o Azure Speech SDK
        """
        try:
            # Criar configuração básica
            speech_config = speechsdk.SpeechConfig(subscription=self.api_key, region=self.region)
            
            # Definir idioma
            speech_config.speech_recognition_language = language
            
            # Configurações padrão
            speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, 
                "3000"  # 3 segundos de silêncio inicial
            )
            
            speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, 
                "1000"  # 1 segundo de silêncio final
            )
            
            # Habilitar ditado para melhorar reconhecimento
            speech_config.enable_dictation()
            
            logger.warning(f"Configuração padrão criada para {language}")
            return speech_config
            
        except Exception as e:
            logger.error(f"Erro ao criar configuração padrão: {str(e)}")
            logger.error(traceback.format_exc())
            # Em caso de erro, retornar None
            return None

    def _select_best_result(self, results, language):
        """Seleciona o melhor resultado de reconhecimento entre vários modos
        
        Args:
            results (list): Lista de resultados de texto reconhecidos
            language (str): Idioma usado para reconhecimento
            
        Returns:
            str: O melhor texto reconhecido ou string vazia
        """
        try:
            # Validar os resultados de entrada
            if not results:
                logger.warning("Nenhum resultado para selecionar")
                return ""
            
            # Registrar todos os resultados para análise
            logger.warning(f"Analisando {len(results)} resultados para seleção do melhor:")
            for i, res in enumerate(results):
                text = res if res else "<vazio>"
                logger.warning(f"Resultado {i+1}: '{text}'")
                
            # Se só há um resultado, retorná-lo (mesmo se for vazio)
            if len(results) == 1:
                result = results[0]
                if result:
                    logger.warning(f"Retornando único resultado disponível: '{result}'")
                    return result
                else:
                    logger.warning("Único resultado disponível está vazio")
                return ""
            
            # Filtrar resultados vazios ou que contenham apenas espaços/pontuação
            non_empty_results = []
            for res in results:
                if not res:
                    continue
                    
                # Remover espaços e pontuação e verificar se ainda sobra algo
                stripped = ''.join(c for c in res if c.isalnum())
                if stripped:
                    non_empty_results.append(res)
                    
            # Se não há resultados não-vazios, retornar string vazia
            if not non_empty_results:
                logger.warning("Todos os resultados estão vazios ou contêm apenas pontuação/espaços")
                return ""
                
            # Se sobrou apenas um resultado não-vazio, retorná-lo
            if len(non_empty_results) == 1:
                logger.warning(f"Apenas um resultado não-vazio encontrado: '{non_empty_results[0]}'")
                return non_empty_results[0]
                
            # Múltiplos resultados não-vazios, precisamos escolher o melhor
            
            # Dicionário de palavras comuns para diferentes idiomas
            common_words = {
                # Português (frequência maior de uso)
                "pt": [
                    # Artigos e determinantes
                    "o", "a", "os", "as", "um", "uma", "uns", "umas", 
                    # Preposições frequentes
                    "de", "em", "para", "por", "com", "sem", "sobre", "até", "desde",
                    # Conjunções frequentes 
                    "e", "ou", "mas", "porém", "contudo", "todavia", "que", "se",
                    # Pronomes pessoais
                    "eu", "tu", "ele", "ela", "nós", "vós", "eles", "elas", "você", "vocês",
                    # Verbos auxiliares e de alta frequência
                    "é", "são", "está", "estão", "foi", "eram", "será", "tem", "têm", "tinha",
                    # Advérbios comuns
                    "não", "sim", "muito", "pouco", "mais", "menos", "já", "ainda", "sempre",
                    # Outros termos comuns
                    "como", "quando", "onde", "porque", "quem", "qual", "tudo", "nada"
                ],
                
                # Inglês
                "en": [
                    # Artigos e determinantes
                    "the", "a", "an", "this", "that", "these", "those", 
                    # Preposições frequentes
                    "of", "in", "to", "for", "with", "on", "at", "from", "by",
                    # Conjunções frequentes
                    "and", "or", "but", "so", "because", "if", "when", "that",
                    # Pronomes pessoais
                    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
                    # Verbos auxiliares e de alta frequência
                    "is", "are", "was", "were", "will", "be", "have", "has", "had", "do", "does", "did",
                    # Advérbios comuns
                    "not", "very", "too", "just", "now", "then", "here", "there", "always",
                    # Outros termos comuns
                    "what", "where", "when", "why", "who", "how", "all", "some", "any"
                ],
                
                # Espanhol
                "es": [
                    # Artigos e determinantes
                    "el", "la", "los", "las", "un", "una", "unos", "unas", 
                    # Preposições frequentes
                    "de", "en", "para", "por", "con", "sin", "sobre", "hasta", "desde",
                    # Conjunções frequentes
                    "y", "o", "pero", "aunque", "porque", "que", "si",
                    # Pronomes pessoais
                    "yo", "tú", "él", "ella", "nosotros", "vosotros", "ellos", "ellas", "usted", "ustedes",
                    # Verbos auxiliares e de alta frequência
                    "es", "son", "está", "están", "fue", "era", "eran", "será", "tiene", "tienen",
                    # Advérbios comuns
                    "no", "sí", "muy", "poco", "más", "menos", "ya", "todavía", "siempre",
                    # Outros termos comuns
                    "como", "cuando", "donde", "porque", "quién", "cuál", "todo", "nada"
                ]
            }
            
            # Preparar para pontuação
            result_scores = []
            
            # Obter lista de palavras comuns para o idioma atual
            language_prefix = language.split('-')[0].lower()
            word_list = common_words.get(language_prefix, common_words.get("pt", []))
            
            for result in non_empty_results:
                # Iniciar com pontuação base
                score = 10
                
                # Normalizar o texto para avaliação (tudo minúsculo, sem pontuação extra)
                normalized = result.lower()
                
                # Dividir em palavras para análise
                words = normalized.split()
                
                # 1. Comprimento do texto (mais palavras = melhor pontuação)
                words_count = len(words)
                # Pontuação por número de palavras (até 15 pontos)
                length_score = min(words_count * 1.5, 15)
                score += length_score
                
                # 2. Presença de palavras comuns do idioma
                common_word_count = sum(1 for word in words if word in word_list)
                # Recompensar tanto a contagem absoluta quanto a proporção
                if words_count > 0:
                    common_words_ratio = common_word_count / words_count
                    common_words_score = min(common_word_count * 1.0 + common_words_ratio * 10, 20)
                    score += common_words_score
                
                # 3. Penalizar caracteres estranhos ou sequências improváveis
                strange_chars = sum(1 for c in result if not (c.isalnum() or c.isspace() or c in ".,;:!?'\"()-"))
                strange_chars_penalty = min(strange_chars * 1.5, 10)
                score -= strange_chars_penalty
                
                # 4. Análise da estrutura da frase
                # Verificar se começa com letra maiúscula
                if result and result[0].isupper():
                    score += 2
                
                # Verificar se termina com ponto final ou outra pontuação adequada
                if result and result[-1] in ".!?":
                    score += 2
                
                # 5. Consistência de capitalização dentro da frase
                # Palavras iniciadas em maiúscula devem ser nomes próprios ou início de frases
                if words_count > 3:
                    caps_inside = sum(1 for word in words[1:] if word and word[0].isupper())
                    # Muitas maiúsculas no meio da frase pode indicar erro de reconhecimento
                    # Penalizar se mais de 50% das palavras internas estão capitalizadas
                    if caps_inside > (len(words) - 1) * 0.5:
                        score -= 3
                
                # 6. Penalizar repetições anormais de palavras ou caracteres
                # Detectar padrões como "a a a" ou "aaaaa" que podem indicar erro
                prev_word = None
                repetition_count = 0
                
                for word in words:
                    if word == prev_word:
                        repetition_count += 1
                    prev_word = word
                
                # Penalizar repetições excessivas
                if repetition_count > 1:
                    score -= min(repetition_count * 2, 8)
                
                # Verificar repetições de caracteres
                for word in words:
                    if len(word) > 3:
                        for i in range(len(word) - 2):
                            if word[i] == word[i+1] == word[i+2]:
                                score -= 2
                                break
                
                # 7. Bônus para frases que parecem completas
                if words_count >= 3 and result[-1] in ".!?":
                    # Verificar se contém verbo e substantivo (aproximação simples)
                    # Em português, muitos verbos terminam com sufixos específicos
                    has_verb_pattern = any(
                        any(word.endswith(suffix) for suffix in ("ar", "er", "ir", "ou", "am", "em", "a", "e", "i"))
                        for word in words
                    )
                    
                    if has_verb_pattern:
                        score += 5
                
                # Adicionar à lista de pontuações
                result_scores.append((result, score))
                
                # Registrar pontuação para análise
                logger.warning(f"Resultado: '{result}' recebeu pontuação {score:.1f}")
                logger.warning(f"  - Palavras: {words_count}, Comuns: {common_word_count}")
                logger.warning(f"  - Caracteres estranhos: {strange_chars}")
            
            # Ordenar por pontuação (do maior para o menor)
            result_scores.sort(key=lambda x: x[1], reverse=True)
            
            if result_scores:
                best_result = result_scores[0][0]
                best_score = result_scores[0][1]
                
                # Se há grande diferença para o segundo resultado, destacar
                if len(result_scores) > 1:
                    second_score = result_scores[1][1]
                    score_diff = best_score - second_score
                    
                    if score_diff > 10:
                        logger.warning(f"Resultado selecionado com grande margem: {score_diff:.1f} pontos de diferença")
                
                logger.warning(f"Melhor resultado: '{best_result}' com pontuação {best_score:.1f}")
                return best_result
            else:
                logger.warning("Nenhum resultado válido após pontuação")
                return ""
            
        except Exception as e:
            logger.error(f"Erro ao selecionar melhor resultado: {str(e)}")
            # Em caso de erro, retornar o primeiro resultado não-vazio, ou vazio
            for r in results:
                if r and r.strip():
                    return r
            return ""

    def _recognize_in_isolated_context(self, audio_file, language="pt-PT"):
        """Executa reconhecimento de fala em um contexto isolado, utilizando 
        estratégias de fallback e configurações agressivas.
        
        Args:
            audio_file (str): Caminho para o arquivo de áudio
            language (str): Código do idioma
            
        Returns:
            str: Texto reconhecido ou string vazia em caso de falha
        """
        if not os.path.exists(audio_file):
            logger.error(f"Arquivo de áudio não existe: {audio_file}")
            return ""
        
        start_time = time.time()
        logger.warning(f"Iniciando reconhecimento em contexto isolado para {audio_file}")
        
        # Verificar tamanho do arquivo
        try:
            file_size = os.path.getsize(audio_file)
            logger.warning(f"Tamanho do arquivo para reconhecimento: {file_size} bytes")
            
            if file_size < 1000:  # Menos de 1KB
                logger.error(f"Arquivo muito pequeno para reconhecimento efetivo: {file_size} bytes")
                return ""
        except Exception as size_err:
            logger.warning(f"Não foi possível verificar tamanho do arquivo: {str(size_err)}")
            
        # Verificar qualidade de áudio para decidir melhor estratégia
        audio_quality_results = self._check_audio_quality(audio_file)
        
        # Extrair informações do resultado
        audio_quality = audio_quality_results.get('quality', 'normal')
        speech_percentage = audio_quality_results.get('speech_percentage', 0)
        energy_level = audio_quality_results.get('energy_level', 'médio')
        
        logger.warning(f"Qualidade do áudio: {audio_quality} ({speech_percentage:.1f}% de fala, energia {energy_level})")
        
        # Verificar se há fala suficiente
        if speech_percentage < 10:
            logger.warning(f"Porcentagem de fala muito baixa: {speech_percentage:.1f}%. Pode não haver fala significativa.")
            # Continuamos mesmo assim, pois nossos algoritmos de detecção podem não ser perfeitos
        
        # Resultados de todos os modos de reconhecimento
        results = []
        
        # Estratégia progressiva baseada na qualidade do áudio
        try:
            # 1. PRIMEIRA TENTATIVA: Abordagem normal (mais rápida)
            logger.warning("Tentativa 1: Reconhecimento com configuração padrão")
            normal_config = self._create_default_config(language)
            
            # Timeouts menores para áudio de boa qualidade
            normal_timeout = 6 if audio_quality == 'bom' else 8
            
            # Executar reconhecimento padrão
            normal_result = self._try_recognition_with_config(
                audio_file, 
                normal_config, 
                config_name="Padrão", 
                timeout=normal_timeout
            )
            
            if normal_result:
                logger.warning(f"Reconhecimento padrão bem-sucedido: '{normal_result}'")
                results.append(normal_result)
                
                # Se o áudio tem boa qualidade e o resultado parece bom, podemos parar aqui
                if audio_quality == 'bom' and len(normal_result.split()) >= 3:
                    logger.warning("Áudio de boa qualidade com resultado aceitável, finalizando reconhecimento")
                    return normal_result
            else:
                logger.warning("Reconhecimento padrão não retornou resultados")
                # Adicionar string vazia como resultado (para saber que foi tentado)
                results.append("")
            
            # 2. SEGUNDA TENTATIVA: Configuração agressiva 
            #    (Útil para resolver problemas de silêncio e timeout)
            logger.warning("Tentativa 2: Reconhecimento com configuração agressiva")
            try:
                aggressive_config = self._create_aggressive_config(language)
                
                # Verificar se a configuração foi criada corretamente
                if aggressive_config:
                    logger.warning("Configuração agressiva criada com sucesso")
                else:
                    logger.error("Falha ao criar configuração agressiva")
                    aggressive_config = self._create_default_config(language)
                    logger.warning("Usando configuração padrão como fallback para configuração agressiva")
                
                # Usar timeout maior para áudio de baixa qualidade
                aggressive_timeout = 12 if audio_quality == 'ruim' else 8
                
                # Executar reconhecimento com config agressiva
                aggressive_result = self._try_recognition_with_config(
                    audio_file, 
                    aggressive_config, 
                    config_name="Agressivo", 
                    timeout=aggressive_timeout
                )
                
                if aggressive_result:
                    logger.warning(f"Reconhecimento agressivo bem-sucedido: '{aggressive_result}'")
                    results.append(aggressive_result)
                else:
                    logger.warning("Reconhecimento agressivo não retornou resultados")
                    # Adicionar string vazia como resultado
                    results.append("")
            except Exception as aggressive_error:
                logger.error(f"Erro ao executar reconhecimento agressivo: {str(aggressive_error)}")
                logger.error(traceback.format_exc())
            
            # 3. TERCEIRA TENTATIVA: Para áudio de baixa qualidade ou sem resultados até agora,
            #    tentar uma abordagem direta usando a API REST do Azure
            # Verifica se nenhum resultado não-vazio foi obtido
            if not any(r for r in results) or audio_quality == 'ruim':
                logger.warning("Tentativa 3: Reconhecimento via API REST como último recurso")
                
                try:
                    # Esta é uma abordagem alternativa que usa diretamente a API REST do Azure
                    # em vez do SDK, o que pode ser útil em casos difíceis
                    direct_recognition_config = self._create_default_config(language)
                    direct_recognition_config.set_property(
                        speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
                        "1000"  # Timeout menor para o reconhecimento direto
                    )
                    
                    # Criar audio_config para o arquivo
                    audio_config = speechsdk.audio.AudioConfig(filename=audio_file)
                    
                    # Criar reconhecedor para tentativa direta
                    recognizer = speechsdk.SpeechRecognizer(
                        speech_config=direct_recognition_config,
                        audio_config=audio_config
                    )
                    
                    # Usar recognize_once diretamente sem callbacks
                    logger.warning("Executando recognize_once() como tentativa final")
                    result = recognizer.recognize_once()
                    
                    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                        direct_result = result.text
                        logger.warning(f"Reconhecimento direto bem-sucedido: '{direct_result}'")
                        results.append(direct_result)
                    else:
                        reason = result.reason
                        logger.warning(f"Reconhecimento direto falhou com reason={reason}")
                        
                        # Registrar detalhes de cancelamento, se aplicável
                        if reason == speechsdk.ResultReason.Canceled:
                            cancellation = speechsdk.CancellationDetails.from_result(result)
                            cancel_reason = cancellation.reason
                            logger.warning(f"Reconhecimento cancelado: {cancel_reason}")
                            
                            if cancel_reason == speechsdk.CancellationReason.Error:
                                logger.warning(f"Erro de cancelamento: {cancellation.error_details}")
                            
                            # Para timeout de silêncio inicial, podemos tentar uma abordagem ainda mais direta
                            if "silencetimeout" in str(cancellation.error_details).lower():
                                logger.warning("Detectado timeout de silêncio, áudio pode não conter fala")
                        
                        # Adicionar string vazia como resultado
                        results.append("")
                
                except Exception as direct_error:
                    logger.error(f"Erro no reconhecimento direto: {str(direct_error)}")
                    logger.error(traceback.format_exc())
            
            # 4. Selecionar o melhor resultado
            # Filtrar apenas os resultados válidos (strings não vazias)
            valid_results = [r for r in results if r and r.strip()]
            
            # Registrar todos os resultados para depuração
            logger.warning(f"Total de resultados obtidos: {len(results)}, válidos: {len(valid_results)}")
            for i, res in enumerate(results):
                result_text = f"'{res}'" if res else "<vazio>"
                logger.warning(f"  - Resultado {i+1}: {result_text}")
            
            if valid_results:
                # Temos pelo menos um resultado válido, usar o método de seleção
                best_result = self._select_best_result(valid_results, language)
                end_time = time.time()
                logger.warning(f"Reconhecimento em contexto isolado concluído em {end_time - start_time:.2f}s")
                return best_result
            elif results:
                # Temos resultados, mas todos são vazios
                end_time = time.time()
                logger.warning(f"Todos os resultados estão vazios após {end_time - start_time:.2f}s de tentativas")
                return ""
            else:
                # Nenhum resultado foi obtido
                logger.warning("Nenhum resultado obtido em qualquer tentativa de reconhecimento")
                end_time = time.time()
                logger.warning(f"Reconhecimento em contexto isolado falhou após {end_time - start_time:.2f}s")
                return ""
                
        except Exception as e:
            logger.error(f"Erro no reconhecimento em contexto isolado: {str(e)}")
            logger.error(traceback.format_exc())
            return ""
                
    def _check_audio_quality(self, audio_file):
        """Verifica a qualidade do áudio e retorna informações relevantes.
        
        Args:
            audio_file (str): Caminho para o arquivo de áudio
            
        Returns:
            dict: Dicionário com informações sobre a qualidade do áudio
        """
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(audio_file):
                logger.error(f"Arquivo não existe: {audio_file}")
                return {"quality": "ruim", "speech_percentage": 0, "energy_level": "baixo"}
            
            # Abrir primeiro em modo binário para verificar o cabeçalho
            try:
                with open(audio_file, 'rb') as f:
                    header = f.read(12)
                    if header[:4] != b'RIFF' or header[8:12] != b'WAVE':
                        logger.error(f"Arquivo não é um WAV válido (sem cabeçalho RIFF): {audio_file}")
                        logger.warning("Tentando corrigir o arquivo WAV para análise...")
                        
                        # Tentar recriar como um arquivo WAV válido
                        try:
                            # Ler todos os bytes
                            with open(audio_file, 'rb') as f_read:
                                audio_data = f_read.read()
                            
                            # Verificar se há dados suficientes
                            if len(audio_data) < 100:  # Um arquivo WAV válido deve ter pelo menos 100 bytes
                                logger.error(f"Arquivo muito pequeno para ser um WAV válido: {len(audio_data)} bytes")
                                return {"quality": "ruim", "speech_percentage": 0, "energy_level": "baixo"}
                            
                            # Procurar pelos bytes 'data' que marcam o início dos dados PCM
                            data_pos = audio_data.find(b'data')
                            if data_pos > 0:
                                # Se encontrar o marcador 'data', assumir que tudo depois dele são os dados PCM
                                # Pular 8 bytes (4 para 'data' e 4 para o tamanho do chunk)
                                raw_data = audio_data[data_pos+8:]
                            else:
                                # Se não encontrar o marcador 'data', assumir que são dados PCM puros
                                raw_data = audio_data
                            
                            # Converter para numpy array
                            samples = np.frombuffer(raw_data, dtype=np.int16)
                            
                            # Informações fixas
                            rate = 16000  # Assumir 16kHz
                            duration = len(samples) / float(rate)
                            
                            logger.warning(f"Análise de áudio sem cabeçalho WAV: {len(samples)} amostras, duração estimada: {duration:.2f}s")
                            
                            # Análise básica sem subdivisão
                            rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
                            peak = np.max(np.abs(samples))
                            max_value = 32767  # Para áudio de 16 bits
                            peak_ratio = peak / max_value
                            
                            # Estimativa aproximada
                            if peak_ratio > 0.5:
                                energy_level = "alto"
                                quality = "normal"
                                speech_percentage = 80
                            elif peak_ratio > 0.2:
                                energy_level = "médio"
                                quality = "normal"
                                speech_percentage = 60
                            else:
                                energy_level = "baixo"
                                quality = "ruim"
                                speech_percentage = 30
                            
                            logger.warning(f"Análise simplificada: Pico={peak}, RMS={rms:.1f}, Proporção de pico={peak_ratio:.2f}")
                            
                            return {
                                "quality": quality,
                                "speech_percentage": speech_percentage,
                                "energy_level": energy_level,
                                "duration": duration,
                                "peak": peak,
                                "rms": rms,
                                "silent_threshold": rms * 0.2  # Estimativa do threshold
                            }
                                
                        except Exception as binary_error:
                            logger.error(f"Erro na análise binária do arquivo: {str(binary_error)}")
                            return {"quality": "normal", "speech_percentage": 50, "energy_level": "médio"}
            except Exception as header_check_error:
                logger.error(f"Erro ao verificar cabeçalho do arquivo: {str(header_check_error)}")
                return {"quality": "normal", "speech_percentage": 50, "energy_level": "médio"}
                
            # Tentar carregar com wave
            try:
                with wave.open(audio_file, 'rb') as wf:
                    # Obter parâmetros
                    channels = wf.getnchannels()
                    sample_width = wf.getsampwidth()
                    rate = wf.getframerate()
                    frames = wf.getnframes()
                    
                    # Ler todos os frames
                    raw_data = wf.readframes(frames)
                    
                # Converter para numpy array
                samples = np.frombuffer(raw_data, dtype=np.int16)
                
                # Calcular duração
                duration = frames / float(rate)
                
                # Análise de silêncio e energia - VERSÃO OTIMIZADA
                # Usar um tamanho de segmento menor para detecção mais precisa
                segment_duration_ms = 5  # 5ms por segmento para detecção mais precisa
                samples_per_segment = int(rate * segment_duration_ms / 1000)
                
                # Calcular RMS total
                rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
                
                # Definir threshold dinâmico baseado no RMS
                silence_threshold = max(150, min(1500, rms * 0.15))  # Entre 150 e 1500, ou 15% do RMS
                
                # Dividir em segmentos pequenos e analisar cada um
                num_segments = len(samples) // samples_per_segment if samples_per_segment > 0 else 0
                segment_volumes = []
                is_silent = []
                
                for i in range(num_segments):
                    start = i * samples_per_segment
                    end = start + samples_per_segment
                    segment = samples[start:end]
                    segment_rms = np.sqrt(np.mean(segment.astype(np.float32)**2))
                    segment_volumes.append(segment_rms)
                    is_silent.append(segment_rms < silence_threshold)
                
                # Contar segmentos não silenciosos
                non_silent_segments = sum(not s for s in is_silent)
                non_silent_percentage = 100 * non_silent_segments / num_segments if num_segments > 0 else 0
                
                # Determinar nível de energia
                peak = np.max(np.abs(samples))
                max_value = 32767  # Para áudio de 16 bits
                peak_ratio = peak / max_value
                
                if peak_ratio > 0.7:
                    energy_level = "alto"
                elif peak_ratio > 0.3:
                    energy_level = "médio"
                else:
                    energy_level = "baixo"
                    
                # Avaliar qualidade global
                if non_silent_percentage > 60 and peak_ratio > 0.3:
                    quality = "bom"
                elif non_silent_percentage > 30 and peak_ratio > 0.1:
                    quality = "normal"
                else:
                    quality = "ruim"
                    
                # Registrar informações
                logger.warning(f"Análise de qualidade do áudio: Duração={duration:.2f}s, " +
                             f"Fala={non_silent_percentage:.1f}%, Pico={peak}, " +
                             f"RMS={rms:.1f}, Threshold={silence_threshold:.1f}")
                
                # Retornar resultados
                return {
                    "quality": quality,
                    "speech_percentage": non_silent_percentage,
                    "energy_level": energy_level,
                    "duration": duration,
                    "peak": peak,
                    "rms": rms,
                    "silent_threshold": silence_threshold
                }
            except wave.Error as wave_error:
                logger.error(f"Erro ao abrir arquivo WAV: {str(wave_error)}")
                # Se falhar com wave.Error, usar valores padrão de qualidade média
                return {"quality": "normal", "speech_percentage": 50, "energy_level": "médio"}
                
        except Exception as e:
            logger.error(f"Erro ao verificar qualidade do áudio: {str(e)}")
            logger.error(traceback.format_exc())
            # Em caso de erro, retornar valores padrão para não bloquear o processo
            return {"quality": "normal", "speech_percentage": 50, "energy_level": "médio"}

    def _try_recognition_with_config(self, audio_file, speech_config, config_name="Desconhecido", timeout=5):
        """Tenta reconhecer fala com uma configuração específica e timeout.
        
        Args:
            audio_file (str): Caminho para o arquivo de áudio
            speech_config (speechsdk.SpeechConfig): Configuração para reconhecimento
            config_name (str): Nome da configuração para logs
            timeout (int): Timeout em segundos
            
        Returns:
            str: Texto reconhecido ou string vazia
        """
        logger.warning(f"Tentando reconhecer fala com config '{config_name}' e timeout de {timeout}s")
        recognition_error = None  # Inicializar para evitar UnboundLocalError
        
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(audio_file):
                logger.error(f"Arquivo não existe: {audio_file}")
                return ""
                
            # Verificar se a configuração é válida
            if not speech_config:
                logger.error(f"Configuração inválida para '{config_name}'")
                # Tentar criar uma configuração padrão como fallback
                speech_config = self._create_default_config("pt-PT")
                config_name += "-Fallback"
                
            # Criar config de áudio
            audio_config = None
            try:
                audio_config = speechsdk.audio.AudioConfig(filename=audio_file)
            except Exception as audio_config_error:
                logger.error(f"Erro ao criar audio_config: {str(audio_config_error)}")
                return ""
                
            # Criar reconhecedor
            recognizer = None
            try:
                recognizer = speechsdk.SpeechRecognizer(
                    speech_config=speech_config, 
                    audio_config=audio_config
                )
            except Exception as recognizer_error:
                logger.error(f"Erro ao criar reconhecedor: {str(recognizer_error)}")
                return ""
                
            # Resultado e flag de conclusão
            result_text = ""
            done = False
            
            # Callbacks para eventos de reconhecimento
            def recognized_cb(evt):
                nonlocal result_text, done
                result_text = evt.result.text
                logger.warning(f"Reconhecido: '{result_text}'")
                done = True
                
            def canceled_cb(evt):
                nonlocal done, recognition_error
                details = evt.cancellation_details
                reason = details.reason
                
                # Registrar razão do cancelamento
                reason_text = {
                    speechsdk.CancellationReason.Error: "Erro",
                    speechsdk.CancellationReason.EndOfStream: "Fim do stream",
                    speechsdk.CancellationReason.ServiceTimeout: "Timeout do serviço",
                    speechsdk.CancellationReason.ServiceError: "Erro do serviço",
                    speechsdk.CancellationReason.AuthenticationFailure: "Falha de autenticação"
                }.get(reason, f"Desconhecido ({reason})")
                
                logger.warning(f"Reconhecimento cancelado: {reason_text}")
                
                if details.error_details:
                    logger.warning(f"Detalhes do erro: {details.error_details}")
                    recognition_error = details.error_details
                else:
                    recognition_error = f"Cancelado: {reason_text}"
                    
                done = True
                
            # Definir callbacks
            recognizer.recognized.connect(recognized_cb)
            recognizer.canceled.connect(canceled_cb)
            
            # Adicionar callback para sessão
            def session_stopped_cb(evt):
                nonlocal done
                logger.warning("Sessão de reconhecimento finalizada")
                done = True
                
            recognizer.session_stopped.connect(session_stopped_cb)
            
            # Iniciar reconhecimento
            start_time = time.time()
            logger.warning(f"Iniciando reconhecimento contínuo para '{config_name}'")
            
            # Iniciar reconhecimento contínuo
            try:
                recognizer.start_continuous_recognition()
            except Exception as start_error:
                logger.error(f"Erro ao iniciar reconhecimento: {str(start_error)}")
                return ""
                
            # Aguardar resultado ou timeout
            try:
                while not done and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                    
                # Se atingiu timeout sem reconhecimento
                if not done:
                    logger.warning(f"Timeout após {timeout}s sem reconhecimento para '{config_name}'")
                    
                    # Tentar fallback com recognize_once 
                    logger.warning("Tentando fallback com recognize_once")
                    try:
                        # Criar novo reconhecedor para fallback
                        fallback_config = self._create_default_config("pt-PT")
                        fallback_config.set_property(
                            speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
                            "1000"  # Timeout curto para iniciar mais rápido
                        )
                        
                        # Criar reconhecedor para fallback
                        fallback_audio_config = speechsdk.audio.AudioConfig(filename=audio_file)
                        fallback_recognizer = speechsdk.SpeechRecognizer(
                            speech_config=fallback_config,
                            audio_config=fallback_audio_config
                        )
                        
                        # Usar recognize_once diretamente
                        logger.warning("Executando recognize_once como fallback")
                        fallback_result = fallback_recognizer.recognize_once()
                        
                        if fallback_result.reason == speechsdk.ResultReason.RecognizedSpeech:
                            result_text = fallback_result.text
                            logger.warning(f"Fallback bem-sucedido: '{result_text}'")
                        else:
                            logger.warning(f"Fallback também falhou: {fallback_result.reason}")
                    except Exception as fallback_error:
                        logger.error(f"Erro no fallback: {str(fallback_error)}")
                
                # Não esquecer de parar o reconhecimento
                try:
                    recognizer.stop_continuous_recognition()
                except Exception as stop_error:
                    logger.warning(f"Erro ao parar reconhecimento: {str(stop_error)}")
                    
            except Exception as recognition_loop_error:
                logger.error(f"Erro durante loop de reconhecimento: {str(recognition_loop_error)}")
                
            # Finalizar e retornar resultado
            end_time = time.time()
            duration = end_time - start_time
            
            if result_text:
                logger.warning(f"Reconhecimento '{config_name}' concluído em {duration:.2f}s: '{result_text}'")
                return result_text.strip()
            else:
                if recognition_error:
                    error_message = str(recognition_error).lower()
                    
                    # Analise específica para tipos comuns de erro
                    if "timeout" in error_message:
                        logger.warning(f"Timeout de reconhecimento: {error_message}")
                    elif "connection" in error_message or "network" in error_message:
                        logger.warning(f"Erro de conexão: {error_message}")
                    elif "auth" in error_message or "key" in error_message:
                        logger.warning(f"Erro de autorização: {error_message}")
                    else:
                        logger.warning(f"Erro de reconhecimento: {error_message}")
                else:
                    logger.warning(f"Reconhecimento '{config_name}' não retornou texto após {duration:.2f}s")
                
                return ""
                
        except Exception as e:
            logger.error(f"Erro geral no reconhecimento: {str(e)}")
            logger.error(traceback.format_exc())
            return ""

    def _create_aggressive_config(self, language="pt-PT"):
        """Cria uma configuração de reconhecimento de fala otimizada para 
        condições desafiadoras de reconhecimento.
        
        Args:
            language (str): Código do idioma a ser usado para reconhecimento
            
        Returns:
            speechsdk.SpeechConfig: Configuração para o Azure Speech SDK
        """
        recognition_error = None  # Evitar UnboundLocalError
        
        try:
            logger.warning(f"Criando configuração agressiva para o idioma {language}")
            
            # Verificar se as credenciais são válidas
            if not self.api_key or not self.region:
                logger.error("Credenciais Azure inválidas para criar configuração agressiva")
                return self._create_default_config(language)
                
            # Criar uma nova configuração diretamente com as credenciais
            speech_config = speechsdk.SpeechConfig(subscription=self.api_key, region=self.region)
            
            if not speech_config:
                logger.error("Falha ao criar SpeechConfig para modo agressivo")
                return self._create_default_config(language)
                
            # Definir o idioma
            speech_config.speech_recognition_language = language
            
            # Configurar para ambiente agressivo - timeouts MUITO maiores
            # IMPORTANTE: Aumentar significativamente o timeout de silêncio inicial
            # para evitar NoMatchReason.InitialSilenceTimeout
            speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, 
                "5000"  # 5 segundos de silêncio inicial
            )
            
            # Reduzir timeout de silêncio final também
            speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, 
                "2000"  # 2 segundos de silêncio final
            )
            
            # Configurar outros parâmetros de silêncio (se disponíveis)
            try:
                # Desativar completamente a detecção de silêncio inicial
                if hasattr(speechsdk.PropertyId, "Speech_SegmentationSilenceTimeoutMs"):
                    speech_config.set_property(
                        speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs,
                        "200"  # 200ms (valor mínimo que funciona bem)
                    )
                    logger.warning("Propriedade Speech_SegmentationSilenceTimeoutMs configurada")
            except Exception as prop_err:
                logger.warning(f"Propriedade de segmentação de silêncio não suportada: {str(prop_err)}")
            
            # CORREÇÃO: Evitar conflito de modo - Usar apenas o modo de ditado
            # em vez de combinar com o modo Conversation (que causa o erro SPXERR_SWITCH_MODE_NOT_ALLOWED)
            
            # Habilitar ditado para melhorar reconhecimento
            speech_config.enable_dictation()
            logger.warning("Modo de ditado ativado (Prioridade sobre Conversation)")
            
            # Não definir modo Conversation, pois é incompatível com dictation
            # Comentado para evitar o erro SPXERR_SWITCH_MODE_NOT_ALLOWED
            # speech_config.set_property(
            #    speechsdk.PropertyId.SpeechServiceConnection_RecoMode,
            #    "Conversation"
            # )
            
            # Aumentar a sensibilidade do reconhecimento
            speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceResponse_RecognitionLatencyMs,
                "0"  # Zero latência para resultados mais rápidos
            )
            
            # Ativar formato detalhado para obter mais informações
            speech_config.output_format = speechsdk.OutputFormat.Detailed
            
            # Definir profanidade para raw (capturar tudo)
            speech_config.set_profanity(speechsdk.ProfanityOption.Raw)
            
            # Tentar configurar reconexão automática
            try:
                # Cancelar menos facilmente o reconhecimento
                if hasattr(speechsdk.PropertyId, "Conversation_Auto_Reconnect_Cancellation_Count"):
                    speech_config.set_property(
                        speechsdk.PropertyId.Conversation_Auto_Reconnect_Cancellation_Count,
                        "10"  # Permitir mais reconexões (padrão é 3)
                    )
                    logger.warning("Propriedade Conversation_Auto_Reconnect_Cancellation_Count configurada")
            except Exception as recon_err:
                logger.warning(f"Propriedade de reconexão não suportada: {str(recon_err)}")
            
            # Verificar se a configuração é válida antes de retornar
            try:
                # Teste simples para verificar se a configuração é válida
                # Tentar obter uma propriedade para ver se não ocorre erro
                speech_config.get_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs)
                logger.warning("Configuração agressiva criada e validada com sucesso no modo Ditado")
            except Exception as test_error:
                logger.error(f"Configuração agressiva criada, mas falhou na validação: {str(test_error)}")
                # Mesmo que falhe a validação, retornar a configuração criada
            
            # Retornar a configuração criada
            return speech_config
            
        except Exception as e:
            logger.error(f"Erro ao criar configuração agressiva: {str(e)}")
            logger.error(traceback.format_exc())
            # Em caso de erro, retornar configuração padrão como fallback
            default_config = self._create_default_config(language)
            logger.warning("Usando configuração padrão como fallback para modo agressivo")
            return default_config

    def recognize_audio(self, audio_data, language):
        """
        Alias for recognize_speech to maintain compatibility with other services.
        
        This method handles both file paths and raw audio data to provide maximum flexibility.
        
        Args:
            audio_data: Either a string containing a file path or bytes object with audio data
            language: Language code for recognition (e.g., 'pt-PT')
            
        Returns:
            dict: Recognition results containing the 'text' key with recognized text
        """
        try:
            logger.info(f"Recognize audio called with language: {language}")
            
            # Check if input is a file path or audio data
            if isinstance(audio_data, str):
                logger.info(f"Input is a file path: {audio_data}")
                
                # Check if file exists
                if not os.path.exists(audio_data):
                    logger.error(f"Audio file does not exist: {audio_data}")
                    return {"text": ""}
                    
                # Load audio file
                with open(audio_data, 'rb') as f:
                    file_data = f.read()
                    
                # Process audio file
                result = self.recognize_speech(file_data, language)
                return {"text": result}
            else:
                # Assume input is raw audio data
                logger.info("Input is raw audio data")
                result = self.recognize_speech(audio_data, language)
                return {"text": result}
        except Exception as e:
            logger.error(f"Error in recognize_audio: {str(e)}")
            logger.error(traceback.format_exc())
            return {"text": ""}