# -*- coding: utf-8 -*-
"""CRM System self-check script (run via selfcheck.bat or directly with .venv python).

Checks in order:
  1. MySQL connectivity (from backend/.env DATABASE_URL)
  2. Backend service (/health)
  3. API smoke tests: admin login -> customer list -> kanban -> notifications
  4. Permission isolation: a sales user must see fewer customers than admin

Exit code 0 = all passed; 1 = something failed.
"""
import json
import os
import re
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
API = "http://127.0.0.1:8000"

results = []  # (name, ok, detail)


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ->  {detail}" if detail else ""))


def read_env(path):
    vals = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return vals


# ---------- 1. MySQL ----------
url = read_env(os.path.join(BASE, "backend", ".env")).get("DATABASE_URL", "")
try:
    import pymysql

    m = re.match(r"mysql\+pymysql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)", url)
    if not m:
        check("MySQL 连接", False, "无法解析 backend/.env 的 DATABASE_URL")
    else:
        user, pwd, host, port, db = m.groups()
        conn = pymysql.connect(
            host=host, port=int(port or 3306), user=user,
            password=pwd, database=db, connect_timeout=5,
        )
        conn.close()
        check("MySQL 连接", True, f"{host}:{port}/{db}")
except Exception as e:  # noqa: BLE001
    check("MySQL 连接", False, str(e))


# ---------- 2. Backend health ----------
def api(path, method="GET", data=None, token=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    body = json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(req, body, timeout=10) as r:
        return json.loads(r.read().decode())


try:
    h = api("/health")
    check("后端服务", h.get("status") == "ok", str(h))
except Exception as e:  # noqa: BLE001
    check("后端服务", False, f"请先双击 start-all.bat 启动系统后再自检（{e}）")
    print("\n== 自检汇总 ==")
    for name, ok, _ in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    sys.exit(1 if any(not ok for _, ok, _ in results) else 0)


# ---------- 3. API smoke tests ----------
tok = None
try:
    login = api("/api/v1/auth/login", "POST",
                {"email": "demo.admin@crm.com", "password": "demo123456"})
    tok = login["data"]["access_token"]
    check("管理员登录", True)
except Exception as e:  # noqa: BLE001
    check("管理员登录", False, str(e))

if tok:
    admin_total = None
    try:
        cust = api("/api/v1/customers?page=1&page_size=5", token=tok)
        admin_total = cust["data"]["total"]
        check("客户列表（分页格式）", admin_total > 0, f"total={admin_total}")
    except Exception as e:  # noqa: BLE001
        check("客户列表（分页格式）", False, str(e))

    try:
        k = api("/api/v1/board/kanban", token=tok)
        cards = sum(len(c.get("customers") or []) for c in k["data"])
        check("看板数据（8 列）", len(k["data"]) == 8, f"{len(k['data'])} 列 / {cards} 卡片")
    except Exception as e:  # noqa: BLE001
        check("看板数据（8 列）", False, str(e))

    try:
        n = api("/api/v1/notifications?page=1&page_size=5", token=tok)
        check("通知列表（分页格式）", "total" in n["data"], f"total={n['data']['total']}")
    except Exception as e:  # noqa: BLE001
        check("通知列表（分页格式）", False, str(e))

    # ---------- 4. Permission isolation ----------
    try:
        l2 = api("/api/v1/auth/login", "POST",
                 {"email": "zhangwei@crm.com", "password": "demo123456"})
        c2 = api("/api/v1/customers?page=1&page_size=5", token=l2["data"]["access_token"])
        sales_total = c2["data"]["total"]
        ok = admin_total is not None and sales_total < admin_total
        check("销售权限隔离（只能看自己的客户）", ok,
              f"admin={admin_total} sales={sales_total}")
    except Exception as e:  # noqa: BLE001
        check("销售权限隔离（只能看自己的客户）", False, str(e))

print("\n== 自检汇总 ==")
failed = [r for r in results if not r[1]]
for name, ok, _ in results:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
if not failed:
    print("\n全部通过，项目可正常交付。")
else:
    print(f"\n有 {len(failed)} 项未通过，请按上方提示排查。")
sys.exit(1 if failed else 0)
