import sys
from src.cyber_network.network_configuration import NetworkConfiguration
from src.cyber_network.traffic_flow import EmulatedTrafficFlow, ReplayTrafficFlow
from src.cyber_network.traffic_flow import TRAFFIC_FLOW_ONE_SHOT
from src.core.net_power import NetPower
from src.core.shared_buffer import *
from src.proto import configuration_pb2
from google.protobuf import text_format

CPUS_SUBSET = "1-12"


class Experiment(NetPower):

    def __init__(self,
                 run_time,
                 network_configuration,
                 project_dir,
                 base_dir,
                 log_dir,
                 emulated_background_traffic_flows,
                 replay_traffic_flows,
                 cyber_host_apps,
                 enable_kronos,
                 relative_cpu_speed):
        super(
            Experiment,
            self).__init__(
            run_time,
            network_configuration,
            project_dir,
            base_dir,
            log_dir,
            emulated_background_traffic_flows,
            replay_traffic_flows,
            cyber_host_apps,
            enable_kronos,
            relative_cpu_speed,
            CPUS_SUBSET)


def get_network_configuration(project_config):
    cyber_node_roles = []
    cyber_emulation_spec = project_config.cyber_emulation_spec
    n_hosts = cyber_emulation_spec.num_hosts
    cyber_host_apps = {}
    topology_params = {
        "num_hosts": cyber_emulation_spec.num_hosts,
        "num_switches": cyber_emulation_spec.num_switches,
        "switch_switch_link_latency_range": (cyber_emulation_spec.inter_switch_link_latency_ms,
                                             cyber_emulation_spec.inter_switch_link_latency_ms),
        "host_switch_link_latency_range": (cyber_emulation_spec.host_switch_link_latency_ms,
                                           cyber_emulation_spec.host_switch_link_latency_ms)
    }

    for param in cyber_emulation_spec.additional_topology_param:
        if param.HasField("parameter_value_string"):
            topology_params[param.parameter_name] = param.parameter_value_string
        if param.HasField("parameter_value_int"):
            topology_params[param.parameter_name] = param.parameter_value_int
        if param.HasField("parameter_value_double"):
            topology_params[param.parameter_name] = param.parameter_value_double
        if param.HasField("parameter_value_bool"):
            topology_params[param.parameter_name] = param.parameter_value_bool

    for host_no in xrange(1, n_hosts + 1):
        curr_host = "h" + str(host_no)
        is_configured = False
        for mapping in project_config.cyber_physical_map:
            if mapping.cyber_entity_id == curr_host:
                cyber_node_roles.append((curr_host,
                                         [(entity.application_id, entity.listen_port) for entity in
                                          mapping.mapped_application]))

                is_configured = True
                if mapping.HasField("app_layer_src"):
                    cyber_host_apps[curr_host] = mapping.app_layer_src
        if not is_configured:
            print "ERROR: Cyber Node Role Not specified for ", curr_host, " in the project configuration!"
            sys.exit(0)


    network_configuration = NetworkConfiguration(
        controller="ryu",
        controller_ip="127.0.0.1",
        controller_port=6633,
        controller_api_base_url="http://localhost:8080/",
        controller_api_user_name="admin",
        controller_api_password="admin",
        topo_name=cyber_emulation_spec.topology_name,
        topo_params=topology_params,
        conf_root="configurations/",
        synthesis_name="SimpleMACSynthesis",
        synthesis_params={},
        roles=cyber_node_roles,
        project_name=project_config.project_name,
    )

    network_configuration.setup_network_graph(mininet_setup_gap=1, synthesis_setup_gap=1)
    return network_configuration, cyber_host_apps


def get_experiment_container(project_config, project_run_time_args):
    network_configuration, cyber_host_apps = get_network_configuration(project_config)
    script_dir = os.path.dirname(os.path.realpath(__file__))
    idx = script_dir.index('Melody')
    base_dir = script_dir[0:idx] + "Melody"
    log_dir = base_dir + "/logs/" + str(network_configuration.project_name)

    bg_flows = []

    for bg_flow_spec in project_config.bg_flow:
        offset = bg_flow_spec.flow_start_time

        cmd_to_run_at_src = bg_flow_spec.cmd_to_run_at_src
        cmd_to_run_at_dst = bg_flow_spec.cmd_to_run_at_dst

        for host_no in xrange(1, project_config.cyber_emulation_spec.num_hosts + 1):
            hostname = "h" + str(host_no)
            cmd_to_run_at_src = cmd_to_run_at_src.replace(hostname,
                                                          network_configuration.mininet_obj.get(hostname).IP())
            cmd_to_run_at_dst = cmd_to_run_at_dst.replace(hostname,
                                                          network_configuration.mininet_obj.get(hostname).IP())

        bg_flows.append(EmulatedTrafficFlow(type=TRAFFIC_FLOW_ONE_SHOT,
                                            offset=offset,
                                            inter_flow_period=0,
                                            run_time=project_run_time_args["run_time"],
                                            src_mn_node=network_configuration.mininet_obj.get(
                                                bg_flow_spec.src_cyber_entity),
                                            dst_mn_node=network_configuration.mininet_obj.get(
                                                bg_flow_spec.dst_cyber_entity),
                                            root_user_name=project_run_time_args["admin_user_name"],
                                            root_password=project_run_time_args["admin_password"],
                                            server_process_start_cmd=cmd_to_run_at_dst,
                                            client_expect_file=cmd_to_run_at_src,
                                            long_running=True))
    replay_flows = []
    for replay_flow_spec in project_config.replay_flow:
        involved_nodes = [cyber_node for cyber_node in replay_flow_spec.involved_cyber_entity]
        replay_flows.append(ReplayTrafficFlow(involved_nodes=involved_nodes,
                                              pcap_file_path=replay_flow_spec.pcap_file_path))

    return Experiment(run_time=project_run_time_args["run_time"],
                      network_configuration=network_configuration,
                      project_dir=project_run_time_args["project_directory"],
                      base_dir=base_dir,
                      log_dir=log_dir,
                      emulated_background_traffic_flows=bg_flows,
                      replay_traffic_flows=replay_flows,
                      cyber_host_apps=cyber_host_apps,
                      enable_kronos=project_run_time_args["enable_kronos"],
                      relative_cpu_speed=project_run_time_args["rel_cpu_speed"])


def parse_experiment_configuration(project_run_time_args):
    assert "project_directory" in project_run_time_args, "ERROR: Project Directory must be specified !"
    assert "run_time" in project_run_time_args, "ERROR: Emulation Run time must be specified !"
    assert "enable_kronos" in project_run_time_args, "ERROR: Kronos state is not specified !"
    assert "rel_cpu_speed" in project_run_time_args, "ERROR: Kronos specific relative cpu speed is not specified !"
    assert "admin_user_name" in project_run_time_args, "ERROR: Admin user name is not specified !"
    assert "admin_password" in project_run_time_args, "ERROR: Admin user password is not specified !"

    configuration_file = project_run_time_args["project_directory"] + "/project_configuration.prototxt"
    if not os.path.isfile(configuration_file):
        print "Configuration file not found for the project !"
        sys.exit(0)

    project_config = configuration_pb2.ProjectConfiguration()
    with open(configuration_file, 'r') as f:
        text_format.Parse(f.read(), project_config)

    return get_experiment_container(project_config, project_run_time_args)

#def get_application_id_params(config_file, )
