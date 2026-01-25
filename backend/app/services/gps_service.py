"""GPS Service - Handles GPS dongle communication and NMEA parsing."""
import threading
import time
import serial
import serial.tools.list_ports
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GPSData:
    """GPS fix data structure."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    timestamp: Optional[str] = None
    fix_quality: int = 0
    satellites: int = 0
    hdop: float = 0.0
    system_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'timestamp': self.timestamp,
            'fix_quality': self.fix_quality,
            'satellites': self.satellites,
            'hdop': self.hdop,
        }

    def is_valid(self) -> bool:
        return (
            self.fix_quality > 0
            and self.latitude is not None
            and self.longitude is not None
            and -90 <= self.latitude <= 90
            and -180 <= self.longitude <= 180
        )


class GPSService:
    """Manages GPS dongle connection and data reading."""

    BAUDRATE = 9600
    TIMEOUT = 1
    MAX_HISTORY = 100  # Keep last 100 GPS readings
    MATCH_THRESHOLD = 30  # Max seconds for temporal matching

    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._enabled = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._current_data: Optional[GPSData] = None
        self._history: List[GPSData] = []
        self._on_update: Optional[Callable[[GPSData], None]] = None
        self._on_disconnect: Optional[Callable[[], None]] = None
        self._on_raw_data: Optional[Callable[[str], None]] = None

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._enabled and self._serial is not None and self._serial.is_open

    @property
    def current_data(self) -> Optional[GPSData]:
        with self._lock:
            return self._current_data

    @property
    def port(self) -> Optional[str]:
        with self._lock:
            return self._serial.port if self._serial else None

    def set_callbacks(
        self,
        on_update: Optional[Callable[[GPSData], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
        on_raw_data: Optional[Callable[[str], None]] = None,
    ):
        """Set callback functions for GPS events."""
        self._on_update = on_update
        self._on_disconnect = on_disconnect
        self._on_raw_data = on_raw_data

    def connect(self, port: str) -> Dict[str, Any]:
        """Connect to GPS dongle on specified port."""
        with self._lock:
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass

            try:
                self._serial = serial.Serial(port, self.BAUDRATE, timeout=self.TIMEOUT)
                self._enabled = True
            except Exception as e:
                return {'success': False, 'error': str(e)}

        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

        return {'success': True, 'port': port}

    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from GPS dongle."""
        with self._lock:
            self._enabled = False
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None

        return {'success': True}

    def find_best_match(self, detection_time: float) -> Optional[GPSData]:
        """Find GPS reading closest in time to detection timestamp."""
        with self._lock:
            if not self._history:
                return None

            best_match = None
            min_diff = float('inf')

            for gps in self._history:
                diff = abs(detection_time - gps.system_timestamp)
                if diff < min_diff and diff <= self.MATCH_THRESHOLD:
                    min_diff = diff
                    best_match = gps

            return best_match

    def _reader_loop(self):
        """Background thread for reading GPS data."""
        while self._enabled:
            if not self._serial or not self._serial.is_open:
                break

            try:
                line = self._serial.readline().decode('utf-8', errors='ignore')
                if line:
                    if self._on_raw_data:
                        self._on_raw_data(f"GPS: {line.strip()}")

                    parsed = self._parse_nmea(line)
                    if parsed and parsed.is_valid():
                        with self._lock:
                            self._current_data = parsed
                            self._history.append(parsed)
                            if len(self._history) > self.MAX_HISTORY:
                                self._history.pop(0)

                        if self._on_update:
                            self._on_update(parsed)

            except Exception as e:
                print(f"GPS read error: {e}")
                with self._lock:
                    self._enabled = False
                if self._on_disconnect:
                    self._on_disconnect()
                break

            time.sleep(0.1)

    def _parse_nmea(self, sentence: str) -> Optional[GPSData]:
        """Parse NMEA GPS sentence."""
        if not sentence.startswith('$'):
            return None

        parts = sentence.strip().split(',')
        if len(parts) < 1:
            return None

        sentence_type = parts[0]

        if sentence_type in ['$GPGGA', '$GNGGA']:
            if len(parts) >= 15:
                try:
                    time_str = parts[1]
                    lat_raw = parts[2]
                    lat_dir = parts[3]
                    lon_raw = parts[4]
                    lon_dir = parts[5]
                    fix_quality = int(parts[6]) if parts[6] else 0
                    satellites = int(parts[7]) if parts[7] else 0
                    hdop = float(parts[8]) if parts[8] else 0
                    altitude = float(parts[9]) if parts[9] else 0

                    if fix_quality == 0 or not lat_raw or not lon_raw:
                        return None

                    lat_degrees = int(lat_raw[:2])
                    lat_minutes = float(lat_raw[2:])
                    lat = lat_degrees + (lat_minutes / 60.0)

                    lon_degrees = int(lon_raw[:3])
                    lon_minutes = float(lon_raw[3:])
                    lon = lon_degrees + (lon_minutes / 60.0)

                    if lat_dir == 'S':
                        lat = -lat
                    if lon_dir == 'W':
                        lon = -lon

                    return GPSData(
                        latitude=round(lat, 8),
                        longitude=round(lon, 8),
                        altitude=round(altitude, 3),
                        timestamp=time_str,
                        fix_quality=fix_quality,
                        satellites=satellites,
                        hdop=hdop,
                        system_timestamp=time.time(),
                    )
                except (ValueError, IndexError) as e:
                    print(f"GPS parsing error: {e}")
                    return None

        return None

    @staticmethod
    def list_ports() -> List[Dict[str, Any]]:
        """List available serial ports."""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'manufacturer': port.manufacturer or 'Unknown',
                'product': port.product or 'Unknown',
                'vid': port.vid,
                'pid': port.pid,
            })
        return ports
