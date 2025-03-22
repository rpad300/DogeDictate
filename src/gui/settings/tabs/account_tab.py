"""
Aba de configuração de conta.
"""

import logging

from .base_tab import BaseTab

logger = logging.getLogger("DogeDictate.SettingsDialog.AccountTab")

class AccountTab(BaseTab):
    """Aba de configuração de conta"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(config_manager, parent)
        
        # Adicionar conteúdo da aba de conta aqui
    
    def load_settings(self):
        """Carregar configurações do config_manager"""
        pass
    
    def save_settings(self):
        """Salvar configurações no config_manager"""
        pass 