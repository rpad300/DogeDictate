#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Version information for DogeDictate
"""

def get_version_string():
    """Get the version string"""
    return "1.0.0"

def get_version_info():
    """Get detailed version information"""
    return {
        "version": "1.0.0",
        "date": "2025-03-07",
        "description": "Primeira versão estável do DogeDictate",
        "codename": "Shiba"
    }

if __name__ == "__main__":
    print(f"DogeDictate versão {get_version_string()}")
    print(f"Lançado em {get_version_info()['date']}")
    print(get_version_info()['description']) 