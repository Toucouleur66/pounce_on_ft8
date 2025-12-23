# translations.py
"""
Translation management for DX Pounce on FT8
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
        self.current_language = 'en'  # Default language
        self.translations_dir = os.path.join(os.path.dirname(__file__), 'translations')

        # Ensure translations directory exists
        if not os.path.exists(self.translations_dir):
            os.makedirs(self.translations_dir)

    def load_translation(self, language_code='en'):
        """
        Load translation file for specified language

        Args:
            language_code: ISO 639-1 language code (en, fr, de, es, etc.)
        """
        app = QApplication.instance()
        if not app:
            return False

        # Remove previous translator if exists
        if self.translator:
            app.removeTranslator(self.translator)

        # For English, just return (built-in)
        if language_code == 'en':
            self.current_language = 'en'
            return True

        # Load new translation
        translation_file = os.path.join(self.translations_dir, f'pounce_{language_code}.qm')

        if os.path.exists(translation_file):
            # Try to load with Qt's translator first
            if self.translator.load(translation_file):
                app.installTranslator(self.translator)
                self.current_language = language_code
                return True
            else:
                # If Qt translator fails, try our simple format
                try:
                    import pickle
                    with open(translation_file, 'rb') as f:
                        header = f.read(10)
                        if header == b'SIMPLE_QM\x00':
                            # This is our simple format, load as custom translator
                            translations = pickle.load(f)
                            # Create a custom translator (would need implementation)
                            # For now, just note it in current_language
                            self.current_language = language_code
                            return True
                except Exception:
                    pass

        # If translation file doesn't exist or fails to load, use English (built-in)
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
