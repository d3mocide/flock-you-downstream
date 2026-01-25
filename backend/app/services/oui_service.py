"""OUI Service - Handles IEEE OUI database lookups."""
import os
import urllib.request
import urllib.error
import tempfile
from typing import Dict, Any, List, Optional
import threading


class OUIService:
    """Manages OUI (Organizationally Unique Identifier) database for manufacturer lookups."""

    def __init__(self, oui_file: str = 'oui.txt'):
        self._oui_file = oui_file
        self._database: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._load_database()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._database)

    def lookup(self, mac_address: str) -> str:
        """Look up manufacturer for a MAC address."""
        if not mac_address:
            return 'Unknown Manufacturer'

        mac_clean = mac_address.replace(':', '').replace('-', '').upper()
        if len(mac_clean) >= 6:
            oui = mac_clean[:6]
            with self._lock:
                return self._database.get(oui, 'Unknown Manufacturer')

        return 'Unknown Manufacturer'

    def search(self, query: str) -> List[Dict[str, str]]:
        """Search OUI database by MAC prefix or manufacturer name."""
        if not query:
            return []

        results = []
        clean_query = query.replace(':', '').replace(' ', '').upper()

        with self._lock:
            # Check if query looks like a MAC address
            if len(clean_query) >= 6 and all(c in '0123456789ABCDEF' for c in clean_query[:6]):
                mac_prefix = clean_query[:6]
                if mac_prefix in self._database:
                    results.append({
                        'mac': mac_prefix,
                        'manufacturer': self._database[mac_prefix],
                    })
            else:
                # Search by manufacturer name
                query_lower = query.lower()
                for mac, manufacturer in self._database.items():
                    if query_lower in manufacturer.lower():
                        results.append({
                            'mac': mac,
                            'manufacturer': manufacturer,
                        })
                        if len(results) >= 100:
                            break

        return results

    def get_all(self) -> List[Dict[str, str]]:
        """Get all OUI entries."""
        with self._lock:
            return [
                {'mac': mac, 'manufacturer': manufacturer}
                for mac, manufacturer in self._database.items()
            ]

    def refresh(self) -> Dict[str, Any]:
        """Refresh OUI database from IEEE website."""
        url = "https://standards-oui.ieee.org/oui/oui.txt"

        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/plain,text/html,application/xhtml+xml',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Connection': 'keep-alive',
                },
            )

            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                temp_path = temp_file.name

            with urllib.request.urlopen(req, timeout=30) as response:
                with open(temp_path, 'wb') as out_file:
                    out_file.write(response.read())

            new_database = {}
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '(hex)' in line:
                        parts = line.split('(hex)')
                        if len(parts) == 2:
                            mac_prefix = parts[0].strip().replace('-', '').replace(' ', '').upper()
                            manufacturer = parts[1].strip()
                            if mac_prefix and manufacturer and len(mac_prefix) == 6:
                                new_database[mac_prefix] = manufacturer

            os.unlink(temp_path)

            if len(new_database) < 1000:
                return {
                    'success': False,
                    'error': f'Downloaded database appears incomplete ({len(new_database)} entries)',
                }

            with self._lock:
                self._database = new_database

            # Save to file
            self._save_database()

            return {'success': True, 'count': len(self._database)}

        except urllib.error.HTTPError as e:
            if e.code == 418:
                return {
                    'success': False,
                    'error': 'IEEE server is refusing automated requests (HTTP 418). Please try again later.',
                }
            return {'success': False, 'error': f'HTTP error {e.code}: {str(e)}'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _load_database(self):
        """Load OUI database from file."""
        try:
            if os.path.exists(self._oui_file):
                with open(self._oui_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '(hex)' in line:
                            parts = line.split('(hex)')
                            if len(parts) == 2:
                                mac_prefix = parts[0].strip().replace('-', '').replace(' ', '').upper()
                                manufacturer = parts[1].strip()
                                if mac_prefix and manufacturer and len(mac_prefix) == 6:
                                    self._database[mac_prefix] = manufacturer
                print(f"Loaded {len(self._database)} OUI entries")
        except Exception as e:
            print(f"Error loading OUI database: {e}")

    def _save_database(self):
        """Save OUI database to file."""
        try:
            with open(self._oui_file, 'w', encoding='utf-8') as f:
                for mac, manufacturer in sorted(self._database.items()):
                    formatted_mac = f"{mac[0:2]}-{mac[2:4]}-{mac[4:6]}"
                    f.write(f"{formatted_mac}   (hex)\t\t\t\t{manufacturer}\n")
            print(f"Saved {len(self._database)} OUI entries")
        except Exception as e:
            print(f"Error saving OUI database: {e}")
