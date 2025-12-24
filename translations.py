# translations.py
"""
Translation management for Wait and Pounce
Using Qt's QTranslator system for proper i18n support
"""

from PyQt6.QtCore import QCoreApplication, QTranslator, QLocale
from PyQt6.QtWidgets import QApplication
import sys
import os

class TranslationManager:
    """Manages application translations using Qt's QTranslator"""

    def __init__(self):
        self.translator = QTranslator()
        self.entities_translator = QTranslator()  # Separate translator for entities
        self.current_language = 'en'  # Default language
        self.translations_dir = os.path.join(os.path.dirname(__file__), 'translations')

        # Ensure translations directory exists
        if not os.path.exists(self.translations_dir):
            os.makedirs(self.translations_dir)

    def load_translation(self, language_code='en'):
        """
        Load translation files for specified language

        Loads both main UI translations (pounce_*.qm) and entity translations (entities_*.qm)

        Args:
            language_code: ISO 639-1 language code (en, fr, de, es, zh, etc.)
        """
        app = QApplication.instance()
        if not app:
            return False

        # Remove previous translators if they exist
        if self.translator:
            app.removeTranslator(self.translator)
        if self.entities_translator:
            app.removeTranslator(self.entities_translator)

        # For English, just return (built-in)
        if language_code == 'en':
            self.current_language = 'en'
            return True

        # Load main UI translation
        translation_file = os.path.join(self.translations_dir, f'pounce_{language_code}.qm')
        entities_file = os.path.join(self.translations_dir, f'entities_{language_code}.qm')

        main_loaded = False
        entities_loaded = False

        # Load main translation
        if os.path.exists(translation_file):
            if self.translator.load(translation_file):
                app.installTranslator(self.translator)
                main_loaded = True

        # Load entities translation
        if os.path.exists(entities_file):
            if self.entities_translator.load(entities_file):
                app.installTranslator(self.entities_translator)
                entities_loaded = True

        # Consider successful if at least one translation loaded
        if main_loaded or entities_loaded:
            self.current_language = language_code
            return True

        # If neither file exists or fails to load, use English (built-in)
        self.current_language = 'en'
        return False

    def get_current_language(self):
        """Get currently active language code"""
        return self.current_language

    def get_available_languages(self):
        """Get list of available language translations"""
        if not os.path.exists(self.translations_dir):
            return ['en']

        languages = ['en']  # English is always available (built-in)

        for file in os.listdir(self.translations_dir):
            if file.startswith('pounce_') and file.endswith('.qm'):
                lang_code = file.replace('pounce_', '').replace('.qm', '')
                if lang_code not in languages:
                    languages.append(lang_code)

        return sorted(languages)


# Global translation manager instance
_translation_manager = None

def get_translation_manager():
    """Get or create global translation manager instance"""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


# Convenience function for translations
def tr(context, text):
    """
    Translate text in given context

    Args:
        context: Context identifier (usually class name)
        text: Text to translate

    Returns:
        Translated text or original if no translation available
    """
    return QCoreApplication.translate(context, text)
