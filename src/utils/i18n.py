#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de internacionalização para DogeDictate
"""

import os
import json
import logging

logger = logging.getLogger("DogeDictate.I18n")

# Dicionário de traduções
translations = {
    "en": {},  # Inglês (padrão)
    "pt": {},  # Português
    "fr": {},  # Francês
    "es": {}   # Espanhol
}

# Linguagem atual
current_language = "en"

def load_translations():
    """Carregar traduções de arquivos JSON"""
    global translations
    
    try:
        # Determinar diretório base do projeto
        script_dir = os.path.dirname(os.path.abspath(__file__))
        i18n_dir = os.path.join(os.path.dirname(script_dir), "i18n")
        translations_dir = os.path.join(i18n_dir, "translations")
        
        if not os.path.exists(translations_dir):
            logger.warning(f"Diretório de traduções não encontrado: {translations_dir}")
            translations_dir = os.path.join(script_dir, "..", "i18n", "translations")
            
            if not os.path.exists(translations_dir):
                logger.warning(f"Diretório alternativo de traduções não encontrado: {translations_dir}")
                return
        
        # Carregar arquivos de traduções para cada idioma
        for lang in translations.keys():
            lang_file = os.path.join(translations_dir, f"{lang}.json")
            
            if os.path.exists(lang_file):
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        translations[lang] = json.load(f)
                    logger.info(f"Loaded translations for {lang}")
                except Exception as e:
                    logger.error(f"Error loading translations for {lang}: {str(e)}")
            else:
                logger.warning(f"Translation file not found: {lang_file}")
    except Exception as e:
        logger.error(f"Error loading translations: {str(e)}")

def _(key, default=None, **kwargs):
    """
    Função de tradução
    
    Args:
        key: Chave de tradução
        default: Texto padrão se a tradução não for encontrada
        **kwargs: Parâmetros para formatação
        
    Returns:
        str: Texto traduzido
    """
    global translations, current_language
    
    # Se não há traduções carregadas, tentar carregar
    if not any(translations.values()):
        load_translations()
    
    # Tentar obter tradução no idioma atual
    text = translations.get(current_language, {}).get(key)
    
    # Se não encontrar, tentar em inglês
    if text is None and current_language != "en":
        text = translations.get("en", {}).get(key)
    
    # Se ainda não encontrar, usar o padrão ou a própria chave
    if text is None:
        text = default if default is not None else key
    
    # Aplicar formatação se houver parâmetros
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception as e:
            logger.error(f"Error formatting translation for {key}: {str(e)}")
            return text
    
    return text

def set_language(lang):
    """
    Definir idioma atual
    
    Args:
        lang: Código do idioma (en, pt, fr, es)
    """
    global current_language
    
    if lang in translations:
        current_language = lang
        logger.info(f"Language set to {lang}")
    else:
        logger.warning(f"Unsupported language: {lang}, using default (en)")
        current_language = "en"

def get_language():
    """
    Obter idioma atual
    
    Returns:
        str: Código do idioma atual
    """
    return current_language

def get_available_languages():
    """
    Obter lista de idiomas disponíveis
    
    Returns:
        list: Lista de códigos de idiomas disponíveis
    """
    return list(translations.keys())

def init_i18n(config_manager=None):
    """
    Inicializar o sistema de internacionalização
    
    Args:
        config_manager: Gerenciador de configuração (opcional)
        
    Returns:
        object: Instância do módulo para ser usada pela aplicação
    """
    # Carregar traduções
    load_translations()
    
    # Definir idioma a partir da configuração, se disponível
    if config_manager:
        try:
            lang = config_manager.get_value("interface", "language", "en")
            set_language(lang)
        except Exception as e:
            logger.error(f"Error getting language from config: {str(e)}")
    
    # Retornar o próprio módulo como uma instância
    return sys.modules[__name__]

# Importar sys para retornar o módulo
import sys 