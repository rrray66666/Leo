# CRM System — Architecture & Design Document

**Version:** 1.0.0
**Status:** Internal technical design

---

## 1. System Overview & Goals

The CRM System is a full-stack web application for managing a customer pipeline from lead generation through project completion. It replaces a manual, spreadsheet-based workflow with a governed 8-stage Kanban process.

**Primary goals:**

1. **Centralized customer lifecycle management** — every customer follows a fixed, enforceable 8-stage pipeline (Lead → Consult → Contract → Requirements → Service → Delivery → Payment → Completed).
2. **Process governance** — stage advancement is sequential and gated by business prerequisites (signed contract, completed tasks, acceptance documents, full payment), preventing data-quality drift.
3. **Visibility & alerting** — stay-time based alerts (normal/warning/danger) flag stalled deals; a dashboard, funnel and kanban board give management and sales real-time visibility.
4. **Traceability** — stage history and audit logs capture who changed what and when, with before/after JSON snapshots.
5. **Role-based access control** — four roles (admin, sales, pm, cs) with distinct read/write permissions.
6. **Operational automation** — a background scheduler auto-marks stale leads as lost, notifies on task due dates and overdue payments, guarded by a Redis distributed lock.
7. **Multi-user scalability target** — 100+ concurrent users via a 4-worker uvicorn deployment, connection pooling and Redis-backed caching/locking.

**Out of scope (current release):** email delivery for follow-up reminders (enum value exists but only `system_notification` is used), MinIO object storage (configured but uploads currently go to the local filesystem), and drag-and-drop kanban persistence (kanban rendering is read-only; stage changes go through the API).

---

## 2. Architecture Diagram (ASCII)

```
                 ┌──────────────────────────────────────────────────────────┐
                 │                        Internet                          │
                 └───────────────────────────┬──────────────────────────────┘
                                             │ HTTP :80
                                             ▼
                             ┌───────────────────────────────┐
                             │         Nginx (frontend)      │
                             │  SPA static files + /api proxy│
                             │  listen 80                    │
                             └───────────────┬───────────────┘
                                             │ /api/* → backend:8000
                                             ▼
                    ┌────────────────────────────────────────────────────┐
                    │              Frontend — Vue 3 (SPA)               │
                    │  Views (12) · Components (6) · Pinia stores (3)  │
                    │  Vue Router · Element Plus · Axios               │
                    └───────────────────────────┬────────────────────────┘
                                                │ REST JSON + JWT (Bearer)
                                                ▼
                    ┌────────────────────────────────────────────────────┐
                    │           Backend — FastAPI (uvicorn x4)          │
                    │  app/api (routes) → app/services (business logic) │
                    │  app/models (SQLAlchemy) → app/schemas (Pydantic) │
                    │  JWT auth (core/security.py, core/deps.py)        │
                    │  APScheduler background jobs                      │
                    └──────┬────────────────────┬───────────────┬───────┘
                           │                    │               │
                           ▼                    ▼               ▼
                 ┌────────────────┐   ┌────────────────┐  ┌────────────────┐
                 │  MySQL 8.0     │   │    Redis 7     │  │  MinIO (S3)    │
                 │  (primary DB)  │   │  distributed   │  │  object store  │
                 │  12 tables     │   │  locks + cache │  │  (configured,  │
                 │  utf8mb4       │   │                │  │  files on disk)│
                 └────────────────┘   └────────────────┘  └────────────────┘
```

Data flow (high level):

1. Browser loads the SPA from Nginx; Nginx serves static assets and proxies `/api/*` to the backend container.
2. The Axios client attaches `Authorization: Bearer <JWT>` on every request (token in `localStorage`).
3. FastAPI validates the JWT (`core/deps.get_current_user`), routes to an endpoint in `app/api`, applies role/ownership checks, delegates to a service in `app/services`, and returns the `{code, message, data}` envelope.
4. Services persist via SQLAlchemy models to MySQL. The APScheduler jobs (started in the FastAPI lifespan) run periodic checks and use Redis locks to guarantee single execution across the 4 workers.
5. MinIO is provisioned and configured (env vars) as the intended object store; document uploads currently write to the backend container's local filesystem (`app/uploads/`).

---

## 3. Technology Stack

| Layer      | Technology                         | Version/Notes                                |
|------------|------------------------------------|----------------------------------------------|
| Frontend   | Vue.js                             | ^3.4.0 (Composition/Options API)             |
|            | Element Plus UI                    | ^2.8.0 (+ @element-plus/icons-vue ^2.3.0)    |
|            | Pinia (state)                      | ^2.1.0                                       |
|            | Vue Router                         | ^4.3.0 (history mode)                        |
|            | Axios (HTTP)                       | ^1.7.0                                       |
|            | Vite (build/dev)                   | ^5.4.0                                       |
|            | Node.js (Docker build)             | 18-alpine                                    |
| Backend    | Python                             | 3.11 (slim image)                            |
|            | FastAPI                            | >=0.104.0                                    |
|            | Uvicorn                            | >=0.24.0 (4 workers)                         |
|            | SQLAlchemy                         | >=2.0.23 (ORM, `Uuid`/`Enum`/`JSON` types)  |
|            | Pydantic + pydantic-settings       | >=2.x (validation + `Settings`)              |
|            | python-jose (JWT)                  | >=3.3.0 (HS256)                              |
|            | passlib[bcrypt]                    | >=1.7.4 (password hashing)                   |
|            | APScheduler                        | >=3.10.0 (AsyncIOScheduler)                  |
|            | redis-py                           | >=5.0.0 (distributed locks)                  |
|            | openpyxl                           | >=3.1.2 (Excel import/export)                |
|            | pymysql                            | >=1.1.0 (MySQL driver)                       |
|            | alembic                            | >=1.13.0 (migrations)                        |
|            | minio (client)                     | >=7.2.0 (configured, not used for uploads yet)|
| Database   | MySQL                              | 8.0 (utf8mb4 / utf8mb4_unicode_ci)           |
| Cache/Lock | Redis                              | 7                                             |
| Files      | MinIO (object store) / local disk  | Local disk fallback active                   |
| Deployment | Docker Compose                     | 3.8; Nginx reverse proxy + static host       |

> Database driver: `pymysql` — the active and only database is **MySQL 8.0**.

---

## 4. Backend Structure & Request Lifecycle

### 4.1 Directory Layout

```
backend/
├── Dockerfile                     # python:3.11-slim, uvicorn --workers 4
├── requirements.txt
├── alembic.ini / alembic/         # Alembic scaffolded for future migrations (create_all runs at startup)
└── app/
    ├── main.py                    # FastAPI app, CORS, lifespan (create_all + scheduler start)
    ├── config.py                  # pydantic-settings Settings (env vars, .env)
    ├── database.py                # engine (pool_size=10, max_overflow=20, pool_pre_ping),
    │                              # SessionLocal, Base, get_db dependency
    ├── api/                       # 16 route modules + router.py aggregation
    │   ├── router.py              # mounts all routers (auth, users, customers, contracts,
    │   │                          #   tasks, documents, communications, payments, board,
    │   │                          #   dashboard, notifications, follow_ups, audit_logs,
    │   │                          #   dicts, search)
    │   └── *.py                   # endpoint definitions, permission checks, orchestration
    ├── core/
    │   ├── security.py            # bcrypt hash/verify, JWT create/decode (HS256)
    │   └── deps.py                # get_db, get_current_user, get_current_active_user,
    │                              #   check_role_admin, check_customer_access,
    │                              #   check_task_access, check_comm_access
    ├── models/                    # 12 SQLAlchemy models (see DATABASE_SCHEMA.md)
    ├── schemas/                   # Pydantic request/response models per module
    └── services/                  # business logic layer
        ├── stage_service.py       # STAGES config, advance/rollback, alert computation
        ├── customer_service.py    # CRUD, search, batch ops, timeline aggregation
        ├── board_service.py       # kanban grouping, alerts
        ├── notification_service.py# create/mark notifications
        ├── audit_service.py       # log_action helper
        └── scheduler_service.py   # 3 background jobs + Redis lock helpers
```

### 4.2 Request Lifecycle

```
HTTP request
   │
   ▼
Nginx (proxy /api/* → backend:8000)                    [deployment layer]
   │
   ▼
CORS middleware (allow all origins, dev default)        [middleware]
   │
   ▼
Router match (app/api/router.py → module router)
   │
   ▼
Dependencies resolved (core/deps.py):
   ├─ get_db()                      → yields a scoped SQLAlchemy session
   └─ get_current_user()            → HTTPBearer → decode JWT → load User
        └─ get_current_active_user()→ 403 if is_active == False
             └─ check_role_admin()  → 403 unless role == 'admin'  (used on admin endpoints)
   │
   ▼
Endpoint handler (app/api/*.py)
   ├─ Pydantic request validation (schemas/*.py) → 422 on failure
   ├─ ownership checks (check_customer_access / check_task_access / check_comm_access)
   └─ delegates to service (app/services/*.py)
   │
   ▼
Service → SQLAlchemy session → MySQL
   │
   ▼
Response envelope {"code": 0, "message": "success", "data": ...}
```

**Key points:**
- JWT payload: `{"sub": <user UUID>, "role": <role>, "exp": <expiry>}`; expiry = `JWT_EXPIRE_MINUTES` (480 min default).
- HTTPBearer dependency (`security_scheme = HTTPBearer()`) makes every protected route require the `Authorization: Bearer` header.
- Table creation is automatic on startup (`Base.metadata.create_all`) in `main.py` lifespan, alongside scheduler startup — Alembic is available for schema evolution.
- The audit-service (`log_action`) exists but the current route handlers do not systematically call it; audit-logs API reads the `audit_logs` table (populated by future/partial instrumentation).

---

## 5. Frontend Structure

```
frontend/
├── Dockerfile                  # multi-stage: node:18-alpine build → nginx:alpine
├── nginx.conf                  # static SPA + /api/ reverse proxy + gzip + SPA fallback
├── vite.config.js              # dev server :5173, /api proxy → :8000, @ alias
└── src/
    ├── main.js                 # createApp + Pinia + Router + Element Plus + all icons
    ├── App.vue
    ├── api/
    │   ├── request.js          # Axios instance: baseURL '/api/v1', 30s timeout,
    │   │                       #   token injection, envelope/code unwrap,
    │   │                       #   401 → logout & redirect to /login
    │   └── index.js            # typed API groups: authApi, customerApi, contractApi,
    │                           #   taskApi, documentApi, communicationApi, paymentApi,
    │                           #   boardApi, dashboardApi, userApi, notificationApi,
    │                           #   followUpApi, auditLogApi, dictApi, searchApi
    ├── router/index.js         # history router; routes: /login, /kanban (default),
    │                           #   /customer/list, /customer/:id, /dashboard, /users
    │                           #   (admin), /notifications, /follow-ups, /audit-logs,
    │                           #   /dict (admin), /import-export, /profile
    │                           #   beforeEach guard: token check + route meta.roles
    ├── stores/                 # Pinia: user (token/userInfo/role getters, login/logout),
    │                           #   customer (kanbanData, customerList, CRUD actions),
    │                           #   notification (list, unreadCount, mark read/all)
    ├── components/             # AppLayout (navbar+sidebar), CustomerCard, StageTag,
    │                           #   AlertBadge, NotificationBell, GlobalSearch
    ├── views/                  # 12 pages (Login, Kanban, CustomerList, CustomerDetail,
    │                           #   Dashboard, UserManage, NotificationList, FollowUpList,
    │                           #   AuditLog, DictManage, ImportExport, Profile)
    └── styles/                 # global.css, variables.css (stage & alert colors, design tokens)
```

**Conventions:**
- Router guard: unauthenticated users are redirected to `/login`; role-restricted routes (Users, Data Dictionary → `roles: ['admin']`) reject non-admins.
- Axios response interceptor unwraps the `{code, message, data}` envelope — a non-zero `code` raises an error toast; HTTP 401 clears the token and redirects to login; 403/404/422/500 produce contextual toasts.
- Stage/alert colors are centralized in `styles/variables.css` (see §6.3).
- Dev mode: Vite proxies `/api` to `http://localhost:8000`; production: Nginx proxies `/api/` to `http://backend:8000`.

---

## 6. Core Business Logic

### 6.1 The 8-Stage Kanban Workflow

Defined in `services/stage_service.py` (`STAGES`):

| Stage | Name        | BASE_DAYS (normal) | ALERT_DAYS (danger) | Meaning |
|-------|-------------|--------------------|---------------------|---------|
| 1     | Lead        | 7                  | 14                  | New lead, initial contact |
| 2     | Consult     | 14                 | 21                  | Needs analysis & consultation |
| 3     | Contract    | 7                  | 14                  | Contract signing, deposit |
| 4     | Requirements| 14                 | 21                  | Requirement analysis & specification |
| 5     | Service     | 30                 | 45                  | Delivery/implementation |
| 6     | Delivery    | 14                 | 21                  | Acceptance & handover |
| 7     | Payment     | 30                 | 45                  | Collection & invoicing |
| 8     | Completed   | 0                  | 0                   | Closed/archived |

- A customer is created at stage 1 with `stage_entered_at = now()`.
- Advancement is **strictly sequential**: `new_stage` must equal `current_stage + 1` (`"Stages can only advance sequentially..."` otherwise).
- Only customers with `status == 'active'` may advance; reaching stage 8 flips status to `completed`.
- Every transition appends a `stage_histories` row (`from_stage`, `to_stage`, `changed_by`, `remark`) and resets `stage_entered_at`.

### 6.2 Stage Prerequisites (enforced in `_check_prerequisites`)

| Transition | Prerequisite |
|------------|--------------|
| 2 → 3 (→ Contract) | At least one **contract** with a non-null `sign_date` exists → else `400 "Please sign a contract before advancing to Contract stage"` |
| 5 → 6 (→ Delivery) | **All tasks** for the customer are `completed` (zero non-completed tasks) → else `400 "Please complete all tasks before advancing to Delivery stage"` |
| 6 → 7 (→ Payment) | At least one **document** with `category == 'acceptance'` exists → else `400 "Please upload customer acceptance documents before advancing to Payment stage"` |
| 7 → 8 (→ Completed) | **Full payment**: `paid_amount >= contract_amount` → else `400 "Please ensure full payment is received before advancing to Completed stage"` |

### 6.3 Alert System (stay-time based)

Computed on the fly by `get_alert_level(customer)` and `get_stay_days(customer)`:

- `stay_days = now - stage_entered_at` (days).
- `alert_level`:
  - `stay_days >= ALERT_DAYS[stage]` → **danger** (`#FF4D4F`)
  - `stay_days >= BASE_DAYS[stage]` → **warning** (`#FAAD14`)
  - otherwise → **normal** (`#52C41A`)

The alert level is returned in every customer payload, kanban cards, and the `GET /board/alerts` list (danger sorted first). Stage colors (frontend):

| Stage | Color | Background |
|-------|-------|------------|
| 1 Lead | `#909399` | `#f4f4f5` |
| 2 Consult | `#409EFF` | `#ecf5ff` |
| 3 Contract | `#36CFC9` | `#e6fffb` |
| 4 Requirements | `#E6A23C` | `#fdf6ec` |
| 5 Service | `#722ED1` | `#f9f0ff` |
| 6 Delivery | `#67C23A` | `#f0f9eb` |
| 7 Payment | `#2F54EB` | `#f0f5ff` |
| 8 Completed | `#389E0D` | `#f6ffed` |

### 6.4 Rollback (admin only)

`PUT /api/v1/customers/{id}/rollback`:
- Requires role `admin` (else 403).
- Moves back exactly one stage (`current - 1`).
- Rejected if already at stage 1 or if `status != 'active'`.
- Also records a `stage_histories` row (remark defaults to `"Rolled back from stage X to Y"`) and resets `stage_entered_at`.

### 6.5 Kanban Board

`services/board_service.py`:
- `get_kanban_data` filters active customers (optional `sales_id`/`region`/`source_channel`), groups them into 8 stage columns ordered by `stage_entered_at`, and enriches each card with `stay_days`, `alert_level`, amounts and timestamps.
- `get_kanban_alerts` returns all active customers with `warning`/`danger` levels, sorted by danger-first then stay days descending.

---

## 7. Permission Model (Role Matrix)

Implemented in `core/deps.py` (`check_customer_access`, `check_customer_readonly`, `check_task_access`, `check_comm_access`) plus inline role checks in route handlers. **Own** = `customer.sales_id == current_user.id`.

| Module / Operation | Admin | Sales | PM | CS |
|--------------------|-------|-------|-----|-----|
| Customer list/search/export | All | Own customers only | All (read) | Own customers only |
| Customer detail / stage / status | All | Own customers | All (read) | Own customers (read) |
| Customer update | All | Own customers | No (403) | No (403) |
| Customer delete / rollback | Yes | No | No | No |
| Batch assign / status | Yes | Own customers only | Own customers only | Own customers only |
| Batch delete | Yes | No | No | No |
| Contracts (read/write) | All | Own customers | Own customers (read) | Own customers (read) |
| Tasks read | All | Own customers | Assigned to self | Own customers |
| Tasks write (create/update/status/assignee/delete) | All | Own customers | Own assigned tasks only | No |
| Documents (read/write) | All | Own customers | Own customers (read) | Own customers (read) |
| Communications (read/write) | All | Own customers | Own customers | Own customers |
| Payments (all ops) | All | Own customers | Own customers (read) | Own customers (read) |
| Follow-ups | All | All (own records) | All | All |
| Audit logs | All | All | All | All |
| Data dictionary GET | All | All | All | All |
| Data dictionary PUT | Yes | No | No | No |
| User create/update/reset password | Yes | No | No | No |
| User list / own profile | All | All | All | All |
| Dashboard / Board / Notifications | All | All | All | All |

**Note:** the matrix above reflects the current implementation (enforced by `core/deps.py` — `check_customer_access` for reads, `check_customer_write_access` for writes, `check_task_access`/`check_comm_access` for task/communication objects, and inline role checks for admin-only endpoints). In the delivery hardening, customer lists, advanced search, kanban, alerts, global search, export, follow-up CRUD and batch operations were all scoped so that sales/CS only see their own customers; batch delete is admin-only.

---

## 8. Authentication & Security

### 8.1 Login & JWT Flow

1. `POST /api/v1/auth/login` verifies email + bcrypt password, checks `is_active`, then issues a token via `create_access_token({"sub": user_id, "role": role})`.
2. `python-jose` signs the payload with HS256 using `JWT_SECRET`; expiry = `JWT_EXPIRE_MINUTES` (default 480 min).
3. Every protected endpoint resolves `get_current_user` (HTTPBearer) → decodes token → loads the user row → `get_current_active_user` rejects disabled accounts.
4. `POST /api/v1/auth/refresh` re-issues a token from a still-valid token (it decodes the existing token rather than using a separate refresh-token store).
5. Registration (`POST /auth/register`) is self-service and stores the account in the MySQL `users` table: email/phone uniqueness checks → bcrypt-hash the password → insert a row with default role `sales` and `is_active = 1` → issue a JWT (auto-login) so no second login step is needed. Any visitor can register; an admin can later change the role.
6. The frontend keeps the token in `localStorage` and attaches `Authorization: Bearer <token>` via an Axios interceptor; a `401` clears the token and redirects to `/login`.
7. Passwords are only ever stored as bcrypt hashes (`passlib.CryptContext(schemes=["bcrypt"])`); self-service change verifies the current password first, admin reset writes a new hash directly.

### 8.2 Password Hashing

- `passlib.CryptContext(schemes=["bcrypt"], deprecated="auto")` — passwords are never stored in plain text.
- `verify_password` is used for login and for self-service password change (which requires the current password).
- Admin reset (`PUT /users/{id}/password`) sets a new hash directly.

### 8.3 CORS

`main.py` enables `CORSMiddleware` with `allow_origins=["*"]`, `allow_credentials=True`, all methods/headers — permissive development default; tighten before production exposure.

### 8.4 Security considerations (production checklist)

- Replace default `JWT_SECRET` (currently `"super-secret-key-change-in-production"`).
- CORS `*` + `allow_credentials=True` is not recommended for production — restrict origins.
- Rate limiting on `/auth/login` is not implemented (brute-force risk).
- Uploaded files are served by filename from local disk; no extension/MIME whitelist is enforced.
- The envelope unwrap in the frontend means business-code responses (`code != 0`) are surfaced as toasts.

---

## 9. Background Scheduler

Started in the FastAPI lifespan (`main.py`) with `AsyncIOScheduler`:

| Job | Interval | Lock key | Rule |
|-----|----------|----------|------|
| `check_lead_timeout` | every 6 h | `scheduler:lead_timeout` | Stage-1 active customers with **no communication for > 30 days** (or created > 30 days ago with none) → `status = 'lost'`, `lost_reason = "Auto-marked: No communication for over 30 days in Lead stage"`, notification `type='auto_lost'` to the salesperson |
| `check_task_due` | every 1 h | `scheduler:task_due` | Tasks with `due_date == today` and status `pending`/`in_progress` → notification `type='task_due'` to the assignee |
| `check_payment_overdue` | every 6 h | `scheduler:payment_overdue` | Customers in stage 7, active, `stage_entered_at` older than 30 days, and `contract_amount > paid_amount` → notification `type='payment_overdue'` to the salesperson; admins also notified once per day (deduplicated by `related_id` + `created_at` date) |

### Redis distributed lock

Because uvicorn runs **4 workers**, the same job would otherwise run 4×. `_acquire_lock(name, timeout)` uses `SET lock_name 1 NX EX timeout` (Redis) and returns `True` only for the winner; `_release_lock` deletes the key. If Redis is unavailable, the lock is skipped (jobs still run, trading duplicate execution for availability). Each job opens its own `SessionLocal()` session and commits independently.

---

## 10. Concurrency Design

| Aspect | Configuration |
|--------|---------------|
| App servers | 4 uvicorn workers (`--workers 4` in Dockerfile CMD) |
| DB connection pool | `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=3600`, `pool_timeout=30` (in `database.py`) |
| Sessions | `SessionLocal` per request via `get_db` dependency (yield-scoped, closed in `finally`) |
| Scheduler dedup | Redis `SET NX EX` distributed locks (§9) |
| Redis cache | Redis is provisioned and used for locks; no business-data caching layer is implemented yet (planned) |
| Payments consistency | `paid_amount` is updated in the same transaction as the payment row (`db.flush()` then `db.commit()`), preserving atomicity; update/delete recompute the delta |

**Scaling rationale:** 4 workers × 10-pool = up to 40 concurrent DB sessions baseline (20 overflow each) — comfortably above the 100-user target for typical CRUD workloads. `pool_pre_ping` avoids serving requests after a stale MySQL connection (e.g., container restarts).

---

## 11. Deployment (Docker Compose)

`docker-compose.yml` (version 3.8) — 5 services on a shared `crm-network` bridge:

| Service   | Image / Build            | Ports            | Depends on | Notes |
|-----------|--------------------------|------------------|------------|-------|
| `mysql`   | `mysql:8.0`              | 3306:3306        | —          | utf8mb4/utf8mb4_unicode_ci; DB `crm`, user `crm`; named volume `mysql_data`; healthcheck via `mysqladmin ping` |
| `redis`   | `redis:7`                | 6379:6379        | —          | named volume `redis_data` |
| `minio`   | `minio/minio`            | 9000:9000, 9001:9001 | —     | S3-compatible storage; console on 9001; named volume `minio_data` |
| `backend` | `./backend` (python:3.11-slim) | 8000:8000    | mysql (healthy), redis, minio | env: `DATABASE_URL`, `REDIS_URL`, `MINIO_*`, `JWT_SECRET`; CMD `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4` |
| `frontend`| `./frontend` (node:18-alpine → nginx:alpine) | 80:80 | backend | serves built SPA; Nginx proxies `/api/` → `http://backend:8000` |

**Nginx (frontend container):** serves static assets from `/usr/share/nginx/html`, gzip enabled for text/JSON, `/assets/` cached immutable for 1 year, SPA fallback `try_files $uri $uri/ /index.html`, `/api/` reverse-proxied to the backend service with X-Real-IP / X-Forwarded-For headers and 60s timeouts.

**Environment variables** (`.env`, consumed by compose; template in `.env.example`):

| Variable         | Used by            | Description                              |
|------------------|--------------------|------------------------------------------|
| `DB_PASSWORD`    | mysql, backend     | MySQL user/root password; part of `DATABASE_URL` |
| `MINIO_USER`     | minio, backend     | MinIO root user (also `MINIO_ACCESS_KEY`) |
| `MINIO_PASSWORD` | minio, backend     | MinIO root password (also `MINIO_SECRET_KEY`) |
| `JWT_SECRET`     | backend            | HS256 signing secret                      |

**Backend env (from compose):** `DATABASE_URL=mysql+pymysql://crm:${DB_PASSWORD}@mysql:3306/crm?charset=utf8mb4`, `REDIS_URL=redis://redis:6379/0`, `MINIO_ENDPOINT=minio:9000`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `JWT_SECRET`.

**Startup:** `Base.metadata.create_all()` auto-creates tables; an admin user must be created manually (the README references a `create_admin` script).

---

## 12. Scaling Roadmap (100+ Users)

Current architecture already handles 100+ users; the following items harden and extend it:

**Short term (correctness first):**
1. Route-ordering fixes: `GET /customers/advanced-search` and `GET /customers/export` are shadowed by `GET /customers/{id}` (UUID path param matches first, yielding 422) — move static paths above the parameterized route or rename paths.
2. Frontend/backend contract alignment: the frontend `api/index.js` calls several paths that do not exist on the backend (`/customers/{id}/advance-stage`, `POST /customers/{id}/assign`, `PUT /customers/batch/status`, `POST /contracts`, `GET /contracts/customer/{id}`, generic `/tasks`, `/documents/upload`, `/communications`, `/payments`, `/follow-ups`, `/audit-logs/customer/{id}`, `/search`); align or remove.
3. Add role checks to batch endpoints (§7) if admin-only is intended; wire `audit_service.log_action` into the write handlers.
4. Enforce upload validation (extension/size whitelist) and move file storage to MinIO (client already configured).

**Medium term (performance & ops):**
5. Introduce Redis caching for hot reads: dashboard stats, board/kanban, dict items (with invalidation on writes).
6. Add DB indexes on filtered columns (`customers.status`, `customers.current_stage`, `customers.sales_id`, `tasks.due_date`, `notifications.user_id`, `audit_logs.customer_id`).
7. Add a reverse proxy rate limiter (e.g. Nginx `limit_req`) for `/auth/login` and upload endpoints.
8. Centralize logging (JSON logs → stdout), add request-id correlation and structured metrics for the scheduler jobs.

**Long term (scale-out):**
9. Move the scheduler out-of-process (a dedicated worker container) so backend scaling doesn't multiply job instances; keep Redis locks as a safety net.
10. Horizontal scaling: stateless backend behind a load balancer (already stateless apart from local file uploads — move to MinIO first); MySQL read replicas or a managed service; paginate/partition `audit_logs`.
11. WebSocket/SSE push for notifications instead of polling `unread-count`.
12. CI/CD pipeline with lint (flake8/black/eslint), tests, image build, and migration-on-deploy (`alembic upgrade head`) instead of `create_all`.

---

## 13. Demo / Test Accounts (designed for acceptance testing)

The seed script (`backend/app/scripts/seed_demo.py`) provisions one demo account per role so every permission level can be verified during acceptance testing. All accounts share the password **`demo123456`** and are created idempotently (safe to re-run; if `demo.admin@crm.com` already exists the script skips without changing data).

| Role    | Purpose in test design                       | Email                | Password    |
|---------|----------------------------------------------|----------------------|-------------|
| admin   | Full access: user management, batch ops, deletes, dictionary maintenance | `demo.admin@crm.com` | `demo123456` |
| sales   | Verify own-customer isolation (list/kanban/search/export all show only the salesperson's own customers) | `zhangwei@crm.com`<br>`lina@crm.com`<br>`wangfang@crm.com` | `demo123456` |
| pm      | Global read-only + tasks assigned to self    | `chenjie@crm.com`    | `demo123456` |
| cs      | Read-only on own customers                   | `liuyang@crm.com`    | `demo123456` |

Key acceptance scenarios covered by these accounts:

1. **Data volume** — the seed also creates ~35 customers distributed across all 8 stages (with contracts, tasks, documents, communications, payments and notifications), so boards/dashboards/export have realistic data to display.
2. **Permission isolation** — log in as `zhangwei@crm.com` (sales) and confirm the kanban/客户列表 only show his own customers; attempting to update another salesperson's customer returns 403.
3. **Stage gating** — advance customers through the pipeline and confirm prerequisites (§6.2) block invalid transitions.
4. **Scheduler notifications** — the seeded follow-ups/due dates generate `task_due` / `auto_lost` / `payment_overdue` notifications that appear in the notification bell.
5. **Production note** — always change these default passwords (or disable the seed) before exposing the system publicly (§11 security checklist).
