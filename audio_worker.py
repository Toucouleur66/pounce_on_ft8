# audio_worker.py

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6 import QtCore

class AudioWorker(QObject):
    play_sound_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.sounds = {}

        self.play_sound_signal.connect(self.on_play_sound)

        self.sounds["wanted_callsign_detected"] = self._create_sound_effect("sounds/495650__matrixxx__supershort-ping-or-short-notification.wav")
        self.sounds["directed_to_my_call"]      = self._create_sound_effect("sounds/716445__scottyd0es__tone12_error.wav")
        self.sounds["ready_to_log"]            = self._create_sound_effect("sounds/709072__scottyd0es__aeroce-dualtone-5.wav")
        self.sounds["error_occurred"]          = self._create_sound_effect("sounds/142608__autistic-lucario__error.wav")
        self.sounds["monitored_callsign_detected"] = self._create_sound_effect("sounds/716442__scottyd0es__tone12_alert_3.wav")
        self.sounds["band_change"]             = self._create_sound_effect("sounds/342759__rhodesmas__score-counter-01.wav")
        self.sounds["enable_global_sound"]      = self._create_sound_effect("sounds/342754__rhodesmas__searching-01.wav")

    def _create_sound_effect(self, path):
        effect = QSoundEffect()
        effect.setSource(QtCore.QUrl.fromLocalFile(path))

        effect.setVolume(1.0)
        return effect

    @pyqtSlot(str)
    def on_play_sound(self, sound_name):
        if sound_name in self.sounds:
            effect = self.sounds[sound_name]
            effect.play()
        else:
            print(f"[AudioWorker] Unknown sound: {sound_name}")
