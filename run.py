#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para executar a aplicação DogeDictate
Este script configura o ambiente e inicia a aplicação.
"""

import os
import sys
import logging
import subprocess

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def run_application():
    """Executar a aplicação principal"""
    logger.info("Iniciando aplicação DogeDictate...")
    
    # Obter diretório atual (raiz do projeto)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(current_dir, "src")
    
    # Verificar se o script main.py existe
    main_script = os.path.join(src_dir, "main.py")
    if not os.path.exists(main_script):
        logger.error(f"Arquivo main.py não encontrado em: {main_script}")
        return
    
    # Executar o aplicativo como um processo separado
    try:
        logger.info(f"Executando o aplicativo: {main_script}")
        
        # Configurar environment variables
        env = os.environ.copy()
        python_path = f"{current_dir}{os.pathsep}{src_dir}"
        
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{python_path}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = python_path
            
        logger.info(f"PYTHONPATH configurado: {env['PYTHONPATH']}")
        
        # Executar o aplicativo
        process = subprocess.run(
            [sys.executable, main_script],
            env=env,
            cwd=current_dir  # Executar a partir do diretório raiz
        )
        
        if process.returncode != 0:
            logger.error(f"Aplicação encerrada com código de erro: {process.returncode}")
        else:
            logger.info("Aplicação encerrada normalmente.")
    except Exception as e:
        logger.error(f"Erro ao iniciar aplicação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    run_application() 