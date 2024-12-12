import json
import logging
from typing import Dict, List, Any

class RFIDConfig:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_data = {
            'epc_list': [],
            'matrix_rows': 3,
            'matrix_cols': 3,
            'display_settings': {
                'peak_rssi': True,
                'last_rssi': True,
                'first_seen': True,
                'last_seen': True,
                'phase': True,
                'doppler': True,
                'read_count': True,
                'epc': True
            },
            'reader_settings': {
                'ip': '192.168.254.100',
                'antennas': [1],
                'power': 30,
                'report_every_n': 1,
                'rssi_threshold': -75
            }
        }

    def load_from_file(self, filename: str) -> None:
        try:
            with open(filename, 'r') as f:
                loaded_config = json.load(f)
                self.config_data.update(loaded_config)
        except Exception as e:
            self.logger.error(f"Error loading configuration from {filename}: {e}")

    def save_to_file(self, filename: str) -> None:
        try:
            with open(filename, 'w') as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving configuration to {filename}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config_data[key] = value

    def update_display_settings(self, settings: Dict[str, bool]) -> None:
        self.config_data['display_settings'].update(settings)

    def update_reader_settings(self, settings: Dict[str, Any]) -> None:
        self.config_data['reader_settings'].update(settings)

    def update_matrix_size(self, rows: int, cols: int) -> None:
        self.config_data['matrix_rows'] = rows
        self.config_data['matrix_cols'] = cols

    def update_epc_list(self, epc_list: List[str]) -> None:
        self.config_data['epc_list'] = epc_list
