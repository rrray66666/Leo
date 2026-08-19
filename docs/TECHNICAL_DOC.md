# CRM 系统技术文档

> 版本：1.0.0 ｜ 适用交付版
> 本文档覆盖：系统整体设计方案、技术架构、数据库设计、前后端接口定义、登录/注册设计、并发能力与部署方案（含国内服务器、跨域与跨国访问风险分析）。

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术架构](#2-技术架构)
3. [项目结构](#3-项目结构)
4. [系统整体设计](#4-系统整体设计)
5. [数据库设计](#5-数据库设计)
6. [API 接口设计](#6-api-接口设计)
7. [登录与注册设计](#7-登录与注册设计)
8. [并发与性能设计](#8-并发与性能设计)
9. [部署方案与跨域/跨国访问](#9-部署方案与跨域跨国访问)

---

## 1. 项目概述

CRM 客户关系管理系统，提供 **8 阶段看板式销售管道**（线索 → 咨询 → 签约 → 需求 → 交付执行 → 交付 → 回款 → 完成），覆盖客户、合同、任务、文档、沟通、回款、跟进、通知、审计等完整业务闭环。

- 前端：Vue 3（组合式 API）+ Element Plus + Pinia + Vue Router + Axios + Vite
- 后端：FastAPI + SQLAlchemy 2.0 + Pydantic v2 + JWT + bcrypt
- 数据库：MySQL 8（utf8mb4）
- 缓存（可选）：Redis 7（调度任务通知降级，非硬依赖）
- 文件存储：MinIO（S3 兼容，可选）/ 本地文件系统（默认 fallback）

## 2. 技术架构

```
┌──────────────────────────────────────────────┐
│                浏览器 (Vue 3 SPA)             │
│  Login / Kanban / CustomerList / Dashboard…  │
└──────────────────────┬───────────────────────┘
                       │  HTTP / JSON  (Axios)
                       │  JWT Bearer Token
              ┌────────▼────────┐  Vite dev proxy / Nginx
              │   FastAPI 后端   │
              │  app/api (15 模块)│
              │  app/services    │
              │  app/core (JWT/权限)│
              └──┬──────────┬───┘
                 │ SQLAlchemy│  aiofiles
        ┌────────▼───┐  ┌───▼────────┐
        │  MySQL 8   │  │ 本地 uploads │──可选──▶ MinIO
        └────────────┘  └────────────┘
```

请求链路：前端 Axios → Vite 代理（开发）/ Nginx（生产）`/api` → FastAPI 路由 → 依赖注入鉴权（`get_current_active_user`）→ 服务层业务逻辑 → SQLAlchemy → MySQL → JSON 统一响应。

## 3. 项目结构

```
backend/
├── app/
│   ├── main.py            # FastAPI 入口，启动时 create_all 建表 + 启动 APScheduler
│   ├── config.py          # Pydantic Settings 配置（读 backend/.env）
│   ├── database.py        # SQLAlchemy engine / SessionLocal / Base
│   ├── models/            # 12 张表的 ORM 模型
│   ├── schemas/           # Pydantic 请求/响应模型（校验）
│   ├── api/               # 15 个 REST 路由模块
│   ├── services/          # 业务逻辑层（客户/看板/通知/调度/审计/阶段）
│   ├── scripts/seed_demo.py  # 演示数据种子（幂等）
│   └── core/              # security.py(JWT/bcrypt) + deps.py(鉴权/越权控制)
├── requirements.txt
├── .env.example           # 本地配置模板
└── Dockerfile
frontend/
├── src/
│   ├── views/             # 12 个页面组件
│   ├── components/        # 公共组件（StageTag/CustomerCard/AlertBadge…）
│   ├── stores/            # Pinia（user/customer/notification）
│   ├── api/               # axios 封装 + 各模块 API 方法
│   ├── router/            # 路由 + 登录守卫
│   └── styles/
├── nginx.conf             # 生产 Nginx 反代配置
└── Dockerfile             # node 构建 → nginx 静态托管
docker-compose.yml         # 5 服务编排（mysql/redis/minio/backend/frontend）
db_init.sql                # MySQL 建库建用户脚本
start-all.bat              # 本地 Windows 一键启动
```

## 4. 系统整体设计

### 4.1 模块划分

| 模块 | 后端路由前缀 | 说明 |
|------|-------------|------|
| 认证 Auth | `/api/v1/auth` | 登录 / 注册 / 刷新 / 当前用户 |
| 客户 Customers | `/api/v1/customers` | CRUD + 阶段推进 + 状态 + 指派 + 批量 + 导入导出 |
| 合同 Contracts | `/api/v1/customers/{id}/contract` | 按客户合同管理 |
| 任务 Tasks | `/api/v1/customers/{id}/tasks` | 客户任务（负责人/优先级/状态/截止） |
| 文档 Documents | `/api/v1/customers/{id}/documents` | 上传/下载/替换 |
| 沟通 Communications | `/api/v1/customers/{id}/communications` | 沟通记录 |
| 回款 Payments | `/api/v1/customers/{id}/payments` | 回款记录 |
| 看板 Board | `/api/v1/board` | 看板数据 / 逾期预警 |
| 仪表盘 Dashboard | `/api/v1/dashboard` | 统计 / 漏斗 / 销售 / 回款趋势 |
| 用户 Users | `/api/v1/users` | 用户管理 / 改密 |
| 通知 Notifications | `/api/v1/notifications` | 站内通知 |
| 跟进 Follow-ups | `/api/v1/follow-ups` | 跟进提醒 |
| 审计 Audit Logs | `/api/v1/audit-logs` | 操作审计 |
| 字典 Dicts | `/api/v1/dict` | 下拉字典（地区/行业/渠道/分类） |
| 搜索 Search | `/api/v1/search` | 全局搜索 |

### 4.2 权限模型（RBAC + 对象级访问控制）

四种角色：

| 角色 | 说明 |
|------|------|
| `admin` | 全部权限，含用户管理、批量操作、删除客户 |
| `sales` | 仅能操作**自有客户**（写），可读自己负责的客户 |
| `pm` | 全局只读 + 查看指派给自己的任务 |
| `cs` | 仅可读自有客户 |

实现要点（`app/core/deps.py`）：

- `get_current_active_user`：JWT 解析 + 用户禁用校验，是除登录外的所有接口依赖。
- `check_customer_access`：**对象级读权限**，不满足直接抛 403（而非返回 bool 让调用方自行判断——历史版本曾因"返回未检查"导致越权，已改为强制抛错）。
- `check_customer_write_access`：写权限（admin 全量、sales 仅自有）。
- 批量接口（assign/status/delete）通过 `_assert_batch_customer_access` 逐条校验归属；`batch/delete` 仅 admin。
- 文档上传采用 `os.path.basename` 净化文件名，防路径穿越。

### 4.3 核心业务流

**客户生命周期（8 阶段）**：阶段只允许前进，不允许回退；跨阶段推进有前置约束：

| 阶段推进 | 前置条件 |
|---------|---------|
| 2 → 3 | 至少一份已签约合同 |
| 5 → 6 | 该客户所有任务已完成 |
| 6 → 7 | 已上传验收文档 |
| 7 → 8 | 已收款 ≥ 合同金额 |

**阶段停留预警**：每阶段有"正常线/预警线"，由 `stage_service.get_alert_level` 根据 `stage_entered_at` 计算，分为 normal / warning / danger，驱动看板告警与通知。

**审计**：客户创建/更新/阶段推进/状态变更等写操作通过 `audit_service.log_action` 记录 before/after 数据快照，写入 `audit_logs`。

**后台调度（APScheduler）**：每小时检查任务逾期、每 6 小时检查线索超时与回款逾期，生成站内通知。

## 5. 数据库设计

数据库：MySQL 8，库名 `crm`，字符集 `utf8mb4`。共 12 张表。主键统一为 UUID（`Uuid(as_uuid=True)`，应用层 `uuid4` 生成）；时间戳统一带时区（`DateTime(timezone=True)`，默认 `CURRENT_TIMESTAMP`，`updated_at` 随更新自动刷新）。

### 5.1 users 用户表

| 字段 | 类型 | 约束/默认 | 说明 |
|------|------|-----------|------|
| id | UUID | PK | 主键 |
| name | varchar(50) | NOT NULL | 姓名 |
| email | varchar(100) | NOT NULL, UNIQUE | 登录邮箱 |
| phone | varchar(20) | 可空 | 手机号 |
| password_hash | varchar(200) | NOT NULL | bcrypt 哈希（不存明文） |
| role | enum('admin','sales','pm','cs') | NOT NULL | 角色 |
| is_active | tinyint(1) | NOT NULL, default 1 | 是否启用 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.2 customers 客户表

| 字段 | 类型 | 约束/默认 | 说明 |
|------|------|-----------|------|
| id | UUID | PK | 主键 |
| name | varchar(100) | NOT NULL | 客户名称 |
| contact_person | varchar(50) | 可空 | 联系人 |
| phone | varchar(20) | NOT NULL, **UNIQUE** | 手机号（唯一） |
| wechat | varchar(50) | 可空 | 微信 |
| email | varchar(100) | 可空 | 邮箱 |
| company | varchar(200) | 可空 | 公司 |
| region | varchar(50) | 可空 | 地区 |
| source_channel | varchar(50) | 可空 | 来源渠道 |
| sales_id | UUID | FK → users.id, 可空 | 负责销售 |
| current_stage | int | NOT NULL, default 1 | 当前阶段 1-8 |
| stage_entered_at | datetime(6) | NOT NULL | 进入当前阶段时间（驱动预警） |
| contract_amount | decimal(12,2) | default 0 | 合同金额 |
| paid_amount | decimal(12,2) | default 0 | 已回款金额 |
| status | enum('active','lost','completed','terminated','deleted') | NOT NULL, default 'active' | 状态（软删除用 deleted） |
| lost_reason | text | 可空 | 流失原因 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.3 contracts 合同表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| customer_id | UUID | FK → customers.id, NOT NULL | 所属客户 |
| contract_no | varchar(50) | NOT NULL | 合同编号 |
| contract_amount | decimal(12,2) | 可空 | 合同金额 |
| sign_date | date | 可空 | 签约日期 |
| payment_terms | text | 可空 | 付款条款 |
| delivery_date | date | 可空 | 交付日期 |
| contract_file | varchar(500) | 可空 | 合同文件路径 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.4 tasks 任务表

| 字段 | 类型 | 约束/默认 | 说明 |
|------|------|-----------|------|
| id | UUID | PK | 主键 |
| customer_id | UUID | FK, NOT NULL | 所属客户 |
| name | varchar(200) | NOT NULL | 任务名 |
| description | text | 可空 | 描述 |
| assignee_id | UUID | FK → users.id, 可空 | 负责人 |
| status | enum('pending','in_progress','completed') | default 'pending' | 状态 |
| priority | enum('low','medium','high','urgent') | default 'medium' | 优先级 |
| start_date / due_date | date | 可空 | 起止日期 |
| completed_at | datetime(6) | 可空 | 完成时间 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.5 documents 文档表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| customer_id | UUID | FK, NOT NULL | 所属客户 |
| file_name | varchar(200) | NOT NULL | 文件名（basename 净化后） |
| file_path | varchar(500) | NOT NULL | 存储路径 |
| file_size | int | 可空 | 字节数 |
| file_type | varchar(20) | 可空 | 扩展名 |
| category | varchar(50) | 可空 | 分类（合同/需求/验收/发票/其他） |
| uploaded_by | UUID | FK → users.id, 可空 | 上传人 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.6 communications 沟通记录表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| customer_id | UUID | FK, NOT NULL | 所属客户 |
| user_id | UUID | FK → users.id, 可空 | 记录人 |
| channel | enum('phone','wechat','meeting','email') | NOT NULL | 渠道 |
| content | text | 可空 | 内容 |
| next_action | text | 可空 | 下一步动作 |
| next_action_date | date | 可空 | 下一步日期 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.7 payments 回款表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| customer_id | UUID | FK, NOT NULL | 所属客户 |
| amount | decimal(12,2) | NOT NULL | 金额 |
| payment_date | date | 可空 | 回款日期 |
| payment_type | enum('deposit','milestone','final') | NOT NULL | 定金/里程碑/尾款 |
| invoice_no | varchar(50) | 可空 | 发票号 |
| notes | text | 可空 | 备注 |
| recorded_by | UUID | FK → users.id, 可空 | 记录人 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.8 notifications 通知表

| 字段 | 类型 | 约束/默认 | 说明 |
|------|------|-----------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users.id, NOT NULL | 接收人 |
| type | varchar(50) | NOT NULL | task/stage_alert/follow_up/system 等 |
| title | varchar(200) | NOT NULL | 标题 |
| content | text | 可空 | 内容 |
| related_id | UUID | 可空 | 关联业务对象 id |
| related_type | varchar(50) | 可空 | 关联类型 |
| is_read | tinyint(1) | NOT NULL, default 0 | 是否已读 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.9 follow_ups 跟进表

| 字段 | 类型 | 约束/默认 | 说明 |
|------|------|-----------|------|
| id | UUID | PK | 主键 |
| customer_id | UUID | FK, NOT NULL | 所属客户 |
| user_id | UUID | FK, 可空 | 跟进人 |
| title | varchar(200) | NOT NULL | 标题 |
| content | text | 可空 | 内容 |
| remind_at | datetime(6) | 可空 | 提醒时间 |
| remind_type | enum('system_notification','email','high_priority') | default 'system_notification' | 提醒方式 |
| is_done | tinyint(1) | NOT NULL, default 0 | 是否完成 |
| done_at | datetime(6) | 可空 | 完成时间 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.10 audit_logs 审计表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users.id, 可空 | 操作人 |
| action | varchar(50) | NOT NULL | create/update/delete/advance_stage… |
| object_type | varchar(50) | NOT NULL | customer/contract/task… |
| object_id | UUID | 可空 | 对象 id |
| customer_id | UUID | FK, 可空 | 关联客户 |
| before_data | json | 可空 | 变更前快照 |
| after_data | json | 可空 | 变更后快照 |
| ip_address | varchar(50) | 可空 | 客户端 IP |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.11 stage_histories 阶段历史表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| customer_id | UUID | FK, NOT NULL | 所属客户 |
| from_stage | int | 可空 | 原阶段 |
| to_stage | int | NOT NULL | 新阶段 |
| changed_by | UUID | FK, 可空 | 操作人 |
| changed_at | datetime(6) | NOT NULL | 变更时间 |
| remark | text | 可空 | 备注 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.12 dict_items 数据字典表

| 字段 | 类型 | 约束/默认 | 说明 |
|------|------|-----------|------|
| id | UUID | PK | 主键 |
| category | varchar(50) | NOT NULL | region/industry/channel/document_category |
| name | varchar(100) | NOT NULL | 显示名 |
| code | varchar(50) | 可空 | 编码 |
| sort_order | int | NOT NULL, default 0 | 排序 |
| is_active | tinyint(1) | NOT NULL, default 1 | 启用 |
| created_at / updated_at | datetime(6) | NOT NULL | 时间戳 |

### 5.13 表关系（ER）

```
users 1 ── n customers (sales_id)
users 1 ── n tasks (assignee_id)
users 1 ── n communications (user_id)
users 1 ── n payments (recorded_by)
users 1 ── n notifications (user_id)
users 1 ── n follow_ups (user_id)
users 1 ── n audit_logs (user_id)
users 1 ── n stage_histories (changed_by)
customers 1 ── n contracts / tasks / documents / communications / payments / follow_ups / stage_histories / audit_logs
```

### 5.14 建表与迁移

- 表结构由 ORM 模型定义，应用启动时 `Base.metadata.create_all(bind=engine)` **自动建表**（`app/main.py` lifespan）。
- 项目同时保留 Alembic 骨架（`backend/alembic/`），正式生产可用 `alembic revision` 做增量迁移。
- 演示数据：`python -m app.scripts.seed_demo`（幂等，重复执行安全跳过）。

---

## 6. API 接口设计

### 6.1 通用约定

- **Base URL**：`http://<host>:8000/api/v1`（开发环境经 Vite 代理 `/api`；生产经 Nginx）
- **交互文档**：Swagger UI `http://<host>:8000/docs`、ReDoc `/redoc`（FastAPI 自动生成）
- **鉴权**：除 `/auth/login`、`/auth/register` 外全部接口需携带请求头 `Authorization: Bearer <access_token>`；无令牌返回 `401`，被禁用用户返回 `403`
- **统一响应格式**：`{"code": 0, "message": "success", "data": ...}`，`code=0` 表示成功
- **分页**：统一使用 `page`（从 1 开始）、`page_size`（默认 20，上限 100）
- **错误**：使用 HTTP 状态码（400 参数/业务校验、401 未认证、403 无权限、404 不存在、422 Pydantic 校验失败、500 服务异常）
- **时间格式**：ISO 8601（如 `2026-08-11T12:00:00+00:00`）；纯日期用 `YYYY-MM-DD`

### 6.2 认证模块 `/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/login` | 登录，返回 JWT 与用户信息 |
| POST | `/auth/register` | 注册（落库 MySQL，默认 sales 角色，成功后自动登录返回 token） |
| POST | `/auth/refresh` | 用现有 token 换新 token |
| GET | `/auth/me` | 当前登录用户信息 |

`POST /auth/login` 请求体：

```json
{ "email": "demo.admin@crm.com", "password": "demo123456" }
```

响应：

```json
{
  "code": 0, "message": "success",
  "data": {
    "access_token": "<jwt>",
    "token_type": "bearer",
    "user": { "id": "...", "name": "Demo Admin", "email": "...", "role": "admin" }
  }
}
```

`POST /auth/register` 请求体：`{ "name", "email", "phone"?, "password" }`。校验：email 唯一、phone 唯一（若提供）、密码 ≥ 6 位。

### 6.3 客户模块 `/customers`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/customers` | 创建客户 | 登录用户（自动归属 sales_id=本人） |
| GET | `/customers` | 分页列表 + 筛选（keyword/stage/status/sales_id/region/alert_level） | 登录 |
| GET | `/customers/advanced-search` | 高级搜索（多条件 + 金额区间 + 时间区间） | 登录 |
| GET | `/customers/export` | 导出 Excel（按筛选条件） | 登录 |
| GET | `/customers/export-template` | 下载导入模板 | 登录 |
| GET | `/customers/{id}` | 客户详情（含 stay_days/alert_level/sales_name） | 对象级读 |
| PUT | `/customers/{id}` | 更新客户（phone 唯一校验） | 写权限 |
| DELETE | `/customers/{id}` | 软删除（status=deleted） | 仅 admin |
| PUT | `/customers/{id}/stage` | 阶段推进（含前置条件校验） | 写权限 |
| PUT | `/customers/{id}/status` | 状态变更（active/lost/completed/terminated） | 写权限 |
| PUT | `/customers/{id}/assign` | 指派/转移负责人 | 写权限 |
| GET | `/customers/{id}/timeline` | 时间线（阶段历史+沟通+审计） | 对象级读 |
| POST | `/customers/batch/assign` | 批量转移负责人 | 归属校验 |
| POST | `/customers/batch/status` | 批量改状态 | 归属校验 |
| POST | `/customers/batch/delete` | 批量删除 | 仅 admin + 归属校验 |
| POST | `/customers/import` | Excel 批量导入 | 登录 |

客户对象核心字段（响应 data）：`id/name/contact_person/phone/wechat/email/company/region/source_channel/sales_id/current_stage/stage_entered_at/contract_amount/paid_amount/status/lost_reason/created_at/updated_at/stay_days/alert_level/sales_name`。

### 6.4 合同模块 `/customers/{customer_id}/contract`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/customers/{id}/contract` | 创建合同 |
| GET | `/customers/{id}/contract` | 查客户合同（可含多份） |
| PUT | `/contracts/{id}` | 更新合同 |
| PUT | `/contracts/{id}/file` | 上传/替换合同文件（multipart） |
| DELETE | `/contracts/{id}` | 删除合同 |

### 6.5 任务模块 `/customers/{customer_id}/tasks`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/customers/{id}/tasks` | 创建任务 |
| GET | `/customers/{id}/tasks` | 任务列表 |
| GET | `/tasks/{id}` | 任务详情 |
| PUT | `/tasks/{id}` | 更新任务 |
| PATCH | `/tasks/{id}/status` | 改状态（自动写 completed_at） |
| PATCH | `/tasks/{id}/assignee` | 改负责人 |
| DELETE | `/tasks/{id}` | 删除任务 |

### 6.6 文档模块 `/customers/{customer_id}/documents`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/customers/{id}/documents` | 上传（multipart，文件名 basename 净化） |
| GET | `/customers/{id}/documents` | 文档列表 |
| GET | `/documents/{id}` | 文档详情 |
| GET | `/documents/{id}/download` | 下载文件（blob） |
| PUT | `/documents/{id}` | 更新元信息 |
| PUT | `/documents/{id}/file` | 替换文件 |
| DELETE | `/documents/{id}` | 删除 |

### 6.7 沟通模块 `/customers/{customer_id}/communications`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/customers/{id}/communications` | 新增沟通记录 |
| GET | `/customers/{id}/communications` | 沟通列表 |
| PUT | `/communications/{id}` | 更新 |
| DELETE | `/communications/{id}` | 删除 |

### 6.8 回款模块 `/customers/{customer_id}/payments`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/customers/{id}/payments` | 新增回款 |
| GET | `/customers/{id}/payments` | 回款列表 |
| PUT | `/payments/{id}` | 更新 |
| DELETE | `/payments/{id}` | 删除 |

### 6.9 看板 `/board`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/board/kanban` | 8 阶段看板数据（各列客户 + 计数），支持 sales_id/region/keyword 筛选 |
| GET | `/board/alerts` | 逾期预警客户列表 |

### 6.10 仪表盘 `/dashboard`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/dashboard/stats` | 总览统计（客户数/金额/回款等） |
| GET | `/dashboard/funnel` | 阶段漏斗分析 |
| GET | `/dashboard/sales` | 销售工作量分布 |
| GET | `/dashboard/payment-trend` | 回款趋势 |

### 6.11 用户管理 `/users`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/users` | 创建用户 | admin |
| GET | `/users` | 用户列表（下拉数据来源） | 登录 |
| PUT | `/users/{id}` | 更新用户/角色 | admin |
| PUT | `/users/{id}/password` | 重置密码 | admin |
| GET | `/users/me` | 我的信息 | 登录 |
| PUT | `/users/me` | 更新个人资料 | 登录 |
| PUT | `/users/me/password` | 修改自己密码 | 登录 |

### 6.12 通知 `/notifications`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/notifications` | 我的通知列表（分页） |
| GET | `/notifications/unread-count` | 未读数 |
| PUT | `/notifications/{id}/read` | 标记已读 |
| PUT | `/notifications/read-all` | 全部已读 |

### 6.13 跟进 `/follow-ups`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/customers/{id}/follow-ups` | 新建跟进提醒 |
| GET | `/customers/{id}/follow-ups` | 某客户跟进列表 |
| GET | `/follow-ups/today` | 今日跟进 |
| PUT | `/follow-ups/{id}` | 更新 |
| PUT | `/follow-ups/{id}/done` | 标记完成 |
| DELETE | `/follow-ups/{id}` | 删除 |

### 6.14 审计 `/audit-logs`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/audit-logs` | 审计日志列表（分页/筛选） |
| GET | `/customers/{id}/audit-logs` | 某客户审计 |

### 6.15 字典 `/dict`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/dict/regions` `/dict/industries` `/dict/channels` `/dict/categories` | 各类字典列表 |
| PUT | `/dict/regions` `/dict/industries` `/dict/channels` `/dict/categories` | 更新字典项（admin） |

### 6.16 全局搜索 `/search`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/search/global` | 按姓名/联系人/电话/公司等全局搜索客户 |

### 6.17 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查（`{"status":"ok"}`） |

---

## 7. 登录与注册设计

### 7.1 密码存储

- 采用 **bcrypt**（`passlib` + `bcrypt==4.0.1` 固定版本，规避 passlib 与 bcrypt≥4.1 的兼容问题）。
- 库中仅存 `password_hash`，**不存明文**；每次哈希带随机盐，相同密码产生不同哈希。
- 校验：`verify_password(plain, hash)`。

### 7.2 注册流程（落库 MySQL）

1. 前端登录页切换到 Register 表单，提交 `{name, email, phone?, password, confirm_password}`。
2. 前端校验：邮箱格式、密码 ≥ 6 位、两次密码一致（`Login.vue`）。
3. 后端 `POST /api/v1/auth/register`（`auth.py`）：
   - 校验 `email` 是否已存在 → 400 "Email already registered"；
   - 校验 `phone` 是否已存在（若提供）→ 400 "Phone number already registered"；
   - `get_password_hash(data.password)` 生成 bcrypt 哈希；
   - 以 `role="sales"`、`is_active=True` 创建 `User` 记录并 `db.commit()` —— **数据写入 MySQL `users` 表**；
   - 签发 JWT 并返回 `{access_token, user}`，前端自动登录跳转 `/kanban`。
4. 新注册用户默认"销售"角色，可由管理员在"用户管理"中升级为 admin/pm/cs。

### 7.3 登录与 JWT

1. `POST /auth/login`：按 email 查用户 → bcrypt 校验密码 → 校验 `is_active`。
2. 签发 JWT（`core/security.create_access_token`）：
   - Payload：`{sub: 用户UUID, role, exp: 当前时间 + JWT_EXPIRE_MINUTES}`；
   - 签名：`HS256`，密钥来自 `JWT_SECRET`（默认弱密钥已被 `backend/.env` 注入随机值替换；生产必须自设强密钥）；
   - 有效期：默认 480 分钟（8 小时）。
3. 前端将 token 与用户信息存 `localStorage`；Axios 拦截器自动附加 `Authorization: Bearer`；收到 401 时登出并跳转登录页。
4. 路由守卫：未登录访问受保护路由 → `/login`；已登录访问 `/login` → 首页；`admin` 专属路由（用户管理/字典）校验角色。

### 7.4 Token 失效与安全

- 无 refresh token 机制的白名单——`/auth/refresh` 用现有未过期 token 换取新 token，令牌本身无服务端吊销列表；
- 用户被禁用（`is_active=false`）后，`get_current_active_user` 对已有 token 一律返回 403，等效"强制下线"；
- 密码修改后旧 token 仍有效（无 jti 吊销）；如需严格吊销，后续可引入 Redis 黑名单/版本号方案（见第 9 章风险建议）。

---

## 8. 并发与性能设计

### 8.1 当前实现

| 环节 | 配置 | 说明 |
|------|------|------|
| DB 连接池 | `pool_size=10, max_overflow=20, pool_timeout=30, pool_recycle=3600, pool_pre_ping=True` | 高并发时最多 30 个连接，超时排队不雪崩 |
| 服务进程 | 本地单进程；Docker 镜像 `uvicorn --workers 4` | 生产建议多 worker |
| 前端 | Vite 懒加载路由 + 看板 30s 自动轮询 | 页面按需加载 |
| 定时任务 | APScheduler（任务逾期 1h / 线索超时与回款 6h） | 独立于请求线程，Redis 连接失败自动降级 |

### 8.2 实测结果（交付前压测）

| 场景 | 并发 | 结果 |
|------|------|------|
| 客户列表读取 100 并发 | 100 | **0 失败**，avg 698ms / max 948ms |
| 列表 page_size=50 100 并发 | 100 | **0 失败**，avg 821ms / max 1148ms |
| 看板数据 100 并发 | 100 | **0 失败**，avg 1156ms / max 1643ms |
| 仪表盘统计 100 并发 | 100 | **0 失败**，avg 1376ms / max 1984ms |
| 高级搜索 100 并发 | 100 | **0 失败**，avg 651ms / max 898ms |
| 创建客户 50 并发 | 50 | **50/50 成功落库**，0 失败 |
| 注册 100 并发 | 100 | 0 失败（前期回归） |

结论：**100 人同时使用（读为主）在当前单机 MySQL + 单进程后端下无失败**；写入受手机号唯一约束与数据库连接池限制，50 并发全通过。

### 8.3 100 人生产场景建议

1. 以 Docker Compose 部署，backend 使用 `--workers 4`（镜像已默认）；
2. 若超 200 并发，MySQL 连接池上调至 `pool_size=20/max_overflow=40`，并在 MySQL 端 `max_connections` 同步放大；
3. 前端看板轮询 30s 一次，100 人 × 每 30s = 约 3-4 req/s 附加量，可忽略；
4. 生产必须用 Nginx 托管静态资源 + 反代 `/api`（`frontend/nginx.conf` 已提供），开启 gzip 与静态缓存；
5. 监控项：MySQL 慢查询、后端请求延迟、内存占用。

---

## 9. 部署方案与跨域/跨国访问

### 9.1 三种部署方式

**A. 本地 Windows（演示/单机）**：MySQL 执行 `db_init.sql` → 配置 `backend/.env` → 双击 `start-all.bat`。详见 README。

**B. Docker Compose（推荐，单服务器）**：`cp .env.example .env` 改密码与 JWT_SECRET → `docker-compose up -d --build` → `docker-compose exec backend python -m app.scripts.seed_demo`。5 个容器：mysql/redis/minio/backend(8000)/frontend(nginx:80)。

**C. 国内云服务器（公司目标场景）**：

```
阿里云/腾讯云 ECS (2C4G 起步)
 ├── Docker + docker-compose 运行上述编排
 ├── 安全组/防火墙放行：80(HTTP)、443(HTTPS)、3306(仅内网)、8000(仅内网或关闭)
 ├── Nginx 容器对外 80/443 → 静态前端 + 反代 /api → backend:8000
 ├── 域名解析 A 记录 → 服务器公网 IP
 └── HTTPS：Let's Encrypt 或云厂商免费证书（必需，跨国访问更稳定）
```

**备案与合规（中国境内服务器）**：域名需 ICP 备案（云厂商控制台办理，个人/企业均可，约 1-2 周）；未备案域名无法用国内服务器 80/443 对外服务。若时间紧，可先放境外节点（如香港）免备案，但延迟与合规需权衡。

### 9.2 跨域（CORS）支持原理与配置

浏览器同源策略下，前端（如 `https://crm.example.com`）访问后端（`https://api.example.com`）会产生跨域。本项目后端已启用 FastAPI CORS 中间件：

```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
```

当前为开发模式（`allow_origins=["*"]`）。生产建议收敛：

- 同域部署（推荐）：前端静态资源与后端反代放同一域名下（Nginx 把 `/api` 转发给 backend），**无跨域问题，可关掉或收紧 CORS**；
- 跨域部署：`allow_origins` 改为具体域名列表，如 `["https://crm.example.com"]`；
- **注意**：`allow_credentials=True` 与 `allow_origins=["*"]` 并存浏览器会拦截，若需携带 Cookie 必须显式列域名。

### 9.3 跨国访问风险分析与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| **网络延迟/丢包** | 国际链路 RTT 高（200-300ms+），页面与接口变慢 | 前端开启 gzip + 静态缓存；API 响应控制在几百 KB 内；图片/文件走 CDN |
| **跨国线路不稳定** | 偶发超时、连接重置 | Axios 超时与重试；后端 `pool_pre_ping=True` 已防死连接；必要时上云厂商海外加速（如阿里云全球加速 GA、DCDN） |
| **证书/CDN 兼容** | 部分国家或老设备对 TLS 版本敏感 | 启用 HTTPS + TLS1.2/1.3；CDN 边缘节点就近分发 |
| **时区差异** | 业务时间显示偏差 | 后端时间戳统一 UTC 存储，前端本地化展示（当前演示数据按 UTC 写入，注意时区展示） |
| **数据合规（重要）** | 境外用户访问、跨境数据传输可能涉及当地个保法/网络安全法 | 生产数据建议部署在境内服务器并备案；明确告知用户数据存储地；敏感数据加密存储 |
| **防火墙/审查** | 部分地区对境内未备案域名或境外节点访问受限 | 面向国内用户必须境内服务器 + 备案域名；若需海外用户，可考虑 CDN 双栈或香港节点做接入层 |

### 9.4 上线安全清单（结合本交付）

1. `JWT_SECRET` 改为随机长密钥（`python -c "import secrets; print(secrets.token_hex(32))"`）；
2. MySQL 强密码，3306 端口不对公网开放；
3. 修改全部演示账号默认密码；`backend/.env` 不入库、不提交；
4. Nginx 层配置请求体大小上限（上传限制）与超时；
5. 生产将 CORS 收紧为具体域名；
6. 定期备份 MySQL（`mysqldump` 或云 RDS 自动备份）；文件上传目录同步备份；
7. 监控告警：磁盘、内存、5xx 比例、慢查询。

---

## 附：演示账号（seed_demo.py）

| 角色 | 邮箱 | 密码 |
|------|------|------|
| Admin | demo.admin@crm.com | demo123456 |
| Sales | zhangwei@crm.com / lina@crm.com / wangfang@crm.com | demo123456 |
| PM | chenjie@crm.com | demo123456 |
| CS | liuyang@crm.com | demo123456 |

