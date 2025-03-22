#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Azure OpenAI Service for DogeDictate
"""

import json
import logging
import requests
import time

class AzureOpenAIService:
    """
    Service for using Azure OpenAI API
    """
    
    def __init__(self, api_key=None, endpoint=None, deployment_name=None):
        """
        Initialize the Azure OpenAI service
        
        Args:
            api_key (str, optional): Azure OpenAI API key. Defaults to None.
            endpoint (str, optional): Azure OpenAI endpoint. Defaults to None.
            deployment_name (str, optional): Azure OpenAI deployment name. Defaults to None.
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment_name = deployment_name
        self.logger = logging.getLogger(__name__)
        
    def is_configured(self):
        """
        Check if the service is properly configured
        
        Returns:
            bool: True if configured, False otherwise
        """
        return (self.api_key is not None and 
                self.endpoint is not None and 
                self.deployment_name is not None)
    
    def translate(self, text, source_lang=None, target_lang=None):
        """
        Traduzir texto usando o Azure OpenAI
        
        Args:
            text (str): Texto a ser traduzido
            source_lang (str, optional): Idioma de origem. Defaults to None.
            target_lang (str, optional): Idioma de destino. Defaults to None.
            
        Returns:
            str: Texto traduzido
        """
        if not self.is_configured():
            self.logger.warning("Azure OpenAI não configurado para tradução")
            return text
            
        try:
            # Log mais detalhado para diagnóstico
            self.logger.info(f"Azure OpenAI configurado: API Key presente = {bool(self.api_key)}, Endpoint = {self.endpoint}, Deployment = {self.deployment_name}")
            
            # Verificar se text é válido
            if not text or len(text.strip()) == 0:
                self.logger.warning("Texto vazio enviado para tradução")
                return text
                
            # Criar prompt para tradução
            prompt = f"Translate the following text from {source_lang} to {target_lang}:\n\n{text}\n\nTranslation:"
            
            self.logger.info(f"Traduzindo com Azure OpenAI de {source_lang} para {target_lang}")
            
            # Limitar tokens para evitar erros (dependendo do tamanho da entrada)
            text_length = len(text.split())
            max_tokens = min(4096, max(1024, text_length * 2))  # Estimar tokens necessários
            
            # Usar o método generate_text para obter a tradução
            try:
                self.logger.info(f"Chamando API Azure OpenAI com {max_tokens} tokens máximos")
                translated_text = self.generate_text(prompt, max_tokens=max_tokens, temperature=0.3)
                
                if not translated_text:
                    self.logger.warning("A tradução com Azure OpenAI falhou ou retornou vazio")
                    return text
                    
                self.logger.info("Tradução com Azure OpenAI concluída com sucesso")
                return translated_text
                
            except Exception as api_error:
                self.logger.error(f"Falha na chamada à API do Azure OpenAI: {str(api_error)}")
                # Retornar o texto original em caso de erro
                return text
            
        except Exception as e:
            self.logger.error(f"Erro ao traduzir com Azure OpenAI: {str(e)}")
            return text
        
    def generate_text(self, prompt, max_tokens=100, temperature=0.7):
        """
        Generate text using Azure OpenAI
        
        Args:
            prompt (str): Prompt for text generation
            max_tokens (int, optional): Maximum tokens to generate. Defaults to 100.
            temperature (float, optional): Creativity temperature. Defaults to 0.7.
            
        Returns:
            str: Generated text
        """
        if not self.is_configured():
            self.logger.warning("Azure OpenAI not configured")
            return ""
            
        try:
            # Verificar se o deployment é um modelo "gpt-4" ou "gpt-3.5-turbo" que precisa usar a API de chat
            is_chat_model = any(model in self.deployment_name.lower() for model in ["gpt-4", "gpt-3.5", "gpt-35"])
            
            if is_chat_model:
                # URL para API de chat (compatível com GPT-4 e GPT-3.5-turbo)
                url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version=2023-05-15"
                self.logger.info(f"Using chat completions API for model {self.deployment_name}")
                
                # Formato de dados para API de chat
                data = {
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 1,
                    "frequency_penalty": 0,
                    "presence_penalty": 0
                }
            else:
                # URL para API de completions (para modelos mais antigos)
                url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/completions?api-version=2023-05-15"
                self.logger.info(f"Using completions API for model {self.deployment_name}")
                
                # Formato de dados para API de completions
                data = {
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 1,
                    "frequency_penalty": 0,
                    "presence_penalty": 0,
                    "stop": None
                }
            
            # Log mais detalhado
            self.logger.info(f"Azure OpenAI URL: {url}")
            self.logger.info(f"Using deployment: {self.deployment_name}")
            
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            self.logger.info("Sending request to Azure OpenAI")
            
            # Adicionar timeout para evitar bloqueio indefinido
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            # Log detalhado do status da resposta
            self.logger.info(f"Response status code: {response.status_code}")
            
            # Verificar explicitamente por erros HTTP
            if response.status_code != 200:
                self.logger.error(f"Azure OpenAI API returned status code {response.status_code}")
                self.logger.error(f"Error response: {response.text}")
                return ""
            
            response.raise_for_status()
            
            response_data = response.json()
            
            # Verificação mais robusta de dados da resposta
            if not response_data:
                self.logger.error("Empty response from Azure OpenAI API")
                return ""
            
            # Extrair o texto da resposta de acordo com o formato da API utilizada
            result = ""
            if is_chat_model:
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    if "message" in response_data["choices"][0] and "content" in response_data["choices"][0]["message"]:
                        result = response_data["choices"][0]["message"]["content"].strip()
                    else:
                        self.logger.error(f"No message content in response: {response_data['choices'][0]}")
                        return ""
                else:
                    self.logger.error("No choices or empty choices in response")
                    return ""
            else:
                # Para a API de completions
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    if "text" in response_data["choices"][0]:
                        result = response_data["choices"][0]["text"].strip()
                    else:
                        self.logger.error(f"No text field in response: {response_data['choices'][0]}")
                        return ""
                else:
                    self.logger.error("No choices returned from Azure OpenAI")
                    return ""
            
            self.logger.info(f"Successfully generated text: {result[:50]}..." if len(result) > 50 else f"Successfully generated text: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error with Azure OpenAI: {str(e)}")
            return ""
        except Exception as e:
            self.logger.error(f"Error generating text with Azure OpenAI: {str(e)}")
            return "" 