#!/usr/bin/env bash
set -euo pipefail

THEME_NAME="silicon-or-soul"
THEME_DST_DIR="/usr/share/plymouth/themes/${THEME_NAME}"
BACKUP_DIR="/etc/silicon-or-soul/boot-backups"

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

BOOT_ROOT="/boot/firmware"
if [[ ! -f "${BOOT_ROOT}/cmdline.txt" ]]; then
  BOOT_ROOT="/boot"
fi
CMDLINE_FILE="${BOOT_ROOT}/cmdline.txt"
CONFIG_FILE="${BOOT_ROOT}/config.txt"

if [[ -f "${BACKUP_DIR}/cmdline.txt.bak" ]]; then
  ${SUDO} cp "${BACKUP_DIR}/cmdline.txt.bak" "${CMDLINE_FILE}"
else
  echo "No cmdline backup found; leaving ${CMDLINE_FILE} unchanged."
fi

if [[ -f "${CONFIG_FILE}" ]] && [[ -f "${BACKUP_DIR}/config.txt.bak" ]]; then
  ${SUDO} cp "${BACKUP_DIR}/config.txt.bak" "${CONFIG_FILE}"
fi

if command -v plymouth-set-default-theme >/dev/null 2>&1; then
  ${SUDO} plymouth-set-default-theme -R spinner
else
  ${SUDO} update-initramfs -u
fi

${SUDO} rm -rf "${THEME_DST_DIR}"

echo "Boot splash changes reverted."
echo "Reboot to verify: sudo reboot"
