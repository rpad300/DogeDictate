#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Language Rules Manager for DogeDictate
Manages language selection rules for different hotkey types
"""

import logging
import traceback

logger = logging.getLogger("DogeDictate.LanguageRulesManager")

class LanguageRulesManager:
    """
    Gerencia as regras de seleção de idioma para diferentes tipos de hotkeys
    
    Regras:
    1. O idioma de reconhecimento é sempre o mesmo, independente da tecla pressionada
    2. Para push-to-talk (Caps Lock), o idioma de destino é o target_language configurado na aba Languages
    3. Para language hotkeys, o idioma de destino é o idioma associado à tecla na configuração
    4. Para hands-free, o idioma de destino é o target_language configurado na aba Languages
    """
    
    def __init__(self, config_manager):
        """
        Inicializa o gerenciador de regras de idioma
        
        Args:
            config_manager: O gerenciador de configurações
        """
        self.config_manager = config_manager
        logger.info("Language Rules Manager initialized")
        
        # Verificar e registrar as configurações de idioma no início
        self.verify_language_settings()
    
    def verify_language_settings(self):
        """
        Verifica e registra as configurações de idioma no início da aplicação
        """
        try:
            logger.warning("[STARTUP] Starting language settings verification")
            
            # Verificar o idioma de reconhecimento
            recognition_language = self.get_recognition_language()
            logger.warning(f"[STARTUP] Recognition language configured as: {recognition_language}")
            
            # Verificar o idioma de destino para push-to-talk
            target_language = self.get_target_language_for_push_to_talk()
            logger.warning(f"[STARTUP] Push-to-talk target language configured as: {target_language}")
            
            # Verificar a configuração de push-to-talk
            push_to_talk = self.config_manager.get_value("hotkeys", "push_to_talk", {})
            if isinstance(push_to_talk, dict):
                key = push_to_talk.get("key", "")
                logger.warning(f"[STARTUP] Push-to-talk configured with key: {key}")
                logger.warning(f"[STARTUP] Push-to-talk will use target language: {target_language}")
            
            # Verificar as language hotkeys
            language_hotkeys = self.config_manager.get_value("hotkeys", "language_hotkeys", [])
            if language_hotkeys:
                logger.warning(f"[STARTUP] Found {len(language_hotkeys)} language hotkeys configured")
                for i, hotkey in enumerate(language_hotkeys):
                    if isinstance(hotkey, dict) and "key" in hotkey:
                        key = hotkey.get("key", "")
                        language = hotkey.get("language", "")
                        logger.warning(f"[STARTUP] Language hotkey {i+1}: key={key}, language={language}")
            
            # Verificar o idioma de destino para hands-free
            target_language = self.get_target_language_for_hands_free()
            logger.warning(f"[STARTUP] Hands-free target language configured as: {target_language}")
            
            # Verificar a configuração de hands-free
            hands_free = self.config_manager.get_value("hotkeys", "toggle_dictation", {})
            if isinstance(hands_free, dict):
                key = hands_free.get("key", "")
                logger.warning(f"[STARTUP] Hands-free configured with key: {key}")
                logger.warning(f"[STARTUP] Hands-free will use target language: {target_language}")
            
            # Garantir que a configuração da tecla Caps Lock esteja correta
            self.ensure_caps_lock_language()
            
            # Registrar que a verificação foi concluída
            logger.warning("[STARTUP] Language settings verification completed")
            
        except Exception as e:
            logger.error(f"[STARTUP] Error verifying language settings: {str(e)}")
            
    def ensure_caps_lock_language(self):
        """
        Garante que a configuração de idioma para a tecla Caps Lock esteja sempre definida como "en-US"
        """
        try:
            logger.warning("[STARTUP] Ensuring Caps Lock language is set to en-US")
            
            # Verificar e corrigir configuração push_to_talk
            push_to_talk = self.config_manager.get_value("hotkeys", "push_to_talk", {})
            if isinstance(push_to_talk, dict) and push_to_talk.get("key") == "caps_lock":
                if push_to_talk.get("language") != "en-US":
                    push_to_talk["language"] = "en-US"
                    self.config_manager.set_value("hotkeys", "push_to_talk", push_to_talk)
                    logger.warning("[STARTUP] Updated Caps Lock language in push_to_talk to en-US")
                else:
                    logger.warning("[STARTUP] Caps Lock language in push_to_talk already set to en-US")
            
            # Verificar e corrigir configuração language_hotkeys
            language_hotkeys = self.config_manager.get_value("hotkeys", "language_hotkeys", [])
            if isinstance(language_hotkeys, list):
                for i, hotkey in enumerate(language_hotkeys):
                    if isinstance(hotkey, dict) and hotkey.get("key") == "caps_lock":
                        if hotkey.get("language") != "en-US":
                            hotkey["language"] = "en-US"
                            # Atualizar o item na lista
                            language_hotkeys[i] = hotkey
                            self.config_manager.set_value("hotkeys", "language_hotkeys", language_hotkeys)
                            logger.warning(f"[STARTUP] Updated Caps Lock language in language_hotkeys[{i}] to en-US")
                        else:
                            logger.warning(f"[STARTUP] Caps Lock language in language_hotkeys[{i}] already set to en-US")
            
            # Verificar e criar/corrigir configuração language_rules.key_languages
            key_languages = self.config_manager.get_value("language_rules", "key_languages", {})
            if isinstance(key_languages, dict):
                if key_languages.get("caps_lock") != "en-US":
                    key_languages["caps_lock"] = "en-US"
                    self.config_manager.set_value("language_rules", "key_languages", key_languages)
                    logger.warning("[STARTUP] Updated Caps Lock in language_rules.key_languages to en-US")
                else:
                    logger.warning("[STARTUP] Caps Lock in language_rules.key_languages already set to en-US")
            
            # Salvar as alterações no arquivo de configuração
            self.config_manager.save_config()
            logger.warning("[STARTUP] Caps Lock language configuration saved")
            
        except Exception as e:
            logger.error(f"[STARTUP] Error ensuring Caps Lock language: {str(e)}")
            logger.error(traceback.format_exc())
    
    def get_recognition_language(self):
        """
        Obtém o idioma de reconhecimento configurado
        
        Returns:
            str: O idioma de reconhecimento
        """
        # O idioma de reconhecimento é sempre o mesmo, independente da tecla
        # Sempre ler do arquivo de configuração, sem valores hardcoded
        recognition_language = self.config_manager.get_value("recognition", "language")
        logger.debug(f"Using recognition language from config: {recognition_language}")
        return recognition_language
    
    def get_target_language_for_push_to_talk(self):
        """
        Obtém o idioma de destino para o modo push-to-talk
        
        Returns:
            str: O idioma de destino para o modo push-to-talk
        """
        # Obter a configuração da tecla push-to-talk
        push_to_talk = self.config_manager.get_value("hotkeys", "push_to_talk", {})
        if not isinstance(push_to_talk, dict) or "key" not in push_to_talk:
            logger.warning("Invalid push-to-talk configuration")
            return self.config_manager.get_value("translation", "target_language")
            
        # Obter a tecla configurada para push-to-talk
        key = push_to_talk.get("key", "")
        logger.warning(f"Push-to-talk key: {key}")
        
        # Verificar se a tecla é ctrl
        if key == "ctrl":
            logger.warning("Push-to-talk key is ctrl, checking target language from translation config")
            target_language = self.config_manager.get_value("translation", "target_language")
            logger.warning(f"Using target language for ctrl from translation config: {target_language}")
            return target_language
        
        # Verificar se existe uma configuração específica para esta tecla em language_rules.key_languages
        key_languages = self.config_manager.get_value("language_rules", "key_languages", {})
        if isinstance(key_languages, dict) and key in key_languages:
            language = key_languages.get(key)
            logger.warning(f"Using language from key_languages for push-to-talk key '{key}': {language}")
            return language
        
        # Se não houver uma configuração específica, usar o idioma de destino configurado na aba Languages
        target_language = self.config_manager.get_value("translation", "target_language")
        logger.warning(f"Push-to-talk target language from config: {target_language}")
        return target_language
    
    def get_target_language_for_hands_free(self):
        """
        Obtém o idioma de destino para hands-free
        
        Returns:
            str: O idioma de destino para hands-free
        """
        # Para hands-free, usar o idioma de destino configurado na aba Languages
        # Sempre ler do arquivo de configuração, sem valores hardcoded
        target_language = self.config_manager.get_value("translation", "target_language")
        logger.debug(f"Using target language for hands-free from config: {target_language}")
        return target_language
    
    def get_target_language_for_language_hotkey(self, language_hotkey):
        """
        Obtém o idioma de destino para uma language hotkey específica
        
        Args:
            language_hotkey (dict): A configuração da language hotkey
            
        Returns:
            str: O idioma de destino para a language hotkey
        """
        # Verificar se a language hotkey é o Caps Lock
        if isinstance(language_hotkey, dict) and language_hotkey.get("key") == "caps_lock":
            # Para Caps Lock, sempre retornar inglês, não importa a configuração
            logger.warning("Caps Lock detected as language hotkey, forcing language to en-US")
            return "en-US"
        
        # Para language hotkeys, usar o idioma associado à tecla na configuração
        if isinstance(language_hotkey, dict) and "language" in language_hotkey:
            language = language_hotkey.get("language", "")
            if language:
                logger.warning(f"Using language hotkey's specific language: {language}")
                return language
            else:
                logger.warning("Language hotkey has no language configured, using fallback")
        
        # Fallback para o idioma de destino configurado na aba Languages
        target_language = self.config_manager.get_value("translation", "target_language")
        logger.warning(f"Using fallback target language from config: {target_language}")
        return target_language
    
    def apply_language_settings(self, dictation_manager, hotkey_type, language_hotkey=None):
        """
        Aplica as configurações de idioma ao DictationManager com base no tipo de hotkey
        
        Args:
            dictation_manager: O gerenciador de ditado
            hotkey_type (str): O tipo de hotkey ("push_to_talk", "hands_free", "language_hotkey")
            language_hotkey (dict, optional): A configuração da language hotkey, se hotkey_type for "language_hotkey"
            
        Returns:
            bool: True se as configurações foram aplicadas com sucesso, False caso contrário
        """
        try:
            # Definir o idioma de reconhecimento (sempre o mesmo)
            recognition_language = self.get_recognition_language()
            logger.warning(f"Setting recognition language to: {recognition_language}")
            dictation_manager.set_language(recognition_language)
            
            # Verificar se o idioma de reconhecimento foi aplicado corretamente
            current_recognition = dictation_manager.get_language()
            if current_recognition != recognition_language:
                logger.error(f"Failed to set recognition language. Expected: {recognition_language}, Got: {current_recognition}")
            
            # Definir o idioma de destino com base no tipo de hotkey
            target_language = None
            
            if hotkey_type == "push_to_talk":
                target_language = self.get_target_language_for_push_to_talk()
                logger.warning(f"[PUSH-TO-TALK] Using push-to-talk target language: {target_language}")
                
                # Log adicional para push-to-talk
                push_to_talk = self.config_manager.get_value("hotkeys", "push_to_talk", {})
                key = push_to_talk.get("key", "")
                logger.warning(f"[PUSH-TO-TALK] Key: {key}, Target Language: {target_language}")
            elif hotkey_type == "hands_free":
                target_language = self.get_target_language_for_hands_free()
                logger.warning(f"Using hands-free target language: {target_language}")
            elif hotkey_type == "language_hotkey" and language_hotkey:
                target_language = self.get_target_language_for_language_hotkey(language_hotkey)
                logger.warning(f"Using language hotkey target language: {target_language}")
            else:
                logger.error(f"Unknown hotkey type: {hotkey_type}")
                return False
            
            # Verificar se temos um idioma de destino válido
            if not target_language:
                logger.error(f"Failed to get target language for hotkey type: {hotkey_type}")
                return False
                
            # Log dos idiomas configurados para diagnóstico
            logger.warning(f"CONFIGURAÇÃO FINAL - Reconhecimento: {recognition_language}, Destino: {target_language}")
            
            # Confirmar se os idiomas estão definidos corretamente
            if recognition_language == target_language:
                logger.warning("AVISO: Idioma de reconhecimento e destino são iguais. A tradução não será aplicada, apenas processamento.")
                # Forçar o processamento mesmo quando os idiomas são iguais
                if hasattr(dictation_manager, 'set_force_process'):
                    dictation_manager.set_force_process(True)
                    logger.warning("Forcing text processing even with same languages")
            else:
                # Desativar o processamento forçado quando os idiomas são diferentes
                if hasattr(dictation_manager, 'set_force_process'):
                    dictation_manager.set_force_process(False)
            
            # Definir o idioma de destino no DictationManager
            logger.warning(f"Setting target language to: {target_language}")
            dictation_manager.set_target_language(target_language)
            
            return True
        except Exception as e:
            logger.error(f"Error applying language settings: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def get_language_for_key(self, key):
        """
        Obtém o idioma apropriado para uma tecla específica.
        Usa as configurações de key_languages ou outras configurações específicas.
        
        Args:
            key (str): A tecla para a qual obter o idioma
            
        Returns:
            str: O idioma apropriado para a tecla
        """
        # Verificar se existe uma regra específica para esta tecla em language_rules.key_languages
        key_languages = self.config_manager.get_value("language_rules", "key_languages", {})
        if isinstance(key_languages, dict) and key in key_languages:
            language = key_languages.get(key)
            logger.warning(f"get_language_for_key: Found specific rule for key '{key}': {language}")
            return language
            
        # Verificar se a tecla está configurada como language_hotkey
        language_hotkeys = self.config_manager.get_value("hotkeys", "language_hotkeys", [])
        if isinstance(language_hotkeys, list):
            for hotkey in language_hotkeys:
                if isinstance(hotkey, dict) and hotkey.get("key") == key and "language" in hotkey:
                    language = hotkey.get("language")
                    logger.warning(f"get_language_for_key: Found language_hotkey for key '{key}': {language}")
                    return language
                    
        # Verificar se a tecla está configurada como push_to_talk
        push_to_talk = self.config_manager.get_value("hotkeys", "push_to_talk", {})
        if isinstance(push_to_talk, dict) and push_to_talk.get("key") == key and "language" in push_to_talk:
            language = push_to_talk.get("language")
            logger.warning(f"get_language_for_key: Found push_to_talk for key '{key}': {language}")
            return language
            
        # Fallback para o idioma de destino padrão
        target_language = self.config_manager.get_value("translation", "target_language")
        logger.warning(f"get_language_for_key: No specific configuration found for key '{key}', using default: {target_language}")
        return target_language
