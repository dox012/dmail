import time, subprocess
import smtplib, imaplib, email
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parseaddr

AGENT_EMAIL = "agent@qq.com"
AGENT_AUTH  = "your_auth_code"
AGENT_CMD   = 'claude -p "{prompt}"'
INTERVAL    = 30

SMTP = ("smtp.qq.com", 465)
IMAP = ("imap.qq.com", 993)

def _dec(s):
    if not s: return ""
    parts = decode_header(s)
    return "".join(d.decode(c or "utf-8", errors="replace") if isinstance(d, bytes) else d for d, c in parts)

def _body(msg):
    raw = ""
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain" and "attachment" not in str(p.get("Content-Disposition", "")):
                raw = p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", errors="replace")
                break
    else:
        payload = msg.get_payload(decode=True)
        raw = payload.decode(msg.get_content_charset() or "utf-8", errors="replace") if payload else ""
    return raw.split('---原始邮件---')[0].replace('&nbsp;', ' ').strip()

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

def ask_agent(prompt):
    cmd = AGENT_CMD.replace("{prompt}", prompt.replace('"', '\\"'))
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=300)
        return out.strip() or err.strip() or "(agent 无响应)"
    except (KeyboardInterrupt, subprocess.TimeoutExpired):
        proc.kill()
        proc.wait()
        raise

def mark_all_seen():
    c = _imap(); c.select("INBOX")
    _, data = c.search(None, "UNSEEN")
    for mid in data[0].split():
        c.store(mid, '+FLAGS', '\\Seen')
    c.logout()

if __name__ == "__main__":
    mark_all_seen()
    print(f"dmail | 每 {INTERVAL}s 轮询 | Ctrl+C 退出")
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
