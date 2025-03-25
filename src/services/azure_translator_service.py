#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Azure Translator Service for DogeDictate
"""

import json
import logging
import requests
import uuid

class AzureTranslatorService:
    """
    Service for translation using Azure Translator API
    """
    
    def __init__(self, config_manager=None, key=None, region=None):
        """
        Initialize the Azure Translator service
        
        Args:
            config_manager: Configuração da aplicação
            key (str, optional): Azure Translator API key. Defaults to None.
            region (str, optional): Azure Translator region. Defaults to None.
        """
        self.config_manager = config_manager
        
        # Inicializar chave e região da API
        if config_manager is not None:
            self.key = config_manager.get_value("translation", "azure_translator_key", "")
            self.region = config_manager.get_value("translation", "azure_translator_region", "")
        else:
            self.key = key
            self.region = region
            
        self.endpoint = "https://api.cognitive.microsofttranslator.com"
        self.logger = logging.getLogger(__name__)
        
        # Log detalhado para diagnóstico
        if self.key:
            masked_key = self.key[:5] + "..." + self.key[-5:] if len(self.key) > 10 else "***"
            self.logger.info(f"Azure Translator inicializado: Key={masked_key}, Region={self.region}")
        else:
            self.logger.warning("Azure Translator não configurado: API Key ausente")
    
    def is_configured(self):
        """
        Check if the service is properly configured
        
        Returns:
            bool: True if configured, False otherwise
        """
        return self.key is not None and self.region is not None and bool(self.key) and bool(self.region)
    
    def update_credentials(self, key, region):
        """
        Update credentials for Azure Translator service
        
        Args:
            key (str): API key for Azure Translator
            region (str): Region for Azure Translator
        
        Returns:
            bool: True if update is successful, False otherwise
        """
        try:
            self.key = key
            self.region = region
            
            # Log detalhado para diagnóstico
            if self.key:
                masked_key = self.key[:5] + "..." + self.key[-5:] if len(self.key) > 10 else "***"
                self.logger.info(f"Credenciais do Azure Translator atualizadas: Key={masked_key}, Region={region}")
            else:
                self.logger.warning("Tentativa de atualizar credenciais com chave vazia")
                
            return self.is_configured()
        except Exception as e:
            self.logger.error(f"Erro ao atualizar credenciais do Azure Translator: {str(e)}")
            return False
        
    def translate(self, text, source_lang=None, target_lang=None):
        """
        Translate text using Azure Translator API
        
        Args:
            text (str): Text to translate
            source_lang (str, optional): Source language code. Defaults to None.
            target_lang (str, optional): Target language code. Defaults to None.
            
        Returns:
            str: Translated text
        """
        if not self.is_configured():
            self.logger.error("Azure Translator não está configurado corretamente. Tradução não realizada.")
            return ""
            
        self.logger.info(f"Traduzindo com Azure Translator de {source_lang} para {target_lang}")
        
        try:
            path = '/translate'
            constructed_url = self.endpoint + path
            
            params = {
                'api-version': '3.0',
                'from': source_lang,
                'to': target_lang
            }
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.key,
                'Ocp-Apim-Subscription-Region': self.region,
                'Content-type': 'application/json',
                'X-ClientTraceId': str(uuid.uuid4())
            }
            
            body = [{
                'text': text
            }]
            
            self.logger.info(f"Translating with Azure: {source_lang} -> {target_lang}")
            
            response = requests.post(constructed_url, params=params, headers=headers, json=body)
            response.raise_for_status()
            
            translation_response = response.json()
            
            if translation_response and len(translation_response) > 0:
                translations = translation_response[0].get('translations', [])
                if translations and len(translations) > 0:
                    return translations[0].get('text', text)
                
            return text
            
        except Exception as e:
            self.logger.error(f"Error translating with Azure: {str(e)}")
            return text 