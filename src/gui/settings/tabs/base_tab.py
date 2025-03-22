"""
Classe base para as abas de configuração.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout

class BaseTab(QWidget):
    """Classe base para todas as abas de configuração"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        
        # Configurar layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(16)
    
    def load_settings(self):
        """Carregar configurações do config_manager"""
        pass
    
    def save_settings(self):
        """Salvar configurações no config_manager"""
        pass 