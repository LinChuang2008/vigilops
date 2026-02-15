# VigilOps — Progress

## Phase 1 — MVP

### Status: 🔧 In Progress

| Category | Status | Notes |
|----------|--------|-------|
| Infrastructure (F001-F005) | ✅ Done | FastAPI + DB + Redis + Config + Alembic |
| Auth (F006-F010) | ✅ Done | User model + JWT + Register/Login/Refresh/Me |
| Agent Backend (F011-F013) | ✅ Done | Token + Register + Heartbeat |
| Server Monitoring (F014-F018) | ✅ Done | Host model + Metrics + API |
| Service Monitoring (F019-F021) | ✅ Done | Service model + Checks + API |
| Alert (F022-F026) | ⬜ Not Started | Rules + Engine + Webhook |
| Agent Client (F027-F030) | ⬜ Not Started | CLI + Collector + Reporter |
| Frontend (F031-F037) | ⬜ Not Started | Layout + Pages |
| Settings (F038) | ⬜ Not Started | System settings |

**Total Features:** 38 | **Completed:** 21 | **Progress:** 55%

---

### Milestones

- [x] Project skeleton created (2026-02-15)
- [x] Backend boots with DB connection (2026-02-15)
- [x] Auth flow works (register → login → access API) (2026-02-15)
- [ ] Agent can report metrics → visible in UI
- [ ] Alerts fire and notify via Webhook
- [ ] MVP feature complete

---

### Session Log

#### 2026-02-15 Session 1
**Completed:** F001-F010 (Infrastructure + Auth)
- F001: /health endpoint with DB/Redis status checks
- F002: PostgreSQL async connection via SQLAlchemy + asyncpg
- F003: Redis async client with connection pool
- F004: Pydantic Settings with .env loading
- F005: Alembic async migration setup
- F006: User model (id, email, name, hashed_password, role, is_active, timestamps)
- F007: bcrypt password hashing + JWT access/refresh tokens
- F008: POST /api/v1/auth/register (first user=admin, email unique check)
- F009: POST /api/v1/auth/login
- F010: POST /api/v1/auth/refresh + GET /api/v1/auth/me + get_current_user dependency

**Issues encountered:**
- Port conflicts with TokenFlow project (changed to 8001/3001/5433/6380)
- passlib + bcrypt 5.x incompatibility → pinned bcrypt==4.0.1
- Frontend node_modules being sent to Docker (added .dockerignore)

**Next steps:** F011-F013 (Agent Token management, registration, heartbeat)

#### 2026-02-15 Session 2
**Completed:** F011-F021 (Agent Backend + Server Monitoring + Service Monitoring)
- F011: AgentToken model + create/list/revoke endpoints + verify_agent_token dependency
- F012: Agent register endpoint (idempotent, creates Host record)
- F013: Agent heartbeat endpoint (updates DB + Redis TTL)
- F014: Host + HostMetric models and schemas
- F015: Metrics upload endpoint POST /api/v1/agent/metrics (writes DB + Redis cache)
- F016: Host list with pagination, filtering, Redis-cached latest metrics
- F017: Host detail + historical metrics with time-range and aggregation (5min/1h/1d)
- F018: Background offline detector task (scans Redis heartbeats every 60s)
- F019: Service + ServiceCheck models and schemas
- F020: Service check report endpoint POST /api/v1/agent/services
- F021: Service list/detail/checks endpoints with uptime calculation

**Next steps:** F022-F026 (Alert system)
