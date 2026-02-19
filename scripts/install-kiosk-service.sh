#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_NAME="silicon-or-soul.service"
UNIT_SRC="${ROOT_DIR}/deploy/systemd/${UNIT_NAME}"
UNIT_DST="/etc/systemd/system/${UNIT_NAME}"

if [[ ! -f "${UNIT_SRC}" ]]; then
  echo "Unit file not found: ${UNIT_SRC}" >&2
  exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "Run as root or install sudo." >&2
    exit 1
  fi
else
  SUDO=""
fi

${SUDO} install -D -m 0644 "${UNIT_SRC}" "${UNIT_DST}"
${SUDO} systemctl daemon-reload
${SUDO} systemctl enable --now "${UNIT_NAME}"

if [[ "${DISABLE_GETTY_TTY1:-0}" == "1" ]]; then
  ${SUDO} systemctl disable --now getty@tty1.service
fi

echo "Installed and started ${UNIT_NAME}."
echo "Check status with: ${SUDO} systemctl status ${UNIT_NAME} --no-pager"
