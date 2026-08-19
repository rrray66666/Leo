# CRM 系统国内云服务器部署指南

> 适用场景：将系统部署到国内云服务器（阿里云 / 腾讯云 / 华为云），对外交付网页链接（`https://你的域名`）。
> 前置条件：已申请域名（如 `crm.company.com`）；服务器费用可报销（公司已确认）。

---

## 1. 云端架构总览

```
用户浏览器
   │  https://crm.company.com
   ▼
[域名 + ICP 备案]  →  云服务器 ECS（公网 IP）
                       │ 安全组放行 80/443/22
                       ▼
                 Docker Compose（本项目自带编排）
                 ├── mysql   :3306（仅内网，不对公网）
                 ├── redis   :6379（仅内网）
                 ├── minio   :9000/9001（文件存储，可选）
                 ├── backend :8000（仅内网，由 Nginx 反代）
                 └── frontend(Nginx) :80/443  ← 对外入口
```

前端容器内置 Nginx 负责：静态页面托管 + `/api` 反向代理到 backend + HTTPS 证书。

---

## 2. 服务器选型与购买

| 项目 | 建议 | 说明 |
|------|------|------|
| 云厂商 | 阿里云 / 腾讯云 任选 | 国内节点必须选**大陆地域**（如杭州、上海、广州）才能绑定备案域名 |
| 配置 | 2 核 4G 起步 | 100 人以内足够；如需更高并发升 4C8G |
| 系统 | Ubuntu 22.04 LTS（64 位） | 示例命令基于 Ubuntu；CentOS 命令略有差异 |
| 带宽 | 5 Mbps 起步 | 页面/接口以 JSON 为主，5M 够用；文件上传多可升 10M |
| 云盘 | 系统盘 40G SSD + 数据盘 50G | 数据库数据、上传文件建议放数据盘（便于备份/快照） |
| 计费 | 包年包月 或 按量付费 | 验收阶段可按量付费，稳定后转包年 |

**费用参考（国内 2C4G，2026 年行情）**：约 ¥80–150/月（ECS）+ ¥30–60/年（域名）+ 免费 SSL 证书。云数据库 RDS 可选（更省心，贵约 ¥100/月），初版用 ECS 自装 MySQL 即可。

---

## 3. 安全组 / 防火墙配置

购买服务器后在云控制台配置**安全组**：

| 端口 | 协议 | 来源 | 用途 |
|------|------|------|------|
| 22 | TCP | 仅你的办公 IP（或 0.0.0.0/0 后尽快改为白名单） | SSH 登录 |
| 80 | TCP | 0.0.0.0/0 | HTTP（备案通过后跳转 HTTPS） |
| 443 | TCP | 0.0.0.0/0 | HTTPS 对外访问 |
| 3306/6379/8000/9000 | TCP | **不开放** | 仅内网容器间通信 |

> 安全组放行后，还需在系统防火墙放行（Ubuntu 默认 ufw 未开启时可跳过；若开启执行 `sudo ufw allow 22,80,443/tcp`）。

---

## 4. 服务器初始化（安装 Docker）

SSH 登录服务器：

```bash
ssh root@<服务器公网IP>
```

安装 Docker + Compose 插件（Ubuntu 22.04）：

```bash
# 安装依赖
sudo apt-get update && sudo apt-get install -y ca-certificates curl

# 安装 Docker
curl -fsSL https://get.docker.com | sudo sh

# 让当前用户免 sudo 使用 docker
sudo usermod -aG docker $USER
newgrp docker

# 验证
docker --version
docker compose version
```

> 服务器需能访问外网拉取镜像（首次 `docker compose up` 会联网拉取 mysql/redis/minio/node/python 镜像）。

---

## 5. 部署项目

### 5.1 拉取代码（GitHub）

```bash
mkdir -p /opt/crm && cd /opt/crm
git clone https://github.com/<你的组织>/<仓库名>.git crm-system
cd crm-system
```

### 5.2 配置生产环境变量

复制模板并填入**强随机密钥**：

```bash
cp .env.example .env
vi .env
```

`.env` 必须包含（示例）：

```bash
# MySQL 密码：生成强密码
DB_PASSWORD=<用 openssl rand -hex 12 生成>
# MinIO 账号
MINIO_USER=minioadmin
MINIO_PASSWORD=<用 openssl rand -hex 12 生成>
# JWT 签名密钥
JWT_SECRET=<用 openssl rand -hex 32 生成>
```

同时配置后端环境（覆盖容器默认）：

```bash
cp backend/.env.example backend/.env
```

### 5.3 首次启动（自动建表 + 灌入测试账号）

```bash
docker compose up -d --build
# 首次启动会自动执行 seed_demo（详见 backend Dockerfile / 启动脚本）
# 若未自动 seed，手动执行：
docker compose exec backend python -m app.scripts.seed_demo
```

查看状态：

```bash
docker compose ps            # 全部 healthy/running
docker compose logs -f backend   # 后端日志
```

### 5.4 验证内网可访问

```bash
curl -s http://localhost/api/v1/health   # 期望 {"status":"ok"}
curl -s http://localhost/                 # 期望返回前端 index.html
```

---

## 6. 域名解析与 HTTPS

### 6.1 域名解析

在域名服务商控制台添加记录：

| 记录类型 | 主机记录 | 记录值 | 说明 |
|----------|----------|--------|------|
| A | `crm`（或 `@`） | 服务器公网 IP | 使 `crm.company.com` 指向服务器 |

### 6.2 ICP 备案（必须，大陆服务器）

- 在**服务器所在云厂商**控制台提交 ICP 备案（个人/企业均可），一般 1–2 周。
- 备案期间 80/443 无法对外提供域名访问；可先用 IP + 端口或临时关闭对外验证。
- 备案号审核通过后，域名才能正常访问。

### 6.3 配置 HTTPS（免费证书）

推荐使用云厂商免费 SSL 证书（在控制台申请 DV 证书，绑定域名），或服务器上用 Let's Encrypt。

**方式 A：云负载均衡/网关托管证书（最简单）**
在云厂商购买/申请免费证书后，可通过云负载均衡 SLB 或 CDN 绑定证书，回源到 ECS 80 端口，无需改动容器。

**方式 B：服务器内自签 Let's Encrypt（自托管）**

```bash
# 安装 certbot
sudo apt-get install -y certbot

# 申请证书（需域名已解析到本机、80 端口可访问）
sudo certbot certonly --standalone -d crm.company.com
# 证书输出到 /etc/letsencrypt/live/crm.company.com/
```

将证书挂载进前端 Nginx 容器并开启 443（`frontend/nginx.conf` 已预留 HTTPS 配置模板，按注释启用即可）：

```yaml
# docker-compose.yml 的 frontend 服务增加：
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
    ports:
      - "80:80"
      - "443:443"
```

重新加载：

```bash
docker compose up -d frontend
```

---

## 7. 上线后检查清单（务必逐项）

1. `https://crm.company.com` 可打开登录页。
2. `https://crm.company.com/api/v1/health` 返回 `{"status":"ok"}`。
3. 用 `demo.admin@crm.com / demo123456` 登录 → 看板/客户列表正常。
4. 用销售账号登录 → 只能看到自己的客户（权限隔离生效）。
5. **更换默认密码**：所有测试账号密码改为随机（可在用户管理中重置，或重新 seed 前修改 seed_demo.py）。
6. `backend/.env` 的 `JWT_SECRET` 已改为强随机值。
7. 数据库端口 3306 未对公网开放（安全组已关闭）。
8. 配置 MySQL 每日自动备份（见下节）。

---

## 8. 备份与监控

### 8.1 数据库自动备份（crontab）

```bash
crontab -e
# 每天凌晨 3 点备份
0 3 * * * docker exec crm-mysql sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" crm' > /opt/crm/backup/crm_$(date +\%F).sql 2>/dev/null && find /opt/crm/backup -name "*.sql" -mtime +14 -delete
```

### 8.2 上传文件备份

`backend` 容器内 `app/uploads/` 目录保存上传文件，挂载持久化：

```yaml
# docker-compose.yml backend 服务增加：
    volumes:
      - ./uploads:/app/app/uploads
```

### 8.3 监控

- 云厂商自带基础监控（CPU/内存/磁盘）。
- 定期 `docker compose ps` 检查容器健康。
- 告警项：5xx 比例、磁盘使用率、容器重启次数。

---

## 9. 常见问题

| 现象 | 原因与处理 |
|------|-----------|
| 域名访问提示未备案 | ICP 备案未完成或被拦截，等待备案通过 |
| 页面能开但接口 502 | backend 未启动或 Nginx 无法连 `backend:8000`；`docker compose logs -f backend` 排查 |
| MySQL 连接失败 | 首次启动需等 mysql healthy；查看 `docker compose logs mysql` |
| 上传文件容器重启丢失 | 未挂载 `./uploads` 卷（见 8.2） |
| 时区显示偏差 | 数据库/容器默认 UTC；可在 docker-compose 中为各服务加 `TZ=Asia/Shanghai` 环境变量 |

---

## 10. 从本仓库交付到云端的完整流程（速查）

```
1. git clone 到服务器
2. 配置 .env（强密码 + JWT_SECRET）
3. docker compose up -d --build
4. 申请域名 + A 记录解析到服务器公网 IP
5. 云厂商提交 ICP 备案（1-2 周）
6. 申请免费 SSL 证书，启用 HTTPS
7. 逐项过第 7 节检查清单
8. 交付链接：https://crm.company.com
```
