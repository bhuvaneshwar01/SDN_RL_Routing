from mininet.node import CPULimitedHost
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
import matplotlib.pyplot as plt
import networkx as nx

"""
Instructions to run the topo:
    1. Go to directory where this fil is.
    2. run: sudo -E python Pkt_Topo_with_loop.py
"""
class SimplePktSwitch(Topo):
    """Simple topology example."""

    def __init__(self, **opts):
        """Create custom topo."""

        # Initialize topology
        super(SimplePktSwitch, self).__init__(**opts)
        #Topo.__init__(self)

        # Add hosts and switches
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')

        opts = dict(protocols='OpenFlow13')

        # Adding switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        
        # Add controllers
        # c1 = self.addCo

        # Add links
        self.addLink(h1, s1,  bw=10, delay='5ms', loss=0, use_htb=True)
        self.addLink(h2, s2,  bw=10, delay='5ms', loss=0, use_htb=True)
        self.addLink(h3, s3,  bw=10, delay='5ms', loss=0, use_htb=True)
        self.addLink(h4, s4,  bw=10, delay='5ms', loss=0, use_htb=True)

        self.addLink(s2, s4,  bw=10, delay='5ms', loss=0, use_htb=True)
        self.addLink(s2, s3,  bw=10, delay='5ms', loss=0, use_htb=True)
        self.addLink(s1, s2,  bw=10, delay='5ms', loss=0, use_htb=True)
        self.addLink(s3, s4,  bw=10, delay='5ms', loss=0, use_htb=True)
        self.addLink(s1, s3,  bw=10, delay='5ms', loss=0, use_htb=True)

def installStaticFlows(net):
    for sw in net.switches:
        info('Adding flows to %s...' % sw.name)
        sw.dpctl('add-flow', 'in_port=1,actions=output=2')
        sw.dpctl('add-flow', 'in_port=2,actions=output=1')
        info(sw.dpctl('dump-flows'))

def gui_topo(net):
    G = nx.Graph()

    for host in net.hosts:
        G.add_node(host.name, type='host')

    for switch in net.switches:
        G.add_node(switch.name, type='switch')

    for link in net.links:
        G.add_edge(link.intf1.node.name, link.intf2.node.name)

    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=1500, edge_color='gray', width=1)
    nx.draw_networkx_labels(G, pos)
    plt.title("Network topologies")
    plt.show()


def run():
    c = RemoteController('c', '0.0.0.0', 6633)
    net = Mininet(topo=SimplePktSwitch(), host=CPULimitedHost, controller=None)
    net.addController(c)
    # gui_topo(net=net)
    net.start()

    installStaticFlows( net )
    h1, h2 = net.get('h1', 'h2')
    result = h1.cmd('ping -c 10 %s' % h2.IP())
    print(result)
    CLI(net)
    
    net.stop()

# if the script is run directly (sudo custom/optical.py):
if __name__ == '__main__':
    setLogLevel('info')
    run()