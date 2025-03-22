#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Services for DogeDictate
"""

from src.services.whisper_service import WhisperService
from src.services.azure_service import AzureService
from src.services.google_service import GoogleService
from src.services.translator_service import TranslatorService
from src.services.stats_service import StatsService
from src.services.local_whisper_service import LocalWhisperService
from src.services.local_llm_translator_service import LocalLLMTranslatorService

# Imports para compatibilidade
from src.services.azure_translator_service import AzureTranslatorService
from src.services.m2m100_translator_service import M2M100TranslatorService
from src.services.azure_openai_service import AzureOpenAIService

__all__ = [
    'WhisperService', 
    'AzureService', 
    'GoogleService', 
    'TranslatorService',
    'StatsService',
    'LocalWhisperService',
    'LocalLLMTranslatorService',
    'AzureTranslatorService',
    'M2M100TranslatorService',
    'AzureOpenAIService'
] 