from __future__ import annotations

from typing import Set

import netifaces


class NetworkIface:

    def __init__(self, iface_name: str, host_ip: str, netmask: str) -> None:
        self.iface_name = iface_name
        self.host_ip = host_ip
        self.netmask = netmask

    @classmethod
    def get_ifaces(cls) -> Set[NetworkIface]:
        host_ifaces = set()
        for iface_name in netifaces.interfaces():
            if not iface_name.startswith('eth'):
                continue

            iface_details = netifaces.ifaddresses(iface_name)
            if netifaces.AF_INET not in iface_details:
                continue

            host_ip = iface_details[netifaces.AF_INET][0]['addr']
            netmask = iface_details[netifaces.AF_INET][0]['netmask']
            host_ifaces.add(NetworkIface(iface_name, host_ip, netmask))
        return host_ifaces
