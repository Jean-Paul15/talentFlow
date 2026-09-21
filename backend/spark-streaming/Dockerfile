FROM apache/spark:3.5.1-python3

USER root

WORKDIR /app

COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY stream_to_minio.py ./

USER spark

CMD ["spark-submit", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1", "/app/stream_to_minio.py"]
