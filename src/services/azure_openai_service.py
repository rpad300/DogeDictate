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
            url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/completions?api-version=2023-05-15"
            
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            data = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "stop": None
            }
            
            self.logger.info("Sending request to Azure OpenAI")
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            response_data = response.json()
            
            if "choices" in response_data and len(response_data["choices"]) > 0:
                return response_data["choices"][0]["text"].strip()
                
            return ""
            
        except Exception as e:
            self.logger.error(f"Error generating text with Azure OpenAI: {str(e)}")
            return "" 