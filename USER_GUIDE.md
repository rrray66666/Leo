# CRM System — User & Deployment Guide

> A complete Customer Relationship Management system with an 8-stage Kanban workflow.
> This guide tells you how to run the system on a new machine and how to use it day to day.

---

## 1. What Is Included in This Package

| Item | Purpose |
|------|---------|
| `backend/` | FastAPI backend with all Python dependencies pre-installed in `.venv` |
| `frontend/` | Vue 3 frontend (all `node_modules` included — no internet needed) |
| `.nodejs/` | Portable Node.js runtime (used by `start-all.bat`) |
| `.venv/` | Python 3.13 virtual environment with all backend packages installed |
| `start-all.bat` | One-click launcher (Windows) — **the normal way to start** |
| `docker-compose.yml` | Alternative deployment via Docker |
| `db_init.sql` | One-time MySQL database setup script |
| `USER_GUIDE.md` | This document |
| `README.md` | Full technical documentation |
| `SEND_CHECKLIST.md` | Delivery checklist |
| `docs/` | API / database / architecture documents |

---

## 2. System Requirements

**Option A — Local run on Windows (recommended, offline):**
- Windows 10/11
- **MySQL 8.x installed and running** (this is the only external requirement)
- No Python / Node.js installation needed — they are bundled.

**Option B — Docker:**
- Docker Desktop installed
- First build requires internet (to pull base images and install dependencies).

---

## 3. Option A — Local Run on Windows (Recommended)

### 3.1 Install MySQL 8 (once)

Download and install MySQL 8.x from https://dev.mysql.com/downloads/mysql/.
Remember the **root password** you set during installation, and make sure the
MySQL service is started (Windows service name: `MySQL80`).

### 3.2 Initialize the database (once)

Open a **Command Prompt** and run (enter your MySQL root password when asked):

```bat
mysql -uroot -p < db_init.sql
```

This creates the `crm` database and the `crm` user (password `crm123`)
that the system uses. If you changed anything later, make sure `backend\.env`
matches it.

### 3.3 Start the system (every time)

Simply **double-click `start-all.bat`** at the project root. It will:

1. Check Python, Node.js and MySQL connectivity.
2. **On the very first run**, automatically create all database tables and
   load demo data (6 accounts, 35 customers across all 8 stages).
3. Open the **backend** (`http://127.0.0.1:8000/docs`) and the **frontend**
   (`http://localhost:5173`) in two new windows.

> Wait a few seconds after the windows appear — the frontend needs a moment to
> compile. Then open `http://localhost:5173` in your browser.

### 3.4 Stop the system

Close the two command-prompt windows (`CRM Backend` / `CRM Frontend`).
Or press `Ctrl + C` in each window.

---

## 4. Option B — Docker Deployment

If the target machine has Docker Desktop:

```bash
# from the project root
docker-compose up -d --build

# create tables (automatic) and load demo data
docker-compose exec backend python -m app.scripts.seed_demo
```

Then open:

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| API Docs (Swagger) | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

Stop everything with `docker-compose down`. Add `-v` to also delete all data.

---

## 5. Demo Accounts

All demo accounts use the password **`demo123456`** (created by the seed step):

| Role | Email | Permissions |
|------|-------|-------------|
| Admin | demo.admin@crm.com | Everything, incl. user management & batch operations |
| Sales | zhangwei@crm.com | Manage own customers (CRUD / follow-up / contracts) |
| Sales | lina@crm.com | Same as above |
| Sales | wangfang@crm.com | Same as above |
| PM | chenjie@crm.com | Global read-only + assigned tasks |
| CS | liuyang@crm.com | Read-only own customers |

New users can also register from the login page — they are created as
`sales` and can be changed by an admin in **User Management**.

---

## 6. Quick Tour of the System

| Menu | What it does |
|------|--------------|
| **Kanban** | Drag customers across 8 stages; colors show overdue alerts |
| **Customers** | List / search / create / edit / delete customers |
| **Customer Detail** | 6 tabs: Info, Contracts, Tasks, Communications, Payments, Documents + timeline |
| **Dashboard** | Statistics, sales funnel, workload, payment trends |
| **Notifications** | In-app alerts (lost leads, overdue payments, due tasks) |
| **Follow-ups** | Today's reminders; mark done / edit / delete |
| **Import/Export** | Excel import (with template) and export |
| **Audit Logs** | Full operation history with before/after data |
| **Dictionary** | Configure dropdown options (industries, regions, channels) |
| **Users** | Manage accounts and roles (admin only) |
| **Profile** | Edit personal info / change password |

---

## 7. FAQ / Troubleshooting

| Symptom | Fix |
|---------|-----|
| `start-all.bat` says MySQL connection failed | MySQL is not running, or `backend\.env` `DATABASE_URL` is wrong; make sure `db_init.sql` was executed once |
| Login page shows 401 | Expected — it means you are not logged in yet. Use a demo account. |
| Port 8000 / 5173 already in use | Another instance is running; close its windows, or `taskkill /F /PID <pid>` |
| Where are uploaded files stored? | `backend/app/uploads/` by default (MinIO when configured) |
| I want to reset all demo data | Stop the app, drop the `crm` database, re-run `db_init.sql`, then double-click `start-all.bat` again |
| Seeded data is already there when I run seed again | Safe — seeding is idempotent and skips existing demo data |

---

## 8. Security Notes (Before Going Live)

- Change the demo account passwords.
- Replace `JWT_SECRET` in `backend\.env` with a long random string:
  `python -c "import secrets; print(secrets.token_hex(32))"`
- Do not commit `backend\.env` / root `.env` to any public repository.
- In production, restrict the backend CORS `allow_origins` to your real domain.

---

© 2026 CRM System. For support, contact the development team.
