# RFID Reader Application

## Description
This application interfaces with an RFID reader to manage and display tag data. It provides features for filtering, displaying, and configuring the reader settings.

## Prerequisites
- Python 3.12 or higher
- Required libraries:
  - PyQt5
  - Twisted
  - sllurp

## Installation
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd R420GUI
   ```
2. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. Run the application:
   ```bash
   python main.py
   ```
2. Configure the reader settings in the GUI.
3. Use the EPC list to filter tag data.

## Configuration
- **Reader Settings**: Configure antenna ports, TX power, report frequency, and RSSI threshold.
- **Display Settings**: Toggle visibility for various tag attributes such as RSSI Peak, RSSI Last, First Seen Time, etc.
- **EPC Management**: Load, save, and edit EPCs from the list.

## Features
- Matrix view for displaying tag data.
- Filtering options for EPCs.
- Asynchronous connection handling for the RFID reader.
- User-friendly interface with intuitive controls.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request.

## Contact
For any inquiries, please contact [ismailakd03@gmail.com].
