FROM ubuntu:22.04

RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /foxmq

COPY foxmq ./foxmq
COPY foxmq.d ./foxmq.d

RUN chmod +x ./foxmq

EXPOSE 1883
EXPOSE 19793/udp

ENV RUST_LOG=foxmq=info

CMD ["./foxmq", "run", \
     "--secret-key-file=foxmq.d/key_0.pem", \
     "--mqtt-addr=0.0.0.0:1883", \
     "--cluster-addr=0.0.0.0:19793"]
