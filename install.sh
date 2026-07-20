#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "錯誤：$*" >&2
  exit 1
}

info() {
  echo "$*"
}

have() {
  command -v "$1" >/dev/null 2>&1
}

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install_dir="${GITMIND_BIN_DIR:-${GMIND_BIN_DIR:-${HOME}/.local/bin}}"
codex_skill_dir="${GITMIND_CODEX_SKILL_DIR:-${GMIND_CODEX_SKILL_DIR:-${HOME}/.agents/skills/gitmind}}"
claude_skill_dir="${GITMIND_CLAUDE_SKILL_DIR:-${GMIND_CLAUDE_SKILL_DIR:-${HOME}/.claude/skills/gitmind}}"
legacy_codex_skill_dir="${HOME}/.agents/skills/gmind"
legacy_claude_skill_dir="${HOME}/.claude/skills/gmind"

info "檢查 GitMind CLI 安裝環境..."

[ -f "${repo_dir}/pyproject.toml" ] || fail "請在解壓縮後的 GitMind CLI 專案資料夾裡執行 install.sh。"

if ! have uv; then
  if [ "${GITMIND_AUTO_INSTALL_UV:-${GMIND_AUTO_INSTALL_UV:-1}}" = "0" ]; then
    fail "找不到 uv。請先安裝 uv，或移除 GITMIND_AUTO_INSTALL_UV=0 後讓本腳本自動安裝。"
  fi
  have curl || fail "找不到 uv，也找不到 curl，無法自動下載 uv。請先安裝 curl 或 uv 後再重跑。"
  info "找不到 uv，開始自動安裝 uv..."
  uv_install_log="$(mktemp)"
  if ! (curl -LsSf https://astral.sh/uv/install.sh | sh) >"$uv_install_log" 2>&1; then
    echo "uv 自動安裝失敗，安裝器輸出如下：" >&2
    sed -n '1,160p' "$uv_install_log" >&2
    exit 1
  fi
  rm -f "$uv_install_log"
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  have uv || fail "uv 安裝後仍然不在 PATH。請開新終端機後重跑 bash install.sh。"
  info "uv 已自動安裝完成。"
fi

uv_bin="$(command -v uv)"

info "確認 Python 3.10+ 可用；如果沒有，uv 會自動安裝 managed Python..."
if ! "$uv_bin" run --project "$repo_dir" python - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  info "目前找不到可用的 Python 3.10+，開始用 uv 安裝 Python 3.12..."
  python_install_log="$(mktemp)"
  if ! "$uv_bin" python install 3.12 >"$python_install_log" 2>&1; then
    echo "Python 自動安裝失敗，uv 輸出如下：" >&2
    sed -n '1,160p' "$python_install_log" >&2
    exit 1
  fi
  rm -f "$python_install_log"
fi

python_version="$("$uv_bin" run --project "$repo_dir" python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
)" || fail "Python 3.10+ 準備失敗。請確認網路可用後重跑 bash install.sh。"

if [ "$(uname -s)" != "Darwin" ]; then
  info "提醒：自動擷取瀏覽器登入 session 目前主要測試在 macOS 的 Chromium profile。"
  info "其他系統仍可使用手動 token 設定：gitmind auth set-token"
fi

info "使用 uv：${uv_bin}"
info "使用 Python：${python_version}"

mkdir -p "$install_dir"

cat > "${install_dir}/gitmind" <<EOF
#!/usr/bin/env bash
cd "$repo_dir"
exec "$uv_bin" run gitmind "\$@"
EOF

chmod +x "${install_dir}/gitmind"
info "已安裝 gitmind 到 ${install_dir}/gitmind"

cat > "${install_dir}/gmind" <<EOF
#!/usr/bin/env bash
cd "$repo_dir"
exec "$uv_bin" run gitmind "\$@"
EOF

chmod +x "${install_dir}/gmind"
info "已安裝短命令 alias 到 ${install_dir}/gmind"

if [ -f "${repo_dir}/SKILL.md" ]; then
  if [ "${GITMIND_INSTALL_CODEX_SKILL:-${GMIND_INSTALL_CODEX_SKILL:-1}}" != "0" ]; then
    mkdir -p "$codex_skill_dir"
    cp "${repo_dir}/SKILL.md" "${codex_skill_dir}/SKILL.md"
    info "已安裝 Codex skill 到 ${codex_skill_dir}/SKILL.md"
    if [ -d "$legacy_codex_skill_dir" ]; then
      rm -rf "$legacy_codex_skill_dir"
      info "已移除舊版 Codex skill 路徑：${legacy_codex_skill_dir}"
    fi
  fi

  if [ "${GITMIND_INSTALL_CLAUDE_SKILL:-${GMIND_INSTALL_CLAUDE_SKILL:-1}}" != "0" ]; then
    mkdir -p "$claude_skill_dir"
    cp "${repo_dir}/SKILL.md" "${claude_skill_dir}/SKILL.md"
    info "已安裝 Claude Code skill 到 ${claude_skill_dir}/SKILL.md"
    if [ -d "$legacy_claude_skill_dir" ]; then
      rm -rf "$legacy_claude_skill_dir"
      info "已移除舊版 Claude Code skill 路徑：${legacy_claude_skill_dir}"
    fi
  fi
fi

echo
info "執行安裝後 smoke test..."
"${install_dir}/gitmind" --help >/dev/null
info "smoke test 通過：gitmind --help"

echo
if [[ ":${PATH}:" != *":${install_dir}:"* ]]; then
  echo "如果 ${install_dir} 不在 PATH，請把這行加到 shell profile："
  echo "  export PATH=\"${install_dir}:\$PATH\""
else
  echo "${install_dir} 已經在 PATH 裡。"
fi

echo
echo "下一步："
echo "1. 先用 Chrome 打開 GitMind，確認你已經登入。"
echo "2. 回到終端機執行："
echo "     gitmind auth import-browser --browser chrome"
echo "3. 確認 GitMind CLI 可以連上你的 GitMind："
echo "     gitmind doctor"
echo
echo "如果你不是用 Chrome，而是用 Comet 登入 GitMind，可以改跑："
echo "     gitmind auth import-browser --browser comet"
