#!/usr/bin/env python3
"""dmail - 极简邮件聊天系统，把一切托管给 agent"""

import sys, time, subprocess
import smtplib, imaplib, email
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parseaddr

# ── 配置（直接改这里）─────────────────────────────────────
AGENT_EMAIL = "agent@qq.com"
AGENT_AUTH  = "your_auth_code"
USER_EMAIL  = "you@qq.com"
AGENT_CMD   = 'claude -p "{prompt}"'

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
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"], msg["To"], msg["Subject"] = AGENT_EMAIL, to, subject
    with smtplib.SMTP_SSL(*SMTP) as s:
        s.login(AGENT_EMAIL, AGENT_AUTH)
        s.sendmail(AGENT_EMAIL, [to], msg.as_string())

def fetch(n=10):
    c = _imap(); c.select("INBOX", readonly=True)
    _, data = c.uid("search", None, "ALL")
    uids = data[0].split()
    if not uids: c.logout(); return []
    results = []
    for uid in reversed(uids[-n:]):
        _, d = c.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        if d[0] is None: continue
        m = email.message_from_bytes(d[0][1])
        _, addr = parseaddr(_dec(m.get("From", "")))
        results.append({"uid": uid.decode(), "from": addr, "subject": _dec(m.get("Subject", "")), "date": _dec(m.get("Date", ""))})
    c.logout()
    return results

def read(uid):
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

# ── Serve 模式 ────────────────────────────────────────

def serve(interval=30):
    print(f"dmail serve | 每 {interval}s 轮询 | Ctrl+C 退出")
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
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n已停止"); break
        except Exception as e:
            print(f"错误: {e}"); time.sleep(interval)

# ── CLI ───────────────────────────────────────────────

HELP = """命令:
  list [n]      最近 n 封邮件
  read <uid>    读取邮件
  send          发送邮件
  reply <uid>   手动回复
  agent <uid>   用 agent 回复
  serve [sec]   自动轮询回复模式
  help / quit"""

def cli():
    print("dmail cli | 输入 help 查看命令\n")
    while True:
        try:
            raw = input("dmail> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见"); break
        if not raw: continue
        parts = raw.split(); cmd, args = parts[0].lower(), parts[1:]
        try:
            if cmd == "list":
                for m in fetch(int(args[0]) if args else 10):
                    print(f"  {m['uid']:<8} {m['from']:<26} {m['subject'][:32]}")
            elif cmd == "read" and args:
                m = read(args[0])
                if m: print(f"  From: {m['from']}\n  Subject: {m['subject']}\n  Date: {m['date']}\n{'─'*40}\n{m['body']}")
                else: print("  邮件不存在")
            elif cmd == "send":
                to = input(f"  收件人 [{USER_EMAIL}]: ").strip() or USER_EMAIL
                subj = input("  主题: ").strip()
                print("  正文 (单独一行 . 结束):"); lines = []
                while True:
                    ln = input()
                    if ln.strip() == ".": break
                    lines.append(ln)
                send(to, subj, "\n".join(lines)); print("  已发送")
            elif cmd == "reply" and args:
                m = read(args[0])
                if not m: print("  邮件不存在"); continue
                print(f"  回复 {m['from']}，正文 (单独一行 . 结束):"); lines = []
                while True:
                    ln = input()
                    if ln.strip() == ".": break
                    lines.append(ln)
                subj = ("Re: " + m["subject"]) if not m["subject"].lower().startswith("re:") else m["subject"]
                send(m["from"], subj, "\n".join(lines)); print("  已回复")
            elif cmd == "agent" and args:
                m = read(args[0])
                if not m: print("  邮件不存在"); continue
                print(f"  调用 agent ..."); reply_body = ask_agent(m["body"])
                print(f"  agent:\n{reply_body}\n")
                if input("  发送? (y/n): ").strip().lower() == "y":
                    subj = ("Re: " + m["subject"]) if not m["subject"].lower().startswith("re:") else m["subject"]
                    send(m["from"], subj, reply_body); print("  已发送")
            elif cmd == "serve":
                serve(int(args[0]) if args else 30)
            elif cmd == "help": print(HELP)
            elif cmd in ("quit", "exit", "q"): print("再见"); break
            else: print("  未知命令，输入 help")
        except Exception as e:
            print(f"  错误: {e}")

# ── 入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve(int(sys.argv[2]) if len(sys.argv) > 2 else 30)
    else:
        cli()
