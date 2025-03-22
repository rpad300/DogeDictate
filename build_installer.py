#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build script for DogeDictate
Creates an executable and installer using PyInstaller
"""

import os
import sys
import shutil
import subprocess
import platform
from version import get_version_string

def main():
    """Main build function"""
    print("Iniciando build do DogeDictate...")
    
    # Obter a versão atual
    version = get_version_string()
    print(f"Versão: {version}")
    
    # Limpar diretórios de build anteriores
    if os.path.exists("build"):
        print("Limpando diretório build...")
        shutil.rmtree("build")
    
    if os.path.exists("dist"):
        print("Limpando diretório dist...")
        shutil.rmtree("dist")
    
    # Criar o arquivo spec para o PyInstaller
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('src/i18n/translations', 'src/i18n/translations'),
        ('LICENSE', '.'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'azure.cognitiveservices.speech',
        'openai',
        'google.cloud.speech',
        'azure.ai.translation.text',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'src.i18n',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DogeDictate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DogeDictate',
)

# Windows specific
if platform.system() == 'Windows':
    import pyi_splash
    splash = SPLASH(
        binaries=a.binaries,
        datas=a.datas,
        text_pos=None,
        text_size=12,
        minify_script=True,
        always_on_top=True,
    )
"""
    
    with open("DogeDictate.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    # Executar o PyInstaller
    print("Executando PyInstaller...")
    subprocess.run(["pyinstaller", "DogeDictate.spec", "--clean"], check=True)
    
    # Criar o instalador (apenas para Windows)
    if platform.system() == "Windows":
        print("Criando instalador para Windows...")
        try:
            # Verificar se o NSIS está instalado
            nsis_path = r"C:\Program Files (x86)\NSIS\makensis.exe"
            if not os.path.exists(nsis_path):
                print("AVISO: NSIS não encontrado. O instalador não será criado.")
                print("Por favor, instale o NSIS de https://nsis.sourceforge.io/Download")
                return
            
            # Criar o script NSIS
            nsis_script = f"""
; Script de instalação para DogeDictate
!include "MUI2.nsh"
!include "LogicLib.nsh"

; Informações do aplicativo
Name "DogeDictate"
OutFile "DogeDictate-{version}-Setup.exe"
InstallDir "$PROGRAMFILES\\DogeDictate"
InstallDirRegKey HKCU "Software\\DogeDictate" ""

; Interface
!define MUI_ABORTWARNING
!define MUI_ICON "resources\\icons\\app_icon.ico"
!define MUI_UNICON "resources\\icons\\app_icon.ico"

; Variáveis
Var InterfaceLanguage

; Páginas
!define MUI_PAGE_CUSTOMFUNCTION_PRE LanguagePagePre
!define MUI_PAGE_CUSTOMFUNCTION_SHOW LanguagePageShow
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE LanguagePageLeave
!insertmacro MUI_PAGE_WELCOME

Page custom LanguagePage LanguagePageLeave

!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Idiomas
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Portuguese"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "Spanish"

; Função para inicializar a página de idioma
Function LanguagePagePre
  ; Inicializar com inglês como padrão
  StrCpy $InterfaceLanguage "en"
FunctionEnd

; Função para mostrar a página de idioma
Function LanguagePage
  !insertmacro MUI_HEADER_TEXT "Select Language" "Choose the language for installation and application interface"
  
  ; Criar diálogo
  nsDialogs::Create 1018
  Pop $0
  
  ; Adicionar texto
  ${NSD_CreateLabel} 0 0 100% 20u "Please select your preferred language:"
  Pop $1
  
  ; Adicionar combobox
  ${NSD_CreateComboBox} 0 25u 100% 15u ""
  Pop $2
  
  ; Adicionar opções
  ${NSD_CB_AddString} $2 "English"
  ${NSD_CB_AddString} $2 "Português"
  ${NSD_CB_AddString} $2 "Français"
  ${NSD_CB_AddString} $2 "Español"
  
  ; Selecionar inglês como padrão
  ${NSD_CB_SelectString} $2 "English"
  
  nsDialogs::Show
FunctionEnd

; Função para processar a seleção de idioma
Function LanguagePageLeave
  ; Obter a seleção
  Pop $0
  ${NSD_GetText} $0 $1
  
  ; Definir o idioma com base na seleção
  ${If} $1 == "English"
    StrCpy $InterfaceLanguage "en"
    !insertmacro MUI_LANGDLL_PUSH "English"
  ${ElseIf} $1 == "Português"
    StrCpy $InterfaceLanguage "pt"
    !insertmacro MUI_LANGDLL_PUSH "Portuguese"
  ${ElseIf} $1 == "Français"
    StrCpy $InterfaceLanguage "fr"
    !insertmacro MUI_LANGDLL_PUSH "French"
  ${ElseIf} $1 == "Español"
    StrCpy $InterfaceLanguage "es"
    !insertmacro MUI_LANGDLL_PUSH "Spanish"
  ${Else}
    StrCpy $InterfaceLanguage "en"
    !insertmacro MUI_LANGDLL_PUSH "English"
  ${EndIf}
FunctionEnd

; Função para mostrar a página de idioma
Function LanguagePageShow
  ; Mostrar a página de idioma
  !insertmacro MUI_LANGDLL_DISPLAY
FunctionEnd

; Seção principal
Section "DogeDictate" SecMain
  SetOutPath "$INSTDIR"
  
  ; Arquivos do programa
  File /r "dist\\DogeDictate\\*.*"
  
  ; Criar atalhos
  CreateDirectory "$SMPROGRAMS\\DogeDictate"
  CreateShortcut "$SMPROGRAMS\\DogeDictate\\DogeDictate.lnk" "$INSTDIR\\DogeDictate.exe"
  CreateShortcut "$DESKTOP\\DogeDictate.lnk" "$INSTDIR\\DogeDictate.exe"
  
  ; Criar desinstalador
  WriteUninstaller "$INSTDIR\\uninstall.exe"
  
  ; Registrar desinstalador
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DogeDictate" "DisplayName" "DogeDictate"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DogeDictate" "UninstallString" "$\\"$INSTDIR\\uninstall.exe$\\""
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DogeDictate" "DisplayIcon" "$\\"$INSTDIR\\DogeDictate.exe$\\""
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DogeDictate" "DisplayVersion" "{version}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DogeDictate" "Publisher" "DogeDictate Team"
  
  ; Salvar o idioma selecionado
  WriteRegStr HKCU "Software\\DogeDictate" "InterfaceLanguage" $InterfaceLanguage
  
  ; Opção de iniciar com o Windows
  WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Run" "DogeDictate" "$\\"$INSTDIR\\DogeDictate.exe$\\""
SectionEnd

; Seção de desinstalação
Section "Uninstall"
  ; Remover arquivos e diretórios
  Delete "$INSTDIR\\uninstall.exe"
  RMDir /r "$INSTDIR"
  
  ; Remover atalhos
  Delete "$SMPROGRAMS\\DogeDictate\\DogeDictate.lnk"
  RMDir "$SMPROGRAMS\\DogeDictate"
  Delete "$DESKTOP\\DogeDictate.lnk"
  
  ; Remover registros
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DogeDictate"
  DeleteRegValue HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Run" "DogeDictate"
  DeleteRegKey HKCU "Software\\DogeDictate"
SectionEnd
"""
            
            with open("installer.nsi", "w", encoding="utf-8") as f:
                f.write(nsis_script)
            
            # Executar o NSIS
            subprocess.run([nsis_path, "installer.nsi"], check=True)
            
            print(f"Instalador criado com sucesso: DogeDictate-{version}-Setup.exe")
            
        except Exception as e:
            print(f"Erro ao criar o instalador: {str(e)}")
    
    print("Build concluído com sucesso!")

if __name__ == "__main__":
    main() 