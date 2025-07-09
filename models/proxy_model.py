# models/proxy_model.py

import json
from typing import Optional, Dict, Any # <-- 添加这一行

class Proxy:
    def __init__(self,
                 name: str,
                 proxy_type: str,
                 server: str,
                 port: int,
                 uuid: Optional[str] = None,
                 password: Optional[str] = None,
                 alter_id: Optional[int] = None,
                 cipher: Optional[str] = None,
                 network: Optional[str] = None, # e.g., "ws", "grpc", "tcp"
                 tls: bool = False,
                 skip_cert_verify: bool = False, # For insecure TLS
                 host: Optional[str] = None, # SNI for TLS, Host header for WS/HTTP
                 path: Optional[str] = None, # Path for WS/HTTP/gRPC
                 service_name: Optional[str] = None, # For gRPC
                 flow: Optional[str] = None, # Vless flow
                 obfs: Optional[str] = None, # Hysteria2 obfs
                 obfs_password: Optional[str] = None, # Hysteria2 obfs password
                 raw_link: Optional[str] = None, # Original raw link
                 latency: Optional[float] = None, # In milliseconds
                 region: Optional[str] = None, # Country/Region
                 isp: Optional[str] = None, # Internet Service Provider
                 last_checked: Optional[float] = None # Unix timestamp
                ):
        self.name = name
        self.proxy_type = proxy_type
        self.server = server
        self.port = port
        self.uuid = uuid
        self.password = password
        self.alter_id = alter_id
        self.cipher = cipher
        self.network = network
        self.tls = tls
        self.skip_cert_verify = skip_cert_verify
        self.host = host
        self.path = path
        self.service_name = service_name
        self.flow = flow
        self.obfs = obfs
        self.obfs_password = obfs_password
        self.raw_link = raw_link
        self.latency = latency
        self.region = region
        self.isp = isp
        self.last_checked = last_checked

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Proxy object to a dictionary."""
        return {
            "name": self.name,
            "type": self.proxy_type,
            "server": self.server,
            "port": self.port,
            "uuid": self.uuid,
            "password": self.password,
            "alter_id": self.alter_id,
            "cipher": self.cipher,
            "network": self.network,
            "tls": self.tls,
            "skip_cert_verify": self.skip_cert_verify,
            "host": self.host,
            "path": self.path,
            "service_name": self.service_name,
            "flow": self.flow,
            "obfs": self.obfs,
            "obfs_password": self.obfs_password,
            "raw_link": self.raw_link,
            "latency": self.latency,
            "region": self.region,
            "isp": self.isp,
            "last_checked": self.last_checked
        }

    def generate_key(self) -> str:
        """Generates a unique key for deduplication."""
        # Normalize name to avoid issues with different names for the same proxy
        normalized_name = self.name.split(' ')[0] if self.name else ''
        parts = [
            self.proxy_type,
            self.server,
            str(self.port),
            self.uuid if self.uuid else '',
            self.password if self.password else '',
            self.cipher if self.cipher else '',
            self.network if self.network else '',
            self.host if self.host else '',
            self.path if self.path else '',
            normalized_name
        ]
        return ":".join(str(p) for p in parts if p is not None).lower()

    def to_clash_proxy_dict(self) -> Dict[str, Any]:
        """Converts the Proxy object to a Clash-compatible dictionary."""
        clash_dict = {
            "name": self.name,
            "type": self.proxy_type,
            "server": self.server,
            "port": self.port
        }

        if self.proxy_type == "vmess":
            clash_dict["uuid"] = self.uuid
            clash_dict["alterId"] = self.alter_id if self.alter_id is not None else 0
            clash_dict["cipher"] = self.cipher if self.cipher else "auto"
            clash_dict["network"] = self.network if self.network else "tcp"
            if self.network == "ws":
                clash_dict["ws-path"] = self.path if self.path else "/"
                clash_dict["ws-headers"] = {"Host": self.host} if self.host else {"Host": self.server}
            elif self.network == "grpc":
                clash_dict["grpc-service-name"] = self.service_name if self.service_name else ""

            if self.tls:
                clash_dict["tls"] = True
                if self.skip_cert_verify:
                    clash_dict["skip-cert-verify"] = True
                if self.host:
                    clash_dict["servername"] = self.host # SNI for TLS

        elif self.proxy_type == "vless":
            clash_dict["uuid"] = self.uuid
            clash_dict["network"] = self.network if self.network else "tcp"
            if self.flow:
                clash_dict["flow"] = self.flow

            if self.network == "ws":
                clash_dict["ws-path"] = self.path if self.path else "/"
                clash_dict["ws-headers"] = {"Host": self.host} if self.host else {"Host": self.server}
            elif self.network == "grpc":
                clash_dict["grpc-service-name"] = self.service_name if self.service_name else ""

            if self.tls:
                clash_dict["tls"] = True
                if self.skip_cert_verify:
                    clash_dict["skip-cert-verify"] = True
                if self.host:
                    clash_dict["servername"] = self.host # SNI for TLS

        elif self.proxy_type == "trojan":
            clash_dict["password"] = self.password
            if self.network:
                clash_dict["network"] = self.network
            if self.tls: # Trojan almost always TLS
                clash_dict["tls"] = True
                if self.skip_cert_verify:
                    clash_dict["skip-cert-verify"] = True
                if self.host:
                    clash_dict["sni"] = self.host # SNI for Trojan

        elif self.proxy_type == "ss":
            clash_dict["password"] = self.password
            clash_dict["cipher"] = self.cipher

        elif self.proxy_type == "hysteria2":
            clash_dict["password"] = self.password
            clash_dict["obfs"] = self.obfs if self.obfs else ""
            clash_dict["obfs-password"] = self.obfs_password if self.obfs_password else ""
            clash_dict["tls"] = True # Hysteria2 implies TLS
            if self.skip_cert_verify:
                clash_dict["skip-cert-verify"] = True
            if self.host:
                clash_dict["sni"] = self.host # Hysteria2 also uses SNI

        elif self.proxy_type in ["http", "https", "socks5", "socks4"]:
            if self.password:
                clash_dict["username"] = self.uuid # Assuming uuid is used for username if available
                clash_dict["password"] = self.password
            if self.tls: # HTTPS implies TLS
                clash_dict["tls"] = True
                if self.skip_cert_verify:
                    clash_dict["skip-cert-verify"] = True


        # Remove None values for cleaner output
        return {k: v for k, v in clash_dict.items() if v is not None}
