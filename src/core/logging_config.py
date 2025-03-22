#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuração de logging para o DogeDictate
"""

import logging
import os
import sys

def configure_logging():
    """Configurar o logging para o DogeDictate"""
    # Configurar o logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Configurar o formato do log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Configurar o handler para o console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Adicionar o handler ao logger raiz
    root_logger.addHandler(console_handler)
    
    # Configurar loggers específicos
    # Configurar o nível de log para o HotkeyManager para INFO para mostrar apenas mensagens importantes
    # e evitar logs de diagnóstico que são muito detalhados
    logging.getLogger("DogeDictate.HotkeyManager").setLevel(logging.INFO)
    
    # Configurar outros loggers conforme necessário
    # ...
    
    return root_logger
