ARG BUILD_FROM
FROM $BUILD_FROM

# Installiamo Python e i pacchetti per l'interfaccia web
RUN apk add --no-cache python3 py3-pip
RUN pip install flask requests --break-system-packages

# Copiamo i file dell'app
COPY app.py /app.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
