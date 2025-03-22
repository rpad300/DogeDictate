# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[
        ('C:\\Users\\rdias\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\azure\\cognitiveservices\\speech\\Microsoft.CognitiveServices.Speech.core.dll', 
         'azure\\cognitiveservices\\speech')
    ],
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
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'src.i18n',
        # Local services
        'whisper',
        'argostranslate',
        'argostranslate.translate',
        'argostranslate.package',
        'torch',
        'torchaudio',
        'numpy',
        'ffmpeg',
        'src.services.local_whisper_service',
        'src.services.local_translator_service',
    ],
    hookspath=[],
    hooksconfig={},
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
