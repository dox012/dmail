#!/usr/bin/env python3
"""dmail - 极简邮件聊天系统，把一切托管给 agent"""

import time, subprocess
import smtplib, imaplib, email
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parseaddr

# ── 配置（直接改这里）─────────────────────────────────────
AGENT_EMAIL = "agent@qq.com"
AGENT_AUTH  = "your_auth_code"
AGENT_CMD   = 'claude -p "{prompt}"'
INTERVAL    = 30

SMTP = ("smtp.qq.com", 465)
IMAP = ("imap.qq.com", 993)

# ── 邮件工具 ────────────────────────────────────────────

def _dec(s):
    if not s: return ""
    parts = decode_header(s)
    return "".join(d.decode(c or "utf-8", errors="replace") if isinstance(d, bytes) else d for d, c in parts)

def _body(msg):
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain" and "attachment" not in str(p.get("Content-Disposition", "")):
                return p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", errors="replace")
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace") if payload else ""

def _imap():
    c = imaplib.IMAP4_SSL(*IMAP)
    c.login(AGENT_EMAIL, AGENT_AUTH)
    return c

def send(to, subject, body):
    c = _imap(); c.select("INBOX", readonly=True)
    _, d = c.uid("fetch", uid.encode(), "(RFC822)")
    c.logout()
    if d[0] is None: return None
    m = email.message_from_bytes(d[0][1])
    _, addr = parseaddr(_dec(m.get("From", "")))
    return {"uid": uid, "from": addr, "subject": _dec(m.get("Subject", "")),
            "date": _dec(m.get("Date", "")), "body": _body(m)}

def get_unseen():
    c = _imap(); c.select("INBOX")
    _, data = c.uid("search", None, "UNSEEN")
    uids = data[0].split(); c.logout()
    return [u.decode() for u in uids]

# ── Agent ─────────────────────────────────────────────

def ask_agent(prompt):
    cmd = AGENT_CMD.replace("{prompt}", prompt.replace('"', '\\"'))
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    return r.stdout.strip() or r.stderr.strip() or "(agent 无响应)"

# ── 入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    print(f"dmail | 每 {INTERVAL}s 轮询 | Ctrl+C 退出")
    print(f"agent: {AGENT_CMD}\n")
    while True:
        try:
            for uid in get_unseen():
                m = read(uid)
                if not m: continue
                print(f"← {m['from']}: {m['subject']}")
                reply_body = ask_agent(m["body"])
                subj = ("Re: " + m["subject"]) if not m["subject"].lower().startswith("re:") else m["subject"]
                send(m["from"], subj, reply_body)
                print(f"→ 已回复 {m['from']}")
            time.sleep(INTERVAL)
        except KeyboardInterrupt:
            print("\n已停止"); break
        except Exception as e:
            print(f"错误: {e}"); time.sleep(INTERVAL)
