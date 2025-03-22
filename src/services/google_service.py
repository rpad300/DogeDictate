#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Service for DogeDictate
Handles speech recognition using Google Speech-to-Text
"""

import os
import logging
from google.cloud import speech
from google.oauth2 import service_account

logger = logging.getLogger("DogeDictate.GoogleService")

class GoogleService:
    """Service for speech recognition using Google Speech-to-Text"""
    
    def __init__(self, config_manager):
        """Initialize the Google service"""
        self.config_manager = config_manager
        self.credentials_path = self.config_manager.get_value(
            "recognition", "google_credentials_path", ""
        )
        self.client = None
        
        # Initialize client if credentials are available
        if self.credentials_path and os.path.exists(self.credentials_path):
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Google Speech-to-Text client"""
        try:
            # Create credentials from the JSON file
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path
            )
            
            # Create the client
            self.client = speech.SpeechClient(credentials=credentials)
            logger.info("Google Speech-to-Text client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Speech-to-Text client: {str(e)}")
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
        if not self.client:
            logger.error("Google Speech client not initialized")
            return ""
            
        try:
            # Create RecognitionAudio object directly from bytes
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Set up RecognitionConfig
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language if language else "en-US",
                enable_automatic_punctuation=True
            )
            
            # Perform speech recognition
            response = self.client.recognize(config=config, audio=audio)
            
            # Extract and return the transcribed text
            transcript = ""
            for result in response.results:
                transcript += result.alternatives[0].transcript
            
            return transcript
            
        except Exception as e:
            logger.error(f"Error recognizing speech: {str(e)}")
            return ""
    
    def test_connection(self):
        """Test the connection to Google Speech-to-Text"""
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            return {
                "success": False,
                "message": "Google Speech-to-Text credentials not configured or file not found"
            }
        
        try:
            # Initialize client if not already done
            if not self.client:
                self._initialize_client()
            
            # If client initialization failed, return error
            if not self.client:
                return {
                    "success": False,
                    "message": "Failed to initialize Google Speech-to-Text client"
                }
            
            # List available operations (this will fail if credentials are invalid)
            self.client.operations.list()
            
            # If we get here, the credentials are valid
            return {
                "success": True,
                "message": "Successfully connected to Google Speech-to-Text"
            }
        
        except Exception as e:
            logger.error(f"Google Speech-to-Text connection test failed: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to connect to Google Speech-to-Text: {str(e)}"
            }
    
    def update_credentials_path(self, credentials_path):
        """Update the Google Speech-to-Text credentials path"""
        if not os.path.exists(credentials_path):
            return {
                "success": False,
                "message": f"Credentials file not found: {credentials_path}"
            }
        
        self.credentials_path = credentials_path
        self.config_manager.set_value("recognition", "google_credentials_path", credentials_path)
        
        # Re-initialize client with new credentials
        self._initialize_client()
        
        return self.test_connection() 