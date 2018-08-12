import argparse
import http.server
import json
import logging
import sys

import prometheus_client

import smc_ipmi_exporter


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    parser = argparse.ArgumentParser("SMC IPMI Exporter")

    parser.add_argument("--port", type=int, default=9795)
    parser.add_argument("--bind_address", default="0.0.0.0")
    parser.add_argument("--config", required=True, type=argparse.FileType("r"))
    parser.add_argument("--no_verify", action="store_false", dest="verify")

    args = parser.parse_args()

    config = json.load(args.config)

    collector = smc_ipmi_exporter.Collector(
        config["address"], config["username"], config["password"],
        verify=args.verify)

    prometheus_client.REGISTRY.register(collector)

    handler = prometheus_client.MetricsHandler.factory(
            prometheus_client.REGISTRY)
    server = http.server.HTTPServer(
            (args.bind_address, args.port), handler)
    server.serve_forever()
