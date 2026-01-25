"""Detection model and related utilities."""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Detection:
    """Represents a device detection."""
    id: int
    mac_address: str
    protocol: str  # 'wifi' or 'bluetooth_le'
    detection_method: str
    rssi: Optional[int] = None
    signal_strength: Optional[str] = None
    ssid: Optional[str] = None
    device_name: Optional[str] = None
    channel: Optional[int] = None
    manufacturer: Optional[str] = None
    alias: str = ''
    detection_count: int = 1
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    gps: Optional[Dict[str, Any]] = None
    server_timestamp: Optional[str] = None
    timestamp_source: str = 'system'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'mac_address': self.mac_address,
            'protocol': self.protocol,
            'detection_method': self.detection_method,
            'rssi': self.rssi,
            'signal_strength': self.signal_strength,
            'ssid': self.ssid,
            'device_name': self.device_name,
            'channel': self.channel,
            'manufacturer': self.manufacturer,
            'alias': self.alias,
            'detection_count': self.detection_count,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen,
            'gps': self.gps,
            'server_timestamp': self.server_timestamp,
            'timestamp_source': self.timestamp_source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Detection':
        return cls(
            id=data.get('id', 0),
            mac_address=data.get('mac_address', ''),
            protocol=data.get('protocol', 'unknown'),
            detection_method=data.get('detection_method', 'unknown'),
            rssi=data.get('rssi'),
            signal_strength=data.get('signal_strength'),
            ssid=data.get('ssid'),
            device_name=data.get('device_name'),
            channel=data.get('channel'),
            manufacturer=data.get('manufacturer'),
            alias=data.get('alias', ''),
            detection_count=data.get('detection_count', 1),
            first_seen=data.get('first_seen', datetime.now().isoformat()),
            last_seen=data.get('last_seen', datetime.now().isoformat()),
            gps=data.get('gps'),
            server_timestamp=data.get('server_timestamp'),
            timestamp_source=data.get('timestamp_source', 'system'),
        )
