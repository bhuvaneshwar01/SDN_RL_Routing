from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

if __name__ == '__main__':
    setLogLevel('info')

    # Create a Mininet network
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch)

    # Add switches to the network
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')

    # Add hosts to the network
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')

    # Add links between the hosts and switches
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(s2, s1)
    net.addLink(s2,s3)
    net.addLink(s1,s3)

    # Start the network
    net.start()
    
    # Start the CLI to interact with the network
    CLI(net)

    # Stop the network
    net.stop()
