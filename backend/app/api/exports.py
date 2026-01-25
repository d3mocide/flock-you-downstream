"""Export API endpoints - CSV and KML export."""
import os
import csv
from datetime import datetime
from flask import request, jsonify, send_file, current_app
from . import api_bp


@api_bp.route('/export/csv', methods=['GET'])
def export_csv():
    """Export detections as CSV."""
    export_type = request.args.get('type', 'session')

    storage = current_app.config['storage_service']

    if export_type == 'cumulative':
        data = storage.cumulative_detections
        filename_prefix = "flockyou_cumulative"
    else:
        data = storage.session_detections
        filename_prefix = f"flockyou_session_{storage.session_start.strftime('%Y%m%d_%H%M%S')}"

    if not data:
        return jsonify({'status': 'error', 'message': 'No detections to export'}), 400

    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join('exports', filename)
    os.makedirs('exports', exist_ok=True)

    fieldnames = [
        'timestamp', 'detection_time', 'server_timestamp', 'protocol', 'detection_method',
        'ssid', 'device_name', 'mac_address', 'manufacturer', 'alias', 'rssi', 'last_rssi',
        'signal_strength', 'channel', 'last_channel', 'detection_count',
        'latitude', 'longitude', 'altitude', 'gps_timestamp', 'satellites', 'fix_quality',
        'gps_time_diff', 'gps_match_quality', 'timestamp_source',
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for detection in data:
            gps = detection.get('gps', {})
            row = {
                'timestamp': detection.get('timestamp'),
                'detection_time': detection.get('detection_time'),
                'server_timestamp': detection.get('server_timestamp'),
                'protocol': detection.get('protocol'),
                'detection_method': detection.get('detection_method'),
                'ssid': detection.get('ssid', ''),
                'device_name': detection.get('device_name', ''),
                'mac_address': detection.get('mac_address'),
                'manufacturer': detection.get('manufacturer', 'Unknown'),
                'alias': detection.get('alias', ''),
                'rssi': detection.get('rssi'),
                'last_rssi': detection.get('last_rssi'),
                'signal_strength': detection.get('signal_strength'),
                'channel': detection.get('channel'),
                'last_channel': detection.get('last_channel'),
                'detection_count': detection.get('detection_count', 1),
                'latitude': gps.get('latitude'),
                'longitude': gps.get('longitude'),
                'altitude': gps.get('altitude'),
                'gps_timestamp': gps.get('timestamp'),
                'satellites': gps.get('satellites'),
                'fix_quality': gps.get('fix_quality'),
                'gps_time_diff': gps.get('time_diff'),
                'gps_match_quality': gps.get('match_quality'),
                'timestamp_source': detection.get('timestamp_source', 'unknown'),
            }
            writer.writerow(row)

    return send_file(filepath, as_attachment=True, download_name=filename)


@api_bp.route('/export/kml', methods=['GET'])
def export_kml():
    """Export detections as KML for Google Earth."""
    export_type = request.args.get('type', 'session')

    storage = current_app.config['storage_service']

    if export_type == 'cumulative':
        data = storage.cumulative_detections
        filename_prefix = "flockyou_cumulative"
        document_name = "Flock You Cumulative Detections"
    else:
        data = storage.session_detections
        filename_prefix = f"flockyou_session_{storage.session_start.strftime('%Y%m%d_%H%M%S')}"
        document_name = f"Flock You Session - {storage.session_start.strftime('%Y-%m-%d %H:%M:%S')}"

    if not data:
        return jsonify({'status': 'error', 'message': 'No detections to export'}), 400

    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.kml"
    filepath = os.path.join('exports', filename)
    os.makedirs('exports', exist_ok=True)

    kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>{document_name}</name>
    <description>Surveillance device detections ({len(data)} detections)</description>
'''

    for i, detection in enumerate(data):
        gps = detection.get('gps', {})
        if gps.get('latitude') and gps.get('longitude'):
            name = detection.get('alias') or f"Detection {i + 1}"
            lat = gps.get('latitude')
            lon = gps.get('longitude')
            alt = gps.get('altitude', 0)

            kml_content += f'''
    <Placemark>
        <name>{name}</name>
        <description><![CDATA[
            <b>Protocol:</b> {detection.get('protocol')}<br/>
            <b>Method:</b> {detection.get('detection_method')}<br/>
            <b>MAC:</b> {detection.get('mac_address')}<br/>
            <b>Manufacturer:</b> {detection.get('manufacturer', 'Unknown')}<br/>
            <b>RSSI:</b> {detection.get('rssi', 'N/A')} dBm<br/>
            <b>Detection Count:</b> {detection.get('detection_count', 1)}<br/>
        ]]></description>
        <Point>
            <coordinates>{lon},{lat},{alt}</coordinates>
        </Point>
    </Placemark>
'''

    kml_content += '''
</Document>
</kml>'''

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(kml_content)

    return send_file(filepath, as_attachment=True, download_name=filename)
