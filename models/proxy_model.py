# proxy_tool/models/proxy_model.py

import hashlib
import json
import time
from typing import Optional, Dict, Any

class Proxy:
    """
    Represents a single proxy server.
    Attributes are designed to be compatible with various proxy protocols
    and for validation/deduplication.
    """
    def __init__(self,
                 name: str,
                 proxy_type: str,
                 server: str,
                 port: int,
                 uuid: Optional[str] = None,
                 password: Optional[str] = None,
                 cipher: Optional[str] = None,
                 tls: bool = False,
                 skip_cert_verify: bool = False,
                 network: Optional[str] = None,  # e.g., ws, grpc, tcp
                 host: Optional[str] = None,     # WebSocket host, SNI for Trojan/Vless
                 path: Optional[str] = None,     # WebSocket path
                 alter_id: Optional[int] = None, # Vmess alterId
                 flow: Optional[str] = None,     # Vless flow
                 service_name: Optional[str] = None, # gRPC service name
                 obfs: Optional[str] = None,     # Hysteria2 obfs type
                 obfs_password: Optional[str] = None, # Hysteria2 obfs password
                 raw_link: Optional[str] = None, # Original raw link/content
                 latency: Optional[float] = None, # Latency in milliseconds
                 region: Optional[str] = None,   # Geographical region
                 isp: Optional[str] = None,      # ISP information
                 last_checked: Optional[float] = None # Timestamp of last check
                 ):
        self.name = name
        self.proxy_type = proxy_type # e.g., vmess, trojan, ss, http, socks5, vless, hysteria2
        self.server = server
        self.port = port
        self.uuid = uuid
        self.password = password
        self.cipher = cipher
        self.tls = tls
        self.skip_cert_verify = skip_cert_verify
        self.network = network
        self.host = host
        self.path = path
        self.alter_id = alter_id
        self.flow = flow
        self.service_name = service_name
        self.obfs = obfs
        self.obfs_password = obfs_password
        self.raw_link = raw_link
        self.latency = latency
        self.region = region
        self.isp = isp
        self.last_checked = last_checked or time.time() # Default to current time if not provided

    def __repr__(self):
        """String representation for easy debugging."""
        return f"Proxy(Name='{self.name}', Type='{self.proxy_type}', Server='{self.server}', Port={self.port})"

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Proxy object to a dictionary, suitable for JSON serialization or display."""
        # Filter out None values for cleaner output
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def generate_key(self) -> str:
        """
        Generates a unique key for the proxy based on its crucial attributes.
        This is used for deduplication.
        """
        # Create a tuple of core attributes that uniquely identify a proxy.
        # Exclude dynamic attributes like latency, region, last_checked, raw_link, name.
        key_content = (
            self.proxy_type,
            self.server,
            self.port,
            self.uuid,
            self.password,
            self.cipher,
            self.tls,
            self.skip_cert_verify,
            self.network,
            self.host,
            self.path,
            self.alter_id,
            self.flow,
            self.service_name,
            self.obfs,
            self.obfs_password,
        )
        # Use JSON dump to convert the tuple to a stable string, then hash it.
        # This handles different data types consistently.
        key_string = json.dumps(key_content, sort_keys=True)
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()

    # You might add methods here for converting to specific config formats (e.g., Clash)
    def to_clash_proxy_dict(self) -> Dict[str, Any]:
        """
        Converts the proxy object to a dictionary suitable for Clash YAML configuration.
        Note: This is a simplified conversion. Complex Clash features might need more logic.
        """
        clash_dict = {
            "name": self.name,
            "type": self.proxy_type,
            "server": self.server,
            "port": self.port,
        }

        if self.proxy_type == "vmess":
            clash_dict["uuid"] = self.uuid
            clash_dict["alterId"] = self.alter_id
            clash_dict["cipher"] = self.cipher if self.cipher else "auto" # Default cipher for vmess
            clash_dict["network"] = self.network if self.network else "tcp"
            if self.network in ["ws", "grpc"]:
                clash_dict["ws-path"] = self.path
                clash_dict["ws-headers"] = {"Host": self.host} if self.host else {}
            clash_dict["tls"] = self.tls
            if self.tls:
                clash_dict["skip-cert-verify"] = self.skip_cert_verify
        elif self.proxy_type == "vless":
            clash_dict["uuid"] = self.uuid
            clash_dict["network"] = self.network if self.network else "tcp"
            if self.network in ["ws", "grpc"]:
                clash_dict["ws-path"] = self.path
                clash_dict["ws-headers"] = {"Host": self.host} if self.host else {}
                if self.network == "grpc":
                    clash_dict["grpc-service-name"] = self.service_name
            clash_dict["tls"] = self.tls
            if self.tls:
                clash_dict["skip-cert-verify"] = self.skip_cert_verify
            if self.flow:
                clash_dict["flow"] = self.flow
        elif self.proxy_type == "trojan":
            clash_dict["password"] = self.password
            clash_dict["network"] = self.network if self.network else "tcp"
            clash_dict["tls"] = self.tls if self.tls else True # Trojan usually requires TLS
            if self.tls:
                clash_dict["skip-cert-verify"] = self.skip_cert_verify
                clash_dict["sni"] = self.host if self.host else self.server # SNI for Trojan
        elif self.proxy_type == "ss":
            clash_dict["password"] = self.password
            clash_dict["cipher"] = self.cipher
            # SS usually doesn't have complex network/TLS settings in basic Clash config
        elif self.proxy_type == "hysteria2":
            clash_dict["password"] = self.password # For Hysteria2, password is a must
            clash_dict["obfs"] = self.obfs
            clash_dict["obfs-password"] = self.obfs_password
            clash_dict["tls"] = True # Hysteria2 implies TLS
            clash_dict["skip-cert-verify"] = self.skip_cert_verify
        elif self.proxy_type in ["http", "socks5"]:
            if self.password: # Basic auth for HTTP/SOCKS
                clash_dict["username"] = self.name # Assuming name holds username for http/socks
                clash_dict["password"] = self.password
            clash_dict["tls"] = self.tls # For HTTPS proxies

        # Clean up empty values for Clash config
        return {k: v for k, v in clash_dict.items() if v is not None and v != "" and v != {}}
