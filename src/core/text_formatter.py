#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text Formatter for DogeDictate
Handles text formatting, capitalization, punctuation, and structure
"""

import re
import logging

logger = logging.getLogger("DogeDictate.TextFormatter")

class TextFormatter:
    """Formats dictated text with proper capitalization, punctuation, and structure"""
    
    def __init__(self):
        """Initialize the text formatter"""
        # Sentence ending punctuation
        self.sentence_endings = ['.', '!', '?']
        
        # Words that should be capitalized (proper nouns, etc.)
        self.always_capitalize = [
            "i", "i'm", "i'll", "i've", "i'd",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "january", "february", "march", "april", "may", "june", 
            "july", "august", "september", "october", "november", "december"
        ]
        
        # Common abbreviations
        self.abbreviations = {
            "dr": "Dr.",
            "mr": "Mr.",
            "mrs": "Mrs.",
            "ms": "Ms.",
            "prof": "Prof.",
            "etc": "etc.",
            "e.g": "e.g.",
            "i.e": "i.e.",
            "vs": "vs."
        }
        
        # Paragraph break indicators
        self.paragraph_indicators = [
            "new paragraph",
            "next paragraph",
            "new line",
            "next line"
        ]
        
        # Formatting commands
        self.formatting_commands = {
            "bold": {"start": "<b>", "end": "</b>"},
            "italic": {"start": "<i>", "end": "</i>"},
            "underline": {"start": "<u>", "end": "</u>"}
        }
        
        logger.info("Text formatter initialized")
    
    def format_text(self, text):
        """
        Format the given text with proper capitalization, punctuation, and structure
        
        Args:
            text (str): The text to format
            
        Returns:
            str: The formatted text
        """
        if not text:
            return text
            
        # Process paragraph breaks
        text = self._process_paragraph_breaks(text)
        
        # Process formatting commands
        text = self._process_formatting_commands(text)
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        # Format each sentence
        formatted_sentences = [self._format_sentence(sentence) for sentence in sentences]
        
        # Join sentences back together
        formatted_text = " ".join(formatted_sentences)
        
        # Fix spacing issues
        formatted_text = self._fix_spacing(formatted_text)
        
        return formatted_text
    
    def _process_paragraph_breaks(self, text):
        """Process paragraph break indicators"""
        for indicator in self.paragraph_indicators:
            text = re.sub(r'\b' + re.escape(indicator) + r'\b', "\n\n", text, flags=re.IGNORECASE)
        return text
    
    def _process_formatting_commands(self, text):
        """Process formatting commands like bold, italic, etc."""
        # Match patterns like "bold this text" or "make this italic"
        for format_type, tags in self.formatting_commands.items():
            # Pattern: "bold|make bold|format bold <text>"
            pattern = r'\b(?:' + re.escape(format_type) + r'|make ' + re.escape(format_type) + r'|format ' + re.escape(format_type) + r') (.*?)(?:\.|,|;|:|\?|!|$)'
            
            # Replace with formatted text
            text = re.sub(pattern, lambda m: tags["start"] + m.group(1) + tags["end"], text, flags=re.IGNORECASE)
        
        return text
    
    def _split_into_sentences(self, text):
        """Split text into sentences"""
        # Basic sentence splitting
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            if char in self.sentence_endings:
                sentences.append(current_sentence.strip())
                current_sentence = ""
        
        # Add any remaining text as a sentence
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def _format_sentence(self, sentence):
        """Format a single sentence"""
        if not sentence:
            return sentence
            
        # Split into words
        words = sentence.split()
        if not words:
            return sentence
            
        # Capitalize first word
        words[0] = words[0].capitalize()
        
        # Process each word
        for i in range(1, len(words)):
            word = words[i].lower()
            
            # Always capitalize certain words
            if word in self.always_capitalize:
                words[i] = words[i].capitalize()
                
            # Handle abbreviations
            if word in self.abbreviations:
                words[i] = self.abbreviations[word]
        
        # Ensure sentence ends with punctuation
        last_word = words[-1]
        if not any(last_word.endswith(end) for end in self.sentence_endings):
            words[-1] = last_word + "."
        
        return " ".join(words)
    
    def _fix_spacing(self, text):
        """Fix spacing issues in the text"""
        # Fix spaces before punctuation
        text = re.sub(r'\s+([.,;:!?)])', r'\1', text)
        
        # Fix spaces after opening parenthesis
        text = re.sub(r'(\()\s+', r'\1', text)
        
        # Ensure single space after punctuation
        text = re.sub(r'([.,;:!?])\s*', r'\1 ', text)
        
        # Fix multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Fix spacing around paragraph breaks
        text = re.sub(r'\s*\n\s*', '\n', text)
        
        return text.strip() 