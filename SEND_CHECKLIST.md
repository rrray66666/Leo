# CRM 系统交付检查清单（发送前必看）

> 本文件用于交付前逐项核对。打勾确认后即可发送给公司。

---

## 一、演示账号速查（一页纸）

**系统地址（本地部署）**
- 前端界面：http://localhost:5173
- 后端接口文档（Swagger）：http://127.0.0.1:8000/docs

**Docker 部署时**
- 前端界面：http://localhost（80 端口）
- 接口文档：http://localhost:8000/docs

| 角色 | 登录邮箱 | 密码 | 权限说明 |
|------|----------|------|----------|
| 管理员 | demo.admin@crm.com | demo123456 | 全部功能 + 用户管理 + 批量操作 |
| 销售 | zhangwei@crm.com | demo123456 | 管理自有客户（增删改/跟进/签约） |
| 销售 | lina@crm.com | demo123456 | 同上 |
| 销售 | wangfang@crm.com | demo123456 | 同上 |
| PM 项目经理 | chenjie@crm.com | demo123456 | 全局只读 + 查看指派任务 |
| CS 客服 | liuyang@crm.com | demo123456 | 自有客户只读 |

> 登录页也有注册入口，新注册用户默认"销售"角色，由管理员在"用户管理"里改角色。

**演示数据（seed 脚本自动生成）**
- 35 个客户分布在 8 个销售阶段、4 位销售名下
- 含合同、任务、沟通记录、回款、阶段历史、跟进提醒、通知
- 下拉框字典（地区/行业/来源/文档分类）已预置

---

## 二、发送前逐项检查

### 1. 打包内容确认
- [ ] `backend/`（含 `app/`、`requirements.txt`、`.env.example`、`alembic/`）
- [ ] `frontend/`（含 `src/`、`package.json`；`node_modules/` 可选带，不带则对方需联网 `npm install`）
- [ ] `docker-compose.yml`、`backend/Dockerfile`、`frontend/Dockerfile`（Docker 部署用）
- [ ] `db_init.sql`（建库脚本，本地部署用）
- [ ] `start-all.bat`（一键启动，本地部署用）
- [ ] `README.md`、`DELIVERY_REPORT.md`
- [ ] `backend/.env` —— 是否打包？
  - 直接发文件夹（zip）：**会带**，需确认里面是本机配置（对方可直接用）
  - 发 git 仓库：**不会带**（已被 .gitignore 忽略），对方按 README 用 `.env.example` 自己生成
- [ ] 根目录 `.env`（Docker 用）——已随包提供 demo 配置，`docker-compose up -d --build` 可直接运行；生产环境请重新生成

### 2. 配置检查（重要）
- [ ] `JWT_SECRET` 已替换为随机长字符串（生成命令：`python -c "import secrets; print(secrets.token_hex(32))"`）
- [ ] MySQL 密码已设置强密码，且 `DATABASE_URL` 与之一致
- [ ] Docker 方式：根目录 `.env` 的 `DB_PASSWORD` / `MINIO_USER` / `MINIO_PASSWORD` / `JWT_SECRET` 均已修改
- [ ] 本地方式：`backend/.env` 的 `DATABASE_URL` 指向正确的 MySQL 地址

### 3. 部署前注意（对方机器）
- [ ] MySQL 8 已安装并启动（本地部署必需；Docker 方式自动装）
- [ ] Docker 方式：对方装好 Docker Desktop
- [ ] 端口 8000 / 5173（本地）或 80 / 8000（Docker）未被占用
- [ ] 首次运行务必执行 seed：`python -m app.scripts.seed_demo`（幂等，可重复执行）

### 4. 安全提醒
- [ ] 正式上线前再次修改所有演示账号密码
- [ ] `backend/.env`、根目录 `.env` 不要提交到公开仓库
- [ ] 生产环境建议更换 CORS 为指定域名（当前 `allow_origins=["*"]`）

---

## 三、部署速览（详见 README）

**方式一 · Docker（推荐）**
```
cp .env.example .env   # 改密码和 JWT_SECRET
docker-compose up -d --build
docker-compose exec backend python -m app.scripts.seed_demo
# 浏览器打开 http://localhost 用上面账号登录
```

**方式二 · 本地 Windows**
```
mysql -uroot -p < db_init.sql          # 1. 建库（只需一次）
cd backend && copy .env.example .env   # 2. 配置
.venv\Scripts\python -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)"   # 3. 建表
.venv\Scripts\python -m app.scripts.seed_demo   # 4. 灌演示数据
双击 start-all.bat                     # 5. 一键启动
```

---

## 四、常见问题速查

| 现象 | 处理 |
|------|------|
| 后端报 MySQL 连接失败 | 确认 MySQL 已启动、`db_init.sql` 已执行、`backend/.env` 账号密码正确 |
| 登录页报 401 | 正常现象，是未登录提示；用演示账号登录即可 |
| 端口 8000/5173 被占用 | `taskkill /F /PID <进程号>` 清理后重试 |
| 上传的文件在哪 | 默认存 `backend/app/uploads/`（配置 MinIO 后存对象存储） |
| seed 跑过还要再跑 | 安全，幂等跳过，不会重复生成 |
