import socket
import logging
from zeroconf import IPVersion, ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)

class ADBServiceBroadcaster:
    """Announces this PC as an ADB pairing service on the network."""
    
    def __init__(self, name="ModelFactory", port=5555, pairing_code="123456"):
        self.name = name
        self.port = port
        self.pairing_code = pairing_code
        self.zeroconf = None
        self.service_info = None

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self):
        try:
            self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            local_ip = self._get_local_ip()
            
            # ADB-TLS Pairing service type (MUST use 'P' as key for pairing code)
            desc = {'P': self.pairing_code}
            
            self.service_info = ServiceInfo(
                "_adb-tls-pairing._tcp.local.",
                f"{self.name}._adb-tls-pairing._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=desc,
                server=f"{socket.gethostname().split('.')[0]}.local.", # Clean hostname
            )
            
            logger.info(f"Broadcasting ADB service {self.name} at {local_ip}:{self.port} with code {self.pairing_code}")
            self.zeroconf.register_service(self.service_info)
            return True
        except Exception as e:
            logger.error(f"Failed to start mDNS broadcaster: {e}")
            return False

    def stop(self):
        if self.zeroconf:
            logger.info(f"Stopping ADB service broadcast: {self.name}")
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
            except Exception as e:
                logger.error(f"Error stopping zeroconf: {e}")
            self.zeroconf = None
