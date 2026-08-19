# CRM System — Database Schema

**Database:** MySQL 8.0 (utf8mb4 / utf8mb4_unicode_ci)
**ORM:** SQLAlchemy 2.0 (`backend/app/models/`)
**Tables:** 12
**DDL:** Tables are created automatically at backend startup via SQLAlchemy `Base.metadata.create_all` (`app/main.py`). Alembic is scaffolded (`backend/alembic/`) for future schema migrations; no migration files are required for initial setup.

This document describes the physical schema generated from the SQLAlchemy models. All tables share a common primary key and timestamp convention defined in `models/base.py` (`TimestampMixin`):

| Column      | Type      | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id`        | UUID      | PRIMARY KEY | Generated client-side via `uuid.uuid4()` |
| `created_at`| DATETIME  | NOT NULL, `server_default = func.now()` | Row creation time |
| `updated_at`| DATETIME  | NOT NULL, `server_default = func.now()`, auto-updated via `onupdate` | Last modification time |

> **UUID storage note (MySQL):** SQLAlchemy's `Uuid(as_uuid=True)` type maps to `CHAR(32)` on MySQL (hex string without dashes). UUIDs are generated in Python (`uuid.uuid4()`) and stored/retrieved as UUID objects by the ORM.
>
> **JSON columns (MySQL):** The `JSON` SQLAlchemy type maps to MySQL's native `JSON` data type (used for `audit_logs.before_data` / `audit_logs.after_data`).
>
> **Character set:** The whole database is created with `utf8mb4` charset and `utf8mb4_unicode_ci` collation (docker-compose MySQL command line flags), and the connection URL appends `?charset=utf8mb4`. This guarantees full Unicode (including emoji) support.

---

## 1. Entity-Relationship Diagram (ASCII)

```
                          +-------------------+
                          |      USERS        |
                          |-------------------|
                          | id UUID      PK   |
                          | name, email, phone|
                          | password_hash     |
                          | role (ENUM)       |
                          | is_active         |
                          | created_at        |
                          | updated_at        |
                          +---------+---------+
            ^                           |                  ^
            | sales_id FK               |                  | user_id FK
            | (owner)                   | assignee_id FK    |
            |                           v                  |
+-----------+---------+      +----------+---------+   +----+------------+
|      CUSTOMERS       |      |        TASKS       |   | NOTIFICATIONS    |
|----------------------|      |--------------------|   |------------------|
| id UUID          PK  |<-----| id UUID        PK  |   | id UUID      PK  |
| name                 |      | customer_id FK  -- |   | user_id FK    -- |
| contact_person       |      | name, description  |   | type, title      |
| phone (UNIQUE)       |      | assignee_id FK  -- |   | content          |
| wechat, email        |      | status (ENUM)      |   | related_id       |
| company, region      |      | priority (ENUM)    |   | related_type     |
| source_channel       |      | start_date, due_date|  | is_read          |
| sales_id FK      ----+      | completed_at       |   +------------------+
| current_stage (1-8)  |      +--------------------+
| stage_entered_at     |
| contract_amount      |      +----------------------+
| paid_amount          |      |    CONTRACTS         |
| status (ENUM)        |----->|----------------------|
| lost_reason          |      | id UUID          PK  |
+----+----+----+-------+      | customer_id FK    -- |
     |    |    |               | contract_no         |
     |    |    |               | contract_amount      |
     |    |    |               | sign_date            |
     |    |    |               | payment_terms        |
     |    |    |               | delivery_date        |
     |    |    |               | contract_file        |
     |    |    |               +----------------------+
     |    |    |
     |    |    +----------> +----------------------+
     |    |                 |    DOCUMENTS         |
     |    |                 |----------------------|
     |    |                 | id UUID          PK  |
     |    |                 | customer_id FK    -- |
     |    |                 | file_name, file_path |
     |    |                 | file_size, file_type |
     |    |                 | category             |
     |    |                 | uploaded_by FK    -- |
     |    |                 +----------------------+
     |    |
     |    +----------> +----------------------+
     |                  |  COMMUNICATIONS     |
     |                  |---------------------|
     |                  | id UUID         PK  |
     |                  | customer_id FK   -- |
     |                  | user_id FK       -- |
     |                  | channel (ENUM)      |
     |                  | content, next_action|
     |                  | next_action_date    |
     |                  +---------------------+
     |
     +----------> +----------------------+
     |             |      PAYMENTS        |
     |             |----------------------|
     |             | id UUID          PK  |
     |             | customer_id FK    -- |
     |             | amount               |
     |             | payment_date         |
     |             | payment_type (ENUM)  |
     |             | invoice_no, notes    |
     |             | recorded_by FK    -- |
     |             +----------------------+
     |
     +----------> +-------------------------+
     |             |     STAGE_HISTORIES     |
     |             |-------------------------|
     |             | id UUID            PK  |
     |             | customer_id FK      -- |
     |             | from_stage, to_stage   |
     |             | changed_by FK       -- |
     |             | changed_at             |
     |             | remark                 |
     |             +-------------------------+
     |
     +----------> +----------------------+
     |             |      FOLLOW_UPS      |
     |             |----------------------|
     |             | id UUID          PK  |
     |             | customer_id FK    -- |
     |             | user_id FK       -- |
     |             | title, content       |
     |             | remind_at            |
     |             | remind_type (ENUM)   |
     |             | is_done, done_at     |
     |             +----------------------+
     |
     +----------> +----------------------+
                   |     AUDIT_LOGS       |
                   |----------------------|
                   | id UUID          PK  |
                   | user_id FK       -- |
                   | action, object_type |
                   | object_id            |
                   | customer_id FK    -- |
                   | before_data (JSON)   |
                   | after_data (JSON)    |
                   | ip_address           |
                   +----------------------+

                     +----------------------+
                     |      DICT_ITEMS      |
                     |----------------------|
                     | id UUID          PK  |
                     | category             |
                     | name, code           |
                     | sort_order           |
                     | is_active            |
                     +----------------------+
```

**Relationship summary (all 1-to-many, FK on the child side):**

| Parent | Child | FK column | Notes |
|--------|-------|-----------|-------|
| `users` | `customers` | `customers.sales_id` | Owner/assigned salesperson (nullable) |
| `users` | `tasks` | `tasks.assignee_id` | Task assignee (nullable) |
| `users` | `documents` | `documents.uploaded_by` | Uploader (nullable) |
| `users` | `communications` | `communications.user_id` | Author (nullable) |
| `users` | `payments` | `payments.recorded_by` | Recorder (nullable) |
| `users` | `stage_histories` | `stage_histories.changed_by` | Operator (nullable) |
| `users` | `notifications` | `notifications.user_id` | Recipient (NOT NULL) |
| `users` | `follow_ups` | `follow_ups.user_id` | Owner (nullable) |
| `users` | `audit_logs` | `audit_logs.user_id` | Actor (nullable) |
| `customers` | `contracts`, `tasks`, `documents`, `communications`, `payments`, `stage_histories`, `follow_ups`, `audit_logs` | `*.customer_id` | All cascade `all, delete-orphan` (except audit_logs handled explicitly) |

---

## 2. Table: `users`

Registered system users. Roles are enforced at the application layer.

| Column         | Type             | Constraints              | Description |
|----------------|------------------|--------------------------|-------------|
| `id`           | UUID (CHAR(32))  | PK                       | User id (TimestampMixin) |
| `name`         | VARCHAR(50)      | NOT NULL                 | Display name |
| `email`        | VARCHAR(100)     | NOT NULL, UNIQUE         | Login account (unique) |
| `phone`        | VARCHAR(20)      | NULL                     | Phone number |
| `password_hash`| VARCHAR(200)     | NOT NULL                 | bcrypt hash (via passlib `CryptContext`) |
| `role`         | ENUM('admin','sales','pm','cs') | NOT NULL | Role used for RBAC |
| `is_active`    | BOOLEAN          | NOT NULL, DEFAULT TRUE   | Soft-disable flag |
| `created_at`   | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`   | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** 1-to-many with `customers` (sales_id), `tasks` (assignee_id), `documents` (uploaded_by), `communications` (user_id), `payments` (recorded_by), `stage_histories` (changed_by), `notifications` (user_id), `follow_ups` (user_id), `audit_logs` (user_id).

---

## 3. Table: `customers`

The central entity — a customer pipeline record flowing through 8 stages.

| Column             | Type             | Constraints              | Description |
|--------------------|------------------|--------------------------|-------------|
| `id`               | UUID (CHAR(32))  | PK                       | Customer id (TimestampMixin) |
| `name`             | VARCHAR(100)     | NOT NULL                 | Customer name |
| `contact_person`   | VARCHAR(50)      | NULL                     | Contact person |
| `phone`            | VARCHAR(20)      | NOT NULL, UNIQUE         | Contact phone (unique) |
| `wechat`           | VARCHAR(50)      | NULL                     | WeChat id |
| `email`            | VARCHAR(100)     | NULL                     | E-mail |
| `company`          | VARCHAR(200)     | NULL                     | Company name |
| `region`           | VARCHAR(50)      | NULL                     | Region (dict `region`) |
| `source_channel`   | VARCHAR(50)      | NULL                     | Lead source (dict `channel`) |
| `sales_id`         | UUID (CHAR(32))  | FK → `users.id`, NULL    | Assigned salesperson |
| `current_stage`    | INT              | NOT NULL, DEFAULT 1      | Current pipeline stage (1–8) |
| `stage_entered_at` | DATETIME         | NOT NULL, `server_default = now()` | When the customer entered the current stage (alert timer start) |
| `contract_amount`  | DECIMAL(12,2)    | DEFAULT 0                | Total contract value |
| `paid_amount`      | DECIMAL(12,2)    | DEFAULT 0                | Total paid (auto-maintained by payment operations) |
| `status`           | ENUM('active','lost','completed','terminated','deleted') | NOT NULL, DEFAULT 'active' | Lifecycle status (`deleted` = soft-deleted, hidden from lists) |
| `lost_reason`      | TEXT             | NULL                     | Reason when status = `lost` |
| `created_at`       | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`       | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** 1-to-many (all `cascade="all, delete-orphan"`) with `contracts`, `tasks`, `documents`, `communications`, `payments`, `stage_histories`, `follow_ups`, `audit_logs`; many-to-1 with `users` (via `sales_id`).

---

## 4. Table: `contracts`

Contracts attached to customers. A contract with a non-null `sign_date` is the prerequisite for advancing from stage 2 → 3.

| Column             | Type           | Constraints              | Description |
|--------------------|----------------|--------------------------|-------------|
| `id`               | UUID (CHAR(32))| PK                       | Contract id (TimestampMixin) |
| `customer_id`      | UUID (CHAR(32))| FK → `customers.id`, NOT NULL | Owning customer |
| `contract_no`      | VARCHAR(50)    | NOT NULL                 | Contract number |
| `contract_amount`  | DECIMAL(12,2)  | NULL                     | Contract amount |
| `sign_date`        | DATE           | NULL                     | Signing date (used by stage rule 2→3) |
| `payment_terms`    | TEXT           | NULL                     | Payment terms |
| `delivery_date`    | DATE           | NULL                     | Delivery date |
| `contract_file`    | VARCHAR(500)   | NULL                     | Stored file path/URL |
| `created_at`       | DATETIME       | NOT NULL                 | TimestampMixin |
| `updated_at`       | DATETIME       | NOT NULL                 | TimestampMixin |

**Relationships:** many-to-1 with `customers` (back-populates `contracts`).

---

## 5. Table: `tasks`

Work items assigned per customer. The stage rule 5→6 requires all tasks to be `completed`.

| Column         | Type             | Constraints              | Description |
|----------------|------------------|--------------------------|-------------|
| `id`           | UUID (CHAR(32))  | PK                       | Task id (TimestampMixin) |
| `customer_id`  | UUID (CHAR(32))  | FK → `customers.id`, NOT NULL | Owning customer |
| `name`         | VARCHAR(200)     | NOT NULL                 | Task title |
| `description`  | TEXT             | NULL                     | Task description |
| `assignee_id`  | UUID (CHAR(32))  | FK → `users.id`, NULL    | Assignee |
| `status`       | ENUM('pending','in_progress','completed') | NOT NULL, DEFAULT 'pending' | Task status |
| `priority`     | ENUM('low','medium','high','urgent') | NOT NULL, DEFAULT 'medium' | Task priority |
| `start_date`   | DATE             | NULL                     | Planned start |
| `due_date`     | DATE             | NULL                     | Due date (scheduler fires "due today" notifications) |
| `completed_at` | DATETIME         | NULL                     | Completion timestamp (set by API when status → completed) |
| `created_at`   | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`   | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** many-to-1 with `customers` and `users` (assignee).

---

## 6. Table: `documents`

Uploaded customer files. The stage rule 6→7 requires at least one document with `category = 'acceptance'`.

| Column         | Type             | Constraints              | Description |
|----------------|------------------|--------------------------|-------------|
| `id`           | UUID (CHAR(32))  | PK                       | Document id (TimestampMixin) |
| `customer_id`  | UUID (CHAR(32))  | FK → `customers.id`, NOT NULL | Owning customer |
| `file_name`    | VARCHAR(200)     | NOT NULL                 | Original file name |
| `file_path`    | VARCHAR(500)     | NOT NULL                 | Path on disk (`backend/app/uploads/{customer_id}/...`) |
| `file_size`    | INT              | NULL                     | Size in bytes |
| `file_type`    | VARCHAR(20)      | NULL                     | Extension without dot |
| `category`     | VARCHAR(50)      | NULL                     | Category (dict `document_category`; `acceptance` is special-cased by the stage engine) |
| `uploaded_by`  | UUID (CHAR(32))  | FK → `users.id`, NULL    | Uploading user |
| `created_at`   | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`   | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** many-to-1 with `customers` and `users` (uploader).

---

## 7. Table: `communications`

Logged customer interaction records (used by the timeline and the lead-timeout scheduler).

| Column             | Type             | Constraints              | Description |
|--------------------|------------------|--------------------------|-------------|
| `id`               | UUID (CHAR(32))  | PK                       | Communication id (TimestampMixin) |
| `customer_id`      | UUID (CHAR(32))  | FK → `customers.id`, NOT NULL | Owning customer |
| `user_id`          | UUID (CHAR(32))  | FK → `users.id`, NULL    | Authoring user |
| `channel`          | ENUM('phone','wechat','meeting','email') | NOT NULL | Communication channel |
| `content`          | TEXT             | NULL                     | Conversation content |
| `next_action`      | TEXT             | NULL                     | Planned next action |
| `next_action_date` | DATE             | NULL                     | Date for next action |
| `created_at`       | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`       | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** many-to-1 with `customers` and `users`.

---

## 8. Table: `payments`

Payment installments. `customers.paid_amount` is kept in sync by the payment APIs.

| Column         | Type             | Constraints              | Description |
|----------------|------------------|--------------------------|-------------|
| `id`           | UUID (CHAR(32))  | PK                       | Payment id (TimestampMixin) |
| `customer_id`  | UUID (CHAR(32))  | FK → `customers.id`, NOT NULL | Owning customer |
| `amount`       | DECIMAL(12,2)    | NOT NULL                 | Payment amount (> 0) |
| `payment_date` | DATE             | NULL                     | Payment date |
| `payment_type` | ENUM('deposit','milestone','final') | NOT NULL | Payment stage type |
| `invoice_no`   | VARCHAR(50)      | NULL                     | Invoice number |
| `notes`        | TEXT             | NULL                     | Notes |
| `recorded_by`  | UUID (CHAR(32))  | FK → `users.id`, NULL    | Recording user |
| `created_at`   | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`   | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** many-to-1 with `customers` and `users` (recorder).

---

## 9. Table: `notifications`

In-app notifications (created by the API and the background scheduler).

| Column         | Type             | Constraints              | Description |
|----------------|------------------|--------------------------|-------------|
| `id`           | UUID (CHAR(32))  | PK                       | Notification id (TimestampMixin) |
| `user_id`      | UUID (CHAR(32))  | FK → `users.id`, NOT NULL | Recipient |
| `type`         | VARCHAR(50)      | NOT NULL                 | Type: `task_due`, `payment_overdue`, `auto_lost`, etc. |
| `title`        | VARCHAR(200)     | NOT NULL                 | Short title |
| `content`      | TEXT             | NULL                     | Body text |
| `related_id`   | UUID (CHAR(32))  | NULL                     | Related entity id (no FK) |
| `related_type` | VARCHAR(50)      | NULL                     | Related entity type (`customer`, `task`, ...) |
| `is_read`      | BOOLEAN          | NOT NULL, DEFAULT FALSE | Read flag |
| `created_at`   | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`   | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** many-to-1 with `users` (recipient).

---

## 10. Table: `follow_ups`

Follow-up reminders owned by users and attached to customers.

| Column         | Type             | Constraints              | Description |
|----------------|------------------|--------------------------|-------------|
| `id`           | UUID (CHAR(32))  | PK                       | Follow-up id (TimestampMixin) |
| `customer_id`  | UUID (CHAR(32))  | FK → `customers.id`, NOT NULL | Owning customer |
| `user_id`      | UUID (CHAR(32))  | FK → `users.id`, NULL    | Owner |
| `title`        | VARCHAR(200)     | NOT NULL                 | Reminder title |
| `content`      | TEXT             | NULL                     | Reminder body |
| `remind_at`    | DATETIME         | NULL                     | Scheduled reminder time |
| `remind_type`  | ENUM('system_notification','email') | NOT NULL, DEFAULT 'system_notification' | Delivery channel |
| `is_done`      | BOOLEAN          | NOT NULL, DEFAULT FALSE | Completion flag |
| `done_at`      | DATETIME         | NULL                     | When marked done |
| `created_at`   | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`   | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** many-to-1 with `customers` and `users`.

---

## 11. Table: `audit_logs`

Immutable operation trail. Stores JSON snapshots for before/after data.

| Column         | Type             | Constraints              | Description |
|----------------|------------------|--------------------------|-------------|
| `id`           | UUID (CHAR(32))  | PK                       | Log id (TimestampMixin) |
| `user_id`      | UUID (CHAR(32))  | FK → `users.id`, NULL    | Acting user |
| `action`       | VARCHAR(50)      | NOT NULL                 | Action name (e.g. `create`, `update`, `delete`, `stage_change`) |
| `object_type`  | VARCHAR(50)      | NOT NULL                 | Object type (e.g. `customer`, `contract`, `task`) |
| `object_id`    | UUID (CHAR(32))  | NULL                     | Affected object id (no FK) |
| `customer_id`  | UUID (CHAR(32))  | FK → `customers.id`, NULL | Customer context (for customer-scoped filtering) |
| `before_data`  | JSON             | NULL                     | State snapshot before the change |
| `after_data`   | JSON             | NULL                     | State snapshot after the change |
| `ip_address`   | VARCHAR(50)      | NULL                     | Client IP |
| `created_at`   | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`   | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** many-to-1 with `users` and `customers`.

---

## 12. Table: `stage_histories`

Full audit of every stage transition (advance and rollback).

| Column         | Type             | Constraints              | Description |
|----------------|------------------|--------------------------|-------------|
| `id`           | UUID (CHAR(32))  | PK                       | History id (TimestampMixin) |
| `customer_id`  | UUID (CHAR(32))  | FK → `customers.id`, NOT NULL | Owning customer |
| `from_stage`   | INT              | NULL                     | Previous stage (NULL for first entry? — nullable in schema) |
| `to_stage`     | INT              | NOT NULL                 | New stage |
| `changed_by`   | UUID (CHAR(32))  | FK → `users.id`, NULL    | Operator |
| `changed_at`   | DATETIME         | NOT NULL, `server_default = now()` | Transition time |
| `remark`       | TEXT             | NULL                     | Operator remark |
| `created_at`   | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`   | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** many-to-1 with `customers` and `users` (operator).

---

## 13. Table: `dict_items`

Configurable dropdown option lists (data dictionary). Four categories are used: `industry`, `region`, `channel`, `document_category`.

| Column         | Type             | Constraints              | Description |
|----------------|------------------|--------------------------|-------------|
| `id`           | UUID (CHAR(32))  | PK                       | Item id (TimestampMixin) |
| `category`     | VARCHAR(50)      | NOT NULL                 | Dictionary category |
| `name`         | VARCHAR(100)     | NOT NULL                 | Display name |
| `code`         | VARCHAR(50)      | NULL                     | Stable code value |
| `sort_order`   | INT              | NOT NULL, DEFAULT 0      | Display order (ascending) |
| `is_active`    | BOOLEAN          | NOT NULL, DEFAULT TRUE  | Soft-hide flag |
| `created_at`   | DATETIME         | NOT NULL                 | TimestampMixin |
| `updated_at`   | DATETIME         | NOT NULL                 | TimestampMixin |

**Relationships:** none (standalone).

---

## 14. MySQL-Specific Implementation Notes

1. **UUID storage.** SQLAlchemy `Uuid(as_uuid=True)` renders as `CHAR(32)` on MySQL — the hex representation of the UUID without dashes. All primary keys and foreign keys use this type, generated as `uuid.uuid4()` at the application layer. The MySQL `UUID()` function is not used.
2. **JSON columns.** `audit_logs.before_data` and `audit_logs.after_data` map to MySQL's native `JSON` type, allowing schema-less snapshots of changed records.
3. **Charset/collation.** The MySQL container is started with `--character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci`, and the SQLAlchemy URL includes `?charset=utf8mb4` (PyMySQL driver), so all text columns are utf8mb4.
4. **ENUM columns.** The following columns are MySQL `ENUM` types (SQLAlchemy `Enum`): `users.role`, `customers.status`, `tasks.status`, `tasks.priority`, `communications.channel`, `payments.payment_type`, `follow_ups.remind_type`. Values are validated at the ORM layer; inserting an unlisted value raises an error.
5. **Timestamps.** `created_at`/`updated_at` use `DateTime(timezone=True)`; on MySQL this is `DATETIME` (no fractional timezone storage), with defaults applied server-side via `func.now()`. `stage_entered_at` and `changed_at` also use `server_default=func.now()`.
6. **Numeric amounts.** `contract_amount`, `paid_amount` and `payments.amount` are `DECIMAL(12,2)` for exact money arithmetic.
7. **Deletion semantics.** Customers are soft-deleted (`status = 'deleted'`, which hides them from all customer lists and the Kanban board); contracts, tasks, documents, communications, payments, follow-ups and audit logs are hard-deleted (with `cascade="all, delete-orphan"` on customer relationships).
8. **No composite indexes** are declared in the models; the only unique constraints are `users.email` and `customers.phone` (plus the implicit PKs/FKs).
