from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QFileDialog, QLabel, QPushButton
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from typing import Dict, Any, Optional
import logging
import csv

class TagDataView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.layout = QVBoxLayout(self)
        self.setup_tree()
        self.tag_counts = {}
        self.rssi_threshold = -75
        self.tag_data = []
        self.status_label = QLabel()
        self.layout.addWidget(self.status_label)
        self.create_export_button()

    def setup_tree(self) -> None:
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "#", "Antenna", "EPC", "Timestamp", "Count", 
            "RSSI (dBm)", "Phase", "Doppler"
        ])
        
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: white;
                font-family: monospace;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        
        self.layout.addWidget(self.tree)

    def update_tag(self, tag_data: Dict[str, Any]) -> None:
        try:
            epc = tag_data.get('epc', '')
            antenna = tag_data.get('antenna', '')
            timestamp = tag_data.get('timestamp', '')
            count = tag_data.get('count', 0)
            rssi = tag_data.get('rssi')
            phase = tag_data.get('phase')
            doppler = tag_data.get('doppler')

            item = QTreeWidgetItem(self.tree)
            item.setText(0, str(self.tree.topLevelItemCount()))
            item.setText(1, str(antenna))
            item.setText(2, epc)
            item.setText(3, str(timestamp))
            item.setText(4, str(count))
            item.setText(5, f"{rssi:.1f}" if rssi is not None else "N/A")
            item.setText(6, f"{phase:.1f}" if phase is not None else "N/A")
            item.setText(7, str(doppler) if doppler is not None else "N/A")

            # Update tag count
            self.tag_counts[epc] = self.tag_counts.get(epc, 0) + 1

            # Highlight row if RSSI is below threshold
            if rssi is not None and rssi < self.rssi_threshold:
                for col in range(item.columnCount()):
                    item.setForeground(col, QColor(255, 0, 0))

            # Limit the number of items
            while self.tree.topLevelItemCount() > 1000:
                self.tree.takeTopLevelItem(0)

            # Store tag data for export
            self.tag_data.append({
                'epc': epc,
                'rssi': rssi,
                'timestamp': timestamp
            })

        except Exception as e:
            self.logger.error(f"Error updating tag data: {e}")

    def set_rssi_threshold(self, threshold: float) -> None:
        self.rssi_threshold = threshold

    def clear(self) -> None:
        self.tree.clear()
        self.tag_counts.clear()
        self.tag_data.clear()

    def get_tag_counts(self) -> Dict[str, int]:
        return self.tag_counts.copy()

    def sort_by_rssi(self) -> None:
        self.tree.sortItems(5, Qt.DescendingOrder)

    def export_to_csv(self):
        # Logic to export tag data to CSV
        import csv
        filename, _ = QFileDialog.getSaveFileName(self, 'Save CSV', '', 'CSV Files (*.csv)')
        if filename:
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['EPC', 'RSSI', 'Timestamp'])  # Header row
                for tag in self.tag_data:
                    writer.writerow([tag['epc'], tag['rssi'], tag['timestamp']])
                self.status_label.setText('Export successful!')

    def create_export_button(self):
        export_button = QPushButton('Export to CSV')
        export_button.clicked.connect(self.export_to_csv)
        self.layout.addWidget(export_button)  # Add the button to the layout
