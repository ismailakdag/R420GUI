import logging
from typing import List, Dict, Any, Optional
from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient, LLRP_DEFAULT_PORT
from PyQt5.QtCore import QObject, pyqtSignal

class RFIDReader(QObject):
    # Define signals for connection status
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.reader = None
        self.reader_config = None
        self.inventory_running = False
        self._callback = None

    def create_config(self, settings: Dict[str, Any]) -> Optional[LLRPReaderConfig]:
        try:
            factory_args = {
                'tx_power': settings.get('power', 30),
                'report_every_n_tags': settings.get('report_every_n', 1),
                'start_inventory': False,
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
                'impinj_tag_content_selector': {
                    'EnableRFPhaseAngle': True,
                    'EnablePeakRSSI': True,
                    'EnableRFDopplerFrequency': True
                }
            }
            
            return LLRPReaderConfig(factory_args)
        except Exception as e:
            self.logger.error(f"Error creating reader config: {e}")
            return None

    def connect(self, ip: str, config: Dict[str, Any], callback) -> bool:
        try:
            self.reader_config = self.create_config(config)
            if not self.reader_config:
                self.connection_error.emit("Failed to create reader configuration")
                return False

            self._callback = callback
            self.reader = LLRPReaderClient(ip, LLRP_DEFAULT_PORT, self.reader_config)
            self.reader.add_tag_report_callback(callback)
            
            # Connect in a non-blocking way
            def on_connect(proto):
                self.logger.info("Connected to reader")
                self.connected.emit()
                return proto

            def on_failed(failure):
                error_msg = str(failure.value)
                self.logger.error(f"Connection failed: {error_msg}")
                self.connection_error.emit(error_msg)
                self.reader = None
                return failure

            d = self.reader.connect()
            d.addCallbacks(on_connect, on_failed)
            return True
            
        except Exception as e:
            error_msg = f"Error connecting to reader: {e}"
            self.logger.error(error_msg)
            self.connection_error.emit(error_msg)
            return False

    def start_inventory(self) -> bool:
        try:
            if self.reader and not self.inventory_running:
                self.reader.start_inventory()
                self.inventory_running = True
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error starting inventory: {e}")
            return False

    def stop_inventory(self) -> bool:
        try:
            if self.reader and self.inventory_running:
                self.reader.stop_inventory()
                self.inventory_running = False
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error stopping inventory: {e}")
            return False

    def disconnect(self) -> None:
        try:
            if self.reader:
                if self.inventory_running:
                    self.stop_inventory()
                self.reader.disconnect()
                self.reader = None
                self.disconnected.emit()
        except Exception as e:
            self.logger.error(f"Error disconnecting from reader: {e}")

    def is_connected(self) -> bool:
        return self.reader is not None and not getattr(self.reader, '_disconnecting', False)
