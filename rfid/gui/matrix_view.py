from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from typing import Dict, Optional, Any, List

class MatrixView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_layout = QGridLayout(self)
        self.labels = {}  # Dictionary to store labels by position
        self.min_rssi = -100
        self.max_rssi = -30
        self.display_settings = {
            'peak_rssi': True,
            'last_rssi': True,
            'first_seen': True,
            'last_seen': True,
            'phase': True,
            'doppler': True,
            'read_count': True,
            'epc': True
        }
        self.epc_list = []  # List of EPCs to display
        self.tag_data = {}  # Store current tag data

    def set_display_settings(self, settings: Dict[str, bool]) -> None:
        self.display_settings.update(settings)
        self.refresh_all_cells()

    def update_epcs(self, epcs: List[str]) -> None:
        self.epc_list = epcs
        self.refresh_all_cells()

    def create_matrix(self, rows: int, cols: int) -> None:
        # Clear existing labels
        for label in self.labels.values():
            self.grid_layout.removeWidget(label)
            label.deleteLater()
        self.labels.clear()

        # Create new matrix
        for i in range(rows):
            for j in range(cols):
                label = QLabel()
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("""
                    QLabel {
                        background-color: white;
                        border: 1px solid #BDBDBD;
                        padding: 10px;
                        min-width: 150px;
                        min-height: 60px;
                        font-family: monospace;
                    }
                """)
                self.grid_layout.addWidget(label, i, j)
                self.labels[(i, j)] = label
        
        self.refresh_all_cells()

    def get_color_for_rssi(self, rssi: Optional[float]) -> QColor:
        if rssi is None:
            return QColor(200, 200, 200)  # Gray for no signal
        
        normalized = (rssi - self.min_rssi) / (self.max_rssi - self.min_rssi)
        normalized = max(0, min(1, normalized))
        
        red = int(255 * (1 - normalized))
        green = int(255 * normalized)
        
        return QColor(red, green, 0)

    def update_cell(self, row: int, col: int, tag_data: Dict[str, Any]) -> None:
        label = self.labels.get((row, col))
        if not label:
            return

        epc = tag_data.get('epc', 'Unknown')
        display_lines = []

        if self.display_settings['epc']:
            display_lines.append(f"EPC: {epc[-4:]}")

        if self.display_settings['peak_rssi']:
            peak_rssi = tag_data.get('peak_rssi')
            if peak_rssi is not None:
                display_lines.append(f"Peak RSSI: {peak_rssi:.1f} dBm")

        if self.display_settings['last_rssi']:
            last_rssi = tag_data.get('last_rssi')
            if last_rssi is not None:
                display_lines.append(f"Last RSSI: {last_rssi:.1f} dBm")

        if self.display_settings['first_seen']:
            first_seen = tag_data.get('first_seen')
            if first_seen is not None:
                display_lines.append(f"First: {first_seen:.2f}s")

        if self.display_settings['last_seen']:
            last_seen = tag_data.get('last_seen')
            if last_seen is not None:
                display_lines.append(f"Last: {last_seen:.2f}s")

        if self.display_settings['phase']:
            phase = tag_data.get('phase')
            if phase is not None:
                display_lines.append(f"Phase: {phase:.1f}°")

        if self.display_settings['doppler']:
            doppler = tag_data.get('doppler')
            if doppler is not None:
                display_lines.append(f"Doppler: {doppler:.1f} Hz")

        if self.display_settings['read_count']:
            read_count = tag_data.get('read_count')
            if read_count is not None:
                display_lines.append(f"Count: {read_count}")

        label.setText('\n'.join(display_lines))
        label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.get_color_for_rssi(tag_data.get('peak_rssi')).name()};
                border: 1px solid #BDBDBD;
                padding: 10px;
                min-width: 150px;
                min-height: 60px;
                font-family: monospace;
                qproperty-alignment: AlignCenter;
            }}
        """)

    def update_tag_data(self, epc: str, data: Dict[str, Any]) -> None:
        self.tag_data[epc] = data
        self.refresh_all_cells()

    def refresh_all_cells(self) -> None:
        if not self.epc_list or not self.labels:
            return

        # Calculate rows and columns from the grid layout
        positions = list(self.labels.keys())
        if not positions:
            return
            
        max_row = max(pos[0] for pos in positions) + 1
        max_col = max(pos[1] for pos in positions) + 1
        
        for i, epc in enumerate(self.epc_list):
            if i >= max_row * max_col:
                break
            
            row = i // max_col
            col = i % max_col
            
            tag_data = self.tag_data.get(epc, {'epc': epc})
            self.update_cell(row, col, tag_data)

    def update_rssi_range(self, min_rssi: float, max_rssi: float) -> None:
        self.min_rssi = min_rssi
        self.max_rssi = max_rssi
        self.refresh_all_cells()

    def clear(self) -> None:
        self.tag_data.clear()
        for label in self.labels.values():
            label.setText("EPC Not Found")
            label.setStyleSheet("""
                QLabel {
                    background-color: white;
                    border: 1px solid #BDBDBD;
                    padding: 10px;
                    min-width: 150px;
                    min-height: 60px;
                    font-family: monospace;
                    qproperty-alignment: AlignCenter;
                }
            """)
