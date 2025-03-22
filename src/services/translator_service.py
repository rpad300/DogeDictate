#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Translator Service for DogeDictate
Handles language detection and translation using Azure Translator API
"""

import logging
import requests
import json
import os
import time
import traceback
from typing import Dict, List, Optional, Any
import uuid
import hashlib
import re

logger = logging.getLogger("DogeDictate.TranslatorService")

class TranslatorService:
    """Service for language detection and translation using Azure Translator API"""
    
    def __init__(self, config_manager):
        """Initialize the translator service"""
        self.config_manager = config_manager
        self.api_key = self.config_manager.get_value("translation", "azure_translator_key", "")
        self.region = self.config_manager.get_value("translation", "azure_translator_region", "")
        self.endpoint = "https://api.cognitive.microsofttranslator.com"
        
        # Azure OpenAI settings
        self.openai_key = self.config_manager.get_value("translation", "azure_openai_key", "")
        self.openai_endpoint = self.config_manager.get_value("translation", "azure_openai_endpoint", "")
        self.openai_deployment = self.config_manager.get_value("translation", "azure_openai_deployment", "")
        self.openai_prompt = self.config_manager.get_value("translation", "azure_openai_prompt", 
            "Traduza para {target_language}:")
        self.openai_system_prompt = self.config_manager.get_value("translation", "azure_openai_system_prompt", 
            "Você é um tradutor profissional. Traduza o texto exatamente como fornecido, mantendo o significado original.")
            
        # Cache de traduções para melhorar o desempenho
        self.translation_cache = {}
        self.max_cache_size = 100  # Número máximo de traduções em cache
        
        # Configurações de timeout para melhorar o desempenho
        self.timeout = 5  # Timeout em segundos para requisições
        
        # Contadores para controle de reinicialização periódica
        self.translation_count = 0
        self.last_reset_time = time.time()
        self.max_translations_before_reset = 100  # Reiniciar após 100 traduções
        self.reset_time_threshold = 1800  # Ou após 30 minutos (1800 segundos)
    
    def update_credentials(self, api_key=None, region=None):
        """Update the Azure Translator credentials"""
        # Se os parâmetros não forem fornecidos, obter do config_manager
        if api_key is None:
            api_key = self.config_manager.get_value("translation", "azure_translator_key", "")
        if region is None:
            region = self.config_manager.get_value("translation", "azure_translator_region", "")
            
        old_key = self.api_key
        old_region = self.region
        
        self.api_key = api_key
        self.region = region
        
        # Salvar no config_manager
        self.config_manager.set_value("translation", "azure_translator_key", api_key)
        self.config_manager.set_value("translation", "azure_translator_region", region)
        self.config_manager.save_config()
        
        # Registrar informações detalhadas para diagnóstico
        if not self.api_key:
            logger.error("Azure Translator API key is empty or not configured")
        else:
            # Mostrar apenas parte da chave por segurança
            masked_key = self.api_key[:5] + "..." + self.api_key[-5:] if len(self.api_key) > 10 else "***"
            logger.info(f"Azure Translator API key configured: {masked_key}")
        
        if not self.region:
            logger.error("Azure Translator region is empty or not configured")
        else:
            logger.info(f"Azure Translator region configured: {self.region}")
        
        # Verificar se as credenciais são válidas
        if self.api_key and self.region:
            logger.info("Azure Translator credentials are valid")
            
            # Verificar se as credenciais mudaram
            if self.api_key != old_key or self.region != old_region:
                logger.info("Azure Translator credentials updated")
            
            # Testar a conexão com as novas credenciais
            return self.test_connection()
        else:
            logger.warning("Azure Translator credentials are invalid or incomplete")
            return {
                "success": False,
                "message": "Azure Translator credentials are invalid or incomplete"
            }
    
    def is_configured(self):
        """Check if the Azure Translator service is configured"""
        try:
            # Usar as mesmas chaves de configuração que o método __init__
            api_key = self.config_manager.get_value("translation", "azure_translator_key", "")
            region = self.config_manager.get_value("translation", "azure_translator_region", "")
            
            if not api_key or not region:
                logger.error("Azure Translator is not configured")
                return False
            
            # Atualizar as propriedades da instância, caso tenham sido alteradas externamente
            if api_key != self.api_key or region != self.region:
                logger.warning("Updating Azure Translator credentials from config")
                self.api_key = api_key
                self.region = region
            
            return True
        except Exception as e:
            logger.error(f"Error checking Azure Translator configuration: {str(e)}")
            return False
    
    def detect_language(self, text):
        """Detect the language of the text using Azure Translator"""
        try:
            if not text:
                return None
            
            logger.info(f"=== DETECTANDO IDIOMA DO TEXTO: '{text}' ===")
            
            # Verificar se as credenciais estão configuradas
            if not self.is_configured():
                logger.error("Azure Translator credentials are not configured")
                return None
            
            # Construct the URL
            constructed_url = self.endpoint + "/detect"
            
            # Set up the request headers
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Ocp-Apim-Subscription-Region": self.region,
                "Content-type": "application/json",
                "X-ClientTraceId": str(uuid.uuid4())
            }
            
            # Set up the request parameters
            params = {
                "api-version": "3.0"
            }
            
            # Set up the request body
            body = [{
                "text": text
            }]
            
            logger.info(f"Enviando solicitação de detecção de idioma para o Azure Translator...")
            logger.debug(f"URL: {constructed_url}")
            logger.debug(f"Parâmetros: {params}")
            
            # Make the request
            response = requests.post(
                constructed_url,
                params=params,
                headers=headers,
                json=body
            )
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            if result and len(result) > 0:
                detected_language = result[0]["language"]
                confidence = result[0]["score"]
                logger.info(f"Idioma detectado: {detected_language} (confiança: {confidence})")
                return detected_language
            else:
                logger.warning("Nenhum idioma detectado")
                return None
                
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def translate_text(self, text, source_language=None, target_language="en"):
        """Translate text using the configured translation service"""
        try:
            if not text:
                return ""
            
            # Verificar se é necessário reiniciar os recursos
            self._check_and_reset_resources()
            
            # Incrementar o contador de traduções
            self.translation_count += 1
            
            # Obter o idioma alvo da configuração, se não for fornecido explicitamente
            if target_language == "en":
                target_language = self.config_manager.get_value("translation", "target_language", "en")
            
            # Verificar qual serviço de tradução está configurado
            service_name = self.config_manager.get_value("translation", "service", "azure").lower()
            
            # Se o serviço for Azure OpenAI, usar o método específico
            if service_name == "azure_openai":
                logger.info("Usando Azure OpenAI para tradução")
                return self.translate_with_openai(text, source_language, target_language)
            
            # Caso contrário, usar o Azure Translator padrão
            # Verificar se o serviço de tradução está configurado
            if not self.is_configured():
                logger.error("Azure Translator is not configured")
                return text
            
            logger.info("=== INICIANDO TRADUÇÃO COM AZURE TRANSLATOR ===")
            logger.info(f"Texto a ser traduzido: {text}")
            logger.info(f"Idioma de destino: {target_language}")
            
            if source_language:
                logger.info(f"Idioma de origem fornecido: {source_language}")
            
            # Extrair o código de idioma de destino (remover a região, se presente)
            target_lang = target_language.split("-")[0] if "-" in target_language else target_language
            
            logger.info(f"Código de idioma de destino extraído: {target_lang}")
            
            # Detectar o idioma de origem, se não for fornecido
            detected_language = source_language
            if not detected_language:
                detected_language = self.detect_language(text)
            
            # Se o idioma detectado for o mesmo que o idioma de destino, não é necessário traduzir
            if detected_language and detected_language.lower() == target_lang.lower():
                logger.info(f"O idioma detectado/fornecido ({detected_language}) é o mesmo que o idioma de destino ({target_lang}). Não é necessário traduzir.")
                return text
            
            # Construct the URL
            constructed_url = self.endpoint + "/translate"
            
            # Set up the request parameters
            params = {
                "api-version": "3.0",
                "to": target_lang
            }
            
            # Add source language if available
            if detected_language:
                logger.info(f"Adicionando idioma de origem detectado: {detected_language}")
                params["from"] = detected_language
            
            logger.debug(f"URL de tradução: {constructed_url}")
            logger.debug(f"Parâmetros: {params}")
            
            # Set up the request headers
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Ocp-Apim-Subscription-Region": self.region,
                "Content-type": "application/json",
                "X-ClientTraceId": str(uuid.uuid4())
            }
            
            # Set up the request body
            body = [{
                "text": text
            }]
            
            # Make the request
            response = requests.post(
                constructed_url,
                params=params,
                headers=headers,
                json=body
            )
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            if result and len(result) > 0 and "translations" in result[0] and len(result[0]["translations"]) > 0:
                translated_text = result[0]["translations"][0]["text"]
                logger.info(f"Texto traduzido: {translated_text}")
                return translated_text
            else:
                logger.warning("Nenhuma tradução retornada")
                return text
                
        except Exception as e:
            logger.error(f"Error translating text: {str(e)}")
            logger.error(traceback.format_exc())
            return text
        finally:
            # Forçar coleta de lixo para garantir que todos os recursos sejam liberados
            import gc
            gc.collect()
    
    def _check_and_reset_resources(self):
        """Verifica se é necessário reiniciar os recursos do tradutor para evitar problemas de memória"""
        current_time = time.time()
        time_since_last_reset = current_time - self.last_reset_time
        
        # Reiniciar se excedeu o número máximo de traduções ou o tempo limite
        if (self.translation_count >= self.max_translations_before_reset or 
            time_since_last_reset >= self.reset_time_threshold):
            
            logger.warning(f"Reiniciando recursos do tradutor após {self.translation_count} traduções " +
                          f"ou {time_since_last_reset:.1f} segundos desde o último reset")
            
            # Forçar coleta de lixo para liberar recursos
            import gc
            gc.collect()
            
            # Limpar o cache de traduções para evitar crescimento excessivo
            self.translation_cache.clear()
            
            # Resetar contadores
            self.translation_count = 0
            self.last_reset_time = current_time
            
            logger.warning("Recursos do tradutor reiniciados com sucesso")
    
    def translate_with_openai(self, text, source_language=None, target_language="en"):
        """Translate text using Azure OpenAI"""
        try:
            if not text:
                return ""
                
            # Medir o tempo de processamento
            start_time = time.time()
            
            # Verificar se a tradução já está em cache - usar hash para chaves mais curtas
            text_hash = hashlib.md5(text.encode()).hexdigest()
            cache_key = f"{text_hash}|{target_language}"
            if cache_key in self.translation_cache:
                cached_result = self.translation_cache[cache_key]
                logger.warning(f"Usando tradução em cache (economizando tempo)")
                return cached_result
            
            # Para textos muito curtos (menos de 5 palavras), usar tradução direta do Azure Translator
            # que é mais rápida para textos simples
            if len(text.split()) < 5:
                logger.warning("Texto curto, usando Azure Translator para maior velocidade")
                # Extrair o código de idioma de destino (remover a região, se presente)
                target_lang = target_language.split("-")[0] if "-" in target_language else target_language
                
                # Verificar se as credenciais estão configuradas
                if self.api_key and self.region:
                    try:
                        # Configurar a requisição
                        constructed_url = self.endpoint + "/translate"
                        params = {
                            "api-version": "3.0",
                            "to": target_lang
                        }
                        headers = {
                            "Ocp-Apim-Subscription-Key": self.api_key,
                            "Ocp-Apim-Subscription-Region": self.region,
                            "Content-type": "application/json"
                        }
                        body = [{"text": text}]
                        
                        # Fazer a requisição com timeout
                        response = requests.post(constructed_url, params=params, headers=headers, json=body, timeout=10)
                        response.raise_for_status()
                        
                        # Processar a resposta
                        result = response.json()
                        if result and len(result) > 0 and "translations" in result[0]:
                            translated_text = result[0]["translations"][0]["text"]
                            
                            # Adicionar ao cache
                            self.translation_cache[cache_key] = translated_text
                            
                            # Registrar tempo
                            end_time = time.time()
                            logger.warning(f"Tempo de tradução Azure Translator: {end_time - start_time:.3f} segundos")
                            
                            return translated_text
                    except:
                        # Se falhar, continuar com OpenAI
                        pass
            
            # Obter o idioma alvo da configuração, se não for fornecido explicitamente
            if target_language == "en":
                target_language = self.config_manager.get_value("translation", "target_language", "en")
            
            # Verificar se as credenciais do Azure OpenAI estão configuradas
            if not self.openai_key or not self.openai_endpoint or not self.openai_deployment:
                logger.error("Azure OpenAI credentials are not configured")
                return text
            
            # Usar o prompt personalizado definido nas configurações
            # Substituir {target_language} pelo idioma de destino real
            prompt = self.openai_prompt.format(target_language=target_language)
            prompt += f" {text}"
            
            # Registrar o prompt usado para diagnóstico (apenas para log, não para o usuário)
            logger.debug(f"Usando prompt personalizado: {prompt}")
            
            # Configurar a requisição
            api_version = "2023-05-15"
            url = f"{self.openai_endpoint}/openai/deployments/{self.openai_deployment}/chat/completions?api-version={api_version}"
            
            headers = {
                "Content-Type": "application/json",
                "api-key": self.openai_key
            }
            
            # Usar o system prompt personalizado das configurações
            data = {
                "messages": [
                    {"role": "system", "content": self.openai_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0,  # Determinístico para máxima velocidade
                "max_tokens": 500,   # Reduzido para respostas mais rápidas
                "top_p": 1.0,        # Otimizado para melhor desempenho
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            # Fazer a requisição com timeout reduzido
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            # Processar a resposta
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                translated_text = result["choices"][0]["message"]["content"].strip()
                
                # Verificar se a resposta contém o prompt original e removê-lo
                # Isso acontece quando o modelo repete o prompt na resposta
                if translated_text.startswith(self.openai_prompt.format(target_language=target_language)):
                    # Remover o prompt do início da resposta
                    prompt_text = self.openai_prompt.format(target_language=target_language)
                    translated_text = translated_text[len(prompt_text):].strip()
                
                # Verificar se a resposta contém instruções ou o texto original
                instruction_markers = [
                    "Você é um assistente especializado em tradução",
                    "You are an assistant specialized in translation",
                    "Traduza o seguinte texto",
                    "Translate the following text",
                    "mantendo o estilo original",
                    "maintaining the original style"
                ]
                
                # Verificar se a resposta contém algum dos marcadores de instrução
                contains_instructions = any(marker in translated_text for marker in instruction_markers)
                
                if contains_instructions:
                    # Tentar extrair apenas a tradução real
                    # Procurar pelo texto original e pegar o que vem depois
                    if text in translated_text:
                        parts = translated_text.split(text, 1)
                        if len(parts) > 1:
                            translated_text = parts[1].strip()
                    else:
                        # Tentar encontrar a última frase que parece ser a tradução
                        sentences = re.split(r'[.!?]\s+', translated_text)
                        if len(sentences) > 1:
                            # Pegar a última frase que não parece ser uma instrução
                            for sentence in reversed(sentences):
                                if not any(marker in sentence for marker in instruction_markers):
                                    translated_text = sentence.strip()
                                    break
                
                # Registrar o resultado final para diagnóstico
                logger.debug(f"Texto traduzido final: {translated_text}")
                
                # Adicionar ao cache
                self.translation_cache[cache_key] = translated_text
                
                # Limitar o tamanho do cache
                if len(self.translation_cache) > self.max_cache_size:
                    # Remover a entrada mais antiga
                    oldest_key = next(iter(self.translation_cache))
                    del self.translation_cache[oldest_key]
                
                # Registrar tempo
                end_time = time.time()
                logger.warning(f"Tempo de tradução OpenAI: {end_time - start_time:.3f} segundos")
                
                return translated_text
            else:
                logger.error("No translation result from OpenAI")
                return text
                
        except Exception as e:
            logger.error(f"Error translating with OpenAI: {str(e)}")
            logger.error(traceback.format_exc())
            return text
        finally:
            # Forçar coleta de lixo para garantir que todos os recursos sejam liberados
            import gc
            gc.collect()
    
    def test_connection(self):
        """Test the connection to Azure Translator API"""
        if not self.api_key or not self.region:
            return {
                "success": False,
                "message": "Azure Translator credentials not configured"
            }
        
        try:
            # Just check if the credentials are valid by making a simple request
            path = '/languages'
            params = {
                'api-version': '3.0',
                'scope': 'translation'
            }
            
            constructed_url = self.endpoint + path
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key,
                'Ocp-Apim-Subscription-Region': self.region,
                'Content-type': 'application/json'
            }
            
            response = requests.get(
                constructed_url,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            
            # If we get here, the connection was successful
            return {
                "success": True,
                "message": "Successfully connected to Azure Translator API"
            }
            
        except Exception as e:
            logger.error(f"Azure Translator API connection test failed: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to connect to Azure Translator API: {str(e)}"
            } 