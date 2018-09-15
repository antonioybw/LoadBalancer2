from concurrent import futures
import time
import argparse
import json
import sys
import grpc
sys.path.append('./protos/gen')
import lb_pb2
import lb_pb2_grpc
import processor_pb2
import processor_pb2_grpc

parser = argparse.ArgumentParser(description='LoadBalancer server controller service')
parser.add_argument('--proc_list_path', default='./proc_list/proc_server_ip.txt',   metavar='', help='processing server ip list, %(default)s')

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

args = vars(parser.parse_args())


proc_list_path = args['proc_list_path'] 
processor_stub_list = []

with open(proc_list_path, 'r') as f:
    proc_array = json.load(f)
    for each in proc_array:
      processor_ip = str(each['processor_ip'].encode('utf-8'))
      processor_port = str(each['processor_port'].encode('utf-8'))
      channel = grpc.insecure_channel(processor_ip + ':' + processor_port)
      try:
        stub = processor_pb2_grpc.ProcessorJobHandlerStub(channel)
        response = stub.JobQueueSizeRequested(processor_pb2.Empty()) 
        print "processor : " + processor_ip +" , current job queue size: " + str(response.job_queue_size)
        processor_stub_list.append([processor_ip, processor_port, stub])
      except:
        print "processor : " + processor_ip + " !! cannot be connected"
    print "currently processor slaves are:"
    print processor_stub_list

class LoadBalancer(lb_pb2_grpc.LoadBalancerServicer):

    def OnServerRequested(self, request, context):
        print 'got minumum load server requested'
        min_load_ip= 'None'
        min_load = sys.maxint
        for each_stub in processor_stub_list:
          stub = each_stub[2]
          try:
            response = stub.JobQueueSizeRequested(processor_pb2.Empty())
            if response.job_queue_size <  min_load:
              min_load = response.job_queue_size
              min_load_ip = each_stub[0]
          except:
            print "processor : " + each_stub[0] + " !! cannot be connected"
        print 'selected server is : '+ min_load_ip +' ,  load is: '+ str(min_load)
        return lb_pb2.SelectedServer(server_addr = min_load_ip)



def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    lb_pb2_grpc.add_LoadBalancerServicer_to_server(LoadBalancer(), server)
    server.add_insecure_port('[::]:9696')
    server.start()
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()
