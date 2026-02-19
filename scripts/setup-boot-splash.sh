#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THEME_NAME="silicon-or-soul"
THEME_SRC_DIR="${ROOT_DIR}/deploy/plymouth/${THEME_NAME}"
THEME_DST_DIR="/usr/share/plymouth/themes/${THEME_NAME}"
BACKUP_DIR="/etc/silicon-or-soul/boot-backups"

if [[ ! -d "${THEME_SRC_DIR}" ]]; then
  echo "Theme source not found: ${THEME_SRC_DIR}" >&2
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

BOOT_ROOT="/boot/firmware"
if [[ ! -f "${BOOT_ROOT}/cmdline.txt" ]]; then
  BOOT_ROOT="/boot"
fi
CMDLINE_FILE="${BOOT_ROOT}/cmdline.txt"
CONFIG_FILE="${BOOT_ROOT}/config.txt"

if [[ ! -f "${CMDLINE_FILE}" ]]; then
  echo "Could not find cmdline.txt under /boot/firmware or /boot." >&2
  exit 1
fi

${SUDO} apt-get update
${SUDO} apt-get install -y plymouth plymouth-themes

${SUDO} install -d -m 0755 "${THEME_DST_DIR}"
${SUDO} install -m 0644 "${THEME_SRC_DIR}/${THEME_NAME}.plymouth" "${THEME_DST_DIR}/${THEME_NAME}.plymouth"
${SUDO} install -m 0644 "${THEME_SRC_DIR}/${THEME_NAME}.script" "${THEME_DST_DIR}/${THEME_NAME}.script"

${SUDO} install -d -m 0755 "${BACKUP_DIR}"
if [[ ! -f "${BACKUP_DIR}/cmdline.txt.bak" ]]; then
  ${SUDO} cp "${CMDLINE_FILE}" "${BACKUP_DIR}/cmdline.txt.bak"
fi
if [[ -f "${CONFIG_FILE}" ]] && [[ ! -f "${BACKUP_DIR}/config.txt.bak" ]]; then
  ${SUDO} cp "${CONFIG_FILE}" "${BACKUP_DIR}/config.txt.bak"
fi

${SUDO} python3 - <<'PY'
from pathlib import Path

paths = [Path("/boot/firmware/cmdline.txt"), Path("/boot/cmdline.txt")]
cmdline = next((p for p in paths if p.exists()), None)
if cmdline is None:
    raise SystemExit("cmdline.txt not found")

content = cmdline.read_text(encoding="utf-8").strip()
tokens = [tok for tok in content.split() if tok]

required = ["quiet", "splash", "plymouth.ignore-serial-consoles", "loglevel=3", "vt.global_cursor_default=0", "logo.nologo"]
for token in required:
    if token not in tokens:
        tokens.append(token)

for noisy in ("plymouth.enable=0",):
    tokens = [t for t in tokens if t != noisy]

cmdline.write_text(" ".join(tokens) + "\n", encoding="utf-8")
PY

if [[ -f "${CONFIG_FILE}" ]]; then
  if ${SUDO} grep -q '^disable_splash=' "${CONFIG_FILE}"; then
    ${SUDO} sed -i 's/^disable_splash=.*/disable_splash=1/' "${CONFIG_FILE}"
  else
    echo "disable_splash=1" | ${SUDO} tee -a "${CONFIG_FILE}" >/dev/null
  fi
fi

if command -v plymouth-set-default-theme >/dev/null 2>&1; then
  ${SUDO} plymouth-set-default-theme -R "${THEME_NAME}"
else
  echo "plymouth-set-default-theme not found; trying update-initramfs directly."
  ${SUDO} update-initramfs -u
fi

echo "Boot splash configured."
echo "Reboot to verify: sudo reboot"
