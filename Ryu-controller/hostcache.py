
UP = 1
DOWN = 0

ETH_ADDRESSES = [0x0802, 0x88CC, 0x8808, 0x8809, 0x0800, 0x86DD, 0x88F7]

"""
This holds the hosts information and their connection to switches.
An instance of this class is used in TopoStructure to save the topo info.
"""
class HostCache(object):
    def __init__(self):
        self.ip_to_dpid_port = {}

    def get_hw_address_of_host(self,in_ip):
        return self.ip_to_dpid_port[self.get_dpid_for_ip(ip=in_ip)][in_ip]["connected_host_mac"]

    def add_dpid_host(self,in_dpid, in_host_ip, **in_dict):
        """
        Here is example of **in_dict : {"connected_host_mac":s_mac, "sw_port_no":in_port,
        "sw_port_mac":self.topo_shape.get_hw_address_for_port_of_dpid(in_dpid=dpid, in_port_no=in_port)}
        :param in_dpid:
        :param in_host_ip:
        :param in_dict:
        """
        self.ip_to_dpid_port.setdefault(in_dpid, {})
        self.ip_to_dpid_port[in_dpid][in_host_ip]=in_dict

    def get_port_num_connected_to_sw(self, in_dpid, in_ip):
        """
        Check if host with ip address in_ip is connected to in_dpid switch.
        If it is connected it will return the port num of switch which the host is connected to.
        If there no host with that ip connected it will return -1
        :param in_dpid: Datapath id of the switch
        :param in_ip: Ip address connected to switch with datapath id equal to in_dpid
        :rtype : int
        """
        if len(self.ip_to_dpid_port[in_dpid][in_ip].keys()) == 0:
            return -1
        else:
            return self.ip_to_dpid_port[in_dpid][in_ip]["sw_port_no"]

    def get_number_of_hosts_connected_to_dpid(self, in_dpid):
        """
        Returns number of hosts connected to the switch with given in_dpid
        :param in_dpid: Datapath id of a switch
        :rtype : int
        """
        return len(self.ip_to_dpid_port[in_dpid])

    def get_ip_addresses_connected_to_dpid(self, in_dpid):
        """
        Return a list of ip addresses  connected to the dpid of switch.
        :param in_dpid: Datapath id
        :rtype : list
        """
        return self.ip_to_dpid_port[in_dpid].values()

    def get_dpid_for_ip(self, ip):
        """
        Checks if the ip address in_ip is connected to any switch. If it is, it return the dpid of that switch.
        Otherwise it returns -1.
        Something to know for later: Not sure if I should also if the mac matches.
        :param ip: Ip address of host
        :rtype : int
        """
        for temp_dpid in self.ip_to_dpid_port.keys():
            if ip in self.ip_to_dpid_port[temp_dpid].keys():
                return temp_dpid
        return -1


    def check_dpid_in_cache(self, in_dpid):
        """
        Checks if an dpid is in self.ip_to_dpid_port
        :param in_dpid: Datapath id
        :rtype : bool
        """
        if in_dpid in self.ip_to_dpid_port.keys():
            return True
        else:
            return False
