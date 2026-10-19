#!/usr/bin/env python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.cli import CLI
from mininet.log import setLogLevel


class PublishSubscribeTopo(Topo):

    def build(self):
        # Hosts
        self.addHost('h1', ip='10.0.0.1/24')  # Publisher
        self.addHost('h2', ip='10.0.0.2/24')  # Broker
        self.addHost('h3', ip='10.0.0.3/24')  # Subscriber 1
        self.addHost('h4', ip='10.0.0.4/24')  # Subscriber 2

        # Switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')

        # Connect hosts
        self.addLink('h1', s1)
        self.addLink('h2', s4)
        self.addLink('h3', s4)
        self.addLink('h4', s4)

        # Primary path: s1 -> s2 -> s4
        self.addLink(s1, s2)
        self.addLink(s2, s4)

        # Alternative path: s1 -> s3 -> s4
        self.addLink(s1, s3)
       # self.addLink(s3, s4)


def run():
    topo = PublishSubscribeTopo()
    net = Mininet(topo=topo, switch=OVSBridge, controller=None)

    net.start()

    print("\n=== Publish-Subscribe Network ===")
    print("h1: Publisher     - 10.0.0.1")
    print("h2: Broker        - 10.0.0.2")
    print("h3: Subscriber 1  - 10.0.0.3")
    print("h4: Subscriber 2  - 10.0.0.4")

    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()
