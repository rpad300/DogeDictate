"""
Aba de estatísticas para a aplicação DogeDictate.
"""

from PyQt5.QtWidgets import (
    QFormLayout, QGroupBox, QLabel, QPushButton, QVBoxLayout, 
    QHBoxLayout, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QComboBox, QCheckBox, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QFont
import logging
import datetime

from .base_tab import BaseTab

logger = logging.getLogger("DogeDictate.SettingsDialog.StatsTab")

class StatsTab(BaseTab):
    """Aba de estatísticas para a aplicação DogeDictate"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(config_manager, parent)
        
        # Filtro de datas
        self._create_date_filter_group()
        
        # Estatísticas gerais
        self._create_general_stats_group()
        
        # Estatísticas de uso de API
        self._create_api_usage_group()
        
        # Histórico de sessões
        self._create_session_history_group()
        
        # Botões de ação
        self._create_action_buttons()
        
        # Timer para atualização automática
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.load_settings)
        self.update_timer.start(300000)  # Atualizar a cada 5 minutos (aumentado de 30 segundos)
        
        # Registrar callback para atualização em tempo real
        try:
            # Obter o serviço de estatísticas do dictation_manager
            if parent and hasattr(parent, 'dictation_manager') and parent.dictation_manager:
                self.stats_service = parent.dictation_manager.stats_service
                logger.info(f"Using stats service from dictation_manager: {self.stats_service}")
                
                # Registrar o callback
                self.stats_service.register_update_callback(self.load_settings)
                logger.info("Callback de atualização registrado com sucesso")
                
                # Depurar estatísticas atuais
                debug_info = self.stats_service.debug_stats()
                logger.info(f"Current stats from init: {debug_info}")
            else:
                # Fallback para criar uma nova instância
                from src.services.stats_service import StatsService
                logger.warning("Parent or dictation_manager not available, creating new StatsService instance")
                self.stats_service = StatsService(self.config_manager._get_config_dir())
                self.stats_service.register_update_callback(self.load_settings)
                
                # Depurar estatísticas atuais
                debug_info = self.stats_service.debug_stats()
                logger.info(f"Current stats from init (fallback): {debug_info}")
        except Exception as e:
            logger.error(f"Erro ao registrar callback de atualização: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Fallback para criar uma nova instância em caso de erro
            try:
                from src.services.stats_service import StatsService
                logger.warning("Error occurred, creating new StatsService instance as fallback")
                self.stats_service = StatsService(self.config_manager._get_config_dir())
            except Exception as e2:
                logger.error(f"Failed to create fallback StatsService: {str(e2)}")
    
    def _create_date_filter_group(self):
        """Criar grupo de filtro de datas"""
        filter_group = QGroupBox("Filtro de Datas")
        filter_layout = QHBoxLayout(filter_group)
        
        # Data inicial
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))  # Últimos 30 dias
        filter_layout.addWidget(QLabel("De:"))
        filter_layout.addWidget(self.start_date_edit)
        
        # Data final
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())  # Hoje
        filter_layout.addWidget(QLabel("Até:"))
        filter_layout.addWidget(self.end_date_edit)
        
        # Período predefinido
        self.period_combo = QComboBox()
        self.period_combo.addItem("Personalizado", "custom")
        self.period_combo.addItem("Hoje", "today")
        self.period_combo.addItem("Últimos 7 dias", "last_7_days")
        self.period_combo.addItem("Últimos 30 dias", "last_30_days")
        self.period_combo.addItem("Este mês", "this_month")
        self.period_combo.addItem("Mês passado", "last_month")
        self.period_combo.addItem("Este ano", "this_year")
        self.period_combo.addItem("Tudo", "all")
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        filter_layout.addWidget(QLabel("Período:"))
        filter_layout.addWidget(self.period_combo)
        
        # Botão de aplicar filtro
        apply_button = QPushButton("Aplicar Filtro")
        apply_button.clicked.connect(self._apply_filter)
        filter_layout.addWidget(apply_button)
        
        # Atualização automática
        self.auto_update_check = QCheckBox("Atualização automática")
        self.auto_update_check.setChecked(True)
        self.auto_update_check.stateChanged.connect(self._toggle_auto_update)
        filter_layout.addWidget(self.auto_update_check)
        
        self.layout.addWidget(filter_group)
    
    def _create_general_stats_group(self):
        """Criar grupo de estatísticas gerais"""
        stats_group = QGroupBox("Estatísticas Gerais")
        stats_layout = QFormLayout(stats_group)
        
        # Estatísticas de palavras
        self.total_words_label = QLabel("0")
        self.total_words_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addRow("Total de Palavras Ditadas:", self.total_words_label)
        
        self.translated_words_label = QLabel("0")
        self.translated_words_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addRow("Total de Palavras Traduzidas:", self.translated_words_label)
        
        # Estatísticas de tempo
        self.total_time_label = QLabel("0h 0m")
        self.total_time_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addRow("Tempo Total de Uso:", self.total_time_label)
        
        self.avg_speed_label = QLabel("0")
        self.avg_speed_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addRow("Velocidade Média (palavras/min):", self.avg_speed_label)
        
        # Estatísticas de sessão atual
        self.current_session_label = QLabel("0h 0m")
        self.current_session_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addRow("Tempo da Sessão Atual:", self.current_session_label)
        
        self.current_words_label = QLabel("0")
        self.current_words_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addRow("Palavras na Sessão Atual:", self.current_words_label)
        
        self.layout.addWidget(stats_group)
    
    def _create_api_usage_group(self):
        """Criar grupo de estatísticas de uso de API"""
        api_group = QGroupBox("Uso de API")
        api_layout = QVBoxLayout(api_group)
        
        # Tabela de uso de API
        self.api_table = QTableWidget(0, 3)
        self.api_table.setHorizontalHeaderLabels(["Serviço", "Tokens Usados", "Custo Estimado"])
        self.api_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        api_layout.addWidget(self.api_table)
        
        # Uso total
        total_layout = QHBoxLayout()
        
        self.total_tokens_label = QLabel("Total de Tokens: 0")
        self.total_tokens_label.setFont(QFont("Arial", 10, QFont.Bold))
        total_layout.addWidget(self.total_tokens_label)
        
        self.total_cost_label = QLabel("Custo Total Estimado: $0.00")
        self.total_cost_label.setFont(QFont("Arial", 10, QFont.Bold))
        total_layout.addWidget(self.total_cost_label)
        
        api_layout.addLayout(total_layout)
        
        self.layout.addWidget(api_group)
    
    def _create_session_history_group(self):
        """Criar grupo de histórico de sessões"""
        history_group = QGroupBox("Histórico de Sessões")
        history_layout = QVBoxLayout(history_group)
        
        # Tabela de histórico de sessões
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Data", "Hora", "Duração", "Palavras", "Velocidade Média"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        history_layout.addWidget(self.history_table)
        
        self.layout.addWidget(history_group)
    
    def _create_action_buttons(self):
        """Criar botões de ação"""
        button_layout = QHBoxLayout()
        
        # Botão para atualizar estatísticas
        refresh_button = QPushButton("Atualizar Estatísticas")
        refresh_button.clicked.connect(self.load_settings)
        button_layout.addWidget(refresh_button)
        
        # Botão para exportar estatísticas
        export_button = QPushButton("Exportar Estatísticas")
        export_button.clicked.connect(self._export_statistics)
        button_layout.addWidget(export_button)
        
        # Botão para resetar estatísticas
        reset_button = QPushButton("Resetar Estatísticas")
        reset_button.clicked.connect(self._reset_statistics)
        button_layout.addWidget(reset_button)
        
        self.layout.addLayout(button_layout)
    
    def _on_period_changed(self, index):
        """Atualizar datas quando o período for alterado"""
        period = self.period_combo.currentData()
        
        today = QDate.currentDate()
        
        if period == "today":
            self.start_date_edit.setDate(today)
            self.end_date_edit.setDate(today)
        elif period == "last_7_days":
            self.start_date_edit.setDate(today.addDays(-6))
            self.end_date_edit.setDate(today)
        elif period == "last_30_days":
            self.start_date_edit.setDate(today.addDays(-29))
            self.end_date_edit.setDate(today)
        elif period == "this_month":
            self.start_date_edit.setDate(QDate(today.year(), today.month(), 1))
            self.end_date_edit.setDate(today)
        elif period == "last_month":
            last_month = today.addMonths(-1)
            self.start_date_edit.setDate(QDate(last_month.year(), last_month.month(), 1))
            self.end_date_edit.setDate(QDate(last_month.year(), last_month.month(), last_month.daysInMonth()))
        elif period == "this_year":
            self.start_date_edit.setDate(QDate(today.year(), 1, 1))
            self.end_date_edit.setDate(today)
        elif period == "all":
            self.start_date_edit.setDate(QDate(2000, 1, 1))
            self.end_date_edit.setDate(today)
        
        # Aplicar filtro automaticamente
        self._apply_filter()
    
    def _apply_filter(self):
        """Aplicar filtro de datas"""
        self.load_settings()
    
    def _toggle_auto_update(self, state):
        """Ativar/desativar atualização automática"""
        if state == Qt.Checked:
            self.update_timer.start(300000)
        else:
            self.update_timer.stop()
    
    def _export_statistics(self):
        """Exportar estatísticas para um arquivo CSV"""
        from PyQt5.QtWidgets import QFileDialog
        import csv
        
        # Abrir diálogo para selecionar arquivo
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Estatísticas",
            "",
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Escrever cabeçalho
                writer.writerow(["Estatísticas DogeDictate", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow([])
                
                # Estatísticas gerais
                writer.writerow(["Estatísticas Gerais"])
                writer.writerow(["Total de Palavras Ditadas", self.total_words_label.text()])
                writer.writerow(["Total de Palavras Traduzidas", self.translated_words_label.text()])
                writer.writerow(["Tempo Total de Uso", self.total_time_label.text()])
                writer.writerow(["Velocidade Média (palavras/min)", self.avg_speed_label.text()])
                writer.writerow([])
                
                # Uso de API
                writer.writerow(["Uso de API"])
                writer.writerow(["Serviço", "Tokens Usados", "Custo Estimado"])
                
                for row in range(self.api_table.rowCount()):
                    service = self.api_table.item(row, 0).text()
                    tokens = self.api_table.item(row, 1).text()
                    cost = self.api_table.item(row, 2).text()
                    writer.writerow([service, tokens, cost])
                
                writer.writerow([])
                writer.writerow(["Total de Tokens", self.total_tokens_label.text().replace("Total de Tokens: ", "")])
                writer.writerow(["Custo Total Estimado", self.total_cost_label.text().replace("Custo Total Estimado: ", "")])
                writer.writerow([])
                
                # Histórico de sessões
                writer.writerow(["Histórico de Sessões"])
                writer.writerow(["Data", "Hora", "Duração", "Palavras", "Velocidade Média"])
                
                for row in range(self.history_table.rowCount()):
                    date = self.history_table.item(row, 0).text()
                    time = self.history_table.item(row, 1).text()
                    duration = self.history_table.item(row, 2).text()
                    words = self.history_table.item(row, 3).text()
                    speed = self.history_table.item(row, 4).text()
                    writer.writerow([date, time, duration, words, speed])
            
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Exportar Estatísticas", "Estatísticas exportadas com sucesso!")
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Erro", f"Erro ao exportar estatísticas: {str(e)}")
    
    def _reset_statistics(self):
        """Resetar estatísticas"""
        from PyQt5.QtWidgets import QMessageBox
        
        # Confirmar reset
        reply = QMessageBox.question(
            self,
            "Resetar Estatísticas",
            "Tem certeza que deseja resetar todas as estatísticas? Esta ação não pode ser desfeita.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Resetar estatísticas
            self.stats_service.reset_statistics()
            
            # Atualizar interface
            self.load_settings()
            
            QMessageBox.information(self, "Resetar Estatísticas", "Estatísticas resetadas com sucesso!")
    
    def _update_api_usage_table(self):
        """Atualizar tabela de uso de API"""
        try:
            # Obter uso de API
            api_usage = self.config_manager.get_value("statistics", "api_usage", {})
            
            # Log para depuração
            logger.debug(f"API usage: {api_usage}")
            
            # Limpar tabela
            self.api_table.setRowCount(0)
            
            # Definir número de linhas
            self.api_table.setRowCount(len(api_usage))
            
            # Preencher tabela
            total_tokens = 0
            total_cost = 0.0
            
            # Mapeamento de serviços para nomes amigáveis
            service_names = {
                "azure_speech": "Azure Speech Services",
                "whisper_api": "OpenAI Whisper API",
                "google_speech": "Google Speech-to-Text",
                "whisper_local": "Local Whisper",
                "azure_translator": "Azure Translator",
                "azure_openai": "Azure OpenAI",
                "m2m100": "M2M100 (Local)"
            }
            
            # Mapeamento de serviços para custos estimados por 1000 tokens
            service_costs = {
                "azure_speech": 0.016,  # $0.016 por 1000 tokens
                "whisper_api": 0.006,   # $0.006 por 1000 tokens
                "google_speech": 0.016, # $0.016 por 1000 tokens
                "whisper_local": 0.0,   # Gratuito (local)
                "azure_translator": 0.01, # $0.01 por 1000 tokens
                "azure_openai": 0.01,   # $0.01 por 1000 tokens
                "m2m100": 0.0           # Gratuito (local)
            }
            
            row = 0
            for service, tokens in api_usage.items():
                # Verificar se tokens é um número válido
                if not isinstance(tokens, (int, float)):
                    logger.error(f"Invalid token count for service {service}: {tokens}")
                    continue
                
                # Nome do serviço
                service_name = service_names.get(service, service)
                service_item = QTableWidgetItem(service_name)
                self.api_table.setItem(row, 0, service_item)
                
                # Tokens usados
                tokens_item = QTableWidgetItem(f"{tokens:,}".replace(",", "."))
                tokens_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.api_table.setItem(row, 1, tokens_item)
                
                # Custo estimado
                cost = (tokens / 1000) * service_costs.get(service, 0.0)
                cost_item = QTableWidgetItem(f"${cost:.2f}")
                cost_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.api_table.setItem(row, 2, cost_item)
                
                # Atualizar totais
                total_tokens += tokens
                total_cost += cost
                
                row += 1
            
            # Atualizar labels de totais
            self.total_tokens_label.setText(f"Total de Tokens: {total_tokens:,}".replace(",", "."))
            self.total_cost_label.setText(f"Custo Total Estimado: ${total_cost:.2f}")
        except Exception as e:
            logger.error(f"Error updating API usage table: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _update_session_history_table(self):
        """Atualizar tabela de histórico de sessões"""
        try:
            # Obter histórico de sessões
            session_history = self.config_manager.get_value("statistics", "session_history", [])
            
            # Log para depuração
            logger.debug(f"Session history: {session_history}")
            
            # Limpar tabela
            self.history_table.setRowCount(0)
            
            # Obter datas do filtro
            start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
            end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
            
            # Filtrar sessões pelo período
            filtered_sessions = []
            for session in session_history:
                # Verificar se session é um dicionário válido
                if not isinstance(session, dict):
                    logger.error(f"Invalid session record: {session}")
                    continue
                
                # Verificar se a sessão tem os campos necessários
                if "date" not in session:
                    logger.error(f"Session record is missing date field: {session}")
                    continue
                
                session_date = session.get("date", "").split(" ")[0]  # Extrair apenas a data
                
                # Verificar se a data da sessão está dentro do intervalo
                if start_date and end_date:
                    if start_date <= session_date <= end_date:
                        filtered_sessions.append(session)
                elif start_date:
                    if start_date <= session_date:
                        filtered_sessions.append(session)
                elif end_date:
                    if session_date <= end_date:
                        filtered_sessions.append(session)
                else:
                    filtered_sessions.append(session)
            
            # Log para depuração
            logger.debug(f"Filtered sessions: {len(filtered_sessions)}")
            
            # Definir número de linhas
            self.history_table.setRowCount(len(filtered_sessions))
            
            # Preencher tabela
            for row, session in enumerate(reversed(filtered_sessions)):  # Mostrar sessões mais recentes primeiro
                # Verificar se session é um dicionário válido
                if not isinstance(session, dict):
                    continue
                
                # Data e hora
                date_time = session.get("date", "")
                if date_time:
                    try:
                        date_parts = date_time.split(" ")
                        date_item = QTableWidgetItem(date_parts[0])
                        self.history_table.setItem(row, 0, date_item)
                        
                        if len(date_parts) > 1:
                            time_item = QTableWidgetItem(date_parts[1])
                            self.history_table.setItem(row, 1, time_item)
                        else:
                            self.history_table.setItem(row, 1, QTableWidgetItem(""))
                    except Exception as e:
                        logger.error(f"Error parsing date: {date_time}, error: {str(e)}")
                        self.history_table.setItem(row, 0, QTableWidgetItem(""))
                        self.history_table.setItem(row, 1, QTableWidgetItem(""))
                else:
                    self.history_table.setItem(row, 0, QTableWidgetItem(""))
                    self.history_table.setItem(row, 1, QTableWidgetItem(""))
                
                # Duração
                duration = session.get("duration", 0)
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                duration_item = QTableWidgetItem(f"{hours}h {minutes}m")
                self.history_table.setItem(row, 2, duration_item)
                
                # Palavras
                words = session.get("words", 0)
                words_item = QTableWidgetItem(f"{words:,}".replace(",", "."))
                words_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.history_table.setItem(row, 3, words_item)
                
                # Velocidade média
                if duration > 0:
                    avg_speed = (words * 60) / duration
                    avg_speed_item = QTableWidgetItem(f"{avg_speed:.1f}")
                else:
                    avg_speed_item = QTableWidgetItem("0.0")
                avg_speed_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.history_table.setItem(row, 4, avg_speed_item)
        except Exception as e:
            logger.error(f"Error updating session history table: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def load_settings(self):
        """Carregar estatísticas do config_manager"""
        try:
            # Estatísticas gerais
            stats = self.config_manager.get_value("statistics", "general", {})
            
            # Log para depuração
            logger.debug(f"Loading statistics: {stats}")
            
            # Verificar se devemos usar estatísticas filtradas
            try:
                # Obter datas do filtro
                start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
                end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
                
                # Obter estatísticas para o período
                if hasattr(self, 'stats_service'):
                    period_stats = self.stats_service.get_stats_for_period(start_date, end_date)
                else:
                    logger.error("Stats service not available")
                    period_stats = {
                        "total_words": stats.get("total_words", 0),
                        "total_time": stats.get("total_time", 0),
                        "avg_speed": 0
                    }
                
                # Log para depuração
                logger.debug(f"Period statistics: {period_stats}")
                
                # Usar estatísticas filtradas para alguns campos
                filtered_total_words = period_stats.get("total_words", 0)
                filtered_total_time = period_stats.get("total_time", 0)
                filtered_avg_speed = period_stats.get("avg_speed", 0)
            except Exception as e:
                logger.error(f"Erro ao obter estatísticas filtradas: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # Fallback para estatísticas gerais
                filtered_total_words = stats.get("total_words", 0)
                filtered_total_time = stats.get("total_time", 0)
                if filtered_total_time > 0:
                    filtered_avg_speed = (filtered_total_words * 60) / filtered_total_time
                else:
                    filtered_avg_speed = 0
            
            # Total de palavras (filtrado)
            self.total_words_label.setText(f"{filtered_total_words:,}".replace(",", "."))
            
            # Total de palavras traduzidas (não filtrado)
            translated_words = stats.get("translated_words", 0)
            self.translated_words_label.setText(f"{translated_words:,}".replace(",", "."))
            
            # Tempo total (filtrado)
            hours = filtered_total_time // 3600
            minutes = (filtered_total_time % 3600) // 60
            self.total_time_label.setText(f"{hours}h {minutes}m")
            
            # Velocidade média (filtrada)
            self.avg_speed_label.setText(f"{filtered_avg_speed:.1f}")
            
            # Sessão atual
            current_session = stats.get("current_session", {})
            
            # Tempo da sessão atual
            current_seconds = current_session.get("duration", 0)
            current_hours = current_seconds // 3600
            current_minutes = (current_seconds % 3600) // 60
            self.current_session_label.setText(f"{current_hours}h {current_minutes}m")
            
            # Palavras da sessão atual
            current_words = current_session.get("words", 0)
            self.current_words_label.setText(f"{current_words:,}".replace(",", "."))
            
            # Atualizar tabelas
            self._update_api_usage_table()
            self._update_session_history_table()
            
            # Log para depuração
            logger.debug("Statistics loaded successfully")
        except Exception as e:
            logger.error(f"Error loading statistics: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def save_settings(self):
        """Salvar estatísticas no config_manager"""
        # Não há nada para salvar aqui, pois as estatísticas são apenas para exibição
        pass 