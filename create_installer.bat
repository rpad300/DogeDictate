@echo off
echo ===== Criando instalador do DogeDictate =====

echo 1. Limpando chaves de API...
python clean_api_keys.py
if %ERRORLEVEL% NEQ 0 (
    echo Erro ao limpar chaves de API!
    exit /b 1
)

echo 2. Criando executável com PyInstaller...
python -m PyInstaller DogeDictate.spec
if %ERRORLEVEL% NEQ 0 (
    echo Erro ao criar executável!
    python clean_api_keys.py --restore
    exit /b 1
)

echo 3. Criando instalador com NSIS...
"C:\Program Files (x86)\NSIS\makensis.exe" "installer.nsi"
if %ERRORLEVEL% NEQ 0 (
    echo Erro ao criar instalador!
    python clean_api_keys.py --restore
    exit /b 1
)

echo 4. Restaurando configuração original...
python clean_api_keys.py --restore

echo ===== Instalador criado com sucesso! =====
echo O instalador está disponível em: %CD%\DogeDictate-1.0.0-Setup.exe 