from src.core.basicHostIPCLayer import basicHostIPCLayer
from src.core.defines import *



class hostApplicationLayer(basicHostIPCLayer):

    def __init__(self, host_id, log_file, application_ids_mapping, managed_application_id):
        """Initialization
        :param host_id: The mininet host name in which this thread is spawned
        :type host_id: str
        :param log_file: The absolute path to a file which will log stdout
        :type log_file: str
        :param application_ids_mapping: A dictionary which maps application_id to ip_address,port
        :type application_ids_mapping: dict
        :param managed_application_id: Application id assigned to this co-simulation process
        :type managed_application_id: str
        :return:  None
        """
        basicHostIPCLayer.__init__(self, host_id, log_file, application_ids_mapping, managed_application_id)


    def on_rx_pkt_from_network(self, pkt):
        """
            This function gets called on reception of message from network.
            pkt will be a string of type CyberMessage proto defined in src/proto/css.proto
        """
        pass

    def on_start_up(self):
        """
            Called after initialization of application layer.
        """
        pass


    def on_shutdown(self):
        """
            Called before shutdown of application layer.
        """
        pass
