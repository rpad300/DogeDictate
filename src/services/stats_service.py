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
        
        self._save_stats()
    
    def get_stats(self):
        """
        Get current stats
        
        Returns:
            dict: Statistics data
        """
        return self.stats 