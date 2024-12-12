import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QLineEdit, QPushButton, QFrame, QTreeWidget, QTreeWidgetItem,
                           QScrollArea, QGridLayout, QGroupBox, QCheckBox, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, QMetaType, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor
from twisted.internet import reactor
from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig, LLRP_DEFAULT_PORT
import logging
from datetime import datetime
import threading
import pytz
import csv

# Register the necessary type for QObject::connect
from PyQt5.QtCore import QObject
QObject.registerUserType = lambda: None  # This is a workaround for the QObject::connect warning

class SllurpGUI(QMainWindow):
    # Define signals for thread-safe updates
    tag_data_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sllurp RFID Reader GUI")
        self.setStyleSheet("QMainWindow{background-color: #f0f0f0;}")
        
        # Logging setup
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # EPC values for visualization
        self.EPC_LIST = [
            "e2801160600002095ad440c6", "e2801160600002095ad45436", "e2801160600002095ad44a16",
            "e2801160600002095ad44a76", "e2801160600002095ad44aa6", "e2801160600002095ad44086",
            "e2801160600002095ad44a06", "e2801160600002095ad44a96", "e2801160600002095ad45406"
        ]
        
        # Initialize RSSI and phase values
        self.current_rssi = {epc: -99 for epc in self.EPC_LIST}
        self.current_phase = {epc: None for epc in self.EPC_LIST}
        
        self.reader = None
        self.inventory_running = False
        self.reader_config = None
        
        # Connect signal to slot
        self.tag_data_signal.connect(self.handle_tag_data)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create all frames
        self.create_control_frame(main_layout)
        self.create_config_frame(main_layout)
        self.create_tag_frame(main_layout)
        self.create_matrix_frame(main_layout)
        
        # Start matrix update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_matrix)
        self.timer.start(1000)
        
    def create_control_frame(self, parent_layout):
        control_group = QGroupBox("Reader Control")
        control_group.setStyleSheet("QGroupBox{font-weight: bold; border: 2px solid #2196F3; border-radius: 5px; margin-top: 1ex;}")
        control_layout = QHBoxLayout()
        
        # IP Address
        ip_label = QLabel("Reader IP:")
        self.ip_entry = QLineEdit("192.168.254.100")
        self.ip_entry.setStyleSheet("QLineEdit{background-color: white; padding: 5px;}")
        
        # Status
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("QLabel{color: #f44336;}")
        
        # Filter Checkbox
        self.filter_checkbox = QCheckBox("Filter Tag Data by EPC List")
        self.filter_checkbox.setChecked(False)
        
        # Impinj Reports Checkbox
        self.impinj_reports_checkbox = QCheckBox("Enable Impinj Reports")
        self.impinj_reports_checkbox.setChecked(True)
        
        for checkbox in [self.filter_checkbox, self.impinj_reports_checkbox]:
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #333;
                    padding: 5px;
                }
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                }
                QCheckBox::indicator:unchecked {
                    border: 2px solid #2196F3;
                    background: white;
                }
                QCheckBox::indicator:checked {
                    border: 2px solid #2196F3;
                    background: #2196F3;
                }
            """)
        
        # Buttons
        self.connect_button = QPushButton("Connect")
        self.start_button = QPushButton("Start Inventory")
        self.stop_button = QPushButton("Stop Inventory")
        self.clear_inventory_button = QPushButton("Clear Inventory")
        
        buttons = [self.connect_button, self.start_button, self.stop_button, self.clear_inventory_button]
        for button in buttons:
            button.setStyleSheet("""
                QPushButton{
                    background-color: #2196F3;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover{
                    background-color: #1976D2;
                }
                QPushButton:disabled{
                    background-color: #BDBDBD;
                }
            """)
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        # Connect signals
        self.connect_button.clicked.connect(lambda: self.connect_reader(False))
        self.start_button.clicked.connect(self.start_inventory)
        self.stop_button.clicked.connect(self.stop_inventory)
        self.clear_inventory_button.clicked.connect(self.clear_inventory)
        
        # Add widgets to layout
        control_layout.addWidget(ip_label)
        control_layout.addWidget(self.ip_entry)
        control_layout.addWidget(self.status_label)
        control_layout.addWidget(self.filter_checkbox)
        control_layout.addWidget(self.impinj_reports_checkbox)
        control_layout.addWidget(self.connect_button)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.clear_inventory_button)
        
        control_group.setLayout(control_layout)
        parent_layout.addWidget(control_group)
        
    def create_config_frame(self, parent_layout):
        config_group = QGroupBox("Reader Configuration")
        config_group.setStyleSheet("QGroupBox{font-weight: bold; border: 2px solid #4CAF50; border-radius: 5px; margin-top: 1ex;}")
        config_layout = QHBoxLayout()
        
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
        self.report_entry = QLineEdit("10")
        self.report_entry.setMaximumWidth(50)
        
        # Add widgets to layout
        config_layout.addWidget(antenna_label)
        config_layout.addWidget(self.antenna_entry)
        config_layout.addWidget(antenna_hint)
        config_layout.addWidget(power_label)
        config_layout.addWidget(self.power_entry)
        config_layout.addWidget(report_label)
        config_layout.addWidget(self.report_entry)
        config_layout.addStretch()
        
        config_group.setLayout(config_layout)
        parent_layout.addWidget(config_group)
        
    def create_tag_frame(self, parent_layout):
        tag_group = QGroupBox("Tag Data")
        tag_group.setStyleSheet("QGroupBox{font-weight: bold; border: 2px solid #FF9800; border-radius: 5px; margin-top: 1ex;}")
        tag_layout = QVBoxLayout()
        
        # Add filter checkbox and export button in a horizontal layout
        control_layout = QHBoxLayout()
        
        self.filter_checkbox = QCheckBox("Filter Known EPCs")
        self.filter_checkbox.setChecked(True)
        control_layout.addWidget(self.filter_checkbox)
        
        # Add export button
        export_button = QPushButton("Export to CSV")
        export_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        export_button.clicked.connect(self.export_tag_data)
        control_layout.addWidget(export_button)
        
        # Add stretch to push controls to the left
        control_layout.addStretch()
        tag_layout.addLayout(control_layout)
        
        # Create tree widget for tag data
        self.tag_tree = QTreeWidget()
        self.tag_tree.setHeaderLabels([
            "#", "Antenna", "EPC", "Timestamp", "Count", 
            "RSSI (dBm)", "Phase", "Doppler"
        ])
        
        self.tag_tree.setStyleSheet("""
            QTreeWidget{
                background-color: white;
                font-family: monospace;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        
        tag_layout.addWidget(self.tag_tree)
        tag_group.setLayout(tag_layout)
        parent_layout.addWidget(tag_group)

    def create_matrix_frame(self, parent_layout):
        matrix_group = QGroupBox("Matrix View")
        matrix_group.setStyleSheet("QGroupBox{font-weight: bold; border: 2px solid #9C27B0; border-radius: 5px; margin-top: 1ex;}")
        matrix_layout = QGridLayout()
        
        self.labels = []
        for i in range(3):
            row_labels = []
            for j in range(3):
                label = QLabel()
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("""
                    QLabel{
                        background-color: white;
                        border: 1px solid #BDBDBD;
                        padding: 10px;
                        min-width: 150px;
                        min-height: 60px;
                    }
                """)
                matrix_layout.addWidget(label, i, j)
                row_labels.append(label)
            self.labels.append(row_labels)
            
        matrix_group.setLayout(matrix_layout)
        parent_layout.addWidget(matrix_group)
        
    def update_display(self, antenna, epc, timestamp, tag_seen_count, peak_rssi, phase, doppler):
        epc_lower = epc.lower()
        if epc_lower in [e.lower() for e in self.EPC_LIST]:  # Matrix always filtered
            self.update_tag_tree(antenna, epc, timestamp, tag_seen_count, peak_rssi, phase, doppler)
            self.current_rssi[epc] = peak_rssi
            self.current_phase[epc] = phase  # Store phase value
            self.refresh_matrix()
        elif not self.filter_checkbox.isChecked():  # Update tag tree only if not filtered
            self.update_tag_tree(antenna, epc, timestamp, tag_seen_count, peak_rssi, phase, doppler)
            
    def refresh_matrix(self):
        try:
            self.logger.info("Refreshing matrix...")
            for i in range(3):
                for j in range(3):
                    index = i * 3 + j
                    if index < len(self.EPC_LIST):
                        epc = self.EPC_LIST[index]
                        rssi = self.current_rssi.get(epc)
                        phase = self.current_phase.get(epc)
                        
                        self.logger.debug(f"Matrix cell [{i}][{j}] - EPC: {epc}, RSSI: {rssi}, Phase: {phase}")
                        
                        # Format display text
                        if rssi is not None:
                            try:
                                rssi_val = float(rssi)
                                display_text = f"EPC: {epc[-4:]}\nRSSI: {rssi_val:.1f} dBm"
                                if phase is not None:
                                    display_text += f"\nPhase: {phase:.1f}°"
                                
                                # Set color based on RSSI
                                if rssi_val > -45:
                                    color = "#90EE90"  # Light green
                                elif rssi_val > -65:
                                    color = "#FFFFE0"  # Light yellow
                                else:
                                    color = "#FFB6C1"  # Light red
                            except (ValueError, TypeError):
                                display_text = f"EPC: {epc[-4:]}\nRSSI: N/A"
                                color = "white"
                        else:
                            display_text = f"EPC: {epc[-4:]}\nWaiting..."
                            color = "white"
                            
                        self.labels[i][j].setText(display_text)
                        self.labels[i][j].setStyleSheet(f"""
                            QLabel{{
                                background-color: {color};
                                border: 1px solid #BDBDBD;
                                padding: 10px;
                                min-width: 150px;
                                min-height: 80px;
                                font-family: monospace;
                                qproperty-alignment: AlignCenter;
                            }}
                        """)
        except Exception as e:
            self.logger.error(f"Error in refresh_matrix: {e}")
            
    def update_matrix(self):
        self.refresh_matrix()
        
    def tag_seen_callback(self, reader, tags):
        """Callback from reader thread - emit signal to update GUI"""
        if not tags:
            return
        try:
            self.logger.info(f"Tags seen: {tags}")
            tags = self.convert_to_unicode(tags)
            for tag in tags:
                try:
                    # Extract tag data
                    antenna = tag.get('AntennaID', 'Unknown')
                    epc = tag.get('EPC-96', 'No EPC')
                    if epc != 'No EPC':
                        epc = epc.hex() if isinstance(epc, bytes) else str(epc)
                    timestamp = tag.get('LastSeenTimestampUTC', 0)
                    if isinstance(timestamp, str):
                        timestamp = int(timestamp)
                    tag_seen_count = tag.get('TagSeenCount', '0')
                    peak_rssi = tag.get('PeakRSSI', 'N/A')
                    
                    # Get Impinj-specific data
                    phase = tag.get('ImpinjRFPhaseAngle', None)
                    if phase is not None:
                        phase = phase / 10.0  # Convert to degrees
                        
                    doppler = tag.get('ImpinjRFDopplerFrequency', None)
                    if doppler is not None:
                        doppler = doppler / 10.0  # Convert to Hz
                    
                    # Emit signal with tag data
                    tag_data = {
                        'antenna': antenna,
                        'epc': epc,
                        'timestamp': timestamp,
                        'tag_seen_count': tag_seen_count,
                        'peak_rssi': peak_rssi,
                        'phase': phase,
                        'doppler': doppler
                    }
                    self.tag_data_signal.emit(tag_data)
                    
                except Exception as e:
                    self.logger.error(f"Error processing tag: {e}")
        except Exception as e:
            self.logger.error(f"Error in tag_seen_callback: {e}")

    @pyqtSlot(dict)
    def handle_tag_data(self, tag_data):
        """Handle tag data updates in GUI thread"""
        try:
            epc = tag_data['epc']
            epc_lower = epc.lower()
            
            # Update current values if EPC is in our list
            if epc_lower in [e.lower() for e in self.EPC_LIST]:
                self.logger.info(f"Updating values for EPC: {epc}")
                try:
                    self.current_rssi[epc] = float(tag_data['peak_rssi'])
                except (ValueError, TypeError):
                    self.current_rssi[epc] = -99
                self.current_phase[epc] = tag_data['phase']
                
                # Refresh the matrix
                self.refresh_matrix()
            
            # Update tag tree if not filtered or if EPC is in list
            if not self.filter_checkbox.isChecked() or epc_lower in [e.lower() for e in self.EPC_LIST]:
                self.update_tag_tree(
                    tag_data['antenna'],
                    epc,
                    tag_data['timestamp'],
                    tag_data['tag_seen_count'],
                    tag_data['peak_rssi'],
                    tag_data['phase'],
                    tag_data['doppler']
                )
                
        except Exception as e:
            self.logger.error(f"Error handling tag data: {e}")
            
    def update_tag_tree(self, antenna, epc, timestamp, tag_seen_count, peak_rssi, phase=None, doppler=None):
        try:
            epc_lower = epc.lower()
            if not self.filter_checkbox.isChecked() or epc_lower in [e.lower() for e in self.EPC_LIST]:
                try:
                    local_time = datetime.fromtimestamp(
                        int(timestamp) / 1e6
                    ).astimezone(pytz.timezone('Europe/Istanbul')).strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    self.logger.error(f"Error converting timestamp: {e}")
                    local_time = "Time Error"
                
                # Format phase and doppler values
                try:
                    phase_str = f"{phase:.2f}°" if phase is not None else "N/A"
                    doppler_str = f"{doppler:.2f} Hz" if doppler is not None else "N/A"
                except Exception as e:
                    self.logger.error(f"Error formatting phase/doppler: {e}")
                    phase_str = "N/A"
                    doppler_str = "N/A"
                
                # Check for existing item
                try:
                    items = self.tag_tree.findItems(epc, Qt.MatchExactly, 2)
                    if items:
                        item = items[0]
                        try:
                            current_count = int(item.text(4))
                        except:
                            current_count = 0
                            
                        values = [
                            str(self.tag_tree.indexOfTopLevelItem(item) + 1),
                            str(antenna),
                            epc,
                            local_time,
                            str(current_count + 1),
                            str(peak_rssi),
                            phase_str,
                            doppler_str
                        ]
                        for i, value in enumerate(values):
                            try:
                                item.setText(i, value)
                            except Exception as e:
                                self.logger.error(f"Error setting text for column {i}: {e}")
                    else:
                        values = [
                            str(self.tag_tree.topLevelItemCount() + 1),
                            str(antenna),
                            epc,
                            local_time,
                            "1",
                            str(peak_rssi),
                            phase_str,
                            doppler_str
                        ]
                        try:
                            item = QTreeWidgetItem(self.tag_tree, values)
                        except Exception as e:
                            self.logger.error(f"Error creating new tree item: {e}")
                            
                    # Limit the number of items in the tree to prevent memory issues
                    try:
                        while self.tag_tree.topLevelItemCount() > 1000:  # Keep last 1000 items
                            self.tag_tree.takeTopLevelItem(0)
                    except Exception as e:
                        self.logger.error(f"Error limiting tree items: {e}")
                        
                except Exception as e:
                    self.logger.error(f"Error updating existing item: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error in update_tag_tree: {e}")
            
        try:
            self.sort_treeview_by_peak_rssi()
        except Exception as e:
            self.logger.error(f"Error sorting tree view: {e}")

    def sort_treeview_by_peak_rssi(self):
        self.tag_tree.sortItems(5, Qt.DescendingOrder)
        
    def convert_to_unicode(self, obj):
        if isinstance(obj, dict):
            return {self.convert_to_unicode(key): self.convert_to_unicode(value)
                    for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_to_unicode(element) for element in obj]
        elif isinstance(obj, bytes):
            return obj.decode('utf-8')
        else:
            return obj
            
    def clear_inventory(self):
        self.current_rssi = {epc: -99 for epc in self.EPC_LIST}
        self.current_phase = {epc: None for epc in self.EPC_LIST}
        for i in range(3):
            for j in range(3):
                self.labels[i][j].setText("EPC Not Found")
                self.labels[i][j].setStyleSheet("""
                    QLabel{
                        background-color: white;
                        border: 1px solid #BDBDBD;
                        padding: 10px;
                        min-width: 150px;
                        min-height: 60px;
                    }
                """)
        self.tag_tree.clear()
        
    def create_reader_config(self, start_inventory=False):
        try:
            antennas = [int(x.strip()) for x in self.antenna_entry.text().split(',')]
            tx_power = int(self.power_entry.text())
            report_n = int(self.report_entry.text())
            
            # Adjust update frequency based on report_n
            update_interval = max(100, min(report_n * 100, 200))  # Between 100ms and 1000ms
            self.timer.setInterval(update_interval)
            
            factory_args = {
                'antennas': antennas,
                'tx_power': tx_power,
                'report_every_n_tags': report_n,
                'start_inventory': start_inventory,
                'tag_content_selector': {
                    'EnableROSpecID': True,
                    'EnableSpecIndex': True,
                    'EnableInventoryParameterSpecID': True,
                    'EnableAntennaID': True,
                    'EnableChannelIndex': True,
                    'EnablePeakRSSI': True,
                    'EnableFirstSeenTimestamp': True,
                    'EnableLastSeenTimestamp': True,
                    'EnableTagSeenCount': True,
                    'EnableAccessSpecID': True,
                    'C1G2EPCMemorySelector': {
                        'EnableCRC': True,
                        'EnablePCBits': True,
                    }
                },
                'impinj_search_mode': '2',
                'impinj_tag_content_selector': None
            }
            
            # Add Impinj-specific features if enabled
            if self.impinj_reports_checkbox.isChecked():
                factory_args['impinj_tag_content_selector'] = {
                    'EnableRFPhaseAngle': True,
                    'EnablePeakRSSI': True,
                    'EnableRFDopplerFrequency': True
                }
            
            return LLRPReaderConfig(factory_args)
        except Exception as e:
            self.logger.error(f"Error creating reader config: {e}")
            raise
            
    def connect_reader(self, start_inventory=False):
        reader_ip = self.ip_entry.text()
        if not reader_ip:
            return
            
        self.status_label.setText("Status: Connecting...")
        self.status_label.setStyleSheet("QLabel{color: #FFA000;}")  # Orange for connecting
        
        try:
            config = self.create_reader_config(start_inventory)
            if not config:
                return
                
            self.reader = LLRPReaderClient(reader_ip, LLRP_DEFAULT_PORT, config)
            self.reader.add_tag_report_callback(self.tag_seen_callback)
            
            self.reader.connect()
            
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("QLabel{color: #4CAF50;}")  # Green for connected
            self.start_button.setEnabled(True)
            self.connect_button.setEnabled(False)
            self.stop_button.setEnabled(True if start_inventory else False)
            self.inventory_running = start_inventory
            
            if not reactor.running:
                thread = threading.Thread(target=reactor.run, args=(False,))
                thread.daemon = True
                thread.start()
                
        except Exception as e:
            self.logger.error(f"Error connecting to reader: {e}")
            self.status_label.setText("Status: Connection Failed")
            self.status_label.setStyleSheet("QLabel{color: #f44336;}")  # Red for error
            
    def start_inventory(self):
        if self.reader:
            self.reader.disconnect()
        self.connect_reader(start_inventory=True)
        
    def stop_inventory(self):
        if self.reader:
            self.reader.disconnect()
        self.connect_reader(start_inventory=False)
        
    def closeEvent(self, event):
        if self.reader:
            self.reader.disconnect()
        if reactor.running:
            reactor.stop()
        event.accept()

    def export_tag_data(self):
        """Export tag data to CSV file"""
        try:
            # Get save file name
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Tag Data",
                f"tag_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)"
            )
            
            if file_name:
                with open(file_name, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write headers
                    headers = ["#", "Antenna", "EPC", "Timestamp", "Count", "RSSI (dBm)", "Phase", "Doppler"]
                    writer.writerow(headers)
                    
                    # Write data from tree widget
                    root = self.tag_tree.invisibleRootItem()
                    for i in range(root.childCount()):
                        item = root.child(i)
                        row_data = [item.text(j) for j in range(self.tag_tree.columnCount())]
                        writer.writerow(row_data)
                
                self.logger.info(f"Tag data exported to {file_name}")
        except Exception as e:
            self.logger.error(f"Error exporting tag data: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SllurpGUI()
    window.setGeometry(100, 100, 1200, 800)
    window.show()
    sys.exit(app.exec_())
