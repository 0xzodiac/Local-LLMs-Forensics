#!/usr/bin/env bash
# 02_install_prereqs.sh -- install the system dependencies the experiments
# need. Written for apt-based distros (original host: Ubuntu + WSL2-era setup);
# adapt the package names on other families.
set -u
sudo apt-get update -qq
sudo apt-get install -y \
  build-essential cmake curl git python3 python3-pip \
  tcpdump tshark jq tmux \
  iproute2 iptables iputils-ping dnsutils \
  libcurl4-openssl-dev
echo "[prereqs] installed. Re-run 00_check_env.sh to verify."
