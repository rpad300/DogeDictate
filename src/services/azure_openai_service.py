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
        
        # Log detalhado das credenciais
        if self.api_key:
            masked_key = self.api_key[:5] + "..." + self.api_key[-5:] if len(self.api_key) > 10 else "***"
            self.logger.info(f"Azure OpenAI configurado: API Key presente = True, Endpoint = {self.endpoint}, Deployment = {self.deployment_name}")
            
            # Logs adicionais para depuração
            self.logger.info(f"API Key Length: {len(self.api_key)}")
            self.logger.info(f"Endpoint válido: {self.endpoint is not None and len(self.endpoint) > 0}")
            self.logger.info(f"Deployment válido: {self.deployment_name is not None and len(self.deployment_name) > 0}")
            
            # Verificar formato do endpoint
            if self.endpoint and not self.endpoint.startswith(("http://", "https://")):
                self.logger.warning(f"Endpoint inválido: {self.endpoint} - deve começar com http:// ou https://")
            
            # Verificar deployment name
            if not self.deployment_name or len(self.deployment_name.strip()) == 0:
                self.logger.warning("Nome do deployment está vazio ou inválido")
        else:
            self.logger.warning("Azure OpenAI não configurado: API Key ausente")
            # Logs adicionais para depuração
            self.logger.warning(f"Endpoint recebido: {self.endpoint}")
            self.logger.warning(f"Deployment recebido: {self.deployment_name}")
        
    def is_configured(self):
        """
        Check if the service is properly configured
        
        Returns:
            bool: True if configured, False otherwise
        """
        is_config_valid = (self.api_key is not None and 
                self.endpoint is not None and 
                self.deployment_name is not None and
                len(self.api_key.strip()) > 0 and
                len(self.endpoint.strip()) > 0 and
                len(self.deployment_name.strip()) > 0)
                
        # Log adicional para depuração
        self.logger.info(f"Azure OpenAI configuração válida: {is_config_valid}")
        self.logger.info(f"  - API Key presente: {self.api_key is not None and len(self.api_key.strip()) > 0}")
        self.logger.info(f"  - Endpoint presente: {self.endpoint is not None and len(self.endpoint.strip()) > 0}")
        self.logger.info(f"  - Deployment presente: {self.deployment_name is not None and len(self.deployment_name.strip()) > 0}")
        
        return is_config_valid
    
    def translate(self, text, source_language, target_language, prompt=None):
        """
        Translate text using Azure OpenAI API
        
        Args:
            text (str): Text to translate
            source_language (str): Source language code
            target_language (str): Target language code
            prompt (str, optional): Custom prompt for translation. Defaults to None.
            
        Returns:
            str: Translated text
        """
        if not self.is_configured():
            self.logger.error(f"Azure OpenAI não está configurado corretamente. API Key: {bool(self.api_key)}, Endpoint: {bool(self.endpoint)}, Deployment: {bool(self.deployment_name)}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "Erro de Configuração",
                "O serviço Azure OpenAI não está configurado corretamente. Verifique suas configurações nas preferências do aplicativo.",
                QMessageBox.Ok
            )
            return ""
            
        self.logger.info(f"Traduzindo com Azure OpenAI de {source_language} para {target_language}")
        
        # Extract language codes without region for better prompting
        source_lang_base = source_language.split('-')[0] if '-' in source_language else source_language
        target_lang_base = target_language.split('-')[0] if '-' in target_language else target_language
        
        # Use custom prompt if provided, or create one
        if not prompt:
            prompt = f"Traduza o seguinte texto de {source_lang_base} para {target_lang_base} mantendo o estilo e significado original:\n\n{text}"
        else:
            prompt = prompt.format(source_language=source_lang_base, target_language=target_lang_base)
            prompt = f"{prompt}\n\n{text}"
            
        self.logger.info(f"Usando prompt de tradução: {prompt[:50]}...")
        
        try:
            result = self.generate_text(prompt, max_tokens=1024, temperature=0.1)
            
            if not result:
                self.logger.error("Tradução falhou: resultado vazio")
                return text
                
            # Clean up the result - remove any "Translation:" prefixes
            cleaned_result = result
            prefixes_to_remove = ["Translation:", "Tradução:", "Translated text:"]
            for prefix in prefixes_to_remove:
                if cleaned_result.startswith(prefix):
                    cleaned_result = cleaned_result[len(prefix):].strip()
            
            self.logger.info(f"Tradução bem-sucedida: '{text[:30]}...' -> '{cleaned_result[:30]}...'")
            return cleaned_result
            
        except Exception as e:
            self.logger.error(f"Erro na tradução com Azure OpenAI: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
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

    def update_credentials(self, api_key, endpoint, deployment_name):
        """
        Update credentials for Azure OpenAI service
        
        Args:
            api_key (str): API key for Azure OpenAI
            endpoint (str): Endpoint URL for Azure OpenAI
            deployment_name (str): Deployment name for Azure OpenAI model
            
        Returns:
            bool: True if update is successful, False otherwise
        """
        try:
            self.api_key = api_key
            self.endpoint = endpoint
            self.deployment_name = deployment_name
            
            # Log detalhado
            masked_key = self.api_key[:5] + "..." + self.api_key[-5:] if len(self.api_key) > 10 else "***"
            self.logger.info(f"Credenciais do Azure OpenAI atualizadas: API Key={masked_key}, Endpoint={endpoint}, Deployment={deployment_name}")
            
            return self.is_configured()
        except Exception as e:
            self.logger.error(f"Erro ao atualizar credenciais do Azure OpenAI: {str(e)}")
            return False 