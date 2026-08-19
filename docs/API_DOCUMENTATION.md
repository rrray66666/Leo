# CRM System — REST API Documentation

**Project:** CRM System (Customer Relationship Management)
**Version:** 1.0.0
**Base URL:** `http://localhost:8000` (or `http://localhost/api/v1` when accessed through the Nginx reverse proxy)

This document describes every HTTP endpoint exposed by the FastAPI backend. All routes are registered under the `/api/v1` prefix (the router modules declare their own sub-prefixes, e.g. `/api/v1/customers`).

---

## 1. General Conventions

### 1.1 Response Envelope

Every endpoint wraps its payload in a uniform envelope:

```json
{
  "code": 0,
  "message": "success",
  "data": { }
}
```

| Field     | Type   | Description                                            |
|-----------|--------|--------------------------------------------------------|
| `code`    | int    | `0` = success. Non-zero codes are used for business errors (e.g. `4004` = not found, `4003` = permission denied in some legacy endpoints). |
| `message` | string | Human-readable result message.                          |
| `data`    | any    | Payload. `null` when there is no payload (e.g. after a delete). |

### 1.2 Error Responses

Two error conventions are used in the codebase:

1. **HTTP exceptions (primary).** FastAPI `HTTPException` responses return the standard shape with an HTTP status code:
   ```json
   { "detail": "Customer not found" }
   ```
   Common status codes:
   - `400 Bad Request` — validation/business-rule failure (e.g. prerequisite not met, duplicate phone)
   - `401 Unauthorized` — missing/invalid/expired JWT, bad credentials
   - `403 Forbidden` — authenticated but insufficient role/ownership
   - `404 Not Found` — resource does not exist
   - `422 Unprocessable Entity` — request body/query fails Pydantic validation (FastAPI auto-generated)
   - `500 Internal Server Error` — unhandled exception

2. **Business-code responses (legacy).** A few endpoints (customer export) return HTTP 200 with a non-zero business code:
   ```json
   { "code": 4004, "message": "Customer not found" }
   ```

### 1.3 Authentication

- Login (`POST /api/v1/auth/login`) returns a JWT `access_token` (HS256).
- All protected endpoints require the header: `Authorization: Bearer <access_token>`.
- Token lifetime: `JWT_EXPIRE_MINUTES = 480` minutes (8 hours) by default.
- The frontend stores the token in `localStorage` and attaches it via an Axios request interceptor.
- The `GET /api/v1/auth/me` endpoint can be used to validate a token and fetch the current user.

### 1.4 Roles

| Role    | Name        |
|---------|-------------|
| `admin` | Administrator |
| `sales` | Salesperson |
| `pm`    | Project Manager |
| `cs`    | Customer Service |

### 1.5 Pagination

List endpoints use `page` (default `1`, min `1`) and `page_size` (default `20`, max `100`) query parameters and return:

```json
{
  "items": [ ],
  "total": 123,
  "page": 1,
  "page_size": 20
}
```

### 1.6 Interactive Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `GET /health` → `{"status": "ok", "message": "Service is running normally"}`

---

## 2. Authentication (`/api/v1/auth`)

### 2.0 Login & Registration Design

**Account sources.** Every account is persisted in the MySQL `users` table (Database Schema §2). Accounts are created in three ways:

1. **Self-service registration** — `POST /auth/register`; any visitor can create an account. Default role is `sales`; an admin can upgrade the role later (`PUT /users/{id}`).
2. **Admin-created users** — `POST /users` (admin only) provisions accounts with an explicit role (`admin | sales | pm | cs`).
3. **Demo seed** — `python -m app.scripts.seed_demo` creates 6 demo accounts (1 admin + 3 sales + 1 pm + 1 cs), all with password `demo123456`.

**Registration flow (self-service):**

1. The login page switches to Register mode; the form is validated client-side (name 2–50 chars, e-mail format, password ≥ 6 chars, confirm-password match).
2. The client calls `POST /api/v1/auth/register` with `{ name, email, phone?, password }`.
3. The backend checks `email` uniqueness, then `phone` uniqueness (both columns are UNIQUE in MySQL) — duplicates return `400`.
4. The password is hashed with **bcrypt** (`get_password_hash`); plain text is never stored.
5. A new row is inserted into `users` with `role = 'sales'` and `is_active = 1`, then committed — the account is now permanently stored in MySQL.
6. The API issues a JWT immediately (auto-login), so the user is signed in without a second login step.

**Login flow:**

1. The client submits `{ email, password }` to `POST /api/v1/auth/login`.
2. The backend looks up the user by e-mail; if the account does not exist → `401 "Invalid email or password"`.
3. `verify_password` compares the bcrypt hash; a mismatch → `401` (same message, avoids user enumeration).
4. If `is_active = 0` → `403 "User has been disabled"`.
5. On success a JWT is issued (HS256; payload `{ sub: user_id, role }`; expires in `JWT_EXPIRE_MINUTES = 480`) together with the user profile.

**Token handling (frontend):** the token is stored in `localStorage`; an Axios request interceptor attaches `Authorization: Bearer <token>` to every request. A `401` response clears the token and redirects to `/login`.

**Password security:** bcrypt via `passlib.CryptContext(schemes=["bcrypt"], deprecated="auto")`. Self-service password change (`PUT /users/me/password`) verifies the current password first; admin reset (`PUT /users/{id}/password`) writes a new hash directly. No password is ever stored or transmitted in plain text.

**Storage:** all accounts live in the MySQL `users` table — there is no separate identity provider or in-memory store.

### 2.1 POST `/api/v1/auth/login`

User login. Returns a JWT and the user profile.

- **Auth required:** No
- **Request body (JSON):**

| Field      | Type   | Required | Description          |
|------------|--------|----------|----------------------|
| `email`    | string | Yes      | Registered e-mail (max 100 chars) |
| `password` | string | Yes      | Plain-text password  |

```json
{
  "email": "admin@example.com",
  "password": "secret123"
}
```

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Admin",
      "email": "admin@example.com",
      "phone": "13800000000",
      "role": "admin",
      "is_active": true,
      "created_at": "2026-01-01T08:00:00"
    }
  }
}
```

- **Errors:** `401` "Invalid email or password"; `403` "User has been disabled" (inactive account).

### 2.2 POST `/api/v1/auth/register`

Self-service registration. The new user is created with the default role `sales` and is immediately logged in (auto-login returns a token).

- **Auth required:** No
- **Request body (JSON):**

| Field      | Type   | Required | Description                          |
|------------|--------|----------|--------------------------------------|
| `name`     | string | Yes      | Display name (2–50 chars)            |
| `email`    | string | Yes      | Unique e-mail (max 100 chars)        |
| `phone`    | string | No       | Phone number (max 20 chars)          |
| `password` | string | Yes      | Password (6–100 chars)               |

```json
{
  "name": "John Sales",
  "email": "john@example.com",
  "phone": "13900000000",
  "password": "secret123"
}
```

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "John Sales",
      "email": "john@example.com",
      "role": "sales"
    }
  }
}
```

- **Errors:** `400` "Email already registered"; `400` "Phone number already registered".

### 2.3 POST `/api/v1/auth/refresh`

Issues a fresh access token for a still-valid token.

- **Auth required:** No (the expired/current token is supplied in the body)
- **Request body (JSON):**

| Field          | Type   | Required | Description      |
|----------------|--------|----------|------------------|
| `access_token` | string | Yes      | Existing JWT     |
| `token_type`   | string | No       | Default `bearer` |

```json
{ "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": { "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer" }
}
```

- **Errors:** `401` "Invalid refresh token"; `401` "User not found or disabled".

### 2.4 GET `/api/v1/auth/me`

Returns the profile of the authenticated user.

- **Auth required:** Yes
- **Query parameters:** None
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Admin",
    "email": "admin@example.com",
    "phone": "13800000000",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-01-01T08:00:00"
  }
}
```

- **Errors:** `401` invalid token; `403` "User has been disabled".

---

## 3. User Management (`/api/v1/users`)

### 3.1 POST `/api/v1/users/`

Create a user. **Admin only.**

- **Auth required:** Yes (role `admin`)
- **Request body (JSON):**

| Field      | Type   | Required | Description                          |
|------------|--------|----------|--------------------------------------|
| `name`     | string | Yes      | Name (1–50 chars)                    |
| `email`    | string | Yes      | Unique e-mail (max 100 chars)        |
| `phone`    | string | Yes      | Phone (max 20 chars)                 |
| `password` | string | Yes      | Password (6–100 chars)               |
| `role`     | string | Yes      | One of `admin`, `sales`, `pm`, `cs`  |

```json
{
  "name": "New PM",
  "email": "pm@example.com",
  "phone": "13700000000",
  "password": "secret123",
  "role": "pm"
}
```

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "New PM",
    "email": "pm@example.com",
    "phone": "13700000000",
    "role": "pm",
    "is_active": true,
    "created_at": "2026-08-05T09:00:00"
  }
}
```

- **Errors:** `400` "Email already registered"; `403` "Admin privileges required".

### 3.2 GET `/api/v1/users/`

List all users, ordered by creation time (newest first).

- **Auth required:** Yes
- **Query parameters:** None
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Admin",
      "email": "admin@example.com",
      "phone": "13800000000",
      "role": "admin",
      "is_active": true,
      "created_at": "2026-01-01T08:00:00"
    }
  ]
}
```

- **Errors:** `401` invalid token.

### 3.3 PUT `/api/v1/users/{id}`

Update a user. **Admin only.**

- **Auth required:** Yes (role `admin`)
- **Path parameters:** `id` (UUID) — target user id
- **Request body (JSON)** — all fields optional:

| Field       | Type    | Description                                |
|-------------|---------|--------------------------------------------|
| `name`      | string  | Name (max 50 chars)                        |
| `email`     | string  | E-mail (max 100 chars)                     |
| `phone`     | string  | Phone (max 20 chars)                       |
| `is_active` | boolean | Enable/disable the account                 |
| `role`      | string  | One of `admin`, `sales`, `pm`, `cs`        |

```json
{ "role": "pm", "is_active": true }
```

- **Success response (200):** user object (same shape as 3.1).
- **Errors:** `404` "User not found"; `403` "Admin privileges required".

### 3.4 PUT `/api/v1/users/{id}/password`

Reset another user's password. **Admin only.**

- **Auth required:** Yes (role `admin`)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):**

| Field         | Type   | Required | Description          |
|---------------|--------|----------|----------------------|
| `new_password`| string | Yes      | New password (6–100 chars) |

```json
{ "new_password": "newSecret123" }
```

- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `404` "User not found"; `403` "Admin privileges required".

### 3.5 GET `/api/v1/users/me`

Current user info (same as `GET /api/v1/auth/me`).

- **Auth required:** Yes
- **Success response (200):** user object.

### 3.6 PUT `/api/v1/users/me`

Update own profile. The `role` and `is_active` fields are always excluded from the update.

- **Auth required:** Yes
- **Request body (JSON):** any of `name`, `email`, `phone` (all optional)

```json
{ "name": "New Display Name" }
```

- **Success response (200):** updated user object.
- **Errors:** `401` invalid token.

### 3.7 PUT `/api/v1/users/me/password`

Change own password. Verifies the current password first.

- **Auth required:** Yes
- **Request body (JSON):**

| Field          | Type   | Required | Description           |
|----------------|--------|----------|-----------------------|
| `old_password` | string | Yes      | Current password      |
| `new_password` | string | Yes      | New password (6–100)  |

```json
{ "old_password": "secret123", "new_password": "newSecret123" }
```

- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `400` "Incorrect original password".

---

## 4. Customers (`/api/v1/customers`)

### 4.1 POST `/api/v1/customers/`

Create a customer. The new customer starts at **stage 1 (Lead)** with status **active** and `stage_entered_at` set to now. Phone must be unique.

- **Auth required:** Yes
- **Request body (JSON):**

| Field            | Type    | Required | Description                     |
|------------------|---------|----------|---------------------------------|
| `name`           | string  | Yes      | Customer name (1–100 chars)     |
| `contact_person` | string  | Yes      | Contact person (max 50 chars)   |
| `phone`          | string  | Yes      | Phone (max 20 chars, unique)    |
| `wechat`         | string  | No       | WeChat id (max 50 chars)        |
| `email`          | string  | No       | E-mail (max 100 chars)          |
| `company`        | string  | No       | Company (max 200 chars)         |
| `region`         | string  | No       | Region (max 50 chars)           |
| `source_channel` | string  | No       | Source channel (max 50 chars)   |
| `sales_id`       | UUID    | No       | Assigned salesperson id         |

```json
{
  "name": "Acme Corp",
  "contact_person": "Alice",
  "phone": "13600000000",
  "wechat": "alice_acme",
  "email": "alice@acme.com",
  "company": "Acme Corp Ltd",
  "region": "Shanghai",
  "source_channel": "exhibition",
  "sales_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

- **Success response (200):** customer object (see 4.2 for shape; includes computed `stay_days` and `alert_level`).
- **Errors:** `400` "Phone number already exists".

### 4.2 GET `/api/v1/customers/`

List customers with pagination and filters.

- **Auth required:** Yes
- **Query parameters:**

| Parameter   | Type    | Required | Description                        |
|-------------|---------|----------|------------------------------------|
| `page`      | int     | No       | Page number (≥1, default 1)        |
| `page_size` | int     | No       | Page size (1–100, default 20)      |
| `keyword`   | string  | No       | Searches name / contact / phone / wechat / company / email (fuzzy) |
| `stage`     | int     | No       | Filter by current stage (1–8)      |
| `status`    | string  | No       | Filter by status (`active`/`lost`/`completed`/`terminated`) |
| `sales_id`  | UUID    | No       | Filter by assigned salesperson     |
| `region`    | string  | No       | Filter by region (exact)           |
| `alert_level` | string | No      | Filter by `normal` / `warning` / `danger` |

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "Acme Corp",
        "contact_person": "Alice",
        "phone": "13600000000",
        "wechat": "alice_acme",
        "email": "alice@acme.com",
        "company": "Acme Corp Ltd",
        "region": "Shanghai",
        "source_channel": "exhibition",
        "sales_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "sales_name": "John Sales",
        "current_stage": 1,
        "stage_entered_at": "2026-08-05T09:00:00",
        "contract_amount": 0.0,
        "paid_amount": 0.0,
        "status": "active",
        "lost_reason": null,
        "created_at": "2026-08-05T09:00:00",
        "updated_at": "2026-08-05T09:00:00",
        "stay_days": 0,
        "alert_level": "normal"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

- **Errors:** `401` invalid token; `422` invalid parameter types.

### 4.3 GET `/api/v1/customers/{id}`

Customer detail. Access rule: `admin` → all customers; `sales` → only customers where `sales_id` equals the caller; other roles → denied.

- **Auth required:** Yes
- **Path parameters:** `id` (UUID)
- **Success response (200):** customer object (as in 4.2, without pagination wrapper).
- **Errors:** `404` "Customer not found"; `403` "Permission denied".

### 4.4 PUT `/api/v1/customers/{id}`

Update customer information. If `phone` changes, uniqueness is re-validated.

- **Auth required:** Yes (access rules as 4.3)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):** any subset of the `CustomerCreate` fields (all optional)

```json
{ "company": "Acme Corp International", "region": "Beijing" }
```

- **Success response (200):** updated customer object.
- **Errors:** `404` "Customer not found"; `400` "Phone number already in use by another customer"; `403` permission denied.

### 4.5 DELETE `/api/v1/customers/{id}`

Soft-delete a customer. **Admin only.** Sets `status = "deleted"` and writes a `delete` audit log.

- **Auth required:** Yes (role `admin`)
- **Path parameters:** `id` (UUID)
- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `404` "Customer not found"; `403` "Permission denied: only admins can delete customers".

### 4.6 PUT `/api/v1/customers/{id}/stage`

Advance a customer to the next stage.

Rules enforced by `stage_service.advance_stage`:
- Only **sequential** advancement is allowed (`new_stage == current_stage + 1`).
- Customer status must be `active`.
- Prerequisites per transition (see Architecture doc §6):
  - 2→3: at least one contract with `sign_date` set
  - 5→6: all tasks completed
  - 6→7: at least one document with `category = "acceptance"`
  - 7→8: `paid_amount >= contract_amount`
- Reaching stage 8 sets status to `completed`.
- A `stage_histories` row is appended and `stage_entered_at` is reset.

- **Auth required:** Yes (access rules as 4.3)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):**

| Field      | Type   | Required | Description              |
|------------|--------|----------|--------------------------|
| `new_stage`| int    | Yes      | Target stage (1–8)       |
| `remark`   | string | No       | Remark (default `""`)    |

```json
{ "new_stage": 2, "remark": "Initial consultation done" }
```

- **Success response (200):** customer object (with updated `current_stage` and `stage_entered_at`).
- **Errors:** `400` "Invalid stage number"; `400` "Stages can only advance sequentially..."; `400` "Customer status is '...', cannot advance stage..."; `400` prerequisite messages (e.g. "Please sign a contract before advancing to Contract stage"); `404` "Customer not found".

### 4.7 PUT `/api/v1/customers/{id}/status`

Update customer status and optional lost reason.

- **Auth required:** Yes (access rules as 4.3)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):**

| Field         | Type   | Required | Description                                   |
|---------------|--------|----------|-----------------------------------------------|
| `status`      | string | Yes      | One of `active`, `lost`, `completed`, `terminated` |
| `lost_reason` | string | No       | Reason (used when marking lost)               |

```json
{ "status": "lost", "lost_reason": "Budget cut by customer" }
```

- **Success response (200):** customer object.
- **Errors:** `404` "Customer not found"; `403` permission denied.

### 4.8 PUT `/api/v1/customers/{id}/assign`

Transfer a single customer to another salesperson.

- **Auth required:** Yes
- **Path parameters:** `id` (UUID)
- **Request body (JSON):**

| Field          | Type   | Required | Description                     |
|----------------|--------|----------|---------------------------------|
| `customer_ids` | array  | Yes      | Array with the customer id(s) (the endpoint uses only the path id for single assign; body schema is shared with batch assign) |
| `new_sales_id` | UUID   | Yes      | Target user id (role must be `sales` or `admin`) |

```json
{ "customer_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"], "new_sales_id": "1b4e28ba-2fa1-11d2-883f-b9a761bde3fb" }
```

- **Success response (200):**

```json
{ "code": 0, "message": "success", "data": { "affected": 1 } }
```

- **Errors:** `400` "New sales person not found or incorrect role".

### 4.9 PUT `/api/v1/customers/{id}/rollback`

Roll the customer back one stage (new stage = current − 1). **Admin only.**

- **Auth required:** Yes (role `admin`)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):** `StageAdvance` — `new_stage` (1–8), `remark` (string)

```json
{ "new_stage": 3, "remark": "Contract terms need renegotiation" }
```

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Acme Corp",
    "current_stage": 3,
    "stage_entered_at": "2026-08-05T10:00:00",
    "status": "active"
  }
}
```

- **Errors:** `400` "Cannot rollback from the first stage"; `400` "Customer status is '...', cannot rollback stage."; `404` "Customer not found"; `403` "Admin privileges required".

### 4.10 GET `/api/v1/customers/{id}/timeline`

Chronological activity timeline for a customer, merging stage changes, communication records and audit logs (newest first).

- **Auth required:** Yes
- **Path parameters:** `id` (UUID)
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "type": "stage_change",
      "id": "c0a80121-0000-4000-8000-000000000001",
      "time": "2026-08-05T09:30:00",
      "data": { "from_stage": 1, "to_stage": 2, "remark": "Consult", "operator_id": "3fa85f64-..." }
    },
    {
      "type": "communication",
      "id": "c0a80121-0000-4000-8000-000000000002",
      "time": "2026-08-05T09:00:00",
      "data": { "channel": "phone", "content": "Discussed needs", "user_id": "3fa85f64-..." }
    },
    {
      "type": "audit_log",
      "id": "c0a80121-0000-4000-8000-000000000003",
      "time": "2026-08-05T08:59:00",
      "data": { "action": "create", "object_type": "customer", "user_id": "3fa85f64-..." }
    }
  ]
}
```

- **Errors:** `401` invalid token.

### 4.11 POST `/api/v1/customers/batch/assign`

Batch-transfer customers to a new salesperson.

- **Auth required:** Yes
- **Request body (JSON):**

| Field          | Type  | Required | Description                     |
|----------------|-------|----------|---------------------------------|
| `customer_ids` | array | Yes      | List of customer UUIDs          |
| `new_sales_id` | UUID  | Yes      | Target user (role `sales`/`admin`) |

```json
{
  "customer_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6", "1b4e28ba-2fa1-11d2-883f-b9a761bde3fb"],
  "new_sales_id": "2c963f66-afa6-4562-b3fc-3fa85f645717"
}
```

- **Success response (200):** `{"code": 0, "message": "success", "data": {"affected": 2}}`
- **Errors:** `400` "New sales person not found or incorrect role".

### 4.12 POST `/api/v1/customers/batch/status`

Batch-update the status of multiple customers.

- **Auth required:** Yes
- **Request body (JSON):**

| Field          | Type   | Required | Description                       |
|----------------|--------|----------|-----------------------------------|
| `customer_ids` | array  | Yes      | List of customer UUIDs            |
| `status`       | string | Yes      | `active`/`lost`/`completed`/`terminated` |

```json
{ "customer_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"], "status": "lost" }
```

- **Success response (200):** `{"code": 0, "message": "success", "data": {"affected": 1}}`

### 4.13 POST `/api/v1/customers/batch/delete`

Batch soft-delete (sets `status = "deleted"`).

- **Auth required:** Yes
- **Request body:** raw JSON array of customer UUIDs

```json
["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
```

- **Success response (200):** `{"code": 0, "message": "success", "data": {"affected": 1}}`

### 4.14 GET `/api/v1/customers/advanced-search`

Multi-field advanced search with pagination. All query parameters are optional; customers with status `deleted` are excluded.

- **Auth required:** Yes
- **Query parameters:**

| Parameter             | Type   | Description                              |
|-----------------------|--------|------------------------------------------|
| `name`                | string | Fuzzy match on name                       |
| `contact_person`      | string | Fuzzy match on contact person             |
| `phone`               | string | Fuzzy match on phone                      |
| `company`             | string | Fuzzy match on company                    |
| `region`              | string | Exact match on region                     |
| `source_channel`      | string | Exact match on source channel             |
| `current_stage`       | int    | Exact stage (1–8)                         |
| `status`              | string | Exact status                              |
| `sales_id`            | UUID   | Assigned salesperson                      |
| `min_contract_amount` | float  | `contract_amount >=` value (≥0)           |
| `max_contract_amount` | float  | `contract_amount <=` value (≥0)           |
| `created_after`       | string | ISO datetime `created_at >=` value        |
| `created_before`      | string | ISO datetime `created_at <=` value        |
| `page`                | int    | Page number (≥1, default 1)               |
| `page_size`           | int    | Page size (1–100, default 20)             |

- **Success response (200):** paginated `{items, total, page, page_size}`; each item contains the customer fields plus `stay_days` and `alert_level`.

### 4.15 GET `/api/v1/customers/{id}/export`

Export a single customer's details (basic info, tasks, payments) as an `.xlsx` file download.

- **Auth required:** Yes (admin: any customer; sales: own customers only)
- **Path parameters:** `id` (UUID)
- **Success response (200):** `StreamingResponse` — Excel file, media type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, filename `customer_{name}_{id}.xlsx`.
- **Business errors (HTTP 200):** `{"code": 4004, "message": "Customer not found"}`, `{"code": 4003, "message": "Permission denied"}`.

### 4.16 POST `/api/v1/customers/import`

Bulk-import customers from an uploaded Excel file (`.xlsx`). Reads the first worksheet from row 2 onward. Rows without both `name` and `phone` are skipped. All imported customers are assigned to the importing user.

- **Auth required:** Yes
- **Request:** `multipart/form-data`

| Field  | Type     | Required | Description |
|--------|----------|----------|-------------|
| `file` | file     | Yes      | `.xlsx` file |

- **Expected column order (0-indexed):** `name`, `contact_person`, `phone`, `wechat`, `email`, `company`, `region`, `source_channel`.
- **Success response (200):**

```json
{ "code": 0, "message": "success", "data": { "imported": 25 } }
```

### 4.17 GET `/api/v1/customers/export`

Export all (optionally filtered) customers to `customers.xlsx`.

- **Auth required:** Yes
- **Query parameters:**

| Parameter   | Type   | Description          |
|-------------|--------|----------------------|
| `stage`     | int    | Filter by stage      |
| `sales_id`  | UUID   | Filter by salesperson|
| `region`    | string | Filter by region     |
| `start_date`| string | ISO datetime `created_at >=` value |
| `end_date`  | string | ISO datetime `created_at <=` value |

- **Success response (200):** Excel file download (`customers.xlsx`) with columns: name, contact_person, phone, wechat, email, company, region, source_channel, current_stage, contract_amount, created_at.

### 4.18 GET `/api/v1/customers/export-template`

Download an Excel import template (header row + one example row) so users can fill in customer data and upload via `POST /api/v1/customers/import`.

- **Auth required:** Yes
- **Success response (200):** Excel file download (`customer_import_template.xlsx`) with columns: name, contact_person, phone, wechat, email, company, region, source_channel.

> **Note:** the `advanced-search`, `export` and `export-template` routes are registered **before** the dynamic `GET /customers/{id}` route in `customers.py`, so no route shadowing occurs.

---

## 5. Contracts (`/api/v1/customers/{customer_id}/contract`, `/api/v1/contracts/...`)

Access rules: **admin** has full CRUD; **sales** has read-only access (any write returns 403); other roles cannot modify contracts.

### 5.1 POST `/api/v1/customers/{customer_id}/contract`

Create a contract for a customer.

- **Auth required:** Yes (admin only)
- **Path parameters:** `customer_id` (UUID)
- **Request body (JSON):**

| Field            | Type   | Required | Description               |
|------------------|--------|----------|---------------------------|
| `contract_no`    | string | Yes      | Contract number (max 50)  |
| `contract_amount`| float  | No       | Amount (Numeric(12,2))    |
| `sign_date`      | date   | No       | Signing date (`YYYY-MM-DD`) |
| `payment_terms`  | string | No       | Payment terms text        |
| `delivery_date`  | date   | No       | Delivery date             |
| `contract_file`  | string | No       | File path/URL (max 500)   |

```json
{
  "contract_no": "HT-2026-001",
  "contract_amount": 50000.00,
  "sign_date": "2026-08-01",
  "payment_terms": "30% deposit, 70% on delivery",
  "delivery_date": "2026-09-30"
}
```

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "customer_id": "1b4e28ba-2fa1-11d2-883f-b9a761bde3fb",
    "contract_no": "HT-2026-001",
    "contract_amount": 50000.0,
    "sign_date": "2026-08-01",
    "payment_terms": "30% deposit, 70% on delivery",
    "delivery_date": "2026-09-30",
    "contract_file": null,
    "created_at": "2026-08-05T09:00:00",
    "updated_at": "2026-08-05T09:00:00"
  }
}
```

- **Errors:** `403` "Sales can only view contracts" / "Permission denied"; `404` "Customer not found".

### 5.2 GET `/api/v1/customers/{customer_id}/contract`

Get the contract of a customer (first match).

- **Auth required:** Yes
- **Path parameters:** `customer_id` (UUID)
- **Success response (200):** contract object (as in 5.1).
- **Errors:** `404` "Contract not found".

### 5.3 PUT `/api/v1/contracts/{id}`

Update a contract.

- **Auth required:** Yes (admin only)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):** any subset of contract fields (all optional)
- **Success response (200):** updated contract object.
- **Errors:** `403` permission; `404` "Contract not found".

### 5.4 DELETE `/api/v1/contracts/{id}`

Delete a contract (hard delete).

- **Auth required:** Yes (admin only)
- **Path parameters:** `id` (UUID)
- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `403` permission; `404` "Contract not found".

### 5.5 PUT `/api/v1/contracts/{id}/file`

Update the stored contract file path.

- **Auth required:** Yes (admin only)
- **Path parameters:** `id` (UUID)
- **Query parameters:** `file_path` (string, required) — new file path/URL
- **Success response (200):** updated contract object.
- **Errors:** `403` permission; `404` "Contract not found".

---

## 6. Tasks (`/api/v1/customers/{customer_id}/tasks`, `/api/v1/tasks/...`)

Access rules (`check_task_access`): **admin** → all tasks; **sales** → tasks of their own customers; **pm** → tasks assigned to them; **cs** → denied. Write operations (update/status/assignee/delete) additionally require role **admin** or **pm**; sales is read-only.

### 6.1 POST `/api/v1/customers/{customer_id}/tasks`

Create a task for a customer.

- **Auth required:** Yes
- **Path parameters:** `customer_id` (UUID)
- **Request body (JSON):**

| Field         | Type   | Required | Description                               |
|---------------|--------|----------|-------------------------------------------|
| `name`        | string | Yes      | Task name (1–200 chars)                   |
| `description` | string | No       | Task description                          |
| `assignee_id` | UUID   | No       | Assignee user id                          |
| `status`      | string | No       | `pending` (default), `in_progress`, `completed` |
| `priority`    | string | No       | `low`, `medium` (default), `high`, `urgent` |
| `start_date`  | date   | No       | Start date                                |
| `due_date`    | date   | No       | Due date                                  |

```json
{
  "name": "Send quotation",
  "description": "Prepare quotation based on requirements",
  "assignee_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "priority": "high",
  "due_date": "2026-08-10"
}
```

- **Success response (200):** task object (see 6.2 shape).
- **Errors:** `404` "Customer not found"; `403` access denied.

### 6.2 GET `/api/v1/customers/{customer_id}/tasks`

List all tasks of a customer (newest first).

- **Auth required:** Yes
- **Path parameters:** `customer_id` (UUID)
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "customer_id": "1b4e28ba-2fa1-11d2-883f-b9a761bde3fb",
      "name": "Send quotation",
      "description": "Prepare quotation based on requirements",
      "assignee_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "assignee_name": "John Sales",
      "status": "pending",
      "priority": "high",
      "start_date": null,
      "due_date": "2026-08-10",
      "completed_at": null,
      "created_at": "2026-08-05T09:00:00",
      "updated_at": "2026-08-05T09:00:00"
    }
  ]
}
```

### 6.3 GET `/api/v1/tasks/{id}`

Task detail.

- **Auth required:** Yes (`check_task_access`)
- **Path parameters:** `id` (UUID)
- **Success response (200):** task object.
- **Errors:** `404` "Task not found"; `403` "Permission denied".

### 6.4 PUT `/api/v1/tasks/{id}`

Update a task (admin/pm only).

- **Auth required:** Yes (role `admin` or `pm`)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):** any subset of task fields (all optional, same types as 6.1)
- **Success response (200):** updated task object.
- **Errors:** `403` "Sales can only view tasks" / "Permission denied"; `404` "Task not found".

### 6.5 PATCH `/api/v1/tasks/{id}/status`

Update task status (admin/pm only). Setting `completed` records `completed_at`.

- **Auth required:** Yes (role `admin` or `pm`)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):**

| Field          | Type     | Required | Description                                  |
|----------------|----------|----------|----------------------------------------------|
| `status`       | string   | Yes      | `pending`, `in_progress`, `completed`        |
| `completed_at` | datetime | No       | Optional completion timestamp (defaults to now when status = completed) |

```json
{ "status": "completed" }
```

- **Success response (200):** updated task object.
- **Errors:** `403` permission; `404` "Task not found".

### 6.6 PATCH `/api/v1/tasks/{id}/assignee`

Reassign a task (admin/pm only).

- **Auth required:** Yes (role `admin` or `pm`)
- **Path parameters:** `id` (UUID)
- **Query parameters:** `assignee_id` (UUID, required)
- **Success response (200):** updated task object.
- **Errors:** `403` permission; `404` "Task not found".

### 6.7 DELETE `/api/v1/tasks/{id}`

Delete a task (admin/pm only).

- **Auth required:** Yes (role `admin` or `pm`)
- **Path parameters:** `id` (UUID)
- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `403` permission; `404` "Task not found".

---

## 7. Documents (`/api/v1/customers/{customer_id}/documents`, `/api/v1/documents/...`)

Write access: **admin** and **pm** may upload/update/delete; **sales** and **cs** are read-only (403 on write). Files are stored on the local filesystem under `backend/app/uploads/{customer_id}/` (MinIO is configured in settings but the current upload code uses local storage).

### 7.1 POST `/api/v1/customers/{customer_id}/documents`

Upload a document for a customer.

- **Auth required:** Yes (admin/pm)
- **Path parameters:** `customer_id` (UUID)
- **Request:** `multipart/form-data`

| Field      | Type   | Required | Description                     |
|------------|--------|----------|---------------------------------|
| `file`     | file   | Yes      | The file to upload              |
| `category` | string | No       | Document category (e.g. `acceptance`, `contract`) |

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "customer_id": "1b4e28ba-2fa1-11d2-883f-b9a761bde3fb",
    "file_name": "acceptance.pdf",
    "file_path": "/app/uploads/1b4e28ba-.../acceptance.pdf",
    "file_size": 204800,
    "file_type": "pdf",
    "category": "acceptance",
    "uploaded_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "created_at": "2026-08-05T09:00:00",
    "updated_at": "2026-08-05T09:00:00"
  }
}
```

- **Errors:** `404` "Customer not found"; `403` "Read-only access to documents".

### 7.2 GET `/api/v1/customers/{customer_id}/documents`

List documents of a customer (newest first).

- **Auth required:** Yes
- **Path parameters:** `customer_id` (UUID)
- **Success response (200):** array of document objects; each item includes `uploaded_by` and `uploaded_by_name` (uploader's display name).

### 7.3 GET `/api/v1/documents/{id}`

Document detail.

- **Auth required:** Yes
- **Path parameters:** `id` (UUID)
- **Success response (200):** document object.
- **Errors:** `404` "Document not found".

### 7.4 GET `/api/v1/documents/{id}/download`

Download the stored file (media type `application/octet-stream`).

- **Auth required:** Yes
- **Path parameters:** `id` (UUID)
- **Success response (200):** file stream with `Content-Disposition: attachment; filename=...`.
- **Errors:** `404` "Document not found"; `404` "File not found on disk".

### 7.5 PUT `/api/v1/documents/{id}`

Update document metadata (`file_name`, `category`).

- **Auth required:** Yes (admin/pm; sales/cs get 403)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):**

| Field       | Type   | Required | Description             |
|-------------|--------|----------|-------------------------|
| `file_name` | string | No       | New file name (max 200) |
| `category`  | string | No       | New category (max 50)   |

- **Success response (200):** updated document object.
- **Errors:** `404` "Document not found"; `403` read-only.

### 7.6 PUT `/api/v1/documents/{id}/file`

Replace the file content of an existing document (old file deleted from disk).

- **Auth required:** Yes (admin/pm)
- **Path parameters:** `id` (UUID)
- **Request:** `multipart/form-data` with field `file`
- **Success response (200):** updated document object.
- **Errors:** `404` "Document not found"; `403` read-only.

### 7.7 DELETE `/api/v1/documents/{id}`

Delete a document (file removed from disk, row hard-deleted).

- **Auth required:** Yes (admin/pm)
- **Path parameters:** `id` (UUID)
- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `404` "Document not found"; `403` read-only.

---

## 8. Communications (`/api/v1/customers/{customer_id}/communications`, `/api/v1/communications/...`)

Access rules (`check_comm_access`): **admin** → all; **sales** → own customers; **pm**/**cs** → own customers' records.

### 8.1 POST `/api/v1/customers/{customer_id}/communications`

Log a communication record for a customer.

- **Auth required:** Yes (sales: only own customers; admin/pm/cs: allowed)
- **Path parameters:** `customer_id` (UUID)
- **Request body (JSON):**

| Field             | Type   | Required | Description                          |
|-------------------|--------|----------|--------------------------------------|
| `channel`         | string | Yes      | One of `phone`, `wechat`, `meeting`, `email` |
| `content`         | string | No       | Communication content                |
| `next_action`     | string | No       | Planned next action                  |
| `next_action_date`| date   | No       | Date for next action                 |

```json
{
  "channel": "phone",
  "content": "Called customer to confirm requirements",
  "next_action": "Send quotation by Friday",
  "next_action_date": "2026-08-07"
}
```

- **Success response (200):** communication object (includes `user_id` = caller).
- **Errors:** `404` "Customer not found"; `403` "Permission denied".

### 8.2 GET `/api/v1/customers/{customer_id}/communications`

List communication records of a customer (newest first).

- **Auth required:** Yes
- **Path parameters:** `customer_id` (UUID)
- **Success response (200):** array of communication objects; each item includes `user_id` and `user_name` (operator's display name, `null` when the user no longer exists).

### 8.3 PUT `/api/v1/communications/{id}`

Update a communication record.

- **Auth required:** Yes (`check_comm_access`)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):** any subset of fields (all optional, types as 8.1)
- **Success response (200):** updated communication object.
- **Errors:** `404` "Communication record not found"; `403` "Permission denied".

### 8.4 DELETE `/api/v1/communications/{id}`

Delete a communication record.

- **Auth required:** Yes (`check_comm_access`)
- **Path parameters:** `id` (UUID)
- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `404` "Communication record not found"; `403` "Permission denied".

---

## 9. Payments (`/api/v1/customers/{customer_id}/payments`, `/api/v1/payments/...`)

**Admin only** for all write operations. Creating/updating/deleting payments automatically adjusts the customer's `paid_amount`.

### 9.1 POST `/api/v1/customers/{customer_id}/payments`

Record a payment. Adds `amount` to the customer's `paid_amount`.

- **Auth required:** Yes (admin only)
- **Path parameters:** `customer_id` (UUID)
- **Request body (JSON):**

| Field          | Type   | Required | Description                           |
|----------------|--------|----------|---------------------------------------|
| `amount`       | float  | Yes      | Payment amount (> 0, Numeric(12,2))   |
| `payment_date` | date   | No       | Payment date                          |
| `payment_type` | string | Yes      | `deposit`, `milestone`, `final`       |
| `invoice_no`   | string | No       | Invoice number (max 50)               |
| `notes`        | string | No       | Notes                                 |

```json
{
  "amount": 15000.00,
  "payment_date": "2026-08-05",
  "payment_type": "deposit",
  "invoice_no": "INV-2026-0001",
  "notes": "30% deposit"
}
```

- **Success response (200):** payment object.

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "customer_id": "1b4e28ba-2fa1-11d2-883f-b9a761bde3fb",
    "amount": 15000.0,
    "payment_date": "2026-08-05",
    "payment_type": "deposit",
    "invoice_no": "INV-2026-0001",
    "notes": "30% deposit",
    "recorded_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "created_at": "2026-08-05T09:00:00",
    "updated_at": "2026-08-05T09:00:00"
  }
}
```

- **Errors:** `403` "Permission denied"; `404` "Customer not found".

### 9.2 GET `/api/v1/customers/{customer_id}/payments`

List payment records of a customer (ordered by `payment_date` descending, then `created_at` descending).

- **Auth required:** Yes
- **Path parameters:** `customer_id` (UUID)
- **Success response (200):** array of payment objects.

### 9.3 PUT `/api/v1/payments/{id}`

Update a payment. Adjusts the customer's `paid_amount` by the difference between old and new amount.

- **Auth required:** Yes (admin only)
- **Path parameters:** `id` (UUID)
- **Request body (JSON):** any subset of fields (all optional, types as 9.1)
- **Success response (200):** updated payment object.
- **Errors:** `403` permission; `404` "Payment record not found".

### 9.4 DELETE `/api/v1/payments/{id}`

Delete a payment. Subtracts the amount from the customer's `paid_amount`.

- **Auth required:** Yes (admin only)
- **Path parameters:** `id` (UUID)
- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `403` permission; `404` "Payment record not found".

---

## 10. Board (Kanban) (`/api/v1/board`)

### 10.1 GET `/api/v1/board/kanban`

Kanban board data — active customers grouped by stage (1–8), each with alert/stay information.

- **Auth required:** Yes
- **Query parameters (all optional):**

| Parameter       | Type   | Description              |
|-----------------|--------|--------------------------|
| `sales_id`      | UUID   | Filter by salesperson    |
| `region`        | string | Filter by region         |
| `source_channel`| string | Filter by source channel |

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "stage": 1,
      "name": "Lead",
      "customers": [
        {
          "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "name": "Acme Corp",
          "contact_person": "Alice",
          "phone": "13600000000",
          "company": "Acme Corp Ltd",
          "region": "Shanghai",
          "source_channel": "exhibition",
          "sales_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "sales_name": "John Sales",
          "status": "active",
          "stage": 1,
          "contract_amount": 0.0,
          "paid_amount": 0.0,
          "stay_days": 3,
          "alert_level": "normal",
          "stage_entered_at": "2026-08-02T09:00:00",
          "created_at": "2026-08-02T09:00:00"
        }
      ],
      "count": 1
    }
  ]
}
```

### 10.2 GET `/api/v1/board/alerts`

All active customers currently in `warning` or `danger` alert state, sorted with danger first, then by stay days descending.

- **Auth required:** Yes
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Acme Corp",
      "contact_person": "Alice",
      "phone": "13600000000",
      "company": "Acme Corp Ltd",
      "current_stage": 5,
      "stage_name": "Service",
      "stay_days": 46,
      "alert_level": "danger",
      "sales_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    }
  ]
}
```

---

## 11. Dashboard (`/api/v1/dashboard`)

### 11.1 GET `/api/v1/dashboard/stats`

Basic statistics.

- **Auth required:** Yes
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total_customers": 120,
    "active_customers": 98,
    "stage_counts": { "stage_1": 30, "stage_2": 20, "stage_3": 15, "stage_4": 10, "stage_5": 12, "stage_6": 5, "stage_7": 4, "stage_8": 2 },
    "overdue_count": 7,
    "today_new": 3,
    "monthly_new": 15,
    "monthly_payment": 120000.0
  }
}
```

### 11.2 GET `/api/v1/dashboard/funnel`

Funnel data — cumulative count of active customers at each stage and beyond.

- **Auth required:** Yes
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "stage": 1, "name": "Lead", "count": 98 },
    { "stage": 2, "name": "Consult", "count": 68 },
    { "stage": 3, "name": "Contract", "count": 48 },
    { "stage": 4, "name": "Requirements", "count": 33 },
    { "stage": 5, "name": "Service", "count": 23 },
    { "stage": 6, "name": "Delivery", "count": 11 },
    { "stage": 7, "name": "Payment", "count": 6 },
    { "stage": 8, "name": "Completed", "count": 2 }
  ]
}
```

### 11.3 GET `/api/v1/dashboard/sales`

Sales workload statistics — number of active customers per salesperson/admin.

- **Auth required:** Yes
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "user_name": "John Sales", "customer_count": 42 }
  ]
}
```

### 11.4 GET `/api/v1/dashboard/payments`

Payment statistics: total paid, current-month paid, total contract amount (active customers), collection rate.

- **Auth required:** Yes
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total_paid": 850000.0,
    "month_paid": 120000.0,
    "total_contract_amount": 1000000.0,
    "collection_rate": 85.0
  }
}
```

### 11.5 GET `/api/v1/dashboard/payment-trend`

Monthly payment trend for a given year — one data point per month (Jan–Dec), used by the Dashboard payment chart.

- **Auth required:** Yes
- **Query parameters:**

| Parameter | Type | Required | Description                          |
|-----------|------|----------|--------------------------------------|
| `year`    | int  | No       | Year (2000–2100, default current year) |

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "month": "2026-01", "total": 0.0 },
    { "month": "2026-02", "total": 85000.0 },
    { "month": "2026-03", "total": 120000.0 }
  ]
}
```

> Each `total` is the sum of `payments.amount` whose `payment_date` falls in that month.

---

## 12. Notifications (`/api/v1/notifications`)

### 12.1 GET `/api/v1/notifications/`

List the current user's notifications (newest first, max 50).

- **Auth required:** Yes
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "user_id": "1b4e28ba-2fa1-11d2-883f-b9a761bde3fb",
      "type": "task_due",
      "title": "Task due today",
      "content": "Task 'Send quotation' is due today. Please complete it on time.",
      "related_id": "c0a80121-0000-4000-8000-000000000001",
      "related_type": "task",
      "is_read": false,
      "created_at": "2026-08-05T00:00:00",
      "updated_at": "2026-08-05T00:00:00"
    }
  ]
}
```

### 12.2 GET `/api/v1/notifications/unread-count`

Unread notification count for the current user.

- **Auth required:** Yes
- **Success response (200):** `{"code": 0, "message": "success", "data": {"count": 5}}`

### 12.3 PUT `/api/v1/notifications/{id}/read`

Mark a single notification as read.

- **Auth required:** Yes
- **Path parameters:** `id` (UUID)
- **Success response (200):** the notification object with `is_read: true`.

### 12.4 PUT `/api/v1/notifications/read-all`

Mark all of the current user's notifications as read.

- **Auth required:** Yes
- **Success response (200):** `{"code": 0, "message": "success", "data": {"affected": 12}}`

---

## 13. Follow-ups (`/api/v1/customers/{customer_id}/follow-ups`, `/api/v1/follow-ups/...`)

### 13.1 POST `/api/v1/customers/{customer_id}/follow-ups`

Create a follow-up reminder for a customer.

- **Auth required:** Yes
- **Path parameters:** `customer_id` (UUID)
- **Query parameters (FastAPI treats these as query parameters):**

| Parameter    | Type     | Required | Default                | Description                 |
|--------------|----------|----------|------------------------|-----------------------------|
| `title`      | string   | Yes      | —                      | Reminder title              |
| `content`    | string   | No       | `null`                 | Reminder content            |
| `remind_at`  | datetime | No       | `null`                 | Reminder time (ISO 8601)    |
| `remind_type`| string   | No       | `system_notification`  | `system_notification` or `email` |

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "customer_id": "1b4e28ba-2fa1-11d2-883f-b9a761bde3fb",
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "Follow up on quotation",
    "content": "Call customer about the quotation",
    "remind_at": "2026-08-06T10:00:00",
    "remind_type": "system_notification",
    "is_done": false,
    "done_at": null,
    "created_at": "2026-08-05T09:00:00",
    "updated_at": "2026-08-05T09:00:00"
  }
}
```

- **Errors:** `404` "Customer not found".

### 13.2 GET `/api/v1/customers/{customer_id}/follow-ups`

List a customer's follow-ups (newest first).

- **Auth required:** Yes
- **Path parameters:** `customer_id` (UUID)
- **Success response (200):** array of follow-up objects.

### 13.3 PUT `/api/v1/follow-ups/{id}`

Update a follow-up (all parameters optional).

- **Auth required:** Yes
- **Path parameters:** `id` (UUID)
- **Query parameters:** `title`, `content`, `remind_at`, `remind_type` (same types as 13.1)
- **Success response (200):** updated follow-up object.
- **Errors:** `404` "Follow-up reminder not found".

### 13.4 PUT `/api/v1/follow-ups/{id}/done`

Mark a follow-up as done (sets `is_done = true`, `done_at = now`).

- **Auth required:** Yes
- **Path parameters:** `id` (UUID)
- **Success response (200):** updated follow-up object.
- **Errors:** `404` "Follow-up reminder not found".

### 13.5 DELETE `/api/v1/follow-ups/{id}`

Delete a follow-up.

- **Auth required:** Yes
- **Path parameters:** `id` (UUID)
- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `404` "Follow-up reminder not found".

### 13.6 GET `/api/v1/follow-ups/today`

The current user's undone follow-ups scheduled from today onward, ordered by `remind_at` ascending.

- **Auth required:** Yes
- **Success response (200):** array of follow-up objects.

---

## 14. Audit Logs (`/api/v1/audit-logs`, `/api/v1/customers/{customer_id}/audit-logs`)

### 14.1 GET `/api/v1/audit-logs`

Paged audit log listing with optional filters. Logs are generated automatically by the backend for customer create / update / delete / stage-advance / status-change operations.

- **Auth required:** Yes
- **Query parameters:**

| Parameter      | Type   | Required | Description              |
|----------------|--------|----------|--------------------------|
| `page`         | int    | No       | Page number (≥1, default 1) |
| `page_size`    | int    | No       | Page size (1–100, default 20) |
| `action`       | string | No       | Filter by action (e.g. `create`, `update`, `delete`, `advance_stage`, `update_status`) |
| `object_type`  | string | No       | Filter by object type (e.g. `customer`, `contract`) |
| `operator_name`| string | No       | Fuzzy filter by operator's user name |
| `start_date`   | string | No       | ISO datetime `created_at >=` value |
| `end_date`     | string | No       | ISO datetime `created_at <=` value |

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "created_at": "2026-08-05T09:00:00",
        "operator_name": "Admin",
        "action": "update",
        "resource_type": "customer",
        "resource_id": "c0a80121-0000-4000-8000-000000000001",
        "customer_id": "c0a80121-0000-4000-8000-000000000001",
        "description": "update customer",
        "changes": { "region": { "old": "Shanghai", "new": "Beijing" } },
        "ip_address": "172.17.0.1"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

> The `changes` object is computed by diffing the stored `before_data` / `after_data` snapshots — only fields whose value changed are included.

### 14.2 GET `/api/v1/customers/{customer_id}/audit-logs`

All audit logs tied to a specific customer (newest first).

- **Auth required:** Yes
- **Path parameters:** `customer_id` (UUID)
- **Success response (200):** array of audit log objects.

---

## 15. Data Dictionary (`/api/v1/dict`)

The dictionary has four categories: `industry`, `region`, `channel`, `document_category`. Each item is `{id, name, code}` (active items only, ordered by `sort_order`).

### 15.1 GET `/api/v1/dict/industries` | `GET /api/v1/dict/regions` | `GET /api/v1/dict/channels` | `GET /api/v1/dict/categories`

List dictionary items for a category.

- **Auth required:** Yes
- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "name": "Manufacturing", "code": "manufacturing" }
  ]
}
```

### 15.2 PUT `/api/v1/dict/industries` | `PUT /api/v1/dict/regions` | `PUT /api/v1/dict/channels` | `PUT /api/v1/dict/categories`

Replace all items of a category (delete-then-insert). **Admin only.**

- **Auth required:** Yes (role `admin`)
- **Request body (JSON):** array of items

| Field        | Type   | Required | Description                 |
|--------------|--------|----------|-----------------------------|
| `name`       | string | Yes      | Display name                |
| `code`       | string | No       | Stable code value           |
| `sort_order` | int    | No       | Sort order (default 0)      |

```json
[
  { "name": "Manufacturing", "code": "manufacturing", "sort_order": 1 },
  { "name": "IT Services", "code": "it_services", "sort_order": 2 }
]
```

- **Success response (200):** `{"code": 0, "message": "success", "data": null}`
- **Errors:** `403` "Admin privileges required".

---

## 16. Global Search (`/api/v1/search`)

### 16.1 GET `/api/v1/search/global`

Search customers by keyword (fuzzy match on `name`, `contact_person`, `phone`, `wechat`, `company`).

- **Auth required:** Yes
- **Query parameters:**

| Parameter   | Type   | Required | Description                        |
|-------------|--------|----------|------------------------------------|
| `keyword`   | string | Yes      | Search keyword (min length 1)      |
| `page`      | int    | No       | Page number (≥1, default 1)        |
| `page_size` | int    | No       | Page size (1–100, default 20)      |

- **Success response (200):**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "Acme Corp",
        "contact_person": "Alice",
        "phone": "13600000000",
        "wechat": "alice_acme",
        "company": "Acme Corp Ltd",
        "region": "Shanghai",
        "current_stage": 1,
        "status": "active",
        "stay_days": 3,
        "alert_level": "normal"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

- **Errors:** `422` missing/empty `keyword`; `401` invalid token.

---

## 17. Appendix — Endpoint Summary

| Method | Path | Module | Auth |
|--------|------|--------|------|
| POST | `/api/v1/auth/login` | Auth | No |
| POST | `/api/v1/auth/register` | Auth | No |
| POST | `/api/v1/auth/refresh` | Auth | No |
| GET | `/api/v1/auth/me` | Auth | Yes |
| POST | `/api/v1/users/` | Users | Yes (admin) |
| GET | `/api/v1/users/` | Users | Yes |
| PUT | `/api/v1/users/{id}` | Users | Yes (admin) |
| PUT | `/api/v1/users/{id}/password` | Users | Yes (admin) |
| GET | `/api/v1/users/me` | Users | Yes |
| PUT | `/api/v1/users/me` | Users | Yes |
| PUT | `/api/v1/users/me/password` | Users | Yes |
| POST | `/api/v1/customers/` | Customers | Yes |
| GET | `/api/v1/customers/` | Customers | Yes |
| GET | `/api/v1/customers/{id}` | Customers | Yes |
| PUT | `/api/v1/customers/{id}` | Customers | Yes |
| DELETE | `/api/v1/customers/{id}` | Customers | Yes (admin) |
| PUT | `/api/v1/customers/{id}/stage` | Customers | Yes |
| PUT | `/api/v1/customers/{id}/status` | Customers | Yes |
| PUT | `/api/v1/customers/{id}/assign` | Customers | Yes |
| PUT | `/api/v1/customers/{id}/rollback` | Customers | Yes (admin) |
| GET | `/api/v1/customers/{id}/timeline` | Customers | Yes |
| POST | `/api/v1/customers/batch/assign` | Customers | Yes |
| POST | `/api/v1/customers/batch/status` | Customers | Yes |
| POST | `/api/v1/customers/batch/delete` | Customers | Yes |
| GET | `/api/v1/customers/advanced-search` | Customers | Yes |
| GET | `/api/v1/customers/{id}/export` | Customers | Yes |
| POST | `/api/v1/customers/import` | Customers | Yes |
| GET | `/api/v1/customers/export` | Customers | Yes |
| GET | `/api/v1/customers/export-template` | Customers | Yes |
| POST | `/api/v1/customers/{customer_id}/contract` | Contracts | Yes (admin) |
| GET | `/api/v1/customers/{customer_id}/contract` | Contracts | Yes |
| PUT | `/api/v1/contracts/{id}` | Contracts | Yes (admin) |
| DELETE | `/api/v1/contracts/{id}` | Contracts | Yes (admin) |
| PUT | `/api/v1/contracts/{id}/file` | Contracts | Yes (admin) |
| POST | `/api/v1/customers/{customer_id}/tasks` | Tasks | Yes |
| GET | `/api/v1/customers/{customer_id}/tasks` | Tasks | Yes |
| GET | `/api/v1/tasks/{id}` | Tasks | Yes |
| PUT | `/api/v1/tasks/{id}` | Tasks | Yes (admin/pm) |
| PATCH | `/api/v1/tasks/{id}/status` | Tasks | Yes (admin/pm) |
| PATCH | `/api/v1/tasks/{id}/assignee` | Tasks | Yes (admin/pm) |
| DELETE | `/api/v1/tasks/{id}` | Tasks | Yes (admin/pm) |
| POST | `/api/v1/customers/{customer_id}/documents` | Documents | Yes (admin/pm) |
| GET | `/api/v1/customers/{customer_id}/documents` | Documents | Yes |
| GET | `/api/v1/documents/{id}` | Documents | Yes |
| GET | `/api/v1/documents/{id}/download` | Documents | Yes |
| PUT | `/api/v1/documents/{id}` | Documents | Yes (admin/pm) |
| PUT | `/api/v1/documents/{id}/file` | Documents | Yes (admin/pm) |
| DELETE | `/api/v1/documents/{id}` | Documents | Yes (admin/pm) |
| POST | `/api/v1/customers/{customer_id}/communications` | Communications | Yes |
| GET | `/api/v1/customers/{customer_id}/communications` | Communications | Yes |
| PUT | `/api/v1/communications/{id}` | Communications | Yes |
| DELETE | `/api/v1/communications/{id}` | Communications | Yes |
| POST | `/api/v1/customers/{customer_id}/payments` | Payments | Yes (admin) |
| GET | `/api/v1/customers/{customer_id}/payments` | Payments | Yes |
| PUT | `/api/v1/payments/{id}` | Payments | Yes (admin) |
| DELETE | `/api/v1/payments/{id}` | Payments | Yes (admin) |
| GET | `/api/v1/board/kanban` | Board | Yes |
| GET | `/api/v1/board/alerts` | Board | Yes |
| GET | `/api/v1/dashboard/stats` | Dashboard | Yes |
| GET | `/api/v1/dashboard/funnel` | Dashboard | Yes |
| GET | `/api/v1/dashboard/sales` | Dashboard | Yes |
| GET | `/api/v1/dashboard/payments` | Dashboard | Yes |
| GET | `/api/v1/dashboard/payment-trend` | Dashboard | Yes |
| GET | `/api/v1/notifications/` | Notifications | Yes |
| GET | `/api/v1/notifications/unread-count` | Notifications | Yes |
| PUT | `/api/v1/notifications/{id}/read` | Notifications | Yes |
| PUT | `/api/v1/notifications/read-all` | Notifications | Yes |
| POST | `/api/v1/customers/{customer_id}/follow-ups` | Follow-ups | Yes |
| GET | `/api/v1/customers/{customer_id}/follow-ups` | Follow-ups | Yes |
| PUT | `/api/v1/follow-ups/{id}` | Follow-ups | Yes |
| PUT | `/api/v1/follow-ups/{id}/done` | Follow-ups | Yes |
| DELETE | `/api/v1/follow-ups/{id}` | Follow-ups | Yes |
| GET | `/api/v1/follow-ups/today` | Follow-ups | Yes |
| GET | `/api/v1/audit-logs` | Audit Logs | Yes |
| GET | `/api/v1/customers/{customer_id}/audit-logs` | Audit Logs | Yes |
| GET | `/api/v1/dict/industries` | Data Dictionary | Yes |
| GET | `/api/v1/dict/regions` | Data Dictionary | Yes |
| GET | `/api/v1/dict/channels` | Data Dictionary | Yes |
| GET | `/api/v1/dict/categories` | Data Dictionary | Yes |
| PUT | `/api/v1/dict/industries` | Data Dictionary | Yes (admin) |
| PUT | `/api/v1/dict/regions` | Data Dictionary | Yes (admin) |
| PUT | `/api/v1/dict/channels` | Data Dictionary | Yes (admin) |
| PUT | `/api/v1/dict/categories` | Data Dictionary | Yes (admin) |
| GET | `/api/v1/search/global` | Search | Yes |
| GET | `/health` | System | No |