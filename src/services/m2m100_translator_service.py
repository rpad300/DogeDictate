#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
M2M100 Translator Service for DogeDictate
"""

import logging
import os
import torch
import time

logger = logging.getLogger(__name__)

class M2M100TranslatorService:
    """
    Service for translation using M2M100 model
    """
    
    def __init__(self, config_manager):
        """
        Initialize M2M100 translator service
        
        Args:
            config_manager: Configuration manager for the service
        """
        self.config_manager = config_manager
        self.model = None
        self.tokenizer = None
        self.model_name = self.config_manager.get_value("translation", "m100_model", "small")
        self.model_path = self.config_manager.get_value("translation", "m100_model_path", "")
        self.use_gpu = self.config_manager.get_value("translation", "m100_use_gpu", False)
        
        # Verificação de GPU
        self.gpu_available = torch.cuda.is_available() if self._is_torch_available() else False
        
        # Log detalhado para diagnóstico
        logger.info(f"M2M100 inicializado: Modelo={self.model_name}, GPU={self.use_gpu and self.gpu_available}")
        if self.use_gpu and not self.gpu_available:
            logger.warning("GPU solicitada mas não disponível para M2M100. Usando CPU.")
        
        # Inicialização adiada do modelo (não carrega automaticamente para economizar memória)
    
    def _is_torch_available(self):
        """Verificar se PyTorch está disponível"""
        try:
            import torch
            return True
        except ImportError:
            logger.warning("PyTorch não está instalado. M2M100 não funcionará.")
            return False
    
    def is_available(self):
        """Verificar se o serviço está disponível"""
        try:
            # Verificar se as dependências estão instaladas
            try:
                import transformers
                return True
            except ImportError:
                logger.warning("Biblioteca transformers não está instalada. M2M100 não funcionará.")
                return False
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade do M2M100: {str(e)}")
            return False
    
    def _initialize_model(self):
        """Inicializar o modelo sob demanda"""
        if self.model is not None:
            return True
            
        try:
            from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
            
            # Determinar o modelo correto
            if self.model_path and os.path.exists(self.model_path):
                model_id = self.model_path
                logger.info(f"Carregando modelo M2M100 de path local: {model_id}")
            else:
                # Usar modelo base da Hugging Face baseado na configuração
                if self.model_name == "small":
                    model_id = "facebook/m2m100_418M"
                elif self.model_name == "medium":
                    model_id = "facebook/m2m100_1.2B"
                else:
                    model_id = "facebook/m2m100_418M"  # default para small
                    
                logger.info(f"Carregando modelo M2M100 da Hugging Face: {model_id}")
            
            # Log para informar o usuário
            logger.info("Carregando modelo M2M100... (pode demorar alguns minutos)")
            
            # Configurar device
            device = "cuda" if self.use_gpu and self.gpu_available else "cpu"
            
            # Carregar modelo e tokenizador
            start_time = time.time()
            
            self.model = M2M100ForConditionalGeneration.from_pretrained(model_id)
            self.tokenizer = M2M100Tokenizer.from_pretrained(model_id)
            
            # Mover modelo para GPU se disponível
            self.model.to(device)
            
            load_time = time.time() - start_time
            logger.info(f"Modelo M2M100 carregado em {load_time:.2f}s ({device})")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar modelo M2M100: {str(e)}")
            self.model = None
            self.tokenizer = None
            return False
    
    def translate(self, text, source_lang, target_lang):
        """
        Translate text using M2M100 model
        
        Args:
            text (str): Text to translate
            source_lang (str): Source language code
            target_lang (str): Target language code
            
        Returns:
            str: Translated text
        """
        # Verificar se texto está vazio
        if not text or len(text.strip()) == 0:
            return text
            
        # Converter códigos de idioma para o formato esperado pelo M2M100
        source_lang = self._normalize_language_code(source_lang)
        target_lang = self._normalize_language_code(target_lang)
            
        # Log detalhado
        logger.info(f"Traduzindo com M2M100 de {source_lang} para {target_lang}")
        
        try:
            # Inicializar modelo se ainda não foi carregado
            if self.model is None or self.tokenizer is None:
                if not self._initialize_model():
                    logger.error("Falha ao inicializar modelo M2M100")
                    return text
                    
            # Definir idioma de origem no tokenizador
            self.tokenizer.src_lang = source_lang
            
            # Tokenizar o texto de entrada
            encoded = self.tokenizer(text, return_tensors="pt")
            
            # Mover para o mesmo device do modelo
            encoded = {k: v.to(self.model.device) for k, v in encoded.items()}
            
            # Configurar o idioma alvo
            forced_bos_token_id = self.tokenizer.get_lang_id(target_lang)
            
            # Gerar tradução
            start_time = time.time()
            generated_tokens = self.model.generate(
                **encoded,
                forced_bos_token_id=forced_bos_token_id,
                max_length=1024
            )
            
            # Decodificar tokens para texto
            translation = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            
            translation_time = time.time() - start_time
            logger.info(f"Tradução M2M100 concluída em {translation_time:.2f}s")
            
            return translation
            
        except Exception as e:
            logger.error(f"Erro ao traduzir com M2M100: {str(e)}")
            return text
            
    def _normalize_language_code(self, lang_code):
        """Converter código de idioma para o formato esperado pelo M2M100"""
        # M2M100 usa códigos ISO 639-1 (2 letras)
        if '-' in lang_code:
            lang_code = lang_code.split('-')[0]
            
        # Mapeamento de códigos de idioma para os suportados pelo M2M100
        mapping = {
            "pt": "pt",
            "en": "en",
            "es": "es",
            "fr": "fr",
            "de": "de",
            "it": "it",
            "ru": "ru",
            "zh": "zh",
            "ja": "ja",
            "ko": "ko",
            "ar": "ar",
            "hi": "hi",
            # Adicionar mais mapeamentos conforme necessário
        }
        
        return mapping.get(lang_code.lower(), "en") 