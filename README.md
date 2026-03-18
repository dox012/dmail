# dmail

<table>
  <tr>
    <td><img src="assets/1.jpg" alt="dmail screenshot 1" width="260"></td>
    <td><img src="assets/2.jpg" alt="dmail screenshot 2" width="260"></td>
    <td><img src="assets/3.jpg" alt="dmail screenshot 3" width="260"></td>
  </tr>
  <tr>
    <td><img src="assets/4.jpg" alt="dmail screenshot 4" width="260"></td>
    <td><img src="assets/5.jpg" alt="dmail screenshot 5" width="260"></td>
    <td><img src="assets/6.jpg" alt="dmail screenshot 6" width="260"></td>
  </tr>
</table>


极简邮件聊天系统，把一切额外功能托管给 agent。
100 行 Python 实现，给邮箱发消息，agent 开始干活。

## 用法

改 `dmail.py` 顶部配置，然后：

```bash
python dmail.py
```

## 配置

```python
USER_EMAIL  = "user@qq.com"             # 你的邮箱（白名单，留空不过滤）
AGENT_EMAIL = "agent@qq.com"            # agent 邮箱
AGENT_AUTH  = "agent_auth_code"         # 授权码
AGENT_CMD   = 'claude -p "{prompt}" --continue --dangerously-skip-permissions'  # agent 命令（--continue 多轮对话）
INTERVAL    = 6                        # 轮询间隔（秒）
```

换 agent 只改 `AGENT_CMD`，如 `codex exec "{prompt}" resume --last --dangerously-bypass-approvals-and-sandbox`、`gemini -p "{prompt}" --yolo`。

授权码：QQ邮箱 → 设置 → 账户 → 开启 IMAP/SMTP → 生成授权码。