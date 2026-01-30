ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-pip
# Installiamo websockets per parlare con il cuore di HA
RUN pip install flask requests websockets --break-system-packages

COPY app.py /app.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
