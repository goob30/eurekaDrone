from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl
from PyQt5.QtCore import QTimer
import sys
import serialpy

app = QApplication(sys.argv)

# main window
window = QWidget()
window.setWindowTitle("Operation Screen")
window.setGeometry(100, 100, 1200, 700)

main_layout = QHBoxLayout(window)

drone_lat = 0.0
drone_long = 0.0

# left panel - drone modes etc
left_widget = QWidget()
left_widget.setFixedWidth(250)
left_panel = QVBoxLayout(left_widget)
connection_label = QLabel("Connection IS FUCKED")
speed_label = QLabel("Speed IS FUCKED")
lat_label = QLabel(f"Lat {drone_lat}")
long_label = QLabel(f"Long {drone_long}")
com_label = QLabel("COM")
com_input = QLineEdit()
com_input.setPlaceholderText("e.g. COM5")
connect_button = QPushButton("Connect serial")

for label in [connection_label, speed_label, lat_label, long_label]:
    label.setWordWrap(True)

def connect_serial():
    com_port = com_input.text().strip()
    if not com_port:
        connection_label.setText("Enter a COM port first")
        return

    try:
        serialpy.connect(com_port)
        connection_label.setText(f"Connected: {com_port}")
    except Exception as e:
        connection_label.setText(f"Connection failed: {e}")

connect_button.clicked.connect(connect_serial)

left_panel.addWidget(connection_label)
left_panel.addWidget(speed_label)
left_panel.addWidget(lat_label)
left_panel.addWidget(long_label)
left_panel.addWidget(com_label)
left_panel.addWidget(com_input)
left_panel.addWidget(connect_button)
left_panel.addStretch()

# center panel - map and cam feed
center_widget = QWidget()
center_widget.setFixedWidth(700)
center_panel = QVBoxLayout(center_widget)

# map with scroll zoom
map_view = QWebEngineView()

# Optimized OpenStreetMap HTML with scroll zoom
map_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { margin: 0; padding: 0; }
        #map { width: 100%; height: 100vh; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {
            center: [43.4643, -80.5204],
            zoom: 13,
            minZoom: 1,
            maxZoom: 19,
            scrollWheelZoom: true,  // Enable scroll zoom
            zoomControl: true,
            attributionControl: true
        });

        // Optimized tile layer
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
            maxNativeZoom: 19,
            keepBuffer: 2,
            updateWhenIdle: false,
            updateWhenZooming: false,
            fadeAnimation: true
        }).addTo(map);

        // Smoother scroll zoom
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
        if isinstance(result, dict) and "lat" in result and "lng" in result:
            drone_lat = result["lat"]
            drone_long = result["lng"]
            lat_label.setText(f"Lat {drone_lat:.6f}")
            long_label.setText(f"Long {drone_long:.6f}")

    map_view.page().runJavaScript("window.currentLocation", handle_location)

location_timer = QTimer()
location_timer.timeout.connect(update_drone_location)
location_timer.start(2000)

# camera feed placeholder
cam_view = QWebEngineView()
cam_view.setHtml("""
    <div style='background-color:#e0e0e0; height:100%; display:flex; 
                align-items:center; justify-content:center; border:2px solid #999;'>
        <h3 style='color:#666;'>Camera Feed Placeholder</h3>
    </div>
""")

center_panel.addWidget(map_view)
center_panel.addWidget(cam_view)

# right panel target list and positions
right_widget = QWidget()
right_widget.setFixedWidth(250)
right_panel = QVBoxLayout(right_widget)
target_label = QLabel("Target List Area")
target_label.setWordWrap(True)

right_panel.addWidget(target_label)
right_panel.addStretch()

main_layout.addWidget(left_widget)
main_layout.addWidget(center_widget)
main_layout.addWidget(right_widget)

window.show()
sys.exit(app.exec_())
