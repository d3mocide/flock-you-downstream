"""Storage Service - Handles data persistence for detections and settings."""
import pickle
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import threading


class StorageService:
    """Manages persistent storage for detections and settings."""

    def __init__(self, data_dir: str = 'data'):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(exist_ok=True)

        self._cumulative_file = self._data_dir / 'cumulative_detections.pkl'
        self._settings_file = self._data_dir / 'settings.json'

        self._lock = threading.Lock()

        # In-memory state
        self._session_detections: List[Dict[str, Any]] = []
        self._cumulative_detections: List[Dict[str, Any]] = []
        self._settings: Dict[str, Any] = {
            'gps_port': '',
            'flock_port': '',
            'filter': 'all',
        }
        self._session_start = datetime.now()
        self._next_id = 1

        # Load persisted data
        self._load_cumulative()
        self._load_settings()

    @property
    def session_start(self) -> datetime:
        return self._session_start

    @property
    def session_detections(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._session_detections.copy()

    @property
    def cumulative_detections(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._cumulative_detections.copy()

    @property
    def settings(self) -> Dict[str, Any]:
        with self._lock:
            return self._settings.copy()

    def add_detection(self, detection: Dict[str, Any]) -> Dict[str, Any]:
        """Add or update a detection. Returns the detection with ID."""
        with self._lock:
            mac_address = detection.get('mac_address')
            existing = None

            if mac_address:
                for d in self._session_detections:
                    if d.get('mac_address') == mac_address:
                        existing = d
                        break

            if existing:
                # Update existing detection
                existing['detection_count'] = existing.get('detection_count', 1) + 1
                existing['last_seen'] = datetime.now().isoformat()
                existing['last_rssi'] = detection.get('rssi', existing.get('last_rssi'))
                existing['last_channel'] = detection.get('channel', existing.get('last_channel'))
                existing['last_ssid'] = detection.get('ssid', existing.get('last_ssid'))
                existing['last_device_name'] = detection.get('device_name', existing.get('last_device_name'))

                if detection.get('gps'):
                    existing['gps'] = detection['gps']

                # Update in cumulative
                for cd in self._cumulative_detections:
                    if cd.get('mac_address') == mac_address:
                        cd.update(existing)
                        break

                self._save_cumulative()
                return existing
            else:
                # Create new detection
                detection['id'] = self._next_id
                self._next_id += 1
                detection['alias'] = ''
                detection['detection_count'] = 1
                detection['first_seen'] = datetime.now().isoformat()
                detection['last_seen'] = datetime.now().isoformat()

                self._session_detections.append(detection)
                self._cumulative_detections.append(detection.copy())
                self._save_cumulative()

                return detection

    def get_detection_by_id(self, detection_id: int) -> Optional[Dict[str, Any]]:
        """Get a detection by its ID."""
        with self._lock:
            for d in self._session_detections:
                if d.get('id') == detection_id:
                    return d.copy()
        return None

    def update_alias(self, detection_id: int, alias: str) -> Optional[Dict[str, Any]]:
        """Update the alias of a detection."""
        with self._lock:
            for d in self._session_detections:
                if d.get('id') == detection_id:
                    d['alias'] = alias.strip()
                    return d.copy()
        return None

    def clear_session(self):
        """Clear all session detections."""
        with self._lock:
            self._session_detections.clear()
            self._next_id = 1
            self._session_start = datetime.now()

    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        with self._lock:
            session = self._session_detections
            cumulative = self._cumulative_detections

        return {
            'session': {
                'total': len(session),
                'wifi': len([d for d in session if d.get('protocol') == 'wifi']),
                'ble': len([d for d in session if d.get('protocol') in ['bluetooth_le', 'bluetooth_classic']]),
                'gps': len([d for d in session if d.get('gps')]),
                'start_time': self._session_start.isoformat(),
            },
            'cumulative': {
                'total': len(cumulative),
                'wifi': len([d for d in cumulative if d.get('protocol') == 'wifi']),
                'ble': len([d for d in cumulative if d.get('protocol') in ['bluetooth_le', 'bluetooth_classic']]),
                'gps': len([d for d in cumulative if d.get('gps')]),
            },
        }

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update settings."""
        with self._lock:
            self._settings.update(new_settings)
            self._save_settings()
            return self._settings.copy()

    def _load_cumulative(self):
        """Load cumulative detections from disk."""
        try:
            if self._cumulative_file.exists():
                with open(self._cumulative_file, 'rb') as f:
                    self._cumulative_detections = pickle.load(f)
                print(f"Loaded {len(self._cumulative_detections)} cumulative detections")
            else:
                self._cumulative_detections = []
        except Exception as e:
            print(f"Error loading cumulative detections: {e}")
            self._cumulative_detections = []

    def _save_cumulative(self):
        """Save cumulative detections to disk."""
        try:
            with open(self._cumulative_file, 'wb') as f:
                pickle.dump(self._cumulative_detections, f)
        except Exception as e:
            print(f"Error saving cumulative detections: {e}")

    def _load_settings(self):
        """Load settings from disk."""
        try:
            if self._settings_file.exists():
                with open(self._settings_file, 'r') as f:
                    self._settings.update(json.load(f))
                print(f"Loaded settings: {self._settings}")
        except Exception as e:
            print(f"Error loading settings: {e}")

    def _save_settings(self):
        """Save settings to disk."""
        try:
            with open(self._settings_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
