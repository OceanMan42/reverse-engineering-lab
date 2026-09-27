FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3

LABEL org.opencontainers.image.source="https://github.com/OceanMan42/reverse-engineering-lab"

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

# Install from a dated archive snapshot so a rebuild gets the same gcc,
# binutils and gdb as the published captures. Re-capture after bumping it.
# snapshot.ubuntu.com is HTTPS-only, so CA certificates come first, from
# the regular archive (they do not affect the toolchain).
ARG APT_SNAPSHOT=20260927T000000Z

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && apt-get update --snapshot "$APT_SNAPSHOT" \
    && apt-get install -y --no-install-recommends --snapshot "$APT_SNAPSHOT" \
       build-essential binutils file gdb python3 less \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /lab
COPY . /lab
RUN make build

CMD ["bash"]
