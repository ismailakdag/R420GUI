from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
import matplotlib.pyplot as plt
import numpy as np

class ReportView(QWidget):
    def __init__(self, tag_data):
        super().__init__()
        self.tag_data = tag_data  # Assuming tag_data is passed during initialization
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.setWindowTitle('Tag Data Reports')

        self.generate_report_button = QPushButton('Generate Report')
        self.generate_report_button.clicked.connect(self.generate_report)
        layout.addWidget(self.generate_report_button)

        self.report_label = QLabel('Report will be displayed here.')
        layout.addWidget(self.report_label)

    def generate_report(self):
        max_epc = self.calculate_max_epc()
        max_rssi = self.calculate_max_rssi()
        read_count = self.calculate_read_count()
        average_rssi = self.calculate_average_rssi()

        report_text = (f'Max EPC: {max_epc}\n'
                       f'Max RSSI: {max_rssi}\n'
                       f'Read Count: {read_count}\n'
                       f'Average RSSI: {average_rssi:.2f}')

        self.report_label.setText(report_text)
        self.plot_radiation_pattern()

    def calculate_max_epc(self):
        # Logic to calculate max EPC from self.tag_data
        return max(self.tag_data, key=lambda x: x['epc'])['epc']

    def calculate_max_rssi(self):
        # Logic to calculate max RSSI from self.tag_data
        return max(self.tag_data, key=lambda x: x['rssi'])['rssi']

    def calculate_read_count(self):
        # Logic to calculate read count
        return len(self.tag_data)

    def calculate_average_rssi(self):
        # Logic to calculate average RSSI
        return np.mean([x['rssi'] for x in self.tag_data])

    def plot_radiation_pattern(self):
        # Placeholder for plotting logic
        angles = np.linspace(0, 2 * np.pi, 100)
        radius = np.abs(np.sin(angles))  # Example pattern

        plt.figure()
        plt.polar(angles, radius)
        plt.title('Antenna Radiation Pattern')
        plt.show()
