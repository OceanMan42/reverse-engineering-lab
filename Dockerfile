FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential binutils file gdb python3 less \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /lab
COPY . /lab
RUN make build

CMD ["bash"]
