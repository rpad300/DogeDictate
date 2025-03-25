"""
Diálogo de configurações principal para a aplicação DogeDictate.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox,
    QSystemTrayIcon, QMenu, QMessageBox, QApplication
)
from PyQt5.QtGui import QIcon
import os
import logging

from .tabs.general_tab import GeneralTab
from .tabs.languages_tab import LanguagesTab
from .tabs.apis_tab import APIsTab
from .tabs.local_tab import LocalTab
from .tabs.plan_tab import PlanTab
from .tabs.account_tab import AccountTab
from .tabs.stats_tab import StatsTab
from src.i18n import get_instance as get_i18n, _

logger = logging.getLogger("DogeDictate.SettingsDialog")

class SettingsDialog(QDialog):
    def __init__(self, config_manager, dictation_manager=None, hotkey_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.dictation_manager = dictation_manager
        self.hotkey_manager = hotkey_manager
        
        # Obter o idioma atual
        i18n = get_i18n()
        
        self.setWindowTitle(_("settings_title", "Settings"))
        self.setMinimumWidth(600)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.general_tab = GeneralTab(config_manager, dictation_manager, hotkey_manager)
        self.languages_tab = LanguagesTab(config_manager, dictation_manager)
        self.apis_tab = APIsTab(config_manager)
        self.local_tab = LocalTab(config_manager)
        self.plan_tab = PlanTab(config_manager)
        self.account_tab = AccountTab(config_manager)
        self.stats_tab = StatsTab(config_manager, self)
        
        # Add tabs to widget
        self.tab_widget.addTab(self.general_tab, _("general_tab", "General"))
        self.tab_widget.addTab(self.languages_tab, _("languages_tab", "Languages"))
        self.tab_widget.addTab(self.apis_tab, _("apis_tab", "APIs"))
        self.tab_widget.addTab(self.local_tab, _("local_tab", "Local Services"))
        self.tab_widget.addTab(self.stats_tab, _("stats_tab", "Statistics"))
        self.tab_widget.addTab(self.plan_tab, _("plan_tab", "Plan"))
        self.tab_widget.addTab(self.account_tab, _("account_tab", "Account"))
        
        # Create button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Traduzir os botões padrão
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText(_("ok", "OK"))
        
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText(_("cancel", "Cancel"))
        
        layout.addWidget(button_box)
        
        # Load settings
        self._load_settings()
        
        # Armazenar o idioma atual para comparação posterior
        current_language = self.config_manager.get_value("interface", "language", "en")
        self.old_language = current_language
    
    def _load_settings(self):
        """Load settings from config manager"""
        self.general_tab.load_settings()
        self.languages_tab.load_settings()
        self.apis_tab.load_settings()
        self.local_tab.load_settings()
        self.stats_tab.load_settings()
        self.plan_tab.load_settings()
        self.account_tab.load_settings()
    
    def _update_translations(self):
        """Atualizar traduções da interface"""
        # Obter o idioma atual
        i18n = get_i18n()
        
        # Atualizar título da janela
        self.setWindowTitle(_("settings_title", "Settings"))
        
        # Atualizar títulos das abas
        self.tab_widget.setTabText(0, _("general_tab", "General"))
        self.tab_widget.setTabText(1, _("languages_tab", "Languages"))
        self.tab_widget.setTabText(2, _("apis_tab", "APIs"))
        self.tab_widget.setTabText(3, _("local_tab", "Local Services"))
        self.tab_widget.setTabText(4, _("stats_tab", "Statistics"))
        self.tab_widget.setTabText(5, _("plan_tab", "Plan"))
        self.tab_widget.setTabText(6, _("account_tab", "Account"))
        
        # Atualizar botões
        button_box = self.findChild(QDialogButtonBox)
        if button_box:
            ok_button = button_box.button(QDialogButtonBox.Ok)
            if ok_button:
                ok_button.setText(_("ok", "OK"))
            
            cancel_button = button_box.button(QDialogButtonBox.Cancel)
            if cancel_button:
                cancel_button.setText(_("cancel", "Cancel"))
    
    def accept(self):
        """Save settings when OK is clicked"""
        try:
            # Armazenar o idioma atual antes de salvar
            old_language = self.old_language
            
            # Save settings from each tab
            self.general_tab.save_settings()
            self.languages_tab.save_settings()
            self.apis_tab.save_settings()
            self.local_tab.save_settings()
            self.stats_tab.save_settings()
            self.plan_tab.save_settings()
            self.account_tab.save_settings()
            
            # Salvar configurações no disco com force=True para garantir que seja salvo imediatamente
            self.config_manager.save_config(force=True)
            
            logger.info("Settings saved")
            
            # Verificar se o idioma foi alterado
            current_language = self.config_manager.get_value("interface", "language", "")
            
            if old_language != current_language:
                # Mostrar mensagem sobre reinicialização
                QMessageBox.information(
                    self,
                    _("language_changed_title", "Language Changed"),
                    _("language_changed_message", "The interface language has been changed. Restart the application to apply the changes.")
                )
            
            # Fechar o diálogo
            super().accept()
        
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            QMessageBox.critical(
                self,
                _("error_title", "Error"),
                _("error_saving_settings", "Error saving settings: {error}").format(error=str(e))
            )
    
    def close_application(self):
        """Close the application"""
        # Confirm before closing
        reply = QMessageBox.question(
            self,
            _("confirm_exit_title", "Confirmar Saída"),
            _("confirm_exit_message", "Tem certeza que deseja sair da aplicação?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Close the application
            QApplication.instance().quit()
    
    def closeEvent(self, event):
        """Handle close event"""
        # Check if we should minimize to tray instead of closing
        minimize_to_tray = self.config_manager.get_value("general", "minimize_to_tray", True)
        
        if minimize_to_tray and QSystemTrayIcon.isSystemTrayAvailable():
            # Minimize to tray instead of closing
            self.hide()
            event.ignore()
        else:
            # Close normally
            event.accept()
    
    def save_without_closing(self):
        """Save settings without closing the dialog"""
        try:
            # Armazenar o idioma atual antes de salvar
            old_language = self.old_language
            
            # Save settings from each tab
            self.general_tab.save_settings()
            self.languages_tab.save_settings()
            self.apis_tab.save_settings()
            self.local_tab.save_settings()
            self.stats_tab.save_settings()
            self.plan_tab.save_settings()
            self.account_tab.save_settings()
            
            # Salvar configurações no disco
            self.config_manager.save_config()
            
            # Verificar se o idioma foi alterado
            current_language = self.config_manager.get_value("interface", "language", "")
            
            if old_language != current_language:
                # Atualizar o idioma armazenado
                self.old_language = current_language
                
                # Mostrar mensagem sobre reinicialização
                QMessageBox.information(
                    self,
                    _("language_changed_title", "Language Changed"),
                    _("language_changed_message", "The interface language has been changed. Restart the application to apply the changes.")
                )
            
            logger.info("Settings saved without closing")
            
            # Show success message
            QMessageBox.information(
                self,
                _("settings_saved_title", "Settings Saved"),
                _("settings_saved_message", "Settings have been saved successfully.")
            )
        
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            QMessageBox.critical(
                self,
                _("error_title", "Error"),
                _("error_saving_settings", "Error saving settings: {error}").format(error=str(e))
            ) 