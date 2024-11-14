#!/bin/bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker ubuntu
sudo systemctl enable docker
sudo systemctl start docker

sudo mkdir -p /mnt/fuse \
    && sudo apt-get update && sudo apt-get install -y \
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
        tzdata \
    && echo "tzdata tzdata/Areas select Etc" | debconf-set-selections \
    && echo "tzdata tzdata/Zones/Etc select UTC" | debconf-set-selections \
    && curl -fsSL https://code-server.dev/install.sh | sh \
    && pip install fusepy

code-server --bind-addr 0.0.0.0:8081 --auth none