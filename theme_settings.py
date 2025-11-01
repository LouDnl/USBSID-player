"""
Theme Settings Window - Global color control for SID Player
Kontrola globalna: Hue, Saturation, Brightness, Temperature
"""

import sys
import colorsys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QGroupBox, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QLinearGradient


class ThemeSettingsWindow(QWidget):
    """Okno ustawień motywu z suwakami do kontroli kolorów"""
    
    # Signal emitowany gdy zmienią się ustawienia
    theme_changed = pyqtSignal(dict)
    player_engine_changed = pyqtSignal(str)  # Emituje nazwę wybranego gracza
    
    def __init__(self, parent=None, initial_settings=None, initial_player=None):
        super().__init__(parent)
        
        # Domyślne wartości
        self.settings = {
            'hue': 210,           # 0-360 (210 = niebieski odcień z oryginalnego motywu)
            'saturation': 50,     # 0-100 (50 = średnie nasycenie)
            'brightness': 50,     # 0-100 (50 = średnia jasność)
            'temperature': 50     # 0-100 (0=cold/blue, 50=neutral, 100=warm/orange)
        }
        
        # Ustawienie gracza
        self.player_engine = initial_player or 'sidplayfp'
        
        # Załaduj początkowe ustawienia jeśli są podane
        if initial_settings:
            self.settings.update(initial_settings)
        
        self.init_ui()
        self.apply_window_theme()
        
        # Ustaw jako osobne okno (nie blokuje głównego)
        self.setWindowFlags(Qt.Window)
    
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        self.setWindowTitle("Theme Settings - Color Control")
        self.setFixedSize(450, 580)  # Zwiększono dla nowego przełącznika
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)  # Zmniejszono marginesy
        layout.setSpacing(12)  # Zmniejszono spacing
        
        # Tytuł
        title = QLabel("GLOBAL THEME SETTINGS")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("color: #c8dce8; letter-spacing: 1px; padding: 5px;")
        title.setFixedHeight(32)  # Fixed height - bez dynamicznych zmian
        layout.addWidget(title)
        
        # Group box dla wyboru gracza
        player_group = QGroupBox("Player Engine Selection")
        player_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        player_layout = QVBoxLayout()
        player_layout.setSpacing(8)
        player_layout.setContentsMargins(12, 12, 12, 12)
        
        player_label = QLabel("Audio Engine:")
        player_label.setFont(QFont("Segoe UI", 10))
        player_label.setStyleSheet("color: #b4c8d8;")
        player_layout.addWidget(player_label)
        
        self.player_combo = QComboBox()
        self.player_combo.addItem("sidplayfp (Default)")
        self.player_combo.addItem("jsidplay2-console (USB SID)")
        
        # Ustaw wybrany gracz
        if self.player_engine == 'jsidplay2':
            self.player_combo.setCurrentIndex(1)
        else:
            self.player_combo.setCurrentIndex(0)
        
        self.player_combo.currentTextChanged.connect(self.on_player_changed)
        self.player_combo.setFixedHeight(32)
        player_layout.addWidget(self.player_combo)
        
        player_group.setLayout(player_layout)
        layout.addWidget(player_group)
        
        # Group box dla suwaków
        sliders_group = QGroupBox("Color Adjustments")
        sliders_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        sliders_layout = QVBoxLayout()
        sliders_layout.setSpacing(10)  # Zmniejszono spacing między suwakami
        sliders_layout.setContentsMargins(12, 12, 12, 12)
        
        # HUE slider (0-360)
        self.hue_slider = self.create_slider_with_label(
            "Hue", 0, 360, self.settings['hue'],
            "0=Red, 120=Green, 210=Blue"
        )
        sliders_layout.addLayout(self.hue_slider['layout'])
        
        # SATURATION slider (0-100)
        self.saturation_slider = self.create_slider_with_label(
            "Saturation", 0, 512, self.settings['saturation'],
            "0=Grayscale, 512=Vivid colors"
        )
        sliders_layout.addLayout(self.saturation_slider['layout'])
        
        # BRIGHTNESS slider (0-100)
        self.brightness_slider = self.create_slider_with_label(
            "Brightness", 0, 290, self.settings['brightness'],
            "0=Dark, 255=Light interface"
        )
        sliders_layout.addLayout(self.brightness_slider['layout'])
        
        # TEMPERATURE slider (0-255)
        self.temperature_slider = self.create_slider_with_label(
            "Temperature", 0, 512, self.settings['temperature'],
            "0=Cold blue, 512=Warm orange"
        )
        sliders_layout.addLayout(self.temperature_slider['layout'])
        
        sliders_group.setLayout(sliders_layout)
        layout.addWidget(sliders_group)
        
        # Przyciski akcji
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        self.reset_button.setFixedHeight(42)
        
        self.apply_button = QPushButton("Apply & Close")
        self.apply_button.clicked.connect(self.apply_and_close)
        self.apply_button.setFixedHeight(42)
        
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.apply_button)
        
        layout.addLayout(button_layout)
        # Usunięto addStretch() - powoduje skakanie przy przesuwaniu suwaków
        
        self.setLayout(layout)
        
        # Połącz slidery z funkcją aktualizacji (live preview)
        self.hue_slider['slider'].valueChanged.connect(self.on_slider_changed)
        self.saturation_slider['slider'].valueChanged.connect(self.on_slider_changed)
        self.brightness_slider['slider'].valueChanged.connect(self.on_slider_changed)
        self.temperature_slider['slider'].valueChanged.connect(self.on_slider_changed)
    
    def create_slider_with_label(self, name, min_val, max_val, current_val, tooltip):
        """Tworzy slider z etykietą i wartością"""
        container_layout = QVBoxLayout()
        container_layout.setSpacing(6)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Górna etykieta z nazwą i wartością
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(name)
        label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        label.setStyleSheet("color: #b4c8d8;")
        
        value_label = QLabel(str(current_val))
        value_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        value_label.setStyleSheet("color: #7fb3d5;")
        value_label.setAlignment(Qt.AlignRight)
        value_label.setFixedWidth(50)  # Fixed width - bez dynamicznych zmian
        
        header_layout.addWidget(label)
        header_layout.addStretch()
        header_layout.addWidget(value_label)
        
        container_layout.addLayout(header_layout)
        
        # Slider
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(current_val)
        slider.setToolTip(tooltip)
        slider.setFixedHeight(24)  # Fixed height - bez dynamicznych zmian
        
        # Połącz slider z value_label
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
        
        container_layout.addWidget(slider)
        
        # Opis - bez word wrap, fixed height
        desc_label = QLabel(tooltip)
        desc_label.setFont(QFont("Segoe UI", 8))
        desc_label.setStyleSheet("color: rgba(180, 200, 216, 0.5);")
        desc_label.setFixedHeight(16)  # Fixed height - eliminuje skakanie
        desc_label.setAlignment(Qt.AlignTop)
        # Usunięto setWordWrap - powodowało dynamiczne zmiany rozmiarów
        container_layout.addWidget(desc_label)
        
        return {
            'layout': container_layout,
            'slider': slider,
            'value_label': value_label
        }
    
    def on_slider_changed(self):
        """Wywołane gdy jakikolwiek slider się zmieni - live preview"""
        # Aktualizuj settings
        self.settings['hue'] = self.hue_slider['slider'].value()
        self.settings['saturation'] = self.saturation_slider['slider'].value()
        self.settings['brightness'] = self.brightness_slider['slider'].value()
        self.settings['temperature'] = self.temperature_slider['slider'].value()
        
        # DEBUG
        print(f"[THEME-SLIDER] Settings changed: {self.settings}")
        
        # Emituj sygnał ze zmienionymi ustawieniami (live preview)
        self.theme_changed.emit(self.settings.copy())
        print("[THEME-SLIDER] Signal emitted!")
    
    def on_player_changed(self, text):
        """Wywołane gdy zmieni się wybrany gracz"""
        if "jsidplay2" in text.lower():
            self.player_engine = 'jsidplay2'
            print("[THEME] Player engine changed to: jsidplay2-console")
        else:
            self.player_engine = 'sidplayfp'
            print("[THEME] Player engine changed to: sidplayfp")
        
        # Emituj sygnał ze zmienioną nazwą gracza
        self.player_engine_changed.emit(self.player_engine)
    
    def reset_to_defaults(self):
        """Resetuj do domyślnych wartości"""
        self.hue_slider['slider'].setValue(210)
        self.saturation_slider['slider'].setValue(50)
        self.brightness_slider['slider'].setValue(50)
        self.temperature_slider['slider'].setValue(50)
        
        # on_slider_changed zostanie wywołane automatycznie
    
    def apply_and_close(self):
        """Zastosuj ustawienia i zamknij okno"""
        # Emit final settings
        self.theme_changed.emit(self.settings.copy())
        self.player_engine_changed.emit(self.player_engine)
        self.close()
    
    def get_player_engine(self):
        """Zwróć wybrany gracz"""
        return self.player_engine
    
    def set_player_engine(self, engine):
        """Ustaw wybrany gracz"""
        self.player_engine = engine
        if engine == 'jsidplay2':
            self.player_combo.setCurrentIndex(1)
        else:
            self.player_combo.setCurrentIndex(0)
    
    def apply_window_theme(self):
        """Zastosuj motyw do okna ustawień"""
        self.setAutoFillBackground(True)
        palette = self.palette()
        gradient = QLinearGradient(0, 0, 0, 480)
        gradient.setColorAt(0.0, QColor(20, 28, 38))
        gradient.setColorAt(0.5, QColor(28, 38, 48))
        gradient.setColorAt(1.0, QColor(18, 25, 35))
        palette.setBrush(QPalette.Window, gradient)
        self.setPalette(palette)
        
        self.setStyleSheet("""
        QWidget {
            background: transparent;
            color: #b4c8d8;
        }
        QGroupBox {
            background-color: transparent;
            border: none;
            border-radius: 12px;
            margin-top: 12px;
            padding-top: 20px;
            font-weight: bold;
            color: #c8dce8;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 8px 16px;
            color: #c8dce8;
        }
        QPushButton {
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            padding: 12px 24px;
            font-size: 10pt;
            font-weight: 500;
            color: #b4c8d8;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.14);
            border-color: rgba(255, 255, 255, 0.2);
        }
        QPushButton:pressed {
            background-color: rgba(255, 255, 255, 0.06);
        }
        QSlider::groove:horizontal {
            border: none;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(100, 150, 180, 0.95),
                stop:1 rgba(70, 110, 140, 0.95));
            border: 2px solid rgba(200, 220, 232, 0.3);
            width: 18px;
            height: 18px;
            margin: -7px 0;
            border-radius: 9px;
        }
        QSlider::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(120, 170, 200, 1.0),
                stop:1 rgba(90, 130, 160, 1.0));
            border-color: rgba(200, 220, 232, 0.5);
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(70, 110, 140, 0.9),
                stop:1 rgba(100, 150, 180, 0.9));
            border-radius: 3px;
        }
        """)
    
    def get_settings(self):
        """Zwróć aktualne ustawienia"""
        return self.settings.copy()
    
    def set_settings(self, settings):
        """Ustaw wartości suwaków z zewnątrz"""
        if 'hue' in settings:
            self.hue_slider['slider'].setValue(settings['hue'])
        if 'saturation' in settings:
            self.saturation_slider['slider'].setValue(settings['saturation'])
        if 'brightness' in settings:
            self.brightness_slider['slider'].setValue(settings['brightness'])
        if 'temperature' in settings:
            self.temperature_slider['slider'].setValue(settings['temperature'])


# Funkcje pomocnicze do konwersji kolorów
def apply_theme_to_color(base_color, hue, saturation, brightness, temperature):
    """
    Zastosuj globalne ustawienia motywu do koloru bazowego
    
    Args:
        base_color: tuple (r, g, b) w zakresie 0-255
        hue: 0-360 (wartość docelowego odcienia, nie shift!)
        saturation: 0-100 (mnożnik nasycenia, 50=bez zmian)
        brightness: 0-100 (mnożnik jasności, 50=bez zmian)
        temperature: 0-100 (0=cold/blue, 50=neutral, 100=warm/orange)
    
    Returns:
        tuple (r, g, b) w zakresie 0-255
    """
    # Konwertuj RGB na HSL
    r, g, b = base_color[0] / 255.0, base_color[1] / 255.0, base_color[2] / 255.0
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    # USTAW HUE jako wartość absolutną (nie dodawaj!)
    h = hue / 360.0
    
    # Zastosuj SATURATION (50 = 1.0x, 0 = 0x, 100 = 2.0x)
    saturation_multiplier = saturation / 50.0
    s = min(1.0, s * saturation_multiplier)
    
    # Zastosuj BRIGHTNESS (50 = 1.0x, 0 = 0x, 100 = 2.0x)
    brightness_multiplier = brightness / 50.0
    l = min(1.0, l * brightness_multiplier)
    
    # Konwertuj z powrotem na RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    
    # Zastosuj TEMPERATURE (mieszaj z ciepłym/zimnym odcieniem)
    # Jeżeli saturation == 0, pozostaw idealną skalę szarości (pomijamy temperaturę)
    if temperature != 50 and saturation > 0:
        temp_factor = (temperature - 50) / 50.0  # -1.0 to 1.0
        
        if temp_factor > 0:  # Warm (orange tint)
            r = min(1.0, r + temp_factor * 0.15)
            g = min(1.0, g + temp_factor * 0.08)
            b = max(0.0, b - temp_factor * 0.1)
        else:  # Cold (blue tint)
            r = max(0.0, r + temp_factor * 0.1)
            g = max(0.0, g + temp_factor * 0.05)
            b = min(1.0, b - temp_factor * 0.15)
    
    # Konwertuj na zakres 0-255
    return (int(r * 255), int(g * 255), int(b * 255))


# Test standalone
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    def on_theme_change(settings):
        print(f"Theme changed: {settings}")
    
    window = ThemeSettingsWindow()
    window.theme_changed.connect(on_theme_change)
    window.show()
    
    sys.exit(app.exec_())
