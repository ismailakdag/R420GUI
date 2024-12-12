from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QLineEdit, QPushButton, QGroupBox, QCheckBox,
                           QTabWidget, QFileDialog, QTreeWidget, QTreeWidgetItem,
                           QInputDialog, QDialog, QTextEdit)
from PyQt5.QtCore import QTimer, pyqtSignal, Qt, QThread, QObject
from datetime import datetime
import logging

from ..config import RFIDConfig
from ..reader import RFIDReader
from .matrix_view import MatrixView
from .tag_data_view import TagDataView
from typing import Dict, Any, Optional
import json

class ReaderConnectWorker(QObject):
    finished = pyqtSignal()
    connection_success = pyqtSignal()
    connection_error = pyqtSignal(str)

    def __init__(self, reader, ip_address):
        super().__init__()
        self.reader = reader
        self.ip_address = ip_address

    def run(self):
        try:
            if self.reader.connect(self.ip_address, RFIDConfig().get('reader_settings', {}), MainWindow.handle_tag_data):
                self.connection_success.emit()
            else:
                self.connection_error.emit("Connection Failed")
        except Exception as e:
            self.connection_error.emit(f"Error connecting to reader: {e}")
        finally:
            self.finished.emit()

class MainWindow(QMainWindow):
    tag_data_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.config = RFIDConfig()
        self.reader = RFIDReader()
        self.setup_ui()
        
        # Connect signals
        self.tag_data_signal.connect(self.handle_tag_data)
        
        # Start update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_matrix)
        self.timer.start(1000)

    def setup_ui(self):
        self.setWindowTitle("RFID Reader GUI")
        self.setup_styles()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create components
        self.create_top_control_panel(main_layout)
        self.create_tab_widget(main_layout)

    def setup_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 1ex;
                padding: 10px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
            }
        """)

    def create_top_control_panel(self, parent_layout):
        panel = QWidget()
        layout = QHBoxLayout(panel)
        
        # IP Address
        ip_layout = QHBoxLayout()
        self.ip_entry = QLineEdit(self.config.get('reader_settings', {}).get('ip', '192.168.254.100'))
        ip_layout.addWidget(QLabel("Reader IP:"))
        ip_layout.addWidget(self.ip_entry)
        
        # Control buttons
        self.connect_button = QPushButton("Connect")
        self.start_button = QPushButton("Start Inventory")
        self.stop_button = QPushButton("Stop Inventory")
        self.clear_button = QPushButton("Clear Inventory")
        
        self.connect_button.clicked.connect(self.connect_reader)
        self.start_button.clicked.connect(self.start_inventory)
        self.stop_button.clicked.connect(self.stop_inventory)
        self.clear_button.clicked.connect(self.clear_inventory)
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        layout.addLayout(ip_layout)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.clear_button)
        
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: #f44336;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        parent_layout.addWidget(panel)

    def create_tab_widget(self, parent_layout):
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.config_tab = QWidget()
        self.matrix_tab = QWidget()
        self.tag_data_tab = QWidget()
        
        self.tab_widget.addTab(self.config_tab, "Configuration")
        self.tab_widget.addTab(self.matrix_tab, "Tag Matrix")
        self.tab_widget.addTab(self.tag_data_tab, "Tag Data")
        
        # Setup tab contents
        self.setup_config_tab()
        self.setup_matrix_tab()
        self.setup_tag_data_tab()
        
        parent_layout.addWidget(self.tab_widget)

    def setup_config_tab(self):
        layout = QVBoxLayout(self.config_tab)
        
        # Reader Settings
        reader_group = QGroupBox("Reader Settings")
        reader_group.setStyleSheet("QGroupBox{font-weight: bold; border: 2px solid #2196F3; border-radius: 5px; margin-top: 1ex;}")
        reader_layout = QVBoxLayout()
        
        # Basic Settings
        basic_layout = QHBoxLayout()
        
        # Antennas
        antenna_label = QLabel("Antennas:")
        self.antenna_entry = QLineEdit("1")
        antenna_hint = QLabel("(comma-separated list)")
        
        # TX Power
        power_label = QLabel("TX Power:")
        self.power_entry = QLineEdit("0")
        self.power_entry.setMaximumWidth(50)
        
        # Report Every N Tags
        report_label = QLabel("Report Every N Tags:")
        self.report_entry = QLineEdit("20")
        self.report_entry.setMaximumWidth(50)
        
        # Add basic widgets to layout
        basic_layout.addWidget(antenna_label)
        basic_layout.addWidget(self.antenna_entry)
        basic_layout.addWidget(antenna_hint)
        basic_layout.addWidget(power_label)
        basic_layout.addWidget(self.power_entry)
        basic_layout.addWidget(report_label)
        basic_layout.addWidget(self.report_entry)
        basic_layout.addStretch()
        
        # RSSI Settings
        rssi_layout = QHBoxLayout()
        rssi_threshold_label = QLabel("RSSI Threshold (dBm):")
        self.rssi_threshold_entry = QLineEdit(str(self.config.get('reader_settings', {}).get('rssi_threshold', -75)))
        self.rssi_threshold_entry.setMaximumWidth(50)
        rssi_hint = QLabel("(Typical range: -100 to -30 dBm)")
        
        rssi_layout.addWidget(rssi_threshold_label)
        rssi_layout.addWidget(self.rssi_threshold_entry)
        rssi_layout.addWidget(rssi_hint)
        rssi_layout.addStretch()

        # Additional Reader Settings
        self.filter_by_epc = QCheckBox("Filter Tag Data by EPC List")
        self.filter_by_epc.setChecked(self.config.get('reader_settings', {}).get('filter_by_epc', True))
        reader_layout.addWidget(self.filter_by_epc)

        self.enable_impinj = QCheckBox("Enable Impinj Reports")
        self.enable_impinj.setChecked(self.config.get('reader_settings', {}).get('enable_impinj', True))
        reader_layout.addWidget(self.enable_impinj)
        
        # Add all layouts to reader group
        reader_layout.addLayout(basic_layout)
        reader_layout.addLayout(rssi_layout)
        reader_group.setLayout(reader_layout)
        layout.addWidget(reader_group)

        # Display Settings
        display_group = QGroupBox("Display Settings")
        display_group.setStyleSheet("QGroupBox{font-weight: bold; border: 2px solid #9C27B0; border-radius: 5px; margin-top: 1ex;}")
        display_layout = QVBoxLayout()

        # Update Interval
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Update Interval (ms):")
        self.interval_entry = QLineEdit(str(self.config.get('display_settings', {}).get('update_interval', 1000)))
        self.interval_entry.setMaximumWidth(50)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_entry)
        interval_layout.addStretch()

        # Display Options
        options_layout = QVBoxLayout()
        self.display_checkboxes = {}
        for setting, label in [
            ('peak_rssi', 'RSSI (Peak)'),
            ('last_rssi', 'RSSI (Last)'),
            ('first_seen', 'First Seen Time'),
            ('last_seen', 'Last Seen Time'),
            ('phase', 'Phase Angle'),
            ('doppler', 'Doppler Frequency'),
            ('read_count', 'Read Count'),
            ('epc', 'EPC')
        ]:
            checkbox = QCheckBox(label)
            checkbox.setChecked(self.config.get('display_settings', {}).get(setting, True))
            checkbox.stateChanged.connect(lambda state, s=setting: self.update_display_settings(s, state))
            self.display_checkboxes[setting] = checkbox
            options_layout.addWidget(checkbox)

        display_layout.addLayout(interval_layout)
        display_layout.addLayout(options_layout)
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # Matrix Settings
        matrix_group = QGroupBox("Matrix Settings")
        matrix_group.setStyleSheet("QGroupBox{font-weight: bold; border: 2px solid #4CAF50; border-radius: 5px; margin-top: 1ex;}")
        matrix_layout = QVBoxLayout()
        
        # Matrix size controls
        size_layout = QHBoxLayout()
        rows_label = QLabel("Matrix Rows:")
        self.rows_entry = QLineEdit(str(self.config.get('matrix_rows', 3)))
        self.rows_entry.setMaximumWidth(50)
        cols_label = QLabel("Matrix Columns:")
        self.cols_entry = QLineEdit(str(self.config.get('matrix_cols', 3)))
        self.cols_entry.setMaximumWidth(50)
        
        size_layout.addWidget(rows_label)
        size_layout.addWidget(self.rows_entry)
        size_layout.addWidget(cols_label)
        size_layout.addWidget(self.cols_entry)
        size_layout.addStretch()
        
        matrix_layout.addLayout(size_layout)
        
        # EPC List
        epc_layout = QVBoxLayout()
        epc_label = QLabel("EPC List:")
        self.epc_list = QTreeWidget()
        self.epc_list.setHeaderLabels(["EPC"])
        self.epc_list.setStyleSheet("""
            QTreeWidget {
                background-color: white;
                font-family: monospace;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        
        # Load EPCs
        for epc in self.config.get('epc_list', []):
            QTreeWidgetItem(self.epc_list, [epc])
        
        epc_layout.addWidget(epc_label)
        epc_layout.addWidget(self.epc_list)
        
        # EPC Buttons
        epc_buttons = QHBoxLayout()
        add_epc = QPushButton("Edit EPCs")
        load_epcs = QPushButton("Load EPCs")
        save_epcs = QPushButton("Save EPCs")
        
        for button in [add_epc, load_epcs, save_epcs]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
        
        epc_buttons.addWidget(add_epc)
        epc_buttons.addWidget(load_epcs)
        epc_buttons.addWidget(save_epcs)
        epc_buttons.addStretch()
        
        epc_layout.addLayout(epc_buttons)
        matrix_layout.addLayout(epc_layout)
        
        matrix_group.setLayout(matrix_layout)
        layout.addWidget(matrix_group)
        
        # Connect signals
        add_epc.clicked.connect(self.add_epc)
        load_epcs.clicked.connect(self.load_epcs)
        save_epcs.clicked.connect(self.save_epcs)
        self.rows_entry.textChanged.connect(self.update_matrix_size)
        self.cols_entry.textChanged.connect(self.update_matrix_size)
        self.rssi_threshold_entry.textChanged.connect(self.update_rssi_threshold)
        self.interval_entry.textChanged.connect(self.update_display_settings)
        self.update_display_settings()

    def setup_matrix_tab(self):
        layout = QVBoxLayout(self.matrix_tab)
        
        # Create matrix view with initial size from config
        self.matrix_view = MatrixView()
        matrix_rows = self.config.get('matrix_rows', 3)
        matrix_cols = self.config.get('matrix_cols', 3)
        self.matrix_view.create_matrix(matrix_rows, matrix_cols)
        
        # Add to layout
        layout.addWidget(self.matrix_view)

    def setup_tag_data_tab(self):
        layout = QVBoxLayout(self.tag_data_tab)
        self.tag_data_view = TagDataView()
        layout.addWidget(self.tag_data_view)

    def connect_reader(self):
        try:
            # Get IP address from input
            ip_address = self.ip_entry.text().strip()
            if not ip_address:
                self.logger.error("IP address is required")
                return

            # Create worker thread for connection
            self.connect_thread = QThread()
            self.connect_worker = ReaderConnectWorker(self.reader, ip_address)
            self.connect_worker.moveToThread(self.connect_thread)

            # Connect signals
            self.connect_thread.started.connect(self.connect_worker.run)
            self.connect_worker.finished.connect(self.connect_thread.quit)
            self.connect_worker.finished.connect(self.connect_worker.deleteLater)
            self.connect_thread.finished.connect(self.connect_thread.deleteLater)
            self.connect_worker.connection_success.connect(self.handle_connection_success)
            self.connect_worker.connection_error.connect(self.handle_connection_error)

            # Disable connect button and update status
            self.connect_button.setEnabled(False)
            self.status_label.setText("Status: Connecting...")
            self.status_label.setStyleSheet("color: #FFA000;")

            # Start connection thread
            self.connect_thread.start()

        except Exception as e:
            self.logger.error(f"Error connecting to reader: {e}")
            self.status_label.setText("Status: Connection Error")
            self.status_label.setStyleSheet("color: #f44336;")
            self.connect_button.setEnabled(True)

    def handle_connection_success(self):
        self.status_label.setText("Status: Connected")
        self.status_label.setStyleSheet("color: #4CAF50;")
        self.connect_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def handle_connection_error(self, error_msg):
        self.status_label.setText(f"Status: {error_msg}")
        self.status_label.setStyleSheet("color: #f44336;")
        self.connect_button.setEnabled(True)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def add_epc(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit EPC List")
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setPlainText('\n'.join([item.text(0) for item in self.epc_list.findItems("", Qt.MatchContains | Qt.MatchRecursive)]))
        layout.addWidget(text_edit)
        
        button_box = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        
        def save_epcs():
            epcs = [epc.strip() for epc in text_edit.toPlainText().split('\n') if epc.strip()]
            self.epc_list.clear()
            for epc in epcs:
                QTreeWidgetItem(self.epc_list, [epc])
            self.config.set('epc_list', epcs)
            self.update_matrix_size()
            dialog.accept()
        
        save_button.clicked.connect(save_epcs)
        cancel_button.clicked.connect(dialog.reject)
        
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def load_epcs(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load EPCs", "", "Text Files (*.txt);;JSON Files (*.json)")
        if file_name:
            try:
                if file_name.endswith('.json'):
                    with open(file_name, 'r') as f:
                        config = json.load(f)
                        epcs = config.get('epc_list', [])
                else:
                    with open(file_name, 'r') as f:
                        epcs = [line.strip() for line in f.readlines() if line.strip()]
                
                self.epc_list.clear()
                for epc in epcs:
                    QTreeWidgetItem(self.epc_list, [epc])
                self.config.set('epc_list', epcs)
                self.update_matrix_size()
            except Exception as e:
                self.logger.error(f"Error loading EPCs: {e}")

    def save_epcs(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save EPCs", "", "Text Files (*.txt);;JSON Files (*.json)")
        if file_name:
            try:
                epcs = [item.text(0) for item in self.epc_list.findItems("", Qt.MatchContains | Qt.MatchRecursive)]
                if file_name.endswith('.json'):
                    config = {'epc_list': epcs}
                    with open(file_name, 'w') as f:
                        json.dump(config, f, indent=4)
                else:
                    with open(file_name, 'w') as f:
                        f.write('\n'.join(epcs))
            except Exception as e:
                self.logger.error(f"Error saving EPCs: {e}")

    def start_inventory(self):
        if self.reader.start_inventory():
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

    def stop_inventory(self):
        if self.reader.stop_inventory():
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def clear_inventory(self):
        self.matrix_view.clear()
        self.tag_data_view.clear()

    def handle_tag_data(self, tag_data: Dict[str, Any]) -> None:
        try:
            # Extract tag data
            epc = tag_data.get('EPC', '')
            
            # Filter by EPC list if enabled
            if self.filter_by_epc.isChecked() and epc not in self.config.get('epc_list', []):
                return

            antenna = tag_data.get('AntennaID', 0)
            peak_rssi = tag_data.get('PeakRSSI', {}).get('Value', None)
            last_rssi = tag_data.get('RSSI', {}).get('Value', None)
            phase = tag_data.get('Phase', {}).get('Value', None)
            doppler = tag_data.get('DopplerFrequency', {}).get('Value', None)
            first_seen = tag_data.get('FirstSeenTimestamp', {}).get('Value', None)
            last_seen = tag_data.get('LastSeenTimestamp', {}).get('Value', None)
            read_count = tag_data.get('TagSeenCount', {}).get('Value', 1)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Update tag data view
            self.tag_data_view.update_tag({
                'epc': epc,
                'antenna': antenna,
                'peak_rssi': peak_rssi,
                'last_rssi': last_rssi,
                'phase': phase,
                'doppler': doppler,
                'first_seen': first_seen,
                'last_seen': last_seen,
                'read_count': read_count,
                'timestamp': timestamp
            })

            # Update matrix if EPC is in the configured list
            if epc in self.config.get('epc_list', []):
                matrix_rows = self.config.get('matrix_rows', 3)
                matrix_cols = self.config.get('matrix_cols', 3)
                epc_index = self.config.get('epc_list', []).index(epc)
                row = epc_index // matrix_cols
                col = epc_index % matrix_cols
                
                if row < matrix_rows and col < matrix_cols:
                    self.matrix_view.update_cell(row, col, {
                        'epc': epc,
                        'peak_rssi': peak_rssi,
                        'last_rssi': last_rssi,
                        'phase': phase,
                        'doppler': doppler,
                        'first_seen': first_seen,
                        'last_seen': last_seen,
                        'read_count': read_count
                    })

        except Exception as e:
            self.logger.error(f"Error handling tag data: {e}")

    def update_matrix(self) -> None:
        try:
            # Update matrix size if needed
            matrix_rows = self.config.get('matrix_rows', 3)
            matrix_cols = self.config.get('matrix_cols', 3)
            self.matrix_view.create_matrix(matrix_rows, matrix_cols)

            # Update RSSI range
            rssi_threshold = self.config.get('reader_settings', {}).get('rssi_threshold', -75)
            self.matrix_view.update_rssi_range(-100, -30)  # Typical RSSI range for RFID
            self.tag_data_view.set_rssi_threshold(rssi_threshold)

        except Exception as e:
            self.logger.error(f"Error updating matrix: {e}")

    def update_matrix_size(self):
        # Update matrix size based on input
        try:
            rows = int(self.rows_entry.text())
            cols = int(self.cols_entry.text())
            if rows > 0 and cols > 0:
                self.config.set('matrix_rows', rows)
                self.config.set('matrix_cols', cols)
                self.matrix_view.create_matrix(rows, cols)
                # Update matrix with current EPCs
                epcs = [item.text(0) for item in self.epc_list.findItems("", Qt.MatchContains | Qt.MatchRecursive)]
                self.config.set('epc_list', epcs)
                self.matrix_view.update_epcs(epcs)
        except ValueError:
            pass

    def update_rssi_threshold(self):
        # Update RSSI threshold based on input
        try:
            rssi_threshold = int(self.rssi_threshold_entry.text())
            if -100 <= rssi_threshold <= -30:  # Validate within typical RFID RSSI range
                self.config.set('reader_settings', {'rssi_threshold': rssi_threshold})
                self.tag_data_view.set_rssi_threshold(rssi_threshold)
        except ValueError:
            pass

    def update_display_settings(self, setting=None, state=None):
        # Update display settings based on input
        try:
            if setting is None:
                update_interval = int(self.interval_entry.text())
                if update_interval > 0:
                    self.config.set('display_settings', {
                        'update_interval': update_interval,
                        'show_rssi': self.display_checkboxes['peak_rssi'].isChecked(),
                        'show_phase': self.display_checkboxes['phase'].isChecked(),
                        'show_doppler': self.display_checkboxes['doppler'].isChecked(),
                        'highlight_changes': self.display_checkboxes['read_count'].isChecked()
                    })
            else:
                self.config.set('display_settings', {setting: state})
        except ValueError:
            pass

    def create_reader_config(self) -> Dict[str, Any]:
        try:
            config = {
                'antennas': [int(p.strip()) for p in self.antenna_entry.text().split(',')],
                'power': int(self.power_entry.text()),
                'report_every_n': int(self.report_entry.text()),
                'rssi_threshold': float(self.rssi_threshold_entry.text()),
                'filter_by_epc': self.filter_by_epc.isChecked(),
                'enable_impinj': self.enable_impinj.isChecked(),
                'display_settings': {
                    'update_interval': int(self.interval_entry.text()),
                    **{k: v.isChecked() for k, v in self.display_checkboxes.items()}
                }
            }
            return config
        except ValueError as e:
            self.logger.error(f"Error creating reader config: {e}")
            return None
