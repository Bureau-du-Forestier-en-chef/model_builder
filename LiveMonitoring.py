import threading
import time
from Logger import Logging
from typing import Callable
from pathlib import Path


class MonitoredReplanningAbort(Exception):
    def __init__(self, message: str):    
        super().__init__(message)


class LiveCSVMonitor:  
    def __init__(self, 
                 csv_path: Path,
                 check_function: Callable[[], tuple[bool, str]], 
                 logger: str, 
                 check_interval: int = 10):
        self.csv_path = csv_path
        self.check_function = check_function
        self.check_interval = check_interval
        self.Logging = Logging(logger)
        self.should_stop = threading.Event()
        self.monitor_thread = None
        self.abort_requested = threading.Event()
        self.last_check_message = ""
        self.is_monitoring = False
    
    def _monitor_loop(self):
        self.Logging.log_message("INFO", f"Monitoring started (interval: {self.check_interval}s)")
        last_check_time = time.time()
        
        while not self.should_stop.is_set():
            current_time = time.time()
            print(f"Monitoring loop tick at {last_check_time}")
            
            if current_time - last_check_time >= self.check_interval and self.csv_path.exists():
                try: 
                    conditions_ok, msg = self.check_function()
                    self.last_check_message = msg
                    
                    if not conditions_ok:
                        raise MonitoredReplanningAbort(
                        f"Abort requested by monitoring: {msg}"
                        )  
                except Exception as e:
                    self.Logging.log_message("ERROR", f"Monitoring error: {str(e)}")
                    break              
                
            last_check_time = current_time
            time.sleep(5)
        
        self.Logging.log_message("INFO", "Monitoring stopped.")
    
    def start(self):
        if self.is_monitoring:
            self.Logging.log_message("WARNING", "Monitoring is already running.")
            return
            
        self.should_stop.clear()
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        self.should_stop.set()
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)

