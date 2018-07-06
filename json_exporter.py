#!/usr/bin/python

## Python JSON Exporter for Prometheus v1.4.0
##
## (C) 2018 Dewangga Alam <dewangga.alam@bukalapak.com>
##
## PoC for IDNOG05, use case: BukaLapak System & Network Environment 


from prometheus_client import start_http_server, Metric, REGISTRY
from ripe.atlas.cousteau import Probe, Measurement
from argparse import RawTextHelpFormatter
from version import __version__
from ConfigParser import SafeConfigParser

import json
import requests
import sys
import time
import argparse
import requests_cache
import itertools
import base64
import dns.message
import re

__version_info__ = ('v1','4','0')
__version__ = '.'.join(__version_info__)

def get_args():
  parser = argparse.ArgumentParser(description='RIPE Atlas JSON Parser for Prometheus\nCreated with love and without warranty :-)', formatter_class=RawTextHelpFormatter)
  parser.add_argument('-m','--measurement', 
  help='Select available measurements (required)\n' 
             '"ping", "traceroute", "dns", "ssl"', 
  required=True)
  parser.add_argument('-p','--port', 
  help='Specify listen port\n'
       'ping \t\t(default: tcp/7979)\n'
       'traceroute \t(default: tcp/7980)\n'
       'dns \t\t(default: tcp/7981)\n'
       'ssl \t\t(default: tcp/7982)\n',
  required=False)
  parser.add_argument('-M', '--metrics',
  help='Specify metrics name', required=True)
  parser.add_argument('--ipaddr', 
  help='Specify listen ip address (default: 127.0.0.1)', 
  default='127.0.0.1' )
  parser.add_argument('-e','--endpoint', 
  help='Specify measurements URI from RIPE Atlas Endpoint (required)', 
  required=True)
  parser.add_argument('-v', '--version', help='Print apps version', action='version', version='%(prog)s ' + __version__)
  args = parser.parse_args()

  msm = args.measurement
  port = args.port
  endpoint = args.endpoint
  ipaddr = args.ipaddr
  metrics = args.metrics
  
  return msm, port, endpoint, ipaddr, metrics

class DictQuery(dict):
    def get(self, path, default = None):
        keys = path.split("/")
        val = None

        for key in keys:
            if val:
                if isinstance(val, list):
                    val = [ v.get(key, default) if v else None for v in val]
                else:
                    val = val.get(key, default)
            else:
                val = dict.get(self, key, default)

            if not val:
                break;

        return val

# We cache a response
requests_cache.install_cache('ripe_query_cache', backend='sqlite', expire_after=60)

class JsonCollector(object):
  msm, port, endpoint, ipaddr, metrics = get_args()
  def __init__(self, endpoint):
    self._endpoint = endpoint
  def collect(self):

    response = json.loads(requests.get('https://atlas.ripe.net/api/v2/measurements/{}/latest?format=json'.format(endpoint)).content.decode('UTF-8'))  
    chk_stats = json.loads(requests.get('https://atlas.ripe.net/api/v2/measurements/{}/status-check?format=json'.format(endpoint)).content.decode('UTF-8'))
    prb_stats = json.loads(requests.get('https://atlas.ripe.net/api/v2/probes/{}?format=json'.format(endpoint)).content.decode('UTF-8'))

    # DNS msm
    if (msm == 'dns'):
      for item in response:
        af = item.get('af')
        probes = item.get('prb_id')
        src_addr = item.get('from')
        dns_rt = DictQuery(item).get('resultset/result/rt')
        dns_ip = DictQuery(item).get('resultset/dst_addr')
        dns_port = DictQuery(item).get('resultset/dst_port')

        dns_response_enc = DictQuery(item).get('resultset/result/abuf')
        print dns_response_enc
        dns_response_dec = str(dns.message.from_wire(base64.b64decode(dns_response_enc[0])))
        dns_results = re.findall(r"[0-9]+(?:\.[0-9]+){1,3}",dns_response_dec)
        dns_domain = re.findall(r"\b(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)+[a-z]{2,}\b",dns_response_dec,re.M)
        try:
          metric = Metric(metrics, 'DNS Measurement', 'summary')
          metric.add_sample(metrics, value=float(dns_rt[0]),
            labels={'prb_id': repr(probes),
                    'src_addr': src_addr,
                    'af': repr(af), 
                    'dns_ip': dns_ip[0],
                    'dns_response': dns_results[0]
            })
          yield metric
          pass
        except None:
          continue
    
    # HTTPS msm
    elif (msm == 'ssl'):
      # SSL msm
      for item in response:
        af = item.get('af')
        probes = item.get('prb_id')
        src_addr = item.get('from')
        round_trip = item.get('rt')
        check_type = item.get('type')
        dst_name = item.get('dst_name')
        
        try:
          metric = Metric(metrics, 'Probes SSL', 'summary')
          metric.add_sample(metrics, value=float(round_trip), 
            labels={'prb_id': repr(probes),
                    'src_addr': src_addr,
                    'dst_name': dst_name, 
                    'af': repr(af), 
                    'type': check_type 
            })
          yield metric
          pass
        except:
          continue

    # Traceroute msm
    elif (msm == 'traceroute'):
      for item in response:
        probes = item.get('prb_id')
        src_addr = item.get('from')
        trace = DictQuery(item).get("result/hop")
        trace_inms = DictQuery(item).get('result/result')
        for result in trace_inms:
      #print (result.get('rtt')[-1])
      # print result[2] 
        #print "Trace msm from {} id {} are {} hops ({}) ms".format(src_addr, probes, trace[-1], )
          metric = Metric(metrics, 'Probes Traceroute', 'summary')
          metric.add_sample(metrics, value=int(last_latency[-1]), 
            labels={'prb_id': repr(probes), 
                    'src_addr': src_addr, 
                    'type': check_type 
                   })
          yield metric 

    # Ping msm
    elif (msm == 'ping'):
      for item in response:
        af = item.get('af')
        probes = item.get('prb_id')
        src_addr = item.get('from')
        last_latency = DictQuery(item).get("result/rtt")
        check_type = item.get('type')
        proto = item.get('proto')
        dst_name = item.get('dst_name')
        prb_id = Probe(id=probes)

        try:
          metric = Metric(metrics, 'Probes ID', 'summary')
          metric.add_sample(metrics, value=float(last_latency[-1]), 
            labels={'prb_id': repr(probes),
                    'src_addr': src_addr,
                    'asn_v4': repr(prb_id.asn_v4), 
                    'dst_name': dst_name, 
                    'af': repr(af),
                    'proto': proto,
                    'type': check_type 
            })
          yield metric
          pass
        except:
          continue
    else:
        sys.exit("No measurements type defined")

if  __name__ == '__main__':
    msm, port, endpoint, ipaddr, metrics = get_args()

    # Listen on specified port
    if port:
        start_http_server(int(port), ipaddr)
    elif (msm == 'ping'):
        start_http_server(int(7979), ipaddr)
    elif (msm == 'dns'):
        start_http_server(int(7980), ipaddr)
    elif (msm == 'ssl'):
        start_http_server(int(7983), ipaddr)
    else:
       sys.exit('Unknown argument, it\'s a bug.')

    # Endpoint URL from RIPE Atlas
    REGISTRY.register(JsonCollector(endpoint))
    while True: time.sleep(1)
