#!/bin/bash

(type -p wget >/dev/null || (apt update && apt-get install wget -y)) &&
  mkdir -p /etc/apt/keyrings &&
  chmod 0755 /etc/apt/keyrings &&
  out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg &&
  cat $out | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null &&
  rm -f "$out" &&
  chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg &&
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null &&
  apt update &&
  apt install gh -y

apt update -y
apt install gh -y
gh auth login --with-token <GH_token.txt
