from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
import sys
import os
import cv2
import numpy as np
import serialpy
from keras.models import load_model



class ClickableCameraLabel(QLabel):
    def __init__(self, click_handler):
        super().__init__('Webcam feed initializing...')
        self._click_handler = click_handler

    def mousePressEvent(self, event):
        if self._click_handler is not None:
            self._click_handler(event)
        super().mousePressEvent(event)


app = QApplication(sys.argv)

# main window
window = QWidget()
window.setWindowTitle('Operation Screen')
window.setGeometry(100, 100, 1200, 700)
window.setObjectName('root')

main_layout = QHBoxLayout(window)
main_layout.setContentsMargins(10, 10, 10, 10)
main_layout.setSpacing(10)

drone_lat = 0.0
drone_long = 0.0

np.set_printoptions(suppress=True)

base_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(base_dir, 'converted_keras', 'keras_Model.h5')
labels_path = os.path.join(base_dir, 'converted_keras', 'labels.txt')

model = None
class_names = []

try:
    model = load_model(model_path, compile=False)
    with open(labels_path, 'r', encoding='utf-8') as f:
        class_names = [line.strip().split(' ', 1)[-1] for line in f.readlines()]
except Exception as e:
    print(f'AI model load failed: {e}')

camera = cv2.VideoCapture(1)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

detected_faces = []
selected_targets = {}
target_counter = 1
last_frame_shape = None
last_render_rect = None
frame_counter = 0
last_predictions = {}

# left panel - drone modes etc
left_widget = QWidget()
left_widget.setFixedWidth(250)
left_widget.setObjectName('sidePanel')
left_panel = QVBoxLayout(left_widget)
left_panel.setContentsMargins(16, 16, 16, 16)
left_panel.setSpacing(10)
connection_label = QLabel('Connection IS FUCKED')
speed_label = QLabel('Speed IS FUCKED')
lat_label = QLabel(f'Lat {drone_lat}')
long_label = QLabel(f'Long {drone_long}')
com_label = QLabel('COM')
com_label.setObjectName('fieldLabel')
com_input = QLineEdit()
com_input.setPlaceholderText('e.g. COM5')
connect_button = QPushButton('Connect serial')
connect_button.setObjectName('primaryButton')

# 1-row directional controls
controls_row = QHBoxLayout()
left_button = QPushButton('Left')
center_button = QPushButton('Center')
right_button = QPushButton('Right')
left_button.setObjectName('controlButton')
center_button.setObjectName('controlButton')
right_button.setObjectName('controlButton')
controls_row.addWidget(left_button)
controls_row.addWidget(center_button)
controls_row.addWidget(right_button)
controls_row.setSpacing(8)
for button in [left_button, center_button, right_button]:
    button.setAutoRepeat(False)
    button.setEnabled(False)

for label in [connection_label, speed_label, lat_label, long_label]:
    label.setWordWrap(True)


def connect_serial():
    com_port = com_input.text().strip()
    if not com_port:
        connection_label.setText('Enter a COM port first')
        return

    try:
        connected_port = serialpy.connect(com_port)
        connection_label.setText(f'Connected: {connected_port}')
        for button in [left_button, center_button, right_button]:
            button.setEnabled(True)
    except Exception as e:
        connection_label.setText(f'Connection failed: {e}')
        for button in [left_button, center_button, right_button]:
            button.setEnabled(False)


def send_servo_command(action_name, action_fn):
    try:
        action_fn()
        speed_label.setText(f'Last cmd: {action_name}')
    except Exception as e:
        connection_label.setText(f'Command failed: {e}')


connect_button.clicked.connect(connect_serial)
left_button.clicked.connect(lambda: send_servo_command('LEFT', serialpy.left))
center_button.clicked.connect(lambda: send_servo_command('CENTER', serialpy.center))
right_button.clicked.connect(lambda: send_servo_command('RIGHT', serialpy.right))

left_panel.addWidget(connection_label)
left_panel.addWidget(speed_label)
left_panel.addWidget(lat_label)
left_panel.addWidget(long_label)
left_panel.addWidget(com_label)
left_panel.addWidget(com_input)
left_panel.addWidget(connect_button)
left_panel.addLayout(controls_row)
left_panel.addStretch()

# center panel - map and cam feed
center_widget = QWidget()
center_widget.setFixedWidth(700)
center_widget.setObjectName('centerPanel')
center_panel = QVBoxLayout(center_widget)
center_panel.setContentsMargins(0, 0, 0, 0)
center_panel.setSpacing(10)

# map with scroll zoom
map_view = QWebEngineView()

# OpenStreetMap HTML with scroll zoom
map_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' />
    <script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
    <style>
        body { margin: 0; padding: 0; }
        #map { width: 100%; height: 100vh; }
    </style>
</head>
<body>
    <div id='map'></div>
    <script>
        var map = L.map('map', {
            center: [43.4643, -80.5204],
            zoom: 13,
            minZoom: 1,
            maxZoom: 19,
            scrollWheelZoom: true,
            zoomControl: true,
            attributionControl: true
        });

        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '(c) OpenStreetMap contributors',
            maxZoom: 19,
            maxNativeZoom: 19,
            keepBuffer: 2,
            updateWhenIdle: false,
            updateWhenZooming: false,
            fadeAnimation: true
        }).addTo(map);

        map.options.scrollWheelZoom = 'center';
        map.options.wheelDebounceTime = 40;
        map.options.wheelPxPerZoomLevel = 120;

        window.currentLocation = null;
        var userMarker = null;

        function setUserLocation(lat, lng) {
            window.currentLocation = {lat: lat, lng: lng};
            if (userMarker) {
                map.removeLayer(userMarker);
            }
            userMarker = L.marker([lat, lng]).addTo(map).bindPopup('Your location');
            map.setView([lat, lng], 15);
        }

        if (navigator.geolocation) {
            navigator.geolocation.watchPosition(
                function(position) {
                    setUserLocation(position.coords.latitude, position.coords.longitude);
                },
                function(error) {
                    console.log('Geolocation failed:', error.message);
                },
                {enableHighAccuracy: true, timeout: 10000, maximumAge: 2000}
            );
        }
    </script>
</body>
</html>
"""

map_view.setHtml(map_html)


def handle_feature_permission_requested(security_origin, feature):
    if feature == QWebEnginePage.Geolocation:
        map_view.page().setFeaturePermission(
            security_origin,
            feature,
            QWebEnginePage.PermissionGrantedByUser
        )
    else:
        map_view.page().setFeaturePermission(
            security_origin,
            feature,
            QWebEnginePage.PermissionDeniedByUser
        )


map_view.page().featurePermissionRequested.connect(handle_feature_permission_requested)


def update_drone_location():
    def handle_location(result):
        global drone_lat, drone_long
        if isinstance(result, dict) and 'lat' in result and 'lng' in result:
            drone_lat = result['lat']
            drone_long = result['lng']
            lat_label.setText(f'Lat {drone_lat:.6f}')
            long_label.setText(f'Long {drone_long:.6f}')

    map_view.page().runJavaScript('window.currentLocation', handle_location)


location_timer = QTimer()
location_timer.timeout.connect(update_drone_location)
location_timer.start(2000)


# right panel target list and positions
right_widget = QWidget()
right_widget.setFixedWidth(250)
right_widget.setObjectName('sidePanel')
right_panel = QVBoxLayout(right_widget)
right_panel.setContentsMargins(16, 16, 16, 16)
right_panel.setSpacing(10)
target_label = QLabel('Target List Area (click face to add)')
target_label.setWordWrap(True)

target_list_widget = QWidget()
target_list_layout = QVBoxLayout(target_list_widget)
target_list_layout.setContentsMargins(0, 0, 0, 0)
target_list_layout.setSpacing(8)

right_panel.addWidget(target_label)
right_panel.addWidget(target_list_widget)
right_panel.addStretch()


def refresh_target_panel():
    while target_list_layout.count():
        item = target_list_layout.takeAt(0)
        child = item.widget()
        if child is not None:
            child.deleteLater()

    for target_id, target in selected_targets.items():
        tx, ty = target['center']
        info = QLabel(
            f"{target_id}\n"
            f"Class: {target['label']}\n"
            f"Confidence: {target['confidence'] * 100:.0f}%\n"
            f"Pos: ({tx}, {ty})\n"
            f"Last seen ticks: {target['last_seen']}"
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            'background-color: #1a223d; border: 1px solid #334155;'
            'border-radius: 6px; padding: 8px; color: #dbe7f6;'
        )
        target_list_layout.addWidget(info)


def camera_click_handler(event):
    global target_counter
    if last_frame_shape is None or last_render_rect is None:
        return

    click_x = event.pos().x()
    click_y = event.pos().y()
    draw_x, draw_y, draw_w, draw_h = last_render_rect
    if draw_w <= 0 or draw_h <= 0:
        return
    if click_x < draw_x or click_x > (draw_x + draw_w) or click_y < draw_y or click_y > (draw_y + draw_h):
        return

    frame_h, frame_w = last_frame_shape[:2]
    frame_x = int((click_x - draw_x) * frame_w / draw_w)
    frame_y = int((click_y - draw_y) * frame_h / draw_h)

    clicked_face = None
    for face in detected_faces:
        x, y, w, h = face['bbox']
        if x <= frame_x <= (x + w) and y <= frame_y <= (y + h):
            clicked_face = face
            break

    if clicked_face is None:
        return

    cx, cy = clicked_face['center']
    for target in selected_targets.values():
        tx, ty = target['center']
        if abs(tx - cx) < 60 and abs(ty - cy) < 60:
            return

    target_id = f'TARGET-{target_counter:03d}'
    target_counter += 1
    selected_targets[target_id] = {
        'center': clicked_face['center'],
        'bbox': clicked_face['bbox'],
        'label': clicked_face['label'],
        'confidence': clicked_face['confidence'],
        'last_seen': 0
    }
    refresh_target_panel()


# camera feed
cam_view = ClickableCameraLabel(camera_click_handler)
cam_view.setAlignment(Qt.AlignCenter)
cam_view.setStyleSheet('background-color: #000; color: #6b7280; border: 1px solid #2a3f5f;')

center_panel.addWidget(map_view)
center_panel.addWidget(cam_view)


def update_camera_feed():
    global detected_faces, last_frame_shape, last_render_rect, frame_counter

    if camera is None or not camera.isOpened():
        cam_view.setText('Webcam not available')
        return

    ret, frame = camera.read()
    if not ret:
        cam_view.setText('Failed to read webcam frame')
        return

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))
    detected_faces = []
    frame_counter += 1

    for idx, (x, y, w, h) in enumerate(faces):
        face_roi = frame[y:y + h, x:x + w]
        if face_roi.size == 0:
            continue

        model_input = cv2.resize(face_roi, (224, 224), interpolation=cv2.INTER_AREA)
        label_name = 'Unknown'
        confidence_score = 0.0
        score_dwait = 0.0
        score_jon = 0.0

        cache_key = f'face_{idx}'
        cached = last_predictions.get(cache_key)

        # Run model every 3rd frame to reduce native backend stress.
        if model is not None and class_names and (frame_counter % 3 == 0 or cached is None):
            image = np.asarray(model_input, dtype=np.float32).reshape(1, 224, 224, 3)
            image = (image / 127.5) - 1
            prediction = model.predict(image, verbose=0)[0]
            index = int(np.argmax(prediction))
            label_name = class_names[index] if index < len(class_names) else 'Unknown'
            confidence_score = float(prediction[index])
            if len(prediction) >= 2:
                score_dwait = float(prediction[0])
                score_jon = float(prediction[1])
            last_predictions[cache_key] = (label_name, confidence_score, score_dwait, score_jon)
        elif cached is not None:
            label_name, confidence_score, score_dwait, score_jon = cached

        detected_faces.append({
            'bbox': (int(x), int(y), int(w), int(h)),
            'center': (int(x + (w / 2)), int(y + (h / 2))),
            'label': label_name,
            'confidence': confidence_score,
            'dwait': score_dwait,
            'jon': score_jon
        })

    speed_label.setText(f'Faces: {len(detected_faces)}')

    for face in detected_faces:
        x, y, w, h = face['bbox']
        cv2.rectangle(frame, (x, y), (x + w, y + h), (74, 158, 255), 2)

        meter_y = max(18, y - 24)
        meter_x = x
        meter_w = max(130, w)
        meter_h = 14
        cv2.rectangle(frame, (meter_x, meter_y), (meter_x + meter_w, meter_y + meter_h), (35, 35, 35), -1)
        dwait_w = int(meter_w * max(0.0, min(1.0, face['dwait'])))
        cv2.rectangle(frame, (meter_x, meter_y), (meter_x + dwait_w, meter_y + meter_h), (80, 200, 120), -1)
        cv2.rectangle(frame, (meter_x, meter_y), (meter_x + meter_w, meter_y + meter_h), (180, 180, 180), 1)

        meter_text = f"Dwait {face['dwait'] * 100:.0f}% | Jon {face['jon'] * 100:.0f}%"
        cv2.putText(frame, meter_text, (meter_x, meter_y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (235, 235, 235), 1, cv2.LINE_AA)

        label_text = f"{face['label']} {face['confidence'] * 100:.0f}%"
        cv2.putText(frame, label_text, (x, y + h + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1, cv2.LINE_AA)

    for target in selected_targets.values():
        best_match = None
        best_dist = 10**9
        tx, ty = target['center']
        for face in detected_faces:
            fx, fy = face['center']
            dist = abs(fx - tx) + abs(fy - ty)
            if dist < best_dist:
                best_dist = dist
                best_match = face

        if best_match is not None and best_dist < 120:
            target['center'] = best_match['center']
            target['bbox'] = best_match['bbox']
            target['label'] = best_match['label']
            target['confidence'] = best_match['confidence']
            target['last_seen'] = 0
        else:
            target['last_seen'] += 1

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    bytes_per_line = ch * w
    last_frame_shape = rgb.shape
    qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    pixmap = QPixmap.fromImage(qt_image)
    scaled = pixmap.scaled(cam_view.width(), cam_view.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    draw_x = int((cam_view.width() - scaled.width()) / 2)
    draw_y = int((cam_view.height() - scaled.height()) / 2)
    last_render_rect = (draw_x, draw_y, scaled.width(), scaled.height())
    cam_view.setPixmap(scaled)
    refresh_target_panel()


camera_timer = QTimer()
camera_timer.timeout.connect(update_camera_feed)
camera_timer.start(33)

main_layout.addWidget(left_widget)
main_layout.addWidget(center_widget)
main_layout.addWidget(right_widget)

app.setStyleSheet("""
QWidget#root {
    background-color: #0a0e27;
    color: #e0e0e0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 13px;
}
QWidget#sidePanel {
    background-color: #151933;
    border: 1px solid #2a3f5f;
    border-radius: 8px;
}
QWidget#centerPanel {
    background-color: #0f1228;
    border: 1px solid #2a3f5f;
    border-radius: 8px;
}
QLabel {
    color: #cfd8e3;
}
QLabel#fieldLabel {
    color: #8fa1ba;
    font-size: 11px;
    font-weight: 600;
}
QLineEdit {
    background-color: #0f172a;
    color: #e0e0e0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 10px;
    min-height: 20px;
}
QLineEdit:focus {
    border: 1px solid #4a9eff;
}
QPushButton {
    background-color: #1a223d;
    color: #e0e0e0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 10px 12px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #223055;
    border-color: #4a9eff;
}
QPushButton:pressed {
    background-color: #192644;
}
QPushButton:disabled {
    background-color: #121a30;
    color: #6b7280;
    border-color: #24324a;
}
QPushButton#primaryButton {
    background-color: #1f2e52;
    border-color: #3f5e8d;
}
QPushButton#primaryButton:hover {
    background-color: #27406f;
    border-color: #4a9eff;
}
QPushButton#controlButton {
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
""")

window.show()
exit_code = app.exec_()
serialpy.close()
if camera is not None and camera.isOpened():
    camera.release()
sys.exit(exit_code)
