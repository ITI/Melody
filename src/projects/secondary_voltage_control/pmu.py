import threading
from src.core.basicHostIPCLayer import basicHostIPCLayer
from src.core.defines import *
from src.proto import css_pb2




class PMU(threading.Thread):
    """Simple PMU implementation. It reads pilot buses ans sends the reading to a SCADA controller.
    """
    def __init__(self, host_control_layer, pmu_name):
        """

        :param host_control_layer: hostApplicationLayer object
        :param pmu_name: application_id
        :type pmu_name: str
        """
        threading.Thread.__init__(self)
        self.host_control_layer = host_control_layer
        self.stop = False
        self.pmu_name = pmu_name
        self.raw_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.obj_type = "bus"
        self.obj_id = self.pmu_name.split('_')[-1]
        self.field_type = "Vm"

    def run(self):
        request_no = 0
        while not self.stop:
            pkt = css_pb2.CyberMessage()
            pkt.src_application_id = self.pmu_name
            pkt.dst_application_id = "SCADA_CONTROLLER"
            pkt.msg_type = "PERIODIC_UPDATE"

            #Sends an RPC read request to get pilot bus reading.
            pilot_busses_to_read = [(self.obj_type, self.obj_id, self.field_type)]
            ret = rpc_read(pilot_busses_to_read)
            assert(ret is not None)

            assert (len(ret) == 1)


            data = pkt.content.add()
            data.key = "VOLTAGE"
            data.value = ret[0]

            data = pkt.content.add()
            data.key = "TIMESTAMP"
            data.value = str(time.time())

            data = pkt.content.add()
            data.key = "COUNTER"
            data.value = str(request_no)

            data = pkt.content.add()
            data.key = "OBJ_ID"
            data.value = self.obj_id

            #Sends pilot bus reading to SCADA controller.
            self.host_control_layer.log.info("Sending Reading: \n" + str(pkt))
            self.host_control_layer.tx_pkt_to_powersim_entity(pkt.SerializeToString())
            time.sleep(1)
            request_no += 1




class hostApplicationLayer(basicHostIPCLayer):

    def __init__(self, host_id, log_file, application_ids_mapping, managed_application_id):
        basicHostIPCLayer.__init__(self, host_id, log_file, application_ids_mapping, managed_application_id)
        self.PMU = PMU(self, managed_application_id)




    def on_rx_pkt_from_network(self, pkt):
        """
            This function gets called on reception of message from network.
            pkt will be a string of type CyberMessage proto defined in src/proto/css.proto
        """
        # just print the proto message for now
        pkt_parsed = css_pb2.CyberMessage()
        pkt_parsed.ParseFromString(pkt)

        self.log.info("Rx New packet from: " + str(pkt_parsed.src_application_id))
        self.log.info("\n" + str(pkt_parsed))


    def on_start_up(self):
        """
            Called after initialization of application layer. Here we start the PMU thread.
        """

        self.log.info("Started PMU:  " + self.managed_application_id + " on " + str(self.host_id))
        self.PMU.start()


    def on_shutdown(self):
        """
            Called before shutdown of application layer. Here we shutdown the PMU thread
        """
        self.PMU.stop = True
        self.PMU.join()
        self.log.info("Stopped PMU: " + self.managed_application_id + " on " + str(self.host_id))
