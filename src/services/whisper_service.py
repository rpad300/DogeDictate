#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Whisper Service for DogeDictate
Handles speech recognition using OpenAI's Whisper API
"""

import os
import logging
import requests
import json
from openai import OpenAI

logger = logging.getLogger("DogeDictate.WhisperService")

class WhisperService:
    """Service for speech recognition using OpenAI's Whisper API"""
    
    def __init__(self, config_manager):
        """Initialize the Whisper service"""
        self.config_manager = config_manager
        self.api_key = self.config_manager.get_value("recognition", "whisper_api_key", "")
        self.client = None
        
        # Initialize client if API key is available
        if self.api_key:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the OpenAI client"""
        try:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("Whisper client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Whisper client: {str(e)}")
            self.client = None
    
    def recognize_speech(self, audio_data, language=None):
        """
        Recognize speech from audio data
        
        Args:
            audio_data (bytes): Audio data in bytes format
            language (str, optional): Language code (e.g., "en-US")
            
        Returns:
            str: Recognized text
        """
        if not self.api_key:
            logger.error("Whisper API key not configured")
            return ""
            
        try:
            import io
            import tempfile
            import os
            
            # Save audio data to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                temp_file.write(audio_data)
            
            # Open the file for the API request
            with open(temp_filename, "rb") as audio_file:
                # Set up OpenAI client
                client = OpenAI(api_key=self.api_key)
                
                # Set language parameter if provided
                language_param = None
                if language:
                    # Convert language code to ISO 639-1 format (e.g., "en-US" -> "en")
                    language_param = language.split('-')[0]
                
                # Make the API request
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language_param
                )
                
                # Clean up temporary file
                try:
                    os.unlink(temp_filename)
                except Exception:
                    pass
                
                # Return the transcribed text
                return response.text
            
        except Exception as e:
            logger.error(f"Error recognizing speech: {str(e)}")
            return ""
    
    def test_connection(self):
        """Test the connection to the Whisper API"""
        if not self.api_key:
            return {
                "success": False,
                "message": "Whisper API key not configured"
            }
        
        try:
            # Initialize client if not already done
            if not self.client:
                self._initialize_client()
            
            # Simple API call to check if the key is valid
            # We'll use the models endpoint as it's lightweight
            response = self.client.models.list()
            
            # If we get here, the API key is valid
            return {
                "success": True,
                "message": "Successfully connected to Whisper API"
            }
        
        except Exception as e:
            logger.error(f"Whisper API connection test failed: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to connect to Whisper API: {str(e)}"
            }
    
    def update_api_key(self, api_key):
        """Update the Whisper API key"""
        self.api_key = api_key
        self.config_manager.set_value("recognition", "whisper_api_key", api_key)
        
        # Re-initialize client with new API key
        self._initialize_client()
        
        return self.test_connection() 