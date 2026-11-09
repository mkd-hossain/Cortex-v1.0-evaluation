#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/cortex-benchmark"
before=$(systemctl --user show cortex-benchmark.service -p MainPID --value)
cp --update=none "$HOME/.config/systemd/user/cortex-benchmark-public.service" cortex-public-before-redesign.service
cp cortex-dashboard-public.service "$HOME/.config/systemd/user/cortex-benchmark-public.service"
systemctl --user daemon-reload
systemctl --user restart cortex-benchmark-public.service
sudo -n tailscale serve --bg --yes --https=8443 http://127.0.0.1:8767
after=$(systemctl --user show cortex-benchmark.service -p MainPID --value)
test "$before" = "$after"
echo "Benchmark controller unchanged: $after"
systemctl --user stop cortex-dashboard-preview.service
echo DASHBOARD_DEPLOYED
