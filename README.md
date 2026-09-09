# 企业级微服务应用系统

基于微服务架构的企业级应用系统，后端使用 FastAPI，前端使用 Vue3，数据库为 PostgreSQL，API 网关为 Kong。

## 🛠 技术栈

- **Frontend**: Vue3 + Element Plus + Vite
- **Backend**: FastAPI + SQLAlchemy + Pydantic
- **Service Layer**: Protocol 接口抽象 + 可替换实现
- **Database**: PostgreSQL 15 + Pgpool
- **API Gateway**: Kong 3.5（双实例直连对外暴露）
- **Service Discovery / Config**: Consul（服务注册 + KV 配置中心）
- **Monitoring**: Prometheus + Grafana + 健康检查 + Exporter
- **Logging**: Structlog JSON 结构化日志
- **Communication**: HTTP/REST + gRPC（支持 TLS/mTLS）
- **CI/CD**: GitHub Actions（CI + 镜像发布 + 远端部署）

## 🏗 架构与高可用

### 网关层

- `kong-1`：对外 `8000/8001`
- `kong-2`：对外 `8002/8003`
- 不再使用 Nginx 作为 Kong 前置入口，网关能力由 Kong 原生提供。

### 数据库层

- `postgres-primary` + `postgres-replica` 主从
- `postgres-pool-1`（`5432`）+ `postgres-pool-2`（`5433`）双 Pgpool 入口
- 应用内通过 `postgres` 别名访问双 Pgpool，降低单点风险。

### 服务治理

- Consul 负责服务注册与健康检查（`scripts/consul/config/services.json`）
- Consul KV 负责用户服务动态配置（`scripts/consul/bootstrap.sh`）
- 用户服务启动时会读取 Consul 配置覆盖环境变量。

### 监控

- Prometheus 抓取：
  - User Service `/metrics`
  - Kong Admin `/metrics`
  - Consul metrics
  - PostgreSQL exporter
- Grafana 预置 Prometheus 数据源。

## 🔗 服务间调用示例：资料服务（profile-service）

`profile-service` 是一个刻意保持轻量的示例服务（FastAPI + 内存存储，无数据库），
用于演示微服务间调用与**调用失败降级**：

- **user-service**：用户基本信息（用户名、邮箱、昵称、手机号、简介、角色）
- **profile-service**：扩展资料（头像、部门、岗位），启动时按用户名预置演示数据
- 前端「资料详情」页（`/profile-detail`）通过 Kong 并行请求两个服务，合并展示

### 调用链

1. 前端带 JWT 请求 `GET /api/v1/profiles/me`（经 Kong 路由到 profile-service）。
2. profile-service 用与 user-service 共享的 `JWT_SECRET_KEY` 本地验签，拿到用户身份。
3. profile-service 通过 httpx **携带原 JWT** 调用 user-service
   `GET /api/v1/auth/me`（容器内地址 `http://user-service:8000`，2s 超时）。
4. 合并 user-service 的基本信息与本地的头像/部门/岗位后返回
   （`data.user` + `data.profile` + `data.degraded`）。

### 降级行为（不让页面空白）

- user-service 不可用 / 超时：profile-service 仍返回 **200**，`degraded=true`，
  用令牌中的身份给出基本字段，头像/部门/岗位照常展示，并在 `warnings` 中说明。
- profile-service 自身不可用：前端独立调用 user-service 仍能展示基本信息，
  资料区域显示"不可用"提示。
- 两个服务都不可用：页面显示错误结果页与"重新加载"按钮，而不是白屏。

### 手动演示降级

页面底部「降级演示」面板可一键注入故障，也可直接调接口：

```bash
# 模拟 profile-service 调用 user-service 失败
curl -X PUT "http://localhost:8012/api/v1/profiles/demo/faults/upstream?failed=true"
# 模拟 profile-service 自身故障（业务接口返回 503）
curl -X PUT "http://localhost:8012/api/v1/profiles/demo/faults/self?failed=true"
# 清除故障
curl -X DELETE "http://localhost:8012/api/v1/profiles/demo/faults"
```

资料服务测试：

```bash
cd services/profile-service
pip install -r requirements.txt
pytest tests/ -v
```

## 🚀 启动

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

## 🔗 服务地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Frontend | http://localhost:3000 | 前端入口 |
| Kong Gateway #1 | http://localhost:8000 | 网关入口 1 |
| Kong Admin #1 | http://localhost:8001 | 管理口 1 |
| Kong Gateway #2 | http://localhost:8002 | 网关入口 2 |
| Kong Admin #2 | http://localhost:8003 | 管理口 2 |
| User Service #1 (HTTP) | http://localhost:8010/docs | Swagger |
| User Service #2 (HTTP) | http://localhost:8011/docs | 副本 |
| User Service #1 (gRPC TLS) | localhost:50051 | gRPC |
| User Service #2 (gRPC TLS) | localhost:50052 | gRPC 副本 |
| Profile Service (HTTP) | http://localhost:8012/docs | 资料服务（服务间调用示例） |
| PostgreSQL Pgpool #1 | localhost:5432 | DB 入口 1 |
| PostgreSQL Pgpool #2 | localhost:5433 | DB 入口 2 |
| Consul UI | http://localhost:8500 | 服务发现/配置 |
| Prometheus | http://localhost:9090 | 指标采集 |
| Grafana | http://localhost:3001 | 可视化 |

## 🔐 安全与一致性

- gRPC 服务端默认支持 TLS，支持可选 mTLS。
- 用户服务数据库使用独立 schema：`user_service`。
- HTTP 异常（含 `HTTPException` 与 422 校验错误）统一输出：
  - `success`
  - `message`
  - `error_code`
  - `details`
  - `timestamp`

## 📁 关键目录

```text
.
├── docker-compose.yml
├── .github/workflows/ci-cd.yml
├── kong/kong.yml
├── scripts/
│   ├── init-db.sql
│   ├── consul/
│   │   ├── bootstrap.sh
│   │   └── config/services.json
│   ├── monitoring/
│   │   ├── prometheus.yml
│   │   └── grafana/provisioning/
│   └── postgres/
├── services/user-service/
│   ├── app/
│   └── certs/                 # 开发用 TLS/mTLS 证书（示例）
├── services/profile-service/  # 资料服务（服务间调用 + 降级示例，内存存储）
│   └── app/
└── frontend/
```

## 🧪 测试

```bash
cd services/user-service
pip install -r requirements.txt
pytest tests/ -v --cov=app --cov-report=term-missing
```

## ⚙️ CI/CD

`/.github/workflows/ci-cd.yml` 当前流水线包含：

1. 代码质量检查
2. 后端/前端测试
3. Docker 构建
4. Compose 集成测试（含 HA 验证）
5. 主分支发布镜像到 GHCR
6. 通过 SSH 远程执行 Docker Compose 部署

部署阶段需配置以下 GitHub Secrets：

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_PATH`
- `DEPLOY_REGISTRY_USERNAME`
- `DEPLOY_REGISTRY_TOKEN`

## ❓ 常见问题

**Q: Kong 路由不生效？**  
A: 检查 `http://localhost:8001/status` 与 `http://localhost:8003/status`。

**Q: 数据库连接异常？**  
A: 检查 `docker compose logs postgres-pool-1 postgres-pool-2`。

**Q: gRPC TLS 启动失败？**  
A: 检查证书是否存在于 `services/user-service/certs`，并确认 `.env` 中 TLS 开关配置。
