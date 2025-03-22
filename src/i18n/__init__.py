#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Internationalization module for DogeDictate
Handles translations for the user interface
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("DogeDictate.I18n")

class I18n:
    """Internationalization manager for DogeDictate"""
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "pt": "Português",
        "fr": "Français",
        "es": "Español"
    }
    
    # Default language
    DEFAULT_LANGUAGE = "en"
    
    def __init__(self, config_manager=None):
        """Initialize the internationalization manager"""
        self.config_manager = config_manager
        self.translations = {}
        self.current_language = self.DEFAULT_LANGUAGE
        
        # Load translations
        self._load_translations()
        
        # Set language from config if available
        if config_manager:
            self.set_language(config_manager.get_value("interface", "language", self.DEFAULT_LANGUAGE))
    
    def _load_translations(self):
        """Load all translation files"""
        try:
            # Get the translations directory
            translations_dir = self._get_translations_dir()
            
            # Load each language file
            for lang_code in self.SUPPORTED_LANGUAGES.keys():
                lang_file = os.path.join(translations_dir, f"{lang_code}.json")
                
                if os.path.exists(lang_file):
                    with open(lang_file, "r", encoding="utf-8") as f:
                        self.translations[lang_code] = json.load(f)
                    logger.info(f"Loaded translations for {lang_code}")
                else:
                    logger.warning(f"Translation file not found for {lang_code}")
                    self.translations[lang_code] = {}
        
        except Exception as e:
            logger.error(f"Error loading translations: {str(e)}")
            # Initialize with empty translations
            for lang_code in self.SUPPORTED_LANGUAGES.keys():
                self.translations[lang_code] = {}
    
    def _get_translations_dir(self):
        """Get the translations directory"""
        # Try to find the translations directory
        possible_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "resources", "translations"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "translations")
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                return path
        
        # If not found, create the directory
        default_path = possible_paths[0]
        os.makedirs(default_path, exist_ok=True)
        return default_path
    
    def set_language(self, language_code):
        """Set the current language"""
        if language_code in self.SUPPORTED_LANGUAGES:
            self.current_language = language_code
            logger.info(f"Language set to {language_code}")
            
            # Save to config if available
            if self.config_manager:
                self.config_manager.set_value("interface", "language", language_code)
                self.config_manager.save_config()
            
            return True
        else:
            logger.warning(f"Unsupported language: {language_code}, using default")
            self.current_language = self.DEFAULT_LANGUAGE
            return False
    
    def get_language(self):
        """Get the current language code"""
        return self.current_language
    
    def get_language_name(self, language_code=None):
        """Get the name of the specified language"""
        if language_code is None:
            language_code = self.current_language
        
        return self.SUPPORTED_LANGUAGES.get(language_code, self.SUPPORTED_LANGUAGES[self.DEFAULT_LANGUAGE])
    
    def get_supported_languages(self):
        """Get a list of supported languages"""
        return [{"code": code, "name": name} for code, name in self.SUPPORTED_LANGUAGES.items()]
    
    def translate(self, key, default=None):
        """Translate a key to the current language"""
        # Try to get the translation for the current language
        translation = self.translations.get(self.current_language, {}).get(key)
        
        # If not found, try the default language
        if translation is None and self.current_language != self.DEFAULT_LANGUAGE:
            translation = self.translations.get(self.DEFAULT_LANGUAGE, {}).get(key)
        
        # If still not found, use the provided default or the key itself
        if translation is None:
            translation = default if default is not None else key
        
        return translation

# Create a global instance
_i18n = None

def init(config_manager=None):
    """Initialize the internationalization system"""
    global _i18n
    _i18n = I18n(config_manager)
    return _i18n

def get_instance():
    """Get the global I18n instance"""
    global _i18n
    if _i18n is None:
        _i18n = I18n()
    return _i18n

def _(key, default=None):
    """Shorthand for translate"""
    return get_instance().translate(key, default) 