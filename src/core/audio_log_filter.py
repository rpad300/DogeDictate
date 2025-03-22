#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audio Log Filter Module for DogeDictate
"""

import logging
import wave
import struct
import os
import time
from datetime import datetime

def setup_dictation_log_filters():
    """Set up custom filters for dictation logging"""
    # Add filter to main logger to prevent binary audio data from being logged
    root_logger = logging.getLogger()
    root_logger.addFilter(AudioLogFilter())

class AudioLogFilter(logging.Filter):
    """
    Filter to prevent audio binary data from being logged
    """
    
    def filter(self, record):
        """
        Filter log records to avoid logging binary audio data
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: True if record should be logged, False otherwise
        """
        # Skip filtering for non-string messages
        if not isinstance(record.msg, str):
            return True
            
        # Check if message contains binary audio data
        is_binary = False
        try:
            if record.msg and len(record.msg) > 1000:
                # Check if this looks like binary data
                binary_chars = 0
                sample = record.msg[:1000]
                for c in sample:
                    if not (32 <= ord(c) <= 126 or ord(c) in (9, 10, 13)):
                        binary_chars += 1
                
                # If more than 10% of characters are non-printable, treat as binary
                if binary_chars / len(sample) > 0.1:
                    is_binary = True
        except:
            pass
        
        # If it looks like binary data, replace with placeholder
        if is_binary:
            record.msg = "<binary audio data>"
            
        return True

def save_debug_audio(audio_data, directory="src/debug"):
    """
    Save audio data for debugging purposes
    
    Args:
        audio_data (bytes): Audio data to save
        directory (str, optional): Directory to save to. Defaults to "src/debug".
    
    Returns:
        str: Path to saved file or empty string if failed
    """
    try:
        # Create directory if needed
        os.makedirs(directory, exist_ok=True)
        
        # Generate filename based on timestamp
        timestamp = int(time.time())
        filename = os.path.join(directory, f"audio_debug_{timestamp}.wav")
        
        # Convert raw audio data to WAV
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)  # 16kHz
            wav_file.writeframes(audio_data)
            
        return filename
    except Exception as e:
        logging.error(f"Failed to save debug audio: {str(e)}")
        return "" 