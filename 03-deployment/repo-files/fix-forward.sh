#!/usr/bin/env bash
# Re-apply Docker bridge forwarding on hosts where a security suite sets
# FORWARD policy DROP and leaves bridge traffic unmatched (symptom:
# "Empty reply from server" on published ports, exit=28 direct to container
# IP). Idempotent-ish: safe to re-run; rules stack at the top of FORWARD.
# Needed again after: reboot, docker daemon restart, security-suite re-flush,
# and after Compose/kind create NEW bridges (br-…)—those are covered by br+.
set -euo pipefail

sudo iptables -P FORWARD ACCEPT
for iface in docker0 br+ veth+; do
  sudo iptables -I FORWARD 1 -i "$iface" -j ACCEPT
  sudo iptables -I FORWARD 1 -o "$iface" -j ACCEPT
done

echo "--- FORWARD head now: ---"
sudo iptables -L FORWARD -n | head -16

