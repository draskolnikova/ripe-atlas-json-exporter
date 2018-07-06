# Prometheus JSON Exporter for RIPE Atlas

## Changelog
Please see [CHANGELOG](CHANGELOG) URI.

## Description

A [prometheus](https://prometheus.io/) exporter which scrapes remote JSON by JSONPath.

Inspired from [prometheus-json-exporter using Go](https://github.com/kawamuray/prometheus-json-exporter), rewrite in simple way using Python.

## How to Use

## Build
### Cent OS 7
```bash
$ git clone https://github.com/draskolnikova/ripe-atlas-json-exporter
$ cd ripe-atlas-json-exporter
$ sudo yum install python-pip
$ sudo pip install -r requirements.txt
$ chmod +x json_exporter.py
```

### Fedora
```bash
$ git clone https://github.com/draskolnikova/ripe-atlas-json-exporter
$ cd ripe-atlas-json-exporter
$ sudo yum install python-pip
$ sudo pip install -r requirements.txt
$ chmod +x json_exporter.py
```

## Usage

Fetch from RIPE Atlas endpoint, for example we fetch [latest measurement](https://atlas.ripe.net/api/v2/measurements/11154937/latest/?format=json).

|:Property:                 |:Description:|
|---------------------------|----------------------------------------|
|`-m`, `--measurements` *(string, required: **yes**)* | `ping` - ping measurements             |
|                           | `traceroute` - traceroute measurements |
|                           | `dns` - dns measurement                |
|                           | `ssl` - ssl measurement                |
|`-M`, `--metrics` *(string, required: **yes**)* | your defined metrics name in prometheus | 
|`-p` *(integer, required: **no**)* | allow the apps listen to port  |
|                           | `ping` (default: tcp/7979)             |
|                           | `traceroute` (default: tcp/7980) *experimental*       |
|                           | `dns` (default: tcp/7981)              |
|                           | `ssl` (default: tcp/7982)              |
|`-e`, `--endpoint` *(string, required: **yes**)* | uri from atlas restful api     |
|`--ipaddr` *(ip, required: **no**)*| allow the apps bind to ip (default: 127.0.0.1) |
|`-v`                       | print version and exit                 |
|`-h`                       | print help and exit                    |

`$ curl https://atlas.ripe.net/api/v2/measurements/11154937/latest/?format=json`

```json
[
  {
    "af": 4,
    "prb_id": 18845,
    "result": [
      {
        "rtt": 398.21054
      },
      {
        "rtt": 17.43532
      },
      {
        "rtt": 15.80598
      }
    ],
    "ttl": 54,
    "avg": 143.81728,
    "size": 48,
    "from": "36.74.50.189",
    "proto": "ICMP",
    "timestamp": 1517996057,
    "dup": 0,
    "type": "ping",
    "sent": 3,
    "msm_id": 11154937,
    "fw": 4900,
    "max": 398.21054,
    "step": 240,
    "src_addr": "10.120.5.154",
    "rcvd": 3,
    "msm_name": "Ping",
    "lts": 40,
    "dst_name": "103.64.14.21",
    "min": 15.80598,
    "stored_timestamp": 1517996127,
    "group_id": 11154937,
    "dst_addr": "103.64.14.21"
  },
  {
    "af": 4,
    "prb_id": 6261,
    "result": [
      {
        "rtt": 18.318281
      },
      {
        "rtt": 18.309326
      },
      {
        "rtt": 18.328688
      }
    ],
    "ttl": 55,
    "avg": 18.318765,
    "size": 48,
    "from": "103.20.91.47",
    "proto": "ICMP",
    "timestamp": 1517996005,
    "dup": 0,
    "type": "ping",
    "sent": 3,
    "msm_id": 11154937,
    "fw": 4900,
    "max": 18.328688,
    "step": 240,
    "src_addr": "103.20.91.47",
    "rcvd": 3,
    "msm_name": "Ping",
    "lts": 252,
    "dst_name": "103.64.14.21",
    "min": 18.309326,
    "stored_timestamp": 1517996098,
    "group_id": 11154937,
    "dst_addr": "103.64.14.21"
  }
]
```

## TO DO
* Traceroute measurements
* Auto discovery by measurements ID
* Run over IPv6
* Feel free to fork and send PR :-)
