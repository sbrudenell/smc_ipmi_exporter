import logging
import re
import xml.etree.ElementTree as ET

import prometheus_client
import requests


class Collector(object):

    def __init__(self, address, username, password, **kwargs):
        self.address = address
        self.username = username
        self.password = password
        self._prefix = "smc_"
        self.s = requests.Session()
        self.kwargs = kwargs

    def headerify(self, text):
        text = text.strip().lower()
        text = re.sub(r"[^a-z0-9]", "_", text)
        return text

    def post(self, path, *args, **kwargs):
        url = self.address + path
        kwargs.update(self.kwargs)
        return self.s.post(url, *args, **kwargs)

    def login(self):
        r = self.post(
            "/cgi/login.cgi", data=dict(name=self.username, pwd=self.password))
        return r

    def call(self, op):
        tries = 0
        while tries < 3:
            tries += 1
            r = self.post("/cgi/ipmi.cgi", data=dict(op=op))
            r.raise_for_status()
            try:
                return ET.fromstring(r.text)
            except ET.ParseError:
                pass
            logging.info("calling %s seems to have failed, trying login", op)
            self.login().raise_for_status()
        else:
            assert False, "%s failed repeatedly" % op

    def make_metric(self, _is_counter, _name, _documentation, _value,
                    **_labels):
        _name = self._prefix + _name
        if _is_counter:
            cls = prometheus_client.core.CounterMetricFamily
        else:
            cls = prometheus_client.core.GaugeMetricFamily
        label_names = list(_labels.keys())
        metric = cls(
            _name, _documentation or "No Documentation", labels=label_names)
        metric.add_metric([str(_labels[k]) for k in label_names], _value)
        return metric

    def collect_psinfo(self):
        metrics = []
        root = self.call("Get_PSInfoReadings.XML")
        prefix = "psinfo_"
        for index, psitem in enumerate(root.findall(".//PSItem")):
            attrib = dict(psitem.attrib)
            status = int(attrib.pop("a_b_PS_Status_I2C"), 16)
            if status == 255:
                continue
            labels = {"ps": index}
            name = attrib.pop("name", None)
            ps_type = attrib.pop("psType", None)
            if name:
                labels["name"] = name
            if ps_type:
                labels["ps_type"] = int(ps_type, 16)
            metrics.append(self.make_metric(
                False, prefix + "status", None, 1, status=status, **labels))
            for k, v in attrib.items():
                metric_labels = dict(labels)
                m = re.match("^(.+)(\d+)$", k)
                if m:
                    k = m.group(1)
                    metric_labels[k] = m.group(2)
                v = int(v, 16)
                metrics.append(self.make_metric(
                    False, prefix + k, None, v, **metric_labels))
        return metrics

    def collect(self):
        metrics = []

        metrics.extend(self.collect_psinfo())

        return metrics
