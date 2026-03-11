import os
import sys
import math
import json
import random
import winreg
import ctypes

from PySide6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QDialog, 
                               QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                               QDoubleSpinBox, QSpinBox, QPushButton, QCheckBox)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QCursor, QPen
from PySide6.QtCore import QTimer, QPoint, Qt

# Win32 API
user32 = ctypes.windll.user32

def set_run_on_startup(enable=True):
    # PyInstaller로 패키징된 exe인지, 일반 py 스크립트인지 구분하여 절대 경로 획득
    if getattr(sys, 'frozen', False):
        app_path = sys.executable
    else:
        app_path = os.path.abspath(__file__)
        
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "TwoEyeApp" # 레지스트리에 등록될 이름
    
    try:
        # 레지스트리 키 열기
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
                
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Registry access error: {e}")

def check_run_on_startup():
    # 현재 시작프로그램으로 등록되어 있는지 확인하여 UI에 반영
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "TwoEyeApp"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 전역 설정 관리 (JSON 연동)
class EyeConfig:
    def __init__(self):
        # 기본값 세팅
        self.theme = "Normal"
        self.sensitivity = 2.5
        self.fps = 30
        
        # 설정 파일 경로: C:\Users\사용자명\.two_eye_config.json
        self.config_path = os.path.join(os.path.expanduser("~"), ".two_eye_config.json")
        
        # 객체 생성 시 자동으로 JSON 파일 읽어오기
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 파일에 값이 없으면 기본값을 유지하도록 get() 사용
                    self.theme = data.get("theme", self.theme)
                    self.sensitivity = data.get("sensitivity", self.sensitivity)
                    self.fps = data.get("fps", self.fps)
            except Exception as e:
                print(f"Config load error: {e}")

    def save(self):
        data = {
            "theme": self.theme,
            "sensitivity": self.sensitivity,
            "fps": self.fps
        }
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Config save error: {e}")

# 전역 객체 생성 (이때 자동으로 load()가 실행됨)
config = EyeConfig()

# 설정 윈도우 UI
class SettingsDialog(QDialog):
    def __init__(self, update_callback):
        super().__init__()
        self.setWindowTitle("Eye Settings")
        self.setFixedSize(250, 200)
        self.update_callback = update_callback # 설정 변경 시 호출할 함수

        layout = QVBoxLayout()

        # 1. 테마 설정
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Normal", "Cat", "Cyborg"])
        self.theme_combo.setCurrentText(config.theme)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # 2. 민감도 설정
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(QLabel("Sensitivity:"))
        self.sens_spin = QDoubleSpinBox()
        self.sens_spin.setRange(1.0, 10.0)
        self.sens_spin.setSingleStep(0.5)
        self.sens_spin.setValue(config.sensitivity)
        sens_layout.addWidget(self.sens_spin)
        layout.addLayout(sens_layout)

        # 3. FPS 설정
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 60)
        self.fps_spin.setValue(config.fps)
        fps_layout.addWidget(self.fps_spin)
        layout.addLayout(fps_layout)

        # 4. 시작프로그램 체크박스
        startup_layout = QHBoxLayout()
        self.startup_check = QCheckBox("Run on Windows Startup")
        
        # 창 열릴 때 레지스트리 확인해서 체크박스 상태 갱신
        self.startup_check.setChecked(check_run_on_startup()) 
        
        startup_layout.addWidget(self.startup_check)
        layout.addLayout(startup_layout)

        # 5. 적용 버튼
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_settings)
        layout.addWidget(self.apply_btn)

        self.setLayout(layout)

    def apply_settings(self):
        # 1. UI의 값을 전역 설정 메모리에 업데이트
        config.theme = self.theme_combo.currentText()
        config.sensitivity = self.sens_spin.value()
        config.fps = self.fps_spin.value()
        
        # 2. 변경된 설정을 JSON 파일로 즉시 저장
        config.save()
        
        # 3. 시작프로그램 설정 윈도우 레지스트리에 반영
        set_run_on_startup(self.startup_check.isChecked())
        
        # 4. 콜백 실행 (눈알 타이머 등 재설정)
        self.update_callback() 
        self.accept()

# 눈알 메인 로직
class PreciseEye(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.blink_step = 0
        self.idle_blink_frames = 0
        self.last_center = QPoint(0, 0)
        
        # 수면 관련 변수
        self.last_mouse_pos = QPoint(0, 0)
        self.idle_ticks = 0
        self.is_sleeping = False
        
        self.update_icon(QCursor.pos())
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.apply_timer_speed()

    def apply_timer_speed(self):
        # FPS 설정에 따라 타이머 주기(ms) 변경
        interval = int(1000 / config.fps)
        self.timer.start(interval)

    def do_idle_blink(self):
        # 수면 상태가 아닐 때만 자동 깜빡임 진행
        if self.blink_step == 0 and not self.is_sleeping:
            self.idle_blink_frames = 4

    def tick(self):
        current_pos = QCursor.pos()
        
        # 1. 수면 감지 로직
        if current_pos != self.last_mouse_pos:
            self.idle_ticks = 0
            self.is_sleeping = False
            self.last_mouse_pos = current_pos
        else:
            self.idle_ticks += 1
            if self.idle_ticks >= (config.fps * 120): # 120초 정지 시 수면
                self.is_sleeping = True

        # 2. 클릭 및 상태 전이 로직
        left_pressed = (user32.GetAsyncKeyState(0x01) & 0x8000) != 0
        right_pressed = (user32.GetAsyncKeyState(0x02) & 0x8000) != 0
        is_pressed = left_pressed or right_pressed

        if is_pressed:
            self.idle_blink_frames = 0 
            if self.blink_step < 2: self.blink_step += 1
        elif self.is_sleeping:
            self.idle_blink_frames = 0
            if self.blink_step < 2: self.blink_step += 1
        elif self.idle_blink_frames > 0:
            if self.idle_blink_frames >= 3:
                if self.blink_step < 2: self.blink_step += 1
            else:
                if self.blink_step > 0: self.blink_step -= 1
            self.idle_blink_frames -= 1
        else:
            if self.blink_step > 0: self.blink_step -= 1
                
        self.update_icon(QCursor.pos())

    def update_icon(self, mouse_pos):
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        geom = self.geometry()
        if geom.isValid() and geom.width() > 0:
            self.last_center = geom.center()
        elif self.last_center == QPoint(0, 0):
            self.last_center = QPoint(1000, 1000)

        dx = mouse_pos.x() - self.last_center.x()
        dy = mouse_pos.y() - self.last_center.y()
        angle = math.atan2(dy, dx)
        
        # [설정 연동] 민감도 적용
        dist = min(6.0, math.hypot(dx, dy) / config.sensitivity)

        # --- 렌더링 분기 ---
        if self.blink_step == 2:
            pen = QPen(QColor("#1a1a1a"), 3, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(6, 16, 26, 16)
        else:
            # 1. 흰자위 테마 처리
            if config.theme == "Cat":
                painter.setBrush(QColor("#F4D03F")) # 노란색 눈
            elif config.theme == "Cyborg":
                painter.setBrush(QColor("#1a1a1a")) # 검은색 눈
            else:
                painter.setBrush(QColor("white"))
            
            painter.setPen(Qt.NoPen)
            # 수면(또는 반깜빡임) 상태면 찌그러진 타원, 아니면 둥근 타원
            eye_h = 10 if self.blink_step == 1 else 24
            eye_y = 11 if self.blink_step == 1 else 4
            painter.drawEllipse(4, eye_y, 24, eye_h)

            # 2. 눈동자 위치 및 모양 처리
            pupil_x = 16 + int(math.cos(angle) * dist)
            pupil_y = 16 + int(math.sin(angle) * dist)
            if self.blink_step == 1: 
                pupil_y = max(11, min(pupil_y, 21)) # 반눈 상태 위치 제한

            if config.theme == "Cat":
                painter.setBrush(QColor("#1a1a1a"))
                painter.drawEllipse(QPoint(pupil_x, pupil_y), 2, 8) # 세로로 찢어진 동공
            elif config.theme == "Cyborg":
                painter.setBrush(QColor("#ff0000"))
                painter.drawRect(pupil_x-3, pupil_y-3, 6, 6) # 네모난 빨간 동공
            else:
                painter.setBrush(QColor("#1a1a1a"))
                painter.drawEllipse(QPoint(pupil_x, pupil_y), 5, 5) # 기본 둥근 동공

        painter.end()
        self.setIcon(QIcon(pixmap))

# 앱 실행 및 설정
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 앱 전체(모든 창, 메뉴)의 기본 아이콘을 강제로 박아넣음
    app_icon = QIcon(resource_path("eye_icon_simple.ico"))
    app.setWindowIcon(app_icon)

    eye_l = PreciseEye()
    eye_r = PreciseEye()

    # 설정 변경 시 양쪽 눈알의 타이머 FPS를 재설정하는 콜백 함수
    def on_settings_updated():
        eye_l.apply_timer_speed()
        eye_r.apply_timer_speed()

    # 설정 창 객체를 보관할 전역 변수
    settings_window = None

    def open_settings():
        global settings_window
        
        # 창이 아예 생성되지 않았거나, X 버튼을 눌러서 숨겨진(닫힌) 경우
        if settings_window is None or not settings_window.isVisible():
            # 기존 창을 덮어쓰거나 새로 생성
            settings_window = SettingsDialog(on_settings_updated)
            settings_window.show() # exec() 대신 show()를 써서 Non-modal로 띄움
        
        # 이미 열려있다면 화면 맨 앞으로 가져오고 포커스 깜빡임
        settings_window.raise_()
        settings_window.activateWindow()

    # 우클릭 메뉴 구성
    menu = QMenu()
    menu.addAction("Settings").triggered.connect(open_settings)
    menu.addSeparator()
    menu.addAction("Exit").triggered.connect(app.quit)
    
    eye_l.setContextMenu(menu)
    eye_r.setContextMenu(menu)

    eye_l.show()
    eye_r.show()

    # 랜덤 자동 깜빡임 타이머
    def trigger_random_blink():
        eye_l.do_idle_blink()
        eye_r.do_idle_blink()
        QTimer.singleShot(random.randint(3000, 7000), trigger_random_blink)

    QTimer.singleShot(3000, trigger_random_blink)

    sys.exit(app.exec())