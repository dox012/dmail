# dmail

极简邮件聊天系统，把一切额外功能托管给 agent。
80 行 Python 实现。给邮箱发消息，agent 开始干活。

## 用法

改 `dmail.py` 顶部配置，然后：

```bash
python dmail.py
```

## 配置

```python
AGENT_EMAIL = "agent@qq.com"        # agent 邮箱
AGENT_AUTH  = "your_auth_code"      # 授权码
AGENT_CMD   = 'claude -p "{prompt}"'# agent 命令
INTERVAL    = 30                    # 轮询间隔（秒）
```

换 agent 只改 `AGENT_CMD`，如 `codex --quiet "{prompt}"`、`ollama run llama3 "{prompt}"`。

授权码：QQ邮箱 → 设置 → 账户 → 开启 IMAP/SMTP → 生成授权码。
