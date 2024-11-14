FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir -p /mnt/fuse \
    && apt-get update && apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common \
        fuse \
        libfuse2 \
        python3-pip \
        strace \
        crun \
        jq \
        fuse-overlayfs \
    && echo "tzdata tzdata/Areas select Etc" | debconf-set-selections \
    && echo "tzdata tzdata/Zones/Etc select UTC" | debconf-set-selections \
    && apt-get install -y tzdata \
    && curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh \
    && curl -fsSL https://code-server.dev/install.sh | sh \
    && pip install fusepy

EXPOSE 8081

CMD ["code-server", "--bind-addr", "0.0.0.0:8081", "--auth", "none"]

# docker build -f workenv.Dockerfile -t linux_dev .
# docker run -d --privileged --device /dev/fuse -p 8081:8081 -v /var/run/docker.sock:/var/run/docker.sock -v $(pwd):/home/coder/project --name ubuntu linux_dev