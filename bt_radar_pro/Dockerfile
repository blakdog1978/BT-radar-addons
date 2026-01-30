ARG BUILD_FROM
FROM $BUILD_FROM

# Installiamo le dipendenze di sistema per il Bluetooth
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bluez \
    dbus

# Installiamo le librerie Python
RUN pip install flask requests bleak --break-system-packages

COPY app.py /app.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
