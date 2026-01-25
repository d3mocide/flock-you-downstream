"""Flock Service - Handles Flock device serial communication."""
import threading
import time
import json
import serial
import serial.tools.list_ports
from typing import Optional, Dict, Any, List, Callable


class FlockService:
    """Manages Flock device serial connection and data reading."""

    BAUDRATE = 115200
    TIMEOUT = 1
    MAX_BUFFER = 1000  # Keep last 1000 lines
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_DELAY = 3  # seconds

    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._connected = False
        self._port: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._buffer: List[str] = []
        self._reconnect_attempts = 0

        # Callbacks
        self._on_detection: Optional[Callable[[Dict[str, Any]], None]] = None
        self._on_raw_data: Optional[Callable[[str], None]] = None
        self._on_disconnect: Optional[Callable[[], None]] = None
        self._on_reconnect: Optional[Callable[[str], None]] = None

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._connected and self._serial is not None and self._serial.is_open

    @property
    def port(self) -> Optional[str]:
        with self._lock:
            return self._port

    @property
    def buffer(self) -> List[str]:
        with self._lock:
            return self._buffer.copy()

    def set_callbacks(
        self,
        on_detection: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_raw_data: Optional[Callable[[str], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
        on_reconnect: Optional[Callable[[str], None]] = None,
    ):
        """Set callback functions for Flock device events."""
        self._on_detection = on_detection
        self._on_raw_data = on_raw_data
        self._on_disconnect = on_disconnect
        self._on_reconnect = on_reconnect

    def connect(self, port: str) -> Dict[str, Any]:
        """Connect to Flock device on specified port."""
        with self._lock:
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass

            try:
                self._serial = serial.Serial(port, self.BAUDRATE, timeout=self.TIMEOUT)
                self._connected = True
                self._port = port
                self._reconnect_attempts = 0
            except Exception as e:
                return {'success': False, 'error': str(e)}

        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

        return {'success': True, 'port': port}

    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from Flock device."""
        with self._lock:
            self._connected = False
            self._port = None
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None

        return {'success': True}

    def _reader_loop(self):
        """Background thread for reading Flock device data."""
        while self._connected:
            if not self._serial or not self._serial.is_open:
                break

            try:
                line = self._serial.readline().decode('utf-8', errors='ignore')
                if line:
                    line = line.strip()
                    if line:
                        with self._lock:
                            self._buffer.append(line)
                            if len(self._buffer) > self.MAX_BUFFER:
                                self._buffer.pop(0)

                        if self._on_raw_data:
                            self._on_raw_data(line)

                        # Try to parse as detection JSON
                        try:
                            data = json.loads(line)
                            if 'detection_method' in data:
                                if self._on_detection:
                                    self._on_detection(data)
                        except json.JSONDecodeError:
                            # Not JSON, just raw serial data
                            pass

            except Exception as e:
                print(f"Flock device read error: {e}")
                with self._lock:
                    self._connected = False
                if self._on_disconnect:
                    self._on_disconnect()
                self._attempt_reconnect()
                break

            time.sleep(0.1)

    def _attempt_reconnect(self):
        """Attempt to reconnect to Flock device."""
        def reconnect_thread():
            while not self._connected and self._reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
                try:
                    print(f"Attempting reconnect ({self._reconnect_attempts + 1}/{self.MAX_RECONNECT_ATTEMPTS})")

                    with self._lock:
                        if self._serial:
                            try:
                                self._serial.close()
                            except Exception:
                                pass

                    time.sleep(1)

                    with self._lock:
                        self._serial = serial.Serial(self._port, self.BAUDRATE, timeout=self.TIMEOUT)
                        self._serial.readline()  # Test read
                        self._connected = True
                        self._reconnect_attempts = 0

                    print(f"Reconnected to Flock device on {self._port}")
                    if self._on_reconnect:
                        self._on_reconnect(self._port)

                    # Restart reader thread
                    self._thread = threading.Thread(target=self._reader_loop, daemon=True)
                    self._thread.start()
                    return

                except Exception as e:
                    print(f"Reconnection attempt failed: {e}")
                    self._reconnect_attempts += 1
                    time.sleep(self.RECONNECT_DELAY)

            if self._reconnect_attempts >= self.MAX_RECONNECT_ATTEMPTS:
                print("Max reconnection attempts reached")
                self._reconnect_attempts = 0

        threading.Thread(target=reconnect_thread, daemon=True).start()

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
