#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Local Whisper Service for DogeDictate
"""

import os
import logging
import tempfile
import time
import torch

class LocalWhisperService:
    """
    Service for local speech recognition using Whisper model
    """
    
    def __init__(self, config_manager):
        """
        Initialize local whisper service
        
        Args:
            config_manager: Configuration manager for the service
        """
        self.config_manager = config_manager
        self.model = None
        self.model_name = self.config_manager.get_value("recognition", "whisper_local_model", "base")
        self.use_gpu = self.config_manager.get_value("recognition", "whisper_local_use_gpu", False)
        
        # Verificação de GPU
        self.gpu_available = torch.cuda.is_available() if self._is_torch_available() else False
        
        # Log detalhado para diagnóstico
        logger.info(f"Local Whisper inicializado: Modelo={self.model_name}, GPU={self.use_gpu and self.gpu_available}")
        if self.use_gpu and not self.gpu_available:
            logger.warning("GPU solicitada mas não disponível para Local Whisper. Usando CPU.")
        
        # Inicialização adiada do modelo
        self._initialize_model()
        
    def _is_torch_available(self):
        """Verificar se PyTorch está disponível"""
        try:
            import torch
            return True
        except ImportError:
            logger.warning("PyTorch não está instalado. Local Whisper funcionará com funcionalidade limitada.")
            return False
    
    def is_available(self):
        """Verificar se o serviço está disponível (modelo carregado)"""
        try:
            return self.model is not None
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade do Local Whisper: {str(e)}")
            return False
    
    def _initialize_model(self):
        """Initialize the model on demand"""
        if self.model is not None:
            return
            
        try:
            import whisper
            
            # Log detalhado
            logger.info(f"Carregando modelo Whisper: {self.model_name}")
            
            # Ajustar device conforme disponibilidade
            device = "cuda" if self.use_gpu and self.gpu_available else "cpu"
            
            # Carregar modelo
            start_time = time.time()
            self.model = whisper.load_model(self.model_name, device=device)
            load_time = time.time() - start_time
            
            logger.info(f"Modelo Whisper {self.model_name} carregado em {load_time:.2f}s ({device})")
        except Exception as e:
            logger.error(f"Erro ao inicializar modelo Whisper: {str(e)}")
            self.model = None
            
    def transcribe(self, audio_data, language=None):
        """
        Transcribe audio data using local Whisper model
        
        Args:
            audio_data (bytes): Audio data to transcribe
            language (str, optional): Language code. Defaults to None.
            
        Returns:
            str: Transcribed text
        """
        if not self.is_available():
            logger.error("Modelo Local Whisper não está disponível")
            return ""
            
        try:
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                temp_file.write(audio_data)
                
            # Here would be actual transcription code
            logger.info(f"Transcribing audio with local Whisper, language: {language}")
            
            # Clean up
            try:
                os.remove(temp_filename)
            except:
                pass
                
            # Return placeholder text
            return "Local whisper transcription would appear here."
            
        except Exception as e:
            logger.error(f"Error transcribing with local Whisper: {str(e)}")
            return ""

    def recognize_speech(self, audio_data, language=None):
        """
        Recognize speech from audio data
        
        Args:
            audio_data (bytes or str): Audio data in bytes format or path to audio file
            language (str, optional): Language code (e.g., "en-US"). Defaults to None.
            
        Returns:
            str: Recognized text
        """
        if not self.is_available():
            logger.error("Modelo Local Whisper não está disponível")
            return ""
            
        # Log detalhado
        logger.info(f"Iniciando reconhecimento com Local Whisper, idioma: {language}")
        
        try:
            # Inicializar modelo se ainda não estiver carregado
            if self.model is None:
                logger.info("Inicializando modelo por demanda")
                self._initialize_model()
                
                if self.model is None:
                    logger.error("Falha ao carregar modelo Whisper")
                    return ""
                
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                temp_file.write(audio_data)
                
            # Here would be actual transcription code
            logger.info(f"Transcribing audio with local Whisper, language: {language}")
            
            # Clean up
            try:
                os.remove(temp_filename)
            except:
                pass
                
            # Return placeholder text
            return "Local whisper transcription would appear here."
            
        except Exception as e:
            logger.error(f"Error transcribing with local Whisper: {str(e)}")
            return "" 