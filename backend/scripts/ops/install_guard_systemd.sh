#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-/opt/talentflow/backend/scripts/ops}"
PY_BIN="${PY_BIN:-/usr/bin/python3}"

install_unit() {
  local name="$1"
  local content="$2"
  printf "%s\n" "$content" | sudo tee "/etc/systemd/system/$name" >/dev/null
}

install_unit "tf-guard-probe-critical.service" "[Unit]
Description=TalentFlow Guard Probe Critical
After=network-online.target
[Service]
Type=oneshot
EnvironmentFile=-/etc/talentflow/runtime.env
WorkingDirectory=${ROOT_DIR}
ExecStart=${PY_BIN} ${ROOT_DIR}/tf_guard_agent.py probe-critical
"

install_unit "tf-guard-probe-full.service" "[Unit]
Description=TalentFlow Guard Probe Full
After=network-online.target
[Service]
Type=oneshot
EnvironmentFile=-/etc/talentflow/runtime.env
WorkingDirectory=${ROOT_DIR}
ExecStart=${PY_BIN} ${ROOT_DIR}/tf_guard_agent.py probe-full
"

install_unit "tf-guard-decision.service" "[Unit]
Description=TalentFlow Guard Decision
After=network-online.target
[Service]
Type=oneshot
EnvironmentFile=-/etc/talentflow/runtime.env
WorkingDirectory=${ROOT_DIR}
ExecStart=${PY_BIN} ${ROOT_DIR}/tf_guard_agent.py decide
"

install_unit "tf-guard-digest.service" "[Unit]
Description=TalentFlow Guard Digest
After=network-online.target
[Service]
Type=oneshot
EnvironmentFile=-/etc/talentflow/runtime.env
WorkingDirectory=${ROOT_DIR}
ExecStart=${PY_BIN} ${ROOT_DIR}/tf_guard_agent.py digest
"

install_unit "tf-guard-probe-critical.timer" "[Unit]
Description=Run guard critical probe every 5 minutes
[Timer]
OnCalendar=*:0/5
Persistent=false
Unit=tf-guard-probe-critical.service
[Install]
WantedBy=timers.target
"

install_unit "tf-guard-probe-full.timer" "[Unit]
Description=Run guard full probe every 30 minutes
[Timer]
OnCalendar=*:0/30
Persistent=false
Unit=tf-guard-probe-full.service
[Install]
WantedBy=timers.target
"

install_unit "tf-guard-decision.timer" "[Unit]
Description=Run guard decision every 5 minutes
[Timer]
OnCalendar=*:1/5
Persistent=false
Unit=tf-guard-decision.service
[Install]
WantedBy=timers.target
"

install_unit "tf-guard-digest.timer" "[Unit]
Description=Run guard digest hourly
[Timer]
OnCalendar=hourly
Persistent=false
Unit=tf-guard-digest.service
[Install]
WantedBy=timers.target
"

sudo systemctl daemon-reload
sudo systemctl enable --now tf-guard-probe-critical.timer tf-guard-probe-full.timer tf-guard-decision.timer tf-guard-digest.timer
sudo systemctl list-timers --all | grep tf-guard || true
echo "Guard timers installed."

