from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost, RemoteController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel


class SimpleTopo(Topo):
    def __init__(self, **opts):
        super(SimpleTopo, self).__init__(**opts)
        opts = dict(protocols='OpenFlow13')
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s1)

def run_link_flooding_attack():
    c = RemoteController('c', '0.0.0.0', 6633)
    net = Mininet(topo=SimpleTopo(),host=CPULimitedHost,link=TCLink,controller=None)
    net.addController(c)
    net.start()
    victim = net.get('h1')
    server = victim.popen('iperf -s')
    trgt = None

    for h in net.hosts:
        if h != victim:
            trgt = h
            break
    print("[+]  Attackingg........\n")
    for i in range(0,10):
        trgt.popen('iperf -c {} -t 60 -P 5'.format(victim.IP()))
    
    server.terminate()
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_link_flooding_attack()