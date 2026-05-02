from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import sys

app = QApplication(sys.argv)

# main window
window = QWidget()
window.setWindowTitle("Operation Screen")
window.setGeometry(100, 100, 1200, 700)

main_layout = QHBoxLayout(window)

drone_lat = 0.0
drone_long = 0.0

# left panel - drone modes etc
left_panel = QVBoxLayout()
connection_label = QLabel("Connection IS FUCKED")
speed_label = QLabel("Speed IS FUCKED")
lat_label = QLabel("Lat {}")

left_panel.addWidget(connection_label)
left_panel.addWidget(speed_label)
left_panel.addStretch()

# center panel - map and cam feed
center_panel = QVBoxLayout()

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
    </script>
</body>
</html>
"""

map_view.setHtml(map_html)

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
right_panel = QVBoxLayout()
target_label = QLabel("Target List Area")

right_panel.addWidget(target_label)
right_panel.addStretch()

main_layout.addLayout(left_panel, 1)
main_layout.addLayout(center_panel, 4)
main_layout.addLayout(right_panel, 1)

window.show()
sys.exit(app.exec_())