; Script de instalação para DogeDictate
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"

; Informações do aplicativo
Name "DogeDictate"
OutFile "DogeDictate-1.0.0-Setup.exe"
InstallDir "$PROGRAMFILES\DogeDictate"
InstallDirRegKey HKCU "Software\DogeDictate" ""

; Interface
!define MUI_ABORTWARNING
; Usar ícones padrão do Windows
; !define MUI_ICON "resources\icons\app_icon.ico"
; !define MUI_UNICON "resources\icons\app_icon.ico"

; Variáveis
Var InterfaceLanguage
Var Dialog
Var Label
Var CheckboxLocalServices
Var InstallLocalServices

; Função para a página de opções
Function LocalServicesPage
  !insertmacro MUI_HEADER_TEXT "Opções de Instalação" "Escolha os componentes adicionais para instalar."
  
  nsDialogs::Create 1018
  Pop $Dialog
  
  ${If} $Dialog == error
    Abort
  ${EndIf}
  
  ${NSD_CreateLabel} 0 0 100% 40u "O DogeDictate pode funcionar com serviços de reconhecimento de fala e tradução locais, sem depender de APIs online. Isso requer o download de componentes adicionais."
  Pop $Label
  
  ${NSD_CreateCheckbox} 0 50u 100% 10u "Instalar serviços locais (recomendado)"
  Pop $CheckboxLocalServices
  ${NSD_Check} $CheckboxLocalServices ; Marcar por padrão
  
  nsDialogs::Show
FunctionEnd

Function LocalServicesPageLeave
  ${NSD_GetState} $CheckboxLocalServices $InstallLocalServices
FunctionEnd

; Páginas
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
Page custom LocalServicesPage LocalServicesPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Idiomas
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Portuguese"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "Spanish"

; Seção principal
Section "DogeDictate" SecMain
  SetOutPath "$INSTDIR"
  
  ; Arquivos do programa
  File /r "dist\DogeDictate\*.*"
  
  ; Copiar script de pós-instalação
  File "post_install.py"
  
  ; Criar atalhos
  CreateDirectory "$SMPROGRAMS\DogeDictate"
  CreateShortcut "$SMPROGRAMS\DogeDictate\DogeDictate.lnk" "$INSTDIR\DogeDictate.exe"
  CreateShortcut "$DESKTOP\DogeDictate.lnk" "$INSTDIR\DogeDictate.exe"
  
  ; Criar desinstalador
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  ; Registrar desinstalador
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DogeDictate" "DisplayName" "DogeDictate"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DogeDictate" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DogeDictate" "DisplayIcon" "$\"$INSTDIR\DogeDictate.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DogeDictate" "DisplayVersion" "1.0.0"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DogeDictate" "Publisher" "DogeDictate Team"
  
  ; Opção de iniciar com o Windows
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "DogeDictate" "$\"$INSTDIR\DogeDictate.exe$\""
  
  ; Executar script de pós-instalação se o usuário escolheu instalar serviços locais
  ${If} $InstallLocalServices == 1
    DetailPrint "Instalando serviços locais..."
    ExecWait '"$INSTDIR\DogeDictate.exe" --first-run'
    ExecWait '"$INSTDIR\python\python.exe" "$INSTDIR\post_install.py"'
  ${EndIf}
SectionEnd

; Seção de desinstalação
Section "Uninstall"
  ; Remover arquivos e diretórios
  Delete "$INSTDIR\uninstall.exe"
  Delete "$INSTDIR\post_install.py"
  RMDir /r "$INSTDIR"
  
  ; Remover atalhos
  Delete "$SMPROGRAMS\DogeDictate\DogeDictate.lnk"
  RMDir "$SMPROGRAMS\DogeDictate"
  Delete "$DESKTOP\DogeDictate.lnk"
  
  ; Remover registros
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DogeDictate"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "DogeDictate"
  DeleteRegKey HKCU "Software\DogeDictate"
  
  ; Não remover os modelos e pacotes de idiomas do AppData para preservar as configurações do usuário
  MessageBox MB_YESNO "Deseja remover também os modelos e pacotes de idiomas baixados? Isso liberará espaço em disco, mas você precisará baixá-los novamente se reinstalar o aplicativo." IDNO SkipDataRemoval
    RMDir /r "$APPDATA\DogeDictate"
  SkipDataRemoval:
SectionEnd 