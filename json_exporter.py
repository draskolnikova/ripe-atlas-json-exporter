#!/usr/bin/python

## Python JSON Exporter for Prometheus v1.4.1
##
## (C) 2018 Dewangga Alam <dewangga.alam@bukalapak.com>
##
## PoC for IDNOG05, use case: BukaLapak System & Network Environment 
## 

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

__version_info__ = ('v1','4','1')
__version__ = '.'.join(__version_info__)

# Arguments to be used in the command line
def get_args():
  parser = argparse.ArgumentParser(description='RIPE Atlas JSON Parser for Prometheus\nCreated with love and without warranty :-)', formatter_class=RawTextHelpFormatter)
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
  parser.add_argument('-id','--msmid', 
  help='Specify measurements ID from RIPE Atlas Endpoint (required)', 
  required=True)
  parser.add_argument('-v', '--version', help='Print apps version', action='version', version='%(prog)s ' + __version__)
  args = parser.parse_args()

  port = args.port
  msmid = args.msmid
  ipaddr = args.ipaddr
  metrics = args.metrics
  
  return port, msmid, ipaddr, metrics

# Auto discovery of measurement type from ID  
def get_msm():
  port, msmid, ipaddr, metrics = get_args()

  uri1 = "https://atlas.ripe.net/api/v2/measurements/"
  uri2 = "/latest?format=json"	
  response = json.loads(requests.get(uri1+msmid+uri2.format(msmid)).content.decode('UTF-8'))
  for item in response:
    msm_name = item.get('msm_name')
  if (msm_name == 'Ping'):
    msm = "ping"
  elif (msm_name == 'Traceroute'):
    msm = "traceroute"
  elif (msm_name == 'Tdig'):
    msm = "dns"
  elif (msm_name == 'SSLCert'):
    msm = "ssl"
  return msm

# Making dictionary from JSON value array
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

# JSON collector
class JsonCollector(object):
  port, msmid, ipaddr, metrics = get_args()
  msm = get_msm()

  def __init__(self, msmid):
    self._msmid = msmid

  def collect(self):
    
    uri1 = "https://atlas.ripe.net/api/v2/measurements/"
    uri2 = "/latest?format=json"
    uri3 = "/status-check?format=json"
    uri4 = "?format=json"
    r = requests.get(uri1+msmid+uri2)	
    response = json.loads(requests.get(uri1+msmid+uri2.format(msmid)).content.decode('UTF-8'))
    chk_stats = json.loads(requests.get(uri1+msmid+uri3.format(msmid)).content.decode('UTF-8'))
    prb_stats = json.loads(requests.get(uri1+msmid+uri4.format(msmid)).content.decode('UTF-8'))

    # return error if endpoint is unreachable
    if r.status_code == 404:
	sys.exit("Endpoint unreachable: Error 404 ")

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
        print (dns_response_enc)
        dns_response_dec = str(dns.message.from_wire(base64.b64decode(dns_response_enc[0])))
        dns_results = re.findall(r"[0-9]+(?:\.[0-9]+){1,3}",dns_response_dec)
        dns_domain = re.findall(r"\b(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)+[a-z]{2,}\b",dns_response_dec,re.M)

	# adding metric to Prometheus
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
    
    # SSL msm
    elif (msm == 'ssl'):
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

    # Traceroute hopcount msm
    elif (msm == 'traceroute'):
      for item in response:
        probes = item.get('prb_id')
        src_addr = item.get('from')
        af = item.get('af')
        hops = DictQuery(item).get("result/hop")
	check_type = item.get('type')
        prb_id = Probe(id=probes)

        try:
          metric = Metric(metrics, 'Probes Traceroute Hopcount', 'summary')
          metric.add_sample(metrics, value=int(hops[-1]), 
            labels={'prb_id': repr(probes), 
                    'src_addr': src_addr, 
                    'af': repr(af),
                    'type': check_type 
                   })
          yield metric 
          pass
        except:
          continue

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
    port, msmid, ipaddr, metrics = get_args()
    msm = get_msm()
    
    # Listen on specified port
    if port:
        start_http_server(int(port), ipaddr)
        print "Started prometheus server on " + ipaddr + ":" + port
    elif (msm == 'ping'):
        start_http_server(int(7979), ipaddr)
        print "Started prometheus server on " + ipaddr + ":7979" 
    elif (msm == 'dns'):
        start_http_server(int(7980), ipaddr)
        print "Started prometheus server on " + ipaddr + ":7980"
    elif (msm == 'ssl'):
        start_http_server(int(7983), ipaddr)
        print "Started prometheus server on " + ipaddr + ":7983"
    elif (msm == 'traceroute'):
   	start_http_server(int(7981), ipaddr)
        print "Started prometheus server on " + ipaddr + ":7981" 
    else:
      sys.exit('Unknown argument, it\'s a bug.')

    # Endpoint URL from RIPE Atlas
    REGISTRY.register(JsonCollector(msmid))
    while True: time.sleep(1)
