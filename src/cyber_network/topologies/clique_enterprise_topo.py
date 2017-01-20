__author__ = 'Rakesh Kumar'

import random
from mininet.topo import Topo


class CliqueEnterpriseTopo(Topo):

    def __init__(self, params):

        Topo.__init__(self)
        self.params = params

        if params["num_switches"] < 2:
            print "Need to have at least three switches for a ring."
            raise

        if params["per_switch_links"] < 2 and params["per_switch_links"] > params["num_switches"] - 1:
            print "Cannot have less than 2 and more than " + str(params["num_switches"] -1) + " links."

        self.num_switches = params["num_switches"]
        self.total_switches = params["num_switches"]
        self.num_hosts_per_switch = params["num_hosts_per_switch"]
        self.per_switch_links = params["per_switch_links"]

        if "switch_switch_link_latency_range" in params:
            switch_switch_link_opts = \
                dict(delay=str(int(random.uniform(*params["switch_switch_link_latency_range"]))) + "ms")
        else:
            switch_switch_link_opts = dict()

        if "host_switch_link_latency_range" in params:
            host_switch_link_opts = \
                dict(delay=str(int(random.uniform(*params["host_switch_link_latency_range"]))) + "ms")
        else:
            host_switch_link_opts = dict()

        self.switch_names = []
        self.host_names = []
        self.host_cntr = 1

        #  Add switches and hosts under them
        for i in xrange(self.num_switches):
            curr_switch = self.addSwitch("s" + str(i+1), protocols="OpenFlow14")
            self.switch_names.append(curr_switch)

            for j in xrange(self.num_hosts_per_switch):
                curr_host = self.addHost("h" + str(self.host_cntr))

                self.host_names.append(curr_host)
                self.host_cntr += 1
                self.addLink(curr_switch, curr_host, **host_switch_link_opts)

        #  Add links between switches
        for i in xrange(self.num_switches - 1):

            dst_switch_offsets = xrange(1, self.per_switch_links)
            for j in dst_switch_offsets:

                try:
                    l = self.g[self.switch_names[i]][self.switch_names[(i + j) % self.num_switches]]
                    print l
                except KeyError:

                    self.addLink(self.switch_names[i], self.switch_names[(i + j) % self.num_switches],
                                 **switch_switch_link_opts)

        #  Form a ring only when there are more than two switches
        self.addLink(self.switch_names[0], self.switch_names[-1], **switch_switch_link_opts)
        self.add_enterprise_net_with_attk_node(host_switch_link_opts,switch_switch_link_opts)

    def add_enterprise_net_with_attk_node(self,host_switch_link_opts,switch_switch_link_opts):
        # For now it contains only one VPN gateway and 1 attack node connected in Liner fashion
        vpn_switch = self.addSwitch("s" + str(self.num_switches + 1), protocols="OpenFlow14")
        self.switch_names.append(vpn_switch)
        vpn_gateway_host = self.addHost("h" + str(self.host_cntr))
        self.host_names.append(vpn_gateway_host)
        self.host_cntr += 1

        self.addLink(vpn_switch,vpn_gateway_host,**host_switch_link_opts)
        simulated_internet_switch = self.addSwitch("s" + str(self.num_switches + 2), protocols="OpenFlow14")
        self.switch_names.append(simulated_internet_switch)
        simulated_attack_host = self.addHost("h" + str(self.host_cntr))
        self.host_names.append(simulated_attack_host)
        self.host_cntr += 1

        self.addLink(simulated_internet_switch, simulated_attack_host, **host_switch_link_opts)
        self.addLink(simulated_internet_switch,vpn_switch,**switch_switch_link_opts)
        self.addLink(vpn_switch,self.switch_names[self.num_switches-1],**switch_switch_link_opts)

    def __str__(self):
        params_str = ''
        for k, v in self.params.items():
            params_str += "_" + str(k) + "_" + str(v)
        return self.__class__.__name__ + params_str


topos = {"cliqueenttopo": (lambda: CliqueEnterpriseTopo())}
