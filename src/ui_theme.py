"""
SID Player UI Theme and Layout Mixin
Extracted from sid_player_modern07.py (Phase 5 refactoring)

This module contains the UIThemeMixin class which provides:
- apply_modern_theme(): Theme application with color transformations
- init_ui(): UI initialization and layout setup

The mixin is designed to be inherited by the SIDPlayer class to separate
UI/styling concerns from the main playback logic.
"""

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QProgressBar, QGroupBox, QFrame, QCheckBox
)
from PyQt5.QtGui import QFont, QPalette, QColor, QLinearGradient, QIcon, QFontMetrics
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal
import os
import ctypes

from theme_settings import apply_theme_to_color
from sid_player_ui import ClickableProgressBar


class UIThemeMixin:
    """Mixin providing UI theme and layout methods for SID Player"""
    
    def apply_modern_theme(self):
        """Zastosuj motyw z uwzględnieniem theme_settings"""
        # Pobierz theme settings
        hue = self.theme_settings['hue']
        sat = self.theme_settings['saturation']
        bright = self.theme_settings['brightness']
        contrast = self.theme_settings['contrast']
        temp = self.theme_settings['temperature']
        
        # Bazowe kolory do transformacji
        base_bg_dark = (20, 28, 38)
        base_bg_mid = (28, 38, 48)
        base_bg_light = (18, 25, 35)
        base_accent = (70, 110, 140)
        base_text = (180, 200, 216)
        
        # Zastosuj transformacje
        bg_dark = apply_theme_to_color(base_bg_dark, hue, sat, bright, contrast, temp)
        bg_mid = apply_theme_to_color(base_bg_mid, hue, sat, bright, contrast, temp)
        bg_light = apply_theme_to_color(base_bg_light, hue, sat, bright, contrast, temp)
        accent = apply_theme_to_color(base_accent, hue, sat, bright, contrast, temp)
        text_color = apply_theme_to_color(base_text, hue, sat, bright, contrast, temp)

        # Składniki kolorów do użycia w rgba(...)
        a_r, a_g, a_b = accent
        t_r, t_g, t_b = text_color
        # Zachowaj do ponownego użycia w funkcjach stylujących przyciski/status
        self._theme_accent_rgb = accent
        self._theme_text_rgb = text_color

        # Skala wygaszania elementów disabled zależnie od jasności (0 -> niewidoczne)
        disabled_scale = max(0.0, min(1.0, bright / 100.0))
        da_btn_bg = round(0.20 * disabled_scale, 3)
        da_btn_border = round(0.30 * disabled_scale, 3)
        da_btn_text = round(0.40 * disabled_scale, 3)
        da_chk_text = round(0.40 * disabled_scale, 3)
        da_chk_bg = round(0.06 * disabled_scale, 3)
        da_chk_border = round(0.10 * disabled_scale, 3)
        
        print(f"[THEME-APPLY] Colors: dark={bg_dark}, mid={bg_mid}, light={bg_light}")
        
        # Aplikuj gradient BEZPOŚREDNIO w CSS (nie przez paletę!)
        self.setStyleSheet(f"""
        #SIDPlayerRoot {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgb{bg_dark},
                stop:0.5 rgb{bg_mid},
                stop:1 rgb{bg_light});
        }}
        QWidget {{
            background: transparent;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            padding: 8px 14px;
            font-size: 10pt;
            font-weight: 500;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton:hover {{ 
            background-color: rgba(255, 255, 255, 0.14);
            border-color: rgba(255, 255, 255, 0.2);
        }}
        QPushButton:pressed {{ 
            background-color: rgba(255, 255, 255, 0.06); 
        }}
        QPushButton:disabled {{
            background-color: rgba(255, 255, 255, 0.03);
            color: rgba({t_r}, {t_g}, {t_b}, 0.3);
            border-color: rgba(255, 255, 255, 0.05);
        }}
        QPushButton#PlayButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border: none;
            color: rgb({t_r}, {t_g}, {t_b});
            font-weight: 600;
        }}
        QPushButton#PauseButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.55);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.65);
            color: rgb({t_r}, {t_g}, {t_b});
            font-weight: 500;
        }}
        QPushButton#PauseButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.65);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.75);
        }}
        QPushButton#PauseButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.45);
        }}
        QPushButton#PauseButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        QPushButton#StopButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#StopButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#StopButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#StopButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        QPushButton#PlayButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.95);
        }}
        QPushButton#PlayButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.75);
        }}
        QPushButton#PlayButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.3);
            color: rgba({t_r}, {t_g}, {t_b}, 0.4);
        }}

        QProgressBar {{
            border: none;
            border-radius: 3px;
            background-color: rgba(255, 255, 255, 0.08);
            height: 6px;
        }}
        QProgressBar::chunk {{
            background-color: rgb({a_r}, {a_g}, {a_b});
            border-radius: 3px;
        }}
        QLabel {{
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QCheckBox {{
            color: rgb({t_r}, {t_g}, {t_b});
            spacing: 8px;
        }}
        /* Loop checkbox: no background under control/text */
        QCheckBox#LoopCheckbox {{
            background-color: transparent;
            border: none;
            padding: 0px;
        }}
        QCheckBox#LoopCheckbox:hover {{
            background-color: transparent;
            border: none;
        }}
        QCheckBox#LoopCheckbox:pressed {{
            background-color: transparent;
            border: none;
        }}
        QCheckBox#LoopCheckbox::indicator:checked {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
        }}
        QCheckBox#LoopCheckbox:disabled {{
            color: rgba({t_r}, {t_g}, {t_b}, {da_chk_text});
            background-color: transparent;
            border: none;
        }}
        QCheckBox#LoopCheckbox::indicator:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_chk_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_chk_border});
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.15);
        }}
        QCheckBox::indicator:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QCheckBox::indicator:checked {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
        }}
        QCheckBox::indicator:checked:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.95);
        }}

        /* Theme button uses accent */
        QPushButton#ThemeButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#ThemeButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#ThemeButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#ThemeButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        /* Playlist button uses accent color like Theme button */
        QPushButton#PlaylistButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#PlaylistButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#PlaylistButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#PlaylistButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        /* Prev/Next Song buttons use accent color like Theme button */
        QPushButton#PrevSongButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#PrevSongButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#PrevSongButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#PrevSongButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        QPushButton#NextSongButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#NextSongButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#NextSongButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#NextSongButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        /* Fast Forward button themed baseline (will be overridden by update_button_style) */
        QPushButton#FastForwardButton {{
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#FastForwardButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        """)

        # Nadpisz style etykiet, aby na pewno reagowały na theme (lokalne QSS)
        self.title_label.setStyleSheet(f"color: rgb({t_r}, {t_g}, {t_b});")
        self.author_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.7);")
        self.year_group_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.7);")
        self.tracker_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.7);")
        self.time_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.95);")
        
        # Style dla kontrolek subtune
        if hasattr(self, 'subtune_label'):
            self.subtune_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.7);")
            self.subtune_number.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.95);")
            
            # Style dla przycisków subtune
            subtune_button_style = f"""
            QPushButton {{
                background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
                border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.4);
                border-radius: 5px;  /* Zmniejszone zaokrąglenie rogów */
                color: rgb({t_r}, {t_g}, {t_b});
                font-weight: bold;
                padding: 0px;
                font-size: 20pt;  /* Większa czcionka w CSS */
                line-height: 1;   /* Lepsze wycentrowanie pionowe */
                text-align: center; /* Wycentrowanie poziome */
            }}
            QPushButton:hover {{
                background-color: rgba({a_r}, {a_g}, {a_b}, 0.3);
                border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.6);
            }}
            QPushButton:pressed {{
                background-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
            }}
            """
            # Apply subtune button style only to subtune arrow buttons
            print(f"[SUBTUNE-STYLE] Applying style to prev_subtune_button, enabled={self.prev_subtune_button.isEnabled()}")
            print(f"[SUBTUNE-STYLE] Applying style to next_subtune_button, enabled={self.next_subtune_button.isEnabled()}")
            self.prev_subtune_button.setStyleSheet(subtune_button_style)
            self.next_subtune_button.setStyleSheet(subtune_button_style)
            print(f"[SUBTUNE-STYLE] ✓ Styles applied successfully")
            # prev_song_button and next_song_button use default button styling

        # Odśwież style progress_bar i loop_checkbox bezpośrednio (force update)
        progress_stylesheet = f"""
        QProgressBar {{
            border: none;
            border-radius: 3px;
            background-color: rgba(255, 255, 255, 0.08);
            height: 6px;
        }}
        QProgressBar::chunk {{
            background-color: rgb({a_r}, {a_g}, {a_b});
            border-radius: 3px;
        }}
        """
        self.progress_bar.setStyleSheet(progress_stylesheet)
        
        loop_stylesheet = f"""
        QCheckBox {{
            color: rgb({t_r}, {t_g}, {t_b});
            spacing: 8px;
            background-color: transparent;
            border: none;
            padding: 0px;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.15);
        }}
        QCheckBox::indicator:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QCheckBox::indicator:checked {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
        }}
        """
        self.loop_checkbox.setStyleSheet(loop_stylesheet)
        
        # Bezpośrednio ustaw stylesheets dla main buttons
        play_button_style = f"""
        QPushButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border: none;
            border-radius: 20px;
            padding: 8px 14px;
            font-size: 10pt;
            font-weight: 600;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.95);
        }}
        QPushButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.75);
        }}
        QPushButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        """
        self.play_button.setStyleSheet(play_button_style)
        
        pause_button_style = f"""
        QPushButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.55);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.65);
            border-radius: 20px;
            padding: 8px 14px;
            font-size: 10pt;
            font-weight: 500;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.65);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.75);
        }}
        QPushButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.45);
        }}
        QPushButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        """
        self.pause_button.setStyleSheet(pause_button_style)
        
        stop_button_style = f"""
        QPushButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-radius: 20px;
            padding: 8px 14px;
            font-size: 10pt;
            font-weight: 500;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        """
        self.stop_button.setStyleSheet(stop_button_style)
        
        # Force refresh UI elements to apply new theme
        self.progress_bar.style().unpolish(self.progress_bar)
        self.progress_bar.style().polish(self.progress_bar)
        self.loop_checkbox.style().unpolish(self.loop_checkbox)
        self.loop_checkbox.style().polish(self.loop_checkbox)
        
        # Force refresh main buttons
        for btn in [self.play_button, self.pause_button, self.stop_button]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        
        # Force refresh root widget and whole tree
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        
        # Odśwież styl przycisku Fast Forward po zmianie motywu
        self.update_button_style()
        # Odśwież status label, aby przejął kolor z motywu
        self.update_status_label()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(0)

        self.status_label = QLabel("READY")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 7, QFont.Bold))
        self.status_label.setStyleSheet("""
            color: rgba(180, 200, 216, 0.5);
            letter-spacing: 12px;
            padding: 2px;
        """)
        layout.addWidget(self.status_label)

        layout.addSpacing(1)

        hero_container = QFrame()
        hero_container.setStyleSheet("background: transparent;")
        hero_container.setFixedHeight(180)
        hero_layout = QVBoxLayout(hero_container)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(1)

        self.title_label = QLabel("DROP A SID FILE")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.title_label.setMaximumHeight(90)  # Ograniczy wysokość aby tekst się nie wylewał
        self.title_label.setMinimumHeight(60)  # Minimum height dla spójności
        self.title_label.setMaximumWidth(350)  # Ograniczy szerokość aby tekst się zawijał
        self.title_label.setStyleSheet("""
            color: #c8dce8;
            line-height: 1.3;
            padding: 2px 2px;
            margin: 0px;
        """)
        hero_layout.addWidget(self.title_label)
        hero_layout.addSpacing(4)

        self.author_label = QLabel("Unknown Artist")
        self.author_label.setAlignment(Qt.AlignCenter)
        self.author_label.setFont(QFont("Segoe UI", 12))
        self.author_label.setStyleSheet("color: rgba(180, 200, 216, 0.7);")
        hero_layout.addWidget(self.author_label)

        self.year_group_label = QLabel()
        self.year_group_label.setAlignment(Qt.AlignCenter)
        self.year_group_label.setFont(QFont("Segoe UI", 10))
        self.year_group_label.setStyleSheet("color: rgba(180, 200, 216, 0.7);")
        self.year_group_label.setMaximumHeight(0)  # Ukryj domyślnie aż do załadowania pliku
        self.year_group_label.hide()
        hero_layout.addWidget(self.year_group_label)

        self.tracker_label = QLabel()
        self.tracker_label.setAlignment(Qt.AlignCenter)
        self.tracker_label.setFont(QFont("Segoe UI", 9))
        self.tracker_label.setObjectName("TrackerLabel")  # Ustaw objectName dla stylowania przez theme
        self.tracker_label.setMaximumHeight(0)  # Ukryj domyślnie
        self.tracker_label.hide()
        hero_layout.addWidget(self.tracker_label)

        layout.addWidget(hero_container)
        layout.addSpacing(2)

        self.time_label = QLabel("00:00 / 02:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.time_label.setStyleSheet("""
            color: rgba(200, 220, 232, 0.95);
            letter-spacing: 2px;
        """)
        layout.addWidget(self.time_label)

        layout.addSpacing(2)

        # Custom clickable progress bar
        self.progress_bar = ClickableProgressBar(total_duration_callback=lambda: self.total_duration)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.seek_requested.connect(self.seek_to_time)
        layout.addWidget(self.progress_bar)
        
        layout.addSpacing(12)
        
        # Subtune selection controls
        subtune_buttons_layout = QHBoxLayout()
        subtune_buttons_layout.setAlignment(Qt.AlignCenter)
        subtune_buttons_layout.setSpacing(8)

        # Previous song button
        self.prev_song_button = QPushButton("Prev Song")  
        self.prev_song_button.setObjectName("PrevSongButton")
        self.prev_song_button.setMinimumHeight(34)
        self.prev_song_button.setMinimumWidth(85)
        self.prev_song_button.setMaximumWidth(95)  # Zapobiegaj rozszerzaniu się
        self.prev_song_button.clicked.connect(self.prev_song)
        subtune_buttons_layout.addWidget(self.prev_song_button)

        # Previous subtune button
        self.prev_subtune_button = QPushButton("←")  # Używamy prostego symbolu strzałki
        self.prev_subtune_button.setObjectName("PrevSubtuneButton")
        self.prev_subtune_button.setFixedSize(32, 32)  # Nieco większy przycisk
        self.prev_subtune_button.setFont(QFont("Arial", 14, QFont.Bold))  # Jeszcze większa czcionka (20pt)
        self.prev_subtune_button.clicked.connect(lambda: self._on_prev_subtune_clicked())
        subtune_buttons_layout.addWidget(self.prev_subtune_button)

        # Subtune number display
        self.subtune_number = QLabel("1")
        self.subtune_number.setObjectName("SubtuneNumber")
        self.subtune_number.setAlignment(Qt.AlignCenter)
        self.subtune_number.setFixedWidth(30)
        self.subtune_number.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.subtune_number.setStyleSheet("color: rgba(200, 220, 232, 0.95);")
        subtune_buttons_layout.addWidget(self.subtune_number)

        # Next subtune button
        self.next_subtune_button = QPushButton("→")  # Używamy prostego symbolu strzałki
        self.next_subtune_button.setObjectName("NextSubtuneButton")
        self.next_subtune_button.setFixedSize(32, 32)  # Nieco większy przycisk
        self.next_subtune_button.setFont(QFont("Arial", 14, QFont.Bold))  # Jeszcze większa czcionka (20pt)
        self.next_subtune_button.clicked.connect(lambda: self._on_next_subtune_clicked())
        subtune_buttons_layout.addWidget(self.next_subtune_button)

        # Next song button
        self.next_song_button = QPushButton("Next Song")  
        self.next_song_button.setObjectName("NextSongButton")
        self.next_song_button.setMinimumHeight(34)
        self.next_song_button.setMinimumWidth(85)
        self.next_song_button.setMaximumWidth(95)  # Zapobiegaj rozszerzaniu się
        self.next_song_button.clicked.connect(self.next_song)
        subtune_buttons_layout.addWidget(self.next_song_button)
        
        # Dodaj przyciski do głównego layoutu
        layout.addLayout(subtune_buttons_layout)
        
        # Subtune label - teraz poniżej przycisków
        subtune_label_layout = QHBoxLayout()
        subtune_label_layout.setAlignment(Qt.AlignCenter)
        
        self.subtune_label = QLabel("1 subtunes")  # Bez nawiasów kwadratowych
        self.subtune_label.setObjectName("SubtuneLabel")
        self.subtune_label.setFont(QFont("Segoe UI", 10))
        self.subtune_label.setStyleSheet("color: rgba(200, 220, 232, 0.7);")
        subtune_label_layout.addWidget(self.subtune_label)
        
        layout.addLayout(subtune_label_layout)
        
        layout.addSpacing(12)

        # Loop checkbox + Default tune only checkbox
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setAlignment(Qt.AlignCenter)
        
        self.loop_checkbox = QCheckBox("Loop Song")
        self.loop_checkbox.setObjectName("LoopCheckbox")
        self.loop_checkbox.setAttribute(Qt.WA_StyledBackground, True)
        self.loop_checkbox.setFont(QFont("Segoe UI", 11))
        self.loop_checkbox.stateChanged.connect(self.toggle_loop)
        checkbox_layout.addWidget(self.loop_checkbox)
        
        checkbox_layout.addSpacing(20)
        
        self.default_tune_only_checkbox = QCheckBox("Default tune only")
        self.default_tune_only_checkbox.setObjectName("DefaultTuneCheckbox")
        self.default_tune_only_checkbox.setAttribute(Qt.WA_StyledBackground, True)
        self.default_tune_only_checkbox.setFont(QFont("Segoe UI", 11))
        self.default_tune_only_checkbox.stateChanged.connect(self.toggle_default_tune_only)
        checkbox_layout.addWidget(self.default_tune_only_checkbox)
        
        layout.addLayout(checkbox_layout)

        layout.addSpacing(24)

        # Main buttons (horizontal layout)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.play_button = QPushButton("PLAY")
        self.play_button.setObjectName("PlayButton")
        self.play_button.clicked.connect(self.start_playing)
        self.play_button.setMinimumHeight(44)
        self.play_button.setMinimumWidth(80)
        
        self.pause_button = QPushButton("PAUSE")
        self.pause_button.setObjectName("PauseButton")
        self.pause_button.clicked.connect(self.pause_playing)
        self.pause_button.setEnabled(False)
        self.pause_button.setMinimumHeight(44)
        self.pause_button.setMinimumWidth(80)
        
        self.stop_button = QPushButton("STOP")
        self.stop_button.setObjectName("StopButton")
        self.stop_button.clicked.connect(self.stop_sid_file)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(44)
        self.stop_button.setMinimumWidth(80)
        
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        layout.addSpacing(20)

        # Speed control button - toggle between 1x and 8x
        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(22)
        
        self.fast_forward_button = QPushButton("Fast Foward")
        self.fast_forward_button.setObjectName("FastForwardButton")
        self.fast_forward_button.clicked.connect(self.toggle_speed)
        self.fast_forward_button.setEnabled(False)
        self.fast_forward_button.setMinimumHeight(40)
        
        speed_layout.addWidget(self.fast_forward_button)
        layout.addLayout(speed_layout)

        layout.addSpacing(20)

        # Playlist & Theme buttons (side by side)
        buttons_layout = QHBoxLayout()
        buttons_layout.setAlignment(Qt.AlignCenter)
        buttons_layout.setSpacing(16)
        
        # Playlist button - teraz jako TOGGLE (checkable)
        self.playlist_button = QPushButton("PLAYLIST")
        self.playlist_button.setObjectName("PlaylistButton")
        self.playlist_button.setCheckable(True)  # ⭐ TOGGLE MODE
        self.playlist_button.toggled.connect(self.toggle_playlist_visibility)  # ⭐ Zmieniono z clicked na toggled
        self.playlist_button.setMinimumHeight(40)
        self.playlist_button.setMinimumWidth(100)
        self.playlist_button.setToolTip("Open playlist manager (Ctrl+L)")
        
        # Theme button
        self.theme_button = QPushButton("THEME")
        self.theme_button.setObjectName("ThemeButton")
        self.theme_button.clicked.connect(self.open_theme_settings)
        self.theme_button.setMinimumHeight(40)
        self.theme_button.setMinimumWidth(100)
        self.theme_button.setToolTip("Theme settings (Hue, Saturation, Brightness, Temperature)")
        
        buttons_layout.addWidget(self.playlist_button)
        buttons_layout.addWidget(self.theme_button)
        layout.addLayout(buttons_layout)

        # FIXED: Dodaj stałe spacing na końcu zamiast stretch
        layout.addSpacing(20)

        self.setLayout(layout)
        self.setWindowTitle("SID Player  [CTRL+X = Toggle Console]")
        
        # Ustaw ikonę aplikacji
        icon_paths = [
            os.path.join(self.base_dir, "assets", "sid_ico.png"),
            os.path.join(self.base_dir, "assets", "sid_ico.svg"),
            os.path.join(self.base_dir, "assets", "sid_ico.ico"),
        ]
        
        for path in icon_paths:
            if os.path.exists(path):
                try:
                    icon = QIcon(path)
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        app = QApplication.instance()
                        app.setWindowIcon(icon)
                        QApplication.setWindowIcon(icon)
                        
                        # AppUserModelID dla Windows
                        try:
                            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('sidplayer.modern.v07')
                        except:
                            pass
                        break
                except:
                    pass

    # ===============================================
    #         DYNAMIC TITLE FONT SCALING
    # ===============================================
    def scale_title_font(self, text):
        """Skaluj rozmiar fontu title_label aby tekst zmieścił się bez dzielenia"""
        if not text or not hasattr(self, 'title_label'):
            return
        
        max_width = 350  # Maksymalna szerokość dostępna dla tekstu
        min_font_size = 10  # Minimalny rozmiar czcionki
        max_font_size = 24  # Maksymalny rozmiar czcionki
        
        # Start with max font size i zmniejszaj aż tekst się zmieści
        for font_size in range(max_font_size, min_font_size - 1, -1):
            font = QFont("Segoe UI", font_size, QFont.Bold)
            metrics = QFontMetrics(font)
            text_width = metrics.horizontalAdvance(text)
            
            # Jeśli tekst się zmieści, użyj tego rozmiaru
            if text_width <= max_width:
                self.title_label.setFont(font)
                return
        
        # Jeśli nic nie passou, użyj minimalnego rozmiaru
        font = QFont("Segoe UI", min_font_size, QFont.Bold)
        self.title_label.setFont(font)

    # ----------------------------------------------
    #         ODCZYT SONG LENGTHS (SONGLENGTHS.MD5)
    # ----------------------------------------------
