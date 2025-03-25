#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stats Service Module for DogeDictate
"""

import os
import json
import time
from datetime import datetime

class StatsService:
    """
    Service class to handle usage statistics for the application
    """
    
    def __init__(self, config_dir=None):
        """
        Initialize the stats service
        
        Args:
            config_dir (str, optional): Directory to store stats. Defaults to None.
        """
        self.config_dir = config_dir
        if not self.config_dir:
            home_dir = os.path.expanduser("~")
            self.config_dir = os.path.join(home_dir, ".dogedictate")
            
        self.stats_file = os.path.join(self.config_dir, "stats.json")
        self.stats = self._load_stats()
        
        # Lista de callbacks para atualização
        self.update_callbacks = []
    
    def _load_stats(self):
        """
        Load stats from file
        
        Returns:
            dict: Statistics data
        """
        if not os.path.exists(self.stats_file):
            return {
                "total_recordings": 0,
                "total_duration": 0,
                "total_characters": 0,
                "recordings_by_date": {},
                "recordings_by_language": {},
                "last_updated": datetime.now().isoformat()
            }
            
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {
                "total_recordings": 0,
                "total_duration": 0,
                "total_characters": 0,
                "recordings_by_date": {},
                "recordings_by_language": {},
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_stats(self):
        """Save stats to file"""
        os.makedirs(self.config_dir, exist_ok=True)
        self.stats["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)
        except Exception:
            pass
    
    def record_transcription(self, language, duration, text_length):
        """
        Record a transcription in stats
        
        Args:
            language (str): Language of transcription
            duration (float): Duration in seconds
            text_length (int): Length of transcribed text
        """
        self.stats["total_recordings"] += 1
        self.stats["total_duration"] += duration
        self.stats["total_characters"] += text_length
        
        # Record by date
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.stats["recordings_by_date"]:
            self.stats["recordings_by_date"][today] = {
                "count": 0,
                "duration": 0,
                "characters": 0
            }
        
        self.stats["recordings_by_date"][today]["count"] += 1
        self.stats["recordings_by_date"][today]["duration"] += duration
        self.stats["recordings_by_date"][today]["characters"] += text_length
        
        # Record by language
        if language not in self.stats["recordings_by_language"]:
            self.stats["recordings_by_language"][language] = {
                "count": 0,
                "duration": 0,
                "characters": 0
            }
        
        self.stats["recordings_by_language"][language]["count"] += 1
        self.stats["recordings_by_language"][language]["duration"] += duration
        self.stats["recordings_by_language"][language]["characters"] += text_length
        
        # Salvar estatísticas
        self._save_stats()
        
        # Notificar callbacks
        self._notify_update_callbacks()
    
    def get_stats(self):
        """
        Get current stats
        
        Returns:
            dict: Statistics data
        """
        return self.stats
        
    def get_stats_for_period(self, start_date, end_date):
        """
        Get statistics for a specific period
        
        Args:
            start_date (str): Start date in format "yyyy-MM-dd"
            end_date (str): End date in format "yyyy-MM-dd"
            
        Returns:
            dict: Statistics for the period
        """
        try:
            # Inicializar estatísticas do período
            period_stats = {
                "total_words": 0,
                "total_time": 0,
                "total_recordings": 0,
                "total_characters": 0,
                "avg_speed": 0
            }
            
            # Se não houver dados por data, retornar estatísticas vazias
            if "recordings_by_date" not in self.stats:
                return period_stats
                
            # Filtrar datas no intervalo
            for date, data in self.stats["recordings_by_date"].items():
                # Verificar se a data está no intervalo
                if start_date <= date <= end_date:
                    # Adicionar estatísticas
                    period_stats["total_recordings"] += data.get("count", 0)
                    period_stats["total_time"] += data.get("duration", 0)
                    period_stats["total_characters"] += data.get("characters", 0)
                    
                    # Calcular palavras aproximadas (6 caracteres por palavra em média)
                    period_stats["total_words"] += int(data.get("characters", 0) / 6)
            
            # Calcular velocidade média (palavras por minuto)
            if period_stats["total_time"] > 0:
                period_stats["avg_speed"] = (period_stats["total_words"] * 60) / period_stats["total_time"]
            
            return period_stats
            
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger("DogeDictate.StatsService")
            logger.error(f"Error getting stats for period: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Retornar estatísticas vazias em caso de erro
            return {
                "total_words": 0,
                "total_time": 0,
                "total_recordings": 0,
                "total_characters": 0,
                "avg_speed": 0
            }
    
    def reset_statistics(self):
        """
        Reset all statistics
        """
        self.stats = {
            "total_recordings": 0,
            "total_duration": 0,
            "total_characters": 0,
            "recordings_by_date": {},
            "recordings_by_language": {},
            "last_updated": datetime.now().isoformat()
        }
        self._save_stats()
        
        # Notificar callbacks
        self._notify_update_callbacks()
        
    def register_update_callback(self, callback):
        """
        Register a callback to be called when stats are updated
        
        Args:
            callback: The callback function
        """
        if callback not in self.update_callbacks:
            self.update_callbacks.append(callback)
            
    def _notify_update_callbacks(self):
        """
        Notify all registered callbacks
        """
        for callback in self.update_callbacks:
            try:
                callback()
            except Exception as e:
                import logging
                import traceback
                logger = logging.getLogger("DogeDictate.StatsService")
                logger.error(f"Error calling update callback: {str(e)}")
                logger.error(traceback.format_exc())
                
    def debug_stats(self):
        """
        Get a debug summary of the stats
        
        Returns:
            str: A debug summary
        """
        try:
            total_recordings = self.stats.get("total_recordings", 0)
            total_duration = self.stats.get("total_duration", 0)
            total_characters = self.stats.get("total_characters", 0)
            num_dates = len(self.stats.get("recordings_by_date", {}))
            num_languages = len(self.stats.get("recordings_by_language", {}))
            
            return f"Recordings: {total_recordings}, Duration: {total_duration:.1f}s, Chars: {total_characters}, Dates: {num_dates}, Languages: {num_languages}"
        except Exception:
            return "Error getting debug stats" 