# dmail

极简邮件聊天系统 — 197 行 Python，零依赖，把一切托管给 agent。

通过 QQ 邮箱 SMTP/IMAP 收发邮件，接入任意 agent CLI（Claude、Codex、Ollama...）自动回复。

## 快速开始

```bash
python dmail.py
```

首次运行会引导配置 QQ 邮箱、授权码和 agent 命令，保存到 `config.json`。

## 使用

```bash
python dmail.py            # 交互式 CLI
python dmail.py serve      # 自动轮询，agent 回复未读邮件
python dmail.py serve 60   # 自定义轮询间隔（秒）
```

CLI 命令：

```
list [n]      最近 n 封邮件
read <uid>    读取邮件
send          发送邮件
reply <uid>   手动回复
agent <uid>   用 agent 回复（发送前确认）
serve [sec]   进入自动轮询模式
```

## 配置

`config.json` 示例：

```json
{
  "email": "你的QQ邮箱",
  "auth_code": "QQ邮箱授权码",
  "agent_cmd": "claude -p \"{prompt}\""
}
```

换 agent 只改 `agent_cmd`，比如 `codex --quiet "{prompt}"` 或 `ollama run llama3 "{prompt}"`。

授权码获取：QQ邮箱 → 设置 → 账户 → 开启 IMAP/SMTP 服务 → 生成授权码。
