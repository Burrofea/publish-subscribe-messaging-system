#!/usr/bin/env python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel


CONTROLLER_IP = "127.0.0.1"
CONTROLLER_PORT = 6633


class PublishSubscribeTopo(Topo):

    def build(self):
        # Hosts
        self.addHost("h1", ip="10.0.0.1/24")  # Publisher
        self.addHost("h2", ip="10.0.0.2/24")  # Broker
        self.addHost("h3", ip="10.0.0.3/24")  # Subscriber 1
        self.addHost("h4", ip="10.0.0.4/24")  # Subscriber 2

        # OpenFlow switches
        s1 = self.addSwitch("s1", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", protocols="OpenFlow13")
        s3 = self.addSwitch("s3", protocols="OpenFlow13")
        s4 = self.addSwitch("s4", protocols="OpenFlow13")

        # Host connections
        self.addLink("h1", s1)
        self.addLink("h2", s4)
        self.addLink("h3", s4)
        self.addLink("h4", s4)

        # Primary path: s1 -> s2 -> s4
        self.addLink(s1, s2)
        self.addLink(s2, s4)

        # Alternative path: s1 -> s3 -> s4
        self.addLink(s1, s3)
        self.addLink(s3, s4)


def run():
    topo = PublishSubscribeTopo()

    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=None,
        autoSetMacs=True
    )

    try:
        # Connect switches to the external OS-Ken controller.
        net.addController(
            "c0",
            controller=RemoteController,
            ip=CONTROLLER_IP,
            port=CONTROLLER_PORT
        )

        net.start()

        # Keep the alternative path available but inactive initially.
        # This avoids a Layer 2 loop during the initial test.
        net.configLinkStatus("s3", "s4", "down")

        print("\n========== Publish-Subscribe SDN Network ==========")
        print("Controller: {}:{}".format(
            CONTROLLER_IP, CONTROLLER_PORT
        ))
        print("h1 - Publisher:    10.0.0.1")
        print("h2 - Broker:       10.0.0.2")
        print("h3 - Subscriber 1: 10.0.0.3")
        print("h4 - Subscriber 2: 10.0.0.4")
        print("\nPrimary path:     s1 -> s2 -> s4")
        print("Alternative path: s1 -> s3 -> s4")
        print("Alternative link s3-s4 is initially DOWN.")
        print("\nUseful Mininet commands:")
        print("  pingall")
        print("  net")
        print("  sh ovs-vsctl show")
        print("  sh ovs-ofctl -O OpenFlow13 dump-flows s1")
        print("  link s2 s4 down")
        print("  link s3 s4 up")
        print("  exit")
        print("===================================================\n")

        CLI(net)

    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run()
