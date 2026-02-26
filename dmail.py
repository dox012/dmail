#!/usr/bin/env python3
"""dmail - 极简邮件聊天系统，把一切托管给 agent"""

import json, os, sys, time, subprocess
import smtplib, imaplib, email
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parseaddr, formataddr

DIR = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(DIR, "config.json")
SMTP = ("smtp.qq.com", 465)
IMAP = ("imap.qq.com", 993)

# ── 配置 ──────────────────────────────────────────────

def load_cfg():
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    print("=== dmail 首次配置 ===")
    print("授权码获取: QQ邮箱 → 设置 → 账户 → 开启IMAP/SMTP服务 → 生成授权码\n")
    cfg = {
        "email": input("QQ 邮箱: ").strip(),
        "auth_code": input("授权码: ").strip(),
        "agent_cmd": input("Agent 命令 (如 claude -p \"{prompt}\"): ").strip()
            or 'claude -p "{prompt}"',
    }
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"已保存到 {CFG_PATH}\n")
    return cfg

# ── 邮件工具 ────────────────────────────────────────────

def _dec(s):
    if not s: return ""
    parts = decode_header(s)
    return "".join(
        d.decode(c or "utf-8", errors="replace") if isinstance(d, bytes) else d
        for d, c in parts
    )

def _body(msg):
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain" and "attachment" not in str(p.get("Content-Disposition", "")):
                return p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", errors="replace")
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace") if payload else ""

def send(cfg, to, subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"], msg["To"], msg["Subject"] = cfg["email"], to, subject
    with smtplib.SMTP_SSL(*SMTP) as s:
        s.login(cfg["email"], cfg["auth_code"])
        s.sendmail(cfg["email"], [to], msg.as_string())

def _imap(cfg):
    c = imaplib.IMAP4_SSL(*IMAP)
    c.login(cfg["email"], cfg["auth_code"])
    return c

def fetch(cfg, n=10):
    c = _imap(cfg); c.select("INBOX", readonly=True)
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

def read(cfg, uid):
    c = _imap(cfg); c.select("INBOX", readonly=True)
    _, d = c.uid("fetch", uid.encode(), "(RFC822)")
    c.logout()
    if d[0] is None: return None
    m = email.message_from_bytes(d[0][1])
    _, addr = parseaddr(_dec(m.get("From", "")))
    return {"uid": uid, "from": addr, "subject": _dec(m.get("Subject", "")),
            "date": _dec(m.get("Date", "")), "body": _body(m)}

def get_unseen(cfg):
    c = _imap(cfg); c.select("INBOX")
    _, data = c.uid("search", None, "UNSEEN")
    uids = data[0].split()
    c.logout()
    return [u.decode() for u in uids]

# ── Agent ─────────────────────────────────────────────

def ask_agent(cfg, prompt):
    cmd = cfg["agent_cmd"].replace("{prompt}", prompt.replace('"', '\\"'))
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    return r.stdout.strip() or r.stderr.strip() or "(agent 无响应)"

# ── Serve 模式：轮询未读邮件，自动用 agent 回复 ──────────

def serve(cfg, interval=30):
    print(f"dmail serve | 每 {interval}s 轮询 | Ctrl+C 退出")
    print(f"agent: {cfg['agent_cmd']}\n")
    while True:
        try:
            for uid in get_unseen(cfg):
                m = read(cfg, uid)
                if not m: continue
                print(f"← {m['from']}: {m['subject']}")
                reply_body = ask_agent(cfg, m["body"])
                subj = ("Re: " + m["subject"]) if not m["subject"].lower().startswith("re:") else m["subject"]
                send(cfg, m["from"], subj, reply_body)
                print(f"→ 已回复 {m['from']}")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n已停止"); break
        except Exception as e:
            print(f"错误: {e}"); time.sleep(interval)

# ── CLI 交互模式 ──────────────────────────────────────

HELP = """命令:
  list [n]      最近 n 封邮件
  read <uid>    读取邮件
  send          发送邮件
  reply <uid>   手动回复
  agent <uid>   用 agent 回复
  serve [sec]   自动轮询回复模式
  help / quit"""

def cli(cfg):
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
                for m in fetch(cfg, int(args[0]) if args else 10):
                    print(f"  {m['uid']:<8} {m['from']:<26} {m['subject'][:32]}")
            elif cmd == "read":
                m = read(cfg, args[0]) if args else None
                if m: print(f"  From: {m['from']}\n  Subject: {m['subject']}\n  Date: {m['date']}\n{'─'*40}\n{m['body']}")
                else: print("  用法: read <uid>")
            elif cmd == "send":
                to = input("  收件人: ").strip(); subj = input("  主题: ").strip()
                print("  正文 (单独一行 . 结束):"); lines = []
                while True:
                    ln = input();
                    if ln.strip() == ".": break
                    lines.append(ln)
                send(cfg, to, subj, "\n".join(lines)); print("  已发送")
            elif cmd == "reply" and args:
                m = read(cfg, args[0])
                if not m: print("  邮件不存在"); continue
                print(f"  回复 {m['from']}，正文 (单独一行 . 结束):"); lines = []
                while True:
                    ln = input()
                    if ln.strip() == ".": break
                    lines.append(ln)
                subj = ("Re: " + m["subject"]) if not m["subject"].lower().startswith("re:") else m["subject"]
                send(cfg, m["from"], subj, "\n".join(lines)); print("  已回复")
            elif cmd == "agent" and args:
                m = read(cfg, args[0])
                if not m: print("  邮件不存在"); continue
                print(f"  调用 agent 处理 [{m['subject']}] ...")
                reply_body = ask_agent(cfg, m["body"])
                print(f"  agent 回复:\n{reply_body}\n")
                if input("  发送? (y/n): ").strip().lower() == "y":
                    subj = ("Re: " + m["subject"]) if not m["subject"].lower().startswith("re:") else m["subject"]
                    send(cfg, m["from"], subj, reply_body); print("  已发送")
            elif cmd == "serve":
                serve(cfg, int(args[0]) if args else 30)
            elif cmd == "help":
                print(HELP)
            elif cmd in ("quit", "exit", "q"):
                print("再见"); break
            else:
                print("  未知命令，输入 help")
        except Exception as e:
            print(f"  错误: {e}")

# ── 入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    cfg = load_cfg()
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve(cfg, int(sys.argv[2]) if len(sys.argv) > 2 else 30)
    else:
        cli(cfg)
