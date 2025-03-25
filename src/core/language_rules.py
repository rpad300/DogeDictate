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
        
        # Garantir que key_targets esteja configurado para todas as teclas de idioma
        self.ensure_key_targets()
    
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
                
                # Garantir que key_targets esteja configurado
                key_targets = self.config_manager.get_value("language_rules", "key_targets", {})
                
                for i, hotkey in enumerate(language_hotkeys):
                    if isinstance(hotkey, dict) and "key" in hotkey:
                        key = hotkey.get("key", "")
                        language = hotkey.get("language", "")
                        # Verificar se há um target_language configurado para essa tecla
                        target_lang = key_targets.get(key, language)
                        logger.warning(f"[STARTUP] Language hotkey {i+1}: key={key}, source={language}, target={target_lang}")
            
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
    
    def get_source_language_for_push_to_talk(self):
        """
        Obtém o idioma de origem para o modo push-to-talk
        
        Returns:
            str: O idioma de origem para o modo push-to-talk
        """
        try:
            # Obter a configuração da tecla push-to-talk
            push_to_talk = self.config_manager.get_value("hotkeys", "push_to_talk", {})
            if not isinstance(push_to_talk, dict) or "key" not in push_to_talk:
                logger.warning("Invalid push-to-talk configuration")
                return self.config_manager.get_value("recognition", "language", "en-US")
            
            # Obter a tecla configurada para push-to-talk
            key = push_to_talk.get("key", "")
            logger.info(f"Push-to-talk key: {key}")
            
            # Verificar se existe uma configuração específica para esta tecla em language_rules.key_languages
            key_languages = self.config_manager.get_value("language_rules", "key_languages", {})
            if isinstance(key_languages, dict) and key in key_languages:
                language = key_languages.get(key)
                logger.info(f"Using language from key_languages for push-to-talk key '{key}': {language}")
                return language
            
            # Se não houver uma configuração específica, usar o idioma de reconhecimento configurado na aba Languages
            recognition_language = self.config_manager.get_value("recognition", "language", "en-US")
            logger.info(f"Push-to-talk source language from config: {recognition_language}")
            return recognition_language
        except Exception as e:
            logger.error(f"Error getting source language for push-to-talk: {str(e)}")
            logger.error(traceback.format_exc())
            # Retornar valor padrão em caso de erro
            return self.config_manager.get_value("recognition", "language", "en-US")
    
    def apply_language_settings(self, dictation_manager, context, hotkey_config=None):
        """
        Aplica as configurações de idioma com base no contexto
        
        Args:
            dictation_manager: O gerenciador de ditado
            context: O contexto para aplicar as configurações (push_to_talk, language_hotkey, etc.)
            hotkey_config: Configuração da hotkey para contextos que exigem isso
        """
        try:
            # Obter o modo de regras de idioma: simple ou advanced
            mode = self.config_manager.get_value("language_rules", "mode", "simple")
            logger.info(f"Applying language rules in {mode} mode for context: {context}")
            
            # Modo simples: aplicar regras baseadas em contexto
            if mode == "simple":
                # Contexto padrão: usar idioma de reconhecimento padrão
                if context == "default":
                    # Para o modo padrão, usar a língua de reconhecimento e traduzir se auto_translate estiver ativado
                    recognition_language = self.config_manager.get_value("recognition", "language", "en-US")
                    target_language = self.config_manager.get_value("translation", "target_language", "pt-BR")
                    auto_translate = self.config_manager.get_value("translation", "auto_translate", True)
                    
                    logger.info(f"Applying default settings: {recognition_language} -> {target_language} (auto_translate: {auto_translate})")
                    self._apply_settings(dictation_manager, recognition_language, target_language, auto_translate)
                
                # Contexto push-to-talk (Caps Lock): usar configuração específica para PTT
                elif context == "push_to_talk":
                    # Para push-to-talk, usar sempre o idioma configurado na aba de reconhecimento (recognition)
                    # e traduzir para o idioma configurado na aba de tradução (translation)
                    recognition_language = self.config_manager.get_value("recognition", "language", "en-US")
                    target_language = self.config_manager.get_value("translation", "target_language", "pt-BR")
                    auto_translate = self.config_manager.get_value("translation", "auto_translate", True)
                    
                    logger.info(f"Applying push-to-talk settings: {recognition_language} -> {target_language} (auto_translate: {auto_translate})")
                    self._apply_settings(dictation_manager, recognition_language, target_language, auto_translate)
                
                # Contexto language_hotkey: usar o idioma configurado para a tecla específica
                elif context == "language_hotkey" and hotkey_config:
                    # Obter o idioma configurado para esta hotkey
                    recognition_language = hotkey_config.get("language")
                    if not recognition_language:
                        logger.warning("No language specified in language hotkey config, using default recognition language")
                        recognition_language = self.config_manager.get_value("recognition", "language", "en-US")
                    else:
                        logger.info(f"Language hotkey recognition language: {recognition_language}")
                    
                    # Verificar se a configuração tem um idioma de destino explícito
                    if "target_language" in hotkey_config:
                        target_language = hotkey_config.get("target_language")
                        logger.info(f"Using explicit target language from hotkey config: {target_language}")
                    else:
                        # Se não tiver, usar o idioma de destino padrão
                        target_language = self.config_manager.get_value("translation", "target_language", "pt-BR")
                        logger.info(f"Using default target language: {target_language}")
                    
                    # Decidir sobre a tradução automática (não traduzir se os idiomas forem iguais)
                    if recognition_language == target_language:
                        auto_translate = False
                        logger.info(f"Recognition and target languages are the same ({recognition_language}), no translation needed")
                    else:
                        auto_translate = True
                        logger.info(f"Different languages, translation needed: {recognition_language} -> {target_language}")
                    
                    logger.info(f"Applying language hotkey settings: {recognition_language} -> {target_language} (auto_translate: {auto_translate})")
                    self._apply_settings(dictation_manager, recognition_language, target_language, auto_translate)
                
                # Contexto hands-free: usar configuração específica para hands-free
                elif context == "hands_free":
                    # Para o modo hands-free, usar a configuração default
                    recognition_language = self.config_manager.get_value("recognition", "language", "en-US")
                    target_language = self.config_manager.get_value("translation", "target_language", "pt-BR")
                    auto_translate = self.config_manager.get_value("translation", "auto_translate", True)
                    
                    logger.info(f"Applying hands-free settings: {recognition_language} -> {target_language} (auto_translate: {auto_translate})")
                    self._apply_settings(dictation_manager, recognition_language, target_language, auto_translate)
                
                # Contexto desconhecido: usar configuração padrão
                else:
                    logger.warning(f"Unknown context: {context}, using default settings")
                    recognition_language = self.config_manager.get_value("recognition", "language", "en-US")
                    target_language = self.config_manager.get_value("translation", "target_language", "pt-BR")
                    auto_translate = self.config_manager.get_value("translation", "auto_translate", True)
                    
                    logger.info(f"Applying fallback settings for unknown context: {recognition_language} -> {target_language} (auto_translate: {auto_translate})")
                    self._apply_settings(dictation_manager, recognition_language, target_language, auto_translate)
            
            # Modo avançado: aplicar regras baseadas em perfis
            elif mode == "advanced":
                # Implementação futura para regras avançadas baseadas em perfis
                logger.warning("Advanced language rules mode not implemented yet, falling back to simple mode")
                self.apply_language_settings(dictation_manager, context, hotkey_config)  # Recursion with simple mode
            
            # Modo desconhecido: usar modo simples como fallback
            else:
                logger.warning(f"Unknown language rules mode: {mode}, falling back to simple mode")
                self.apply_language_settings(dictation_manager, context, hotkey_config)  # Recursion with simple mode
            
        except Exception as e:
            logger.error(f"Error applying language settings: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Em caso de erro, tentar aplicar configurações básicas
            try:
                recognition_language = self.config_manager.get_value("recognition", "language", "en-US")
                target_language = self.config_manager.get_value("translation", "target_language", "pt-BR")
                auto_translate = self.config_manager.get_value("translation", "auto_translate", True)
                
                logger.info(f"Applying fallback settings after error: {recognition_language} -> {target_language}")
                self._apply_settings(dictation_manager, recognition_language, target_language, auto_translate)
            except Exception as fallback_error:
                logger.error(f"Error applying fallback settings: {str(fallback_error)}")
                logger.error(traceback.format_exc())

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

    def _apply_settings(self, dictation_manager, recognition_language, target_language, auto_translate):
        """Aplica configurações específicas de idioma ao dictation_manager
        
        Args:
            dictation_manager: O gerenciador de ditado
            recognition_language: O idioma de reconhecimento
            target_language: O idioma de destino da tradução
            auto_translate: Se a tradução automática deve ser ativada
        """
        try:
            # Log detalhado para diagnóstico
            logger.info(f"Applying language settings: {recognition_language} -> {target_language} (auto_translate: {auto_translate})")
            
            # Definir o idioma de reconhecimento
            if hasattr(dictation_manager, 'set_language'):
                dictation_manager.set_language(recognition_language)
                logger.info(f"Recognition language set to: {recognition_language}")
            else:
                logger.warning("dictation_manager does not have set_language method")
            
            # Definir o idioma de destino
            if hasattr(dictation_manager, 'set_target_language'):
                dictation_manager.set_target_language(target_language)
                logger.info(f"Target language set to: {target_language}")
            else:
                logger.warning("dictation_manager does not have set_target_language method")
            
            # Definir auto-tradução
            if hasattr(dictation_manager, 'set_auto_translate'):
                dictation_manager.set_auto_translate(auto_translate)
                logger.info(f"Auto-translate set to: {auto_translate}")
            else:
                logger.warning("dictation_manager does not have set_auto_translate method")
            
            # Configuração adicional para tratamento de idiomas iguais
            if recognition_language == target_language:
                logger.info("Recognition and target languages are the same, translation will be skipped")
                # Forçar processamento mesmo quando os idiomas são iguais (formatação, etc.)
                if hasattr(dictation_manager, 'set_force_process'):
                    dictation_manager.set_force_process(True)
                    logger.info("Force processing enabled for same languages")
            else:
                # Desativar processamento forçado quando os idiomas são diferentes
                if hasattr(dictation_manager, 'set_force_process'):
                    dictation_manager.set_force_process(False)
                    logger.info("Force processing disabled for different languages")
                
        except Exception as e:
            logger.error(f"Error applying settings: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def ensure_key_targets(self):
        """
        Garantir que cada tecla de idioma tenha uma configuração de idioma-alvo
        no config.json em language_rules.key_targets
        """
        try:
            logger.info("Ensuring key_targets configuration exists")
            
            # Obter configuração atual de key_targets
            key_targets = self.config_manager.get_value("language_rules", "key_targets", {})
            if not isinstance(key_targets, dict):
                key_targets = {}
            
            # Obter as language_hotkeys configuradas
            language_hotkeys = self.config_manager.get_value("hotkeys", "language_hotkeys", [])
            if not isinstance(language_hotkeys, list):
                language_hotkeys = []
            
            # Inicializar flag para verificar se houve alterações
            changes_made = False
            
            # Registrar para debug
            logger.info(f"Language hotkeys encontradas: {len(language_hotkeys)}")
            for i, hotkey in enumerate(language_hotkeys):
                if isinstance(hotkey, dict):
                    key_name = hotkey.get("key", "")
                    language = hotkey.get("language", "")
                    logger.info(f"  Hotkey #{i}: key={key_name}, language={language}")
            
            # Para cada language_hotkey, garantir que haja uma entrada em key_targets
            for hotkey in language_hotkeys:
                if isinstance(hotkey, dict) and "key" in hotkey and "language" in hotkey:
                    key = hotkey.get("key")
                    language = hotkey.get("language")
                    
                    # Se a tecla não tiver uma configuração de idioma-alvo ou estiver diferente do configurado
                    if key not in key_targets or key_targets[key] != language:
                        # Configurar o idioma de destino para ser o mesmo configurado na hotkey
                        key_targets[key] = language
                        logger.info(f"Updated target language for hotkey '{key}' to '{language}'")
                        changes_made = True
            
            # Se houver alterações, salvar a configuração
            if changes_made:
                self.config_manager.set_value("language_rules", "key_targets", key_targets)
                self.config_manager.save_config()
                logger.info("Saved updated key_targets configuration")
                
            # Log das configurações atuais
            logger.info(f"Current key_targets configuration: {key_targets}")
            return key_targets
        
        except Exception as e:
            logger.error(f"Error ensuring key_targets: {str(e)}")
            logger.error(traceback.format_exc())
            return {}

    def get_target_language_for_hotkey(self, pressed_key):
        """
        Retorna o idioma de destino configurado para uma tecla específica
        
        Args:
            pressed_key: A tecla que foi pressionada
            
        Returns:
            O idioma de destino para a tecla pressionada ou o mesmo idioma da tecla
            se nenhum destino estiver configurado
        """
        try:
            # Obter a configuração de targets para teclas
            key_targets = self.config_manager.get_value("language_rules", "key_targets", {})
            
            # Obter o idioma de origem para a tecla pressionada
            language_hotkeys = self.config_manager.get_value("hotkeys", "language_hotkeys", [])
            source_language = None
            
            # Encontrar o idioma de origem da tecla pressionada
            for hotkey in language_hotkeys:
                if isinstance(hotkey, dict) and hotkey.get("key", "") == pressed_key:
                    source_language = hotkey.get("language", "")
                    break
            
            # Se não encontramos o idioma de origem, não podemos determinar o alvo
            if not source_language:
                logger.warning(f"No source language found for key: {pressed_key}")
                return None
            
            # Verificar se há um target específico configurado para esta tecla
            target_language = key_targets.get(pressed_key, source_language)
            
            logger.info(f"Target language for key '{pressed_key}' is '{target_language}' (source: '{source_language}')")
            return target_language
            
        except Exception as e:
            logger.error(f"Error getting target language for hotkey: {str(e)}")
            return None
