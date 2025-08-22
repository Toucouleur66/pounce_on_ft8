from PyQt6.QtCore import QTimer, QObject, pyqtSignal
import math


class AnimatedCounter(QObject):
    valueChanged = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, duration_ms=2000, fps=60, parent=None):
        super().__init__(parent)
        self.duration_ms = duration_ms
        self.fps = fps
        self.interval_ms = int(1000 / fps)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        
        self.start_value = 0
        self.end_value = 0
        self.current_value = 0
        self.elapsed_time = 0
        self.is_running = False
    
    def animate_to(self, target_value, start_value=0):
        self.start_value = start_value
        self.end_value = target_value
        self.current_value = start_value
        self.elapsed_time = 0
        self.is_running = True
        
        if self.start_value == self.end_value:
            self.valueChanged.emit(self.end_value)
            self.finished.emit()
            return
        
        self.timer.start(self.interval_ms)
    
    def stop(self):
        self.timer.stop()
        self.is_running = False
    
    def _update(self):
        self.elapsed_time += self.interval_ms
        progress = min(self.elapsed_time / self.duration_ms, 1.0)
        
        eased_progress = self._ease_in_out_expo(progress)
        
        self.current_value = int(self.start_value + (self.end_value - self.start_value) * eased_progress)
        
        self.valueChanged.emit(self.current_value)
        
        if progress >= 1.0:
            self.timer.stop()
            self.is_running = False
            self.finished.emit()
    
    def _ease_in_out_expo(self, t):
        if t == 0:
            return 0
        if t == 1:
            return 1
        if t < 0.5:
            return 0.5 * math.pow(2, 20 * t - 10)
        else:
            return 0.5 * (2 - math.pow(2, -20 * t + 10))
    
    def get_current_value(self):
        return self.current_value
    
    def is_animating(self):
        return self.is_running