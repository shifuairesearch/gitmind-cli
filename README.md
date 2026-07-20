# gmind

`gmind` 是給 ShiFu 同事和 AI agent 使用的 GitMind 本機 CLI。

它可以在不分享密碼、不把瀏覽器 cookie 貼到聊天裡的前提下，完成這幾件事：

- 從已登入的本機瀏覽器擷取 GitMind session token。
- 搜尋、定位、讀取 GitMind 心智圖。
- 把心智圖匯出成 Markdown 或 GitMind 原始 JSON。
- 把 AI 討論好的 Markdown 大綱建立成新的 GitMind 心智圖。
- 更新既有心智圖；更新前會自動備份原圖 JSON + Markdown。

## 安裝

環境需求：

- macOS 或 Linux shell 環境。
- `bash`。
- `curl`：只有在電腦還沒有 `uv`、需要自動下載安裝時才會用到。
- 可連線到 GitMind / `gw.aoscdn.com`。
- 若要自動擷取登入 session：建議先在 Chrome 登入 GitMind。Comet 也支援，但放在備用選項；其他環境可用 `gmind auth set-token` 手動設定。

`uv` 和 Python 3.10+ 不需要同事事先裝好。`install.sh` 會自動檢查；缺 `uv` 會直接下載安裝，缺 Python 3.10+ 會用 `uv` 安裝 managed Python。

解壓縮 source package 後進入資料夾：

```bash
cd gmind
```

開發模式可以直接用 `uv` 跑：

```bash
uv run gmind --help
```

也可以安裝一個本機 wrapper，之後從任何資料夾都能執行 `gmind`：

```bash
bash install.sh
gmind doctor --json
```

`install.sh` 全程使用中文提示，會自動處理：

- 檢查目前資料夾是不是 gmind 專案。
- 找不到 `uv` 時，自動用 `curl` 安裝 `uv`。
- 找不到 Python 3.10+ 時，自動用 `uv python install 3.12` 補齊。
- 安裝後跑一次 `gmind --help` smoke test。

`install.sh` 會依照同事自己的 `$HOME` 安裝，不會寫死任何人的本機路徑。預設會安裝：

```text
~/.local/bin/gmind
~/.agents/skills/gmind/SKILL.md
~/.claude/skills/gmind/SKILL.md
```

其中 `~/.agents/skills/gmind/SKILL.md` 給 Codex 使用，`~/.claude/skills/gmind/SKILL.md` 給 Claude Code 使用。這讓支援 skills 的 agent 之後能自動知道怎麼使用 `gmind`。

單純執行 `gmind` 命令不會自動安裝或修改 skill；只有跑 `install.sh` 時才會做這件事。

進階安裝選項：

```bash
GMIND_BIN_DIR="$HOME/bin" bash install.sh
GMIND_AUTO_INSTALL_UV=0 bash install.sh
GMIND_INSTALL_CODEX_SKILL=0 bash install.sh
GMIND_INSTALL_CLAUDE_SKILL=0 bash install.sh
GMIND_CODEX_SKILL_DIR="$HOME/.agents/skills/gmind" bash install.sh
GMIND_CLAUDE_SKILL_DIR="$HOME/.claude/skills/gmind" bash install.sh
```

## 第一次登入

一般同事建議用 Chrome。請先用 Chrome 打開 GitMind 並確認已登入，然後回到終端機執行：

```bash
gmind auth import-browser --browser chrome
```

這個指令會從你自己電腦上已登入的 Chrome 裡找到 GitMind 的登入狀態。它不會讀你的 GitMind 密碼，也不需要你把 cookie 貼給別人。

如果你是用 Comet 登入 GitMind，才改用：

```bash
gmind auth import-browser --browser comet
```

確認登入狀態：

```bash
gmind doctor --json
```

正常會看到 `ok: true`，而且 token 只會顯示遮蔽版本，不會印出完整 token。

如果瀏覽器 session 擷取失敗，手動從 GitMind 網頁的 DevTools Network 複製任一個 `gw.aoscdn.com` request 的 `Authorization` header，然後執行：

```bash
gmind auth set-token
```

## 搜尋與讀取心智圖

搜尋檔案：

```bash
gmind files search "AI 研究所" --json
```

把心智圖名稱解析成穩定的 `file_guid`：

```bash
gmind minds resolve "AI 研究所 - 週會課程規劃_Irene（勿動）" --json
```

匯出成 Markdown：

```bash
gmind minds export-name "AI 研究所 - 週會課程規劃_Irene（勿動）" --format md --out ./mind.md
```

匯出成 GitMind 原始 JSON：

```bash
gmind minds export-name "AI 研究所 - 週會課程規劃_Irene（勿動）" --format json --out ./mind.json
```

## 從 Markdown 建立新心智圖

Markdown 格式用一般大綱即可：

```markdown
# Claude 討論整理

- 第一個主題
  - 子題
  - 子題
- 第二個主題
```

建立新圖：

```bash
gmind minds create --name "Claude 討論整理" --from-md ./outline.md
```

## 更新既有心智圖

更新前先 dry-run：

```bash
gmind minds update-name "既有圖名稱" --from-md ./outline.md --dry-run
```

dry-run 會顯示：

- 目標心智圖名稱與 `file_guid`
- 線上版本目前有幾個節點
- 準備上傳的新版本有幾個節點
- 是否會建立備份

確認沒問題後才真的更新：

```bash
gmind minds update-name "既有圖名稱" --from-md ./outline.md --confirm
```

`--confirm` 會先自動備份原圖：

```text
~/.local/share/gmind/backups/{圖名}-{file_guid}-{時間}.json
~/.local/share/gmind/backups/{圖名}-{file_guid}-{時間}.md
```

備份成功後才會上傳新版內容。如果備份失敗，更新會停止。

## 常用命令

```bash
gmind doctor --json
gmind auth import-browser --browser chrome
gmind files list --limit 20 --json
gmind files search "關鍵字" --json
gmind files tree --max-depth 3 --json
gmind minds resolve "心智圖名稱" --json
gmind minds get <file_guid> --json
gmind minds export <file_guid> --format md --out ./mind.md
gmind minds create --name "新圖" --from-md ./outline.md
gmind minds update-name "既有圖名稱" --from-md ./outline.md --dry-run
gmind minds update-name "既有圖名稱" --from-md ./outline.md --confirm
```

## 安全邊界

- 不讀取 GitMind 密碼。
- 不在輸出中印出完整 token。
- 不把 token 寫進匯出的 Markdown / JSON。
- 不快取或印出 GitMind 的 `project_url` signed URL。
- 更新既有心智圖必須加 `--confirm`。
- 更新前會強制備份 JSON + Markdown。
- v0.1.0 不支援刪除、分享設定、官方模板建立、付款、團隊、留言或 AI 扣點 API。

## 給 agent 的使用建議

先檢查狀態：

```bash
gmind doctor --json
```

讀圖前先 resolve，避免名稱模糊：

```bash
gmind minds resolve "心智圖名稱" --json
```

更新圖以前一定先 dry-run：

```bash
gmind minds update-name "心智圖名稱" --from-md ./outline.md --dry-run
```

只有在使用者明確同意覆蓋時，才使用：

```bash
gmind minds update-name "心智圖名稱" --from-md ./outline.md --confirm
```
