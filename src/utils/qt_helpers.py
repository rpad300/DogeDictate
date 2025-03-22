#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Qt Helper utilities for DogeDictate
"""

import logging
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger("DogeDictate.QtHelpers")

class QVectorSignalHelper(QObject):
    """Helper class to handle list signals"""
    # Usar list em vez de list
    vectorSignal = pyqtSignal(list)
    
    def __init__(self):
        """Initialize the helper"""
        super().__init__()
        logger.info("QVectorSignalHelper initialized")
    
    def register_types():
        """Register Qt metatypes"""
        try:
            # Tentar registrar list
            from PyQt5.QtCore import QMetaType
            QMetaType.type("list")
            logger.info("Registered list metatype using QMetaType.type")
            return True
        except Exception as e:
            logger.warning(f"Failed to register list using QMetaType.type: {str(e)}")
            
            # Tentar método alternativo
            try:
                from PyQt5.QtCore import qRegisterMetaType
                qRegisterMetaType("list")
                logger.info("Registered list metatype using qRegisterMetaType")
                return True
            except Exception as e2:
                logger.warning(f"Failed to register list using qRegisterMetaType: {str(e2)}")
                return False
