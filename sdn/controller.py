from collections import deque

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from os_ken.topology import event
from os_ken.topology.api import get_switch, get_link
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib import hub


class PublishSubscribeController(app_manager.OSKenApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    HOSTS = {
        "10.0.0.1": (1, 1),
        "10.0.0.2": (4, 1),
        "10.0.0.3": (4, 2),
        "10.0.0.4": (4, 3),
    }

    FLOW_COOKIE = 1

    def __init__(self, *args, **kwargs):
        super(PublishSubscribeController, self).__init__(*args, **kwargs)

        self.datapaths = {}
        self.adjacency = {}
        self.port_map = {}
        self.reroute_scheduled = False

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath

        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER
            )
        ]

        instructions = [
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                actions
            )
        ]

        flow_mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=0,
            match=match,
            instructions=instructions
        )

        datapath.send_msg(flow_mod)
        self.logger.info("Switch connected: %s", datapath.id)
        self.schedule_reroute()

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        datapath = ev.datapath

        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath

        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(datapath.id, None)
            self.schedule_reroute()

    def get_path(self, src, dst):
        queue = deque([[src]])
        visited = set()

        while queue:
            path = queue.popleft()
            node = path[-1]

            if node == dst:
                return path

            if node in visited:
                continue

            visited.add(node)

            for neighbor in sorted(self.adjacency.get(node, {})):
                if neighbor not in visited:
                    queue.append(path + [neighbor])

        return None

    def schedule_reroute(self):
        if not self.reroute_scheduled:
            self.reroute_scheduled = True
            hub.spawn_after(3, self.reroute)

    def rebuild_topology(self):
        switches = get_switch(self, None)
        links = get_link(self, None)

        new_adjacency = {}
        new_port_map = {}

        for switch in switches:
            new_adjacency.setdefault(switch.dp.id, {})

        for link in links:
            src = link.src.dpid
            dst = link.dst.dpid

            new_adjacency.setdefault(src, {})[dst] = 1
            new_port_map[(src, dst)] = link.src.port_no

        if not new_adjacency or not links:
            self.logger.warning("Topology discovery is incomplete; keeping existing forwarding rules")
            return False

        self.adjacency = new_adjacency
        self.port_map = new_port_map

        self.logger.info("Topology updated: %s", self.adjacency)
        return True

    def remove_installed_flows(self):
        for datapath in self.datapaths.values():
            parser = datapath.ofproto_parser
            ofproto = datapath.ofproto

            flow_mod = parser.OFPFlowMod(
                datapath=datapath,
                cookie=self.FLOW_COOKIE,
                cookie_mask=0xffffffffffffffff,
                command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY,
                match=parser.OFPMatch()
            )

            datapath.send_msg(flow_mod)

    def add_flow(self, datapath, match, out_port):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        actions = [parser.OFPActionOutput(out_port)]
        instructions = [
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                actions
            )
        ]

        flow_mod = parser.OFPFlowMod(
            datapath=datapath,
            cookie=self.FLOW_COOKIE,
            priority=20,
            match=match,
            instructions=instructions
        )

        datapath.send_msg(flow_mod)

    def install_host_pair(self, src_ip, dst_ip):
        src_switch, src_host_port = self.HOSTS[src_ip]
        dst_switch, dst_host_port = self.HOSTS[dst_ip]

        path = self.get_path(src_switch, dst_switch)

        if path is None:
            return

        for index, switch_id in enumerate(path):
            datapath = self.datapaths.get(switch_id)

            if datapath is None:
                continue

            if index == 0:
                in_port = src_host_port
            else:
                in_port = self.port_map.get(
                    (switch_id, path[index - 1])
                )

            if index == len(path) - 1:
                out_port = dst_host_port
            else:
                out_port = self.port_map.get(
                    (switch_id, path[index + 1])
                )

            if in_port is None or out_port is None:
                continue

            parser = datapath.ofproto_parser

            ipv4_match = parser.OFPMatch(
                in_port=in_port,
                eth_type=0x0800,
                ipv4_src=src_ip,
                ipv4_dst=dst_ip
            )

            arp_match = parser.OFPMatch(
                in_port=in_port,
                eth_type=0x0806,
                arp_spa=src_ip,
                arp_tpa=dst_ip
            )

            self.add_flow(datapath, ipv4_match, out_port)
            self.add_flow(datapath, arp_match, out_port)

    def reroute(self):
        self.reroute_scheduled = False

        if not self.rebuild_topology():
            return

        if not all(switch_id in self.datapaths for switch_id in (1, 2, 3, 4)):
            self.logger.warning("Waiting for all four switches to connect")
            return

        path = self.get_path(1, 4)

        if path is None:
            self.logger.warning("No available route between s1 and s4")
            return

        self.logger.info("Selected route: %s", path)

        self.remove_installed_flows()

        host_ips = list(self.HOSTS.keys())

        for src_ip in host_ips:
            for dst_ip in host_ips:
                if src_ip != dst_ip:
                    self.install_host_pair(src_ip, dst_ip)

        self.logger.info("Forwarding rules installed for all host pairs")

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        self.logger.info("Switch discovered")
        self.schedule_reroute()

    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        self.logger.warning("Switch disconnected")
        self.schedule_reroute()

    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        self.logger.info("Link added")
        self.schedule_reroute()

    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        self.logger.warning("Link removed")
        self.schedule_reroute()
