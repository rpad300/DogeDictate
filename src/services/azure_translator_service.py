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
    
    def __init__(self, key=None, region=None):
        """
        Initialize the Azure Translator service
        
        Args:
            key (str, optional): Azure Translator API key. Defaults to None.
            region (str, optional): Azure Translator region. Defaults to None.
        """
        self.key = key
        self.region = region
        self.endpoint = "https://api.cognitive.microsofttranslator.com"
        self.logger = logging.getLogger(__name__)
        
    def is_configured(self):
        """
        Check if the service is properly configured
        
        Returns:
            bool: True if configured, False otherwise
        """
        return self.key is not None and self.region is not None
        
    def translate(self, text, source_lang, target_lang):
        """
        Translate text using Azure Translator
        
        Args:
            text (str): Text to translate
            source_lang (str): Source language code
            target_lang (str): Target language code
            
        Returns:
            str: Translated text
        """
        if not self.is_configured():
            self.logger.warning("Azure Translator not configured")
            return text
            
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