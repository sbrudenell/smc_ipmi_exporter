FROM python:3-slim

COPY . /src

RUN pip install --upgrade /src && \
    cp /usr/local/bin/smc_ipmi_exporter /smc_ipmi_exporter

EXPOSE 9795

VOLUME /config.json
ENTRYPOINT ["/smc_ipmi_exporter"]
CMD ["--config", "/config.json"]
