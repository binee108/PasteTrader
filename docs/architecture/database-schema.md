# PasteTrader Database Schema Architecture

> **Version**: 0.1.0
> **Database**: PostgreSQL 16
> **ORM**: SQLAlchemy 2.0 (async)
> **Last Updated**: 2025-01-11

## Overview

PasteTrader Workflow Engine을 위한 데이터베이스 스키마 설계 문서입니다.

---

## Entity Relationship Diagram

```
                                    +------------------+
                                    |      users       |
                                    +------------------+
                                    | id (PK, UUID)    |
                                    | email            |
                                    | hashed_password  |
                                    | is_active        |
                                    | created_at       |
                                    | updated_at       |
                                    | deleted_at       |
                                    +------------------+
                                             |
              +------------------------------+------------------------------+
              |                              |                              |
              v                              v                              v
     +------------------+         +------------------+         +------------------+
     |     workflows    |         |      tools       |         |      agents      |
     +------------------+         +------------------+         +------------------+
     | id (PK, UUID)    |         | id (PK, UUID)    |         | id (PK, UUID)    |
     | owner_id (FK)    |         | owner_id (FK)    |         | owner_id (FK)    |
     | name             |         | name             |         | name             |
     | description      |         | tool_type        |         | model_provider   |
     | config (JSONB)   |         | config (JSONB)   |         | model_name       |
     | is_active        |         | schema (JSONB)   |         | config (JSONB)   |
     | version          |         | is_active        |         | system_prompt    |
     | created_at       |         | created_at       |         | is_active        |
     | updated_at       |         | updated_at       |         | created_at       |
     | deleted_at       |         | deleted_at       |         | updated_at       |
     +------------------+         +------------------+         | deleted_at       |
              |                                                +------------------+
              |
    +---------+---------+
    |                   |
    v                   v
+------------------+  +------------------+
|      nodes       |  |      edges       |
+------------------+  +------------------+
| id (PK, UUID)    |  | id (PK, UUID)    |
| workflow_id (FK) |  | workflow_id (FK) |
| name             |  | source_node (FK) |
| node_type        |  | target_node (FK) |
| position (JSONB) |  | condition (JSONB)|
| config (JSONB)   |  | priority         |
| tool_id (FK)?    |  | created_at       |
| agent_id (FK)?   |  +------------------+
| created_at       |
| updated_at       |
+------------------+

+-------------------------+         +------------------+
| workflow_executions     |<------->| node_executions  |
+-------------------------+         +------------------+
| id (PK, UUID)           |         | id (PK, UUID)    |
| workflow_id (FK)        |         | execution_id(FK) |
| triggered_by            |         | node_id (FK)     |
| status                  |         | status           |
| input (JSONB)           |         | input (JSONB)    |
| output (JSONB)          |         | output (JSONB)   |
| error (JSONB)           |         | error (JSONB)    |
| started_at              |         | started_at       |
| completed_at            |         | completed_at     |
| created_at              |         | retry_count      |
+-------------------------+         | created_at       |
                                    +------------------+
                                             |
                                             v
                                    +------------------+
                                    | execution_logs   |
                                    +------------------+
                                    | id (PK, UUID)    |
                                    | node_exec_id(FK) |
                                    | level            |
                                    | message          |
                                    | metadata (JSONB) |
                                    | timestamp        |
                                    +------------------+

+------------------+
|    schedules     |
+------------------+
| id (PK, UUID)    |
| workflow_id (FK) |
| schedule_type    |
| cron_expression  |
| interval_seconds |
| config (JSONB)   |
| is_active        |
| next_run_at      |
| last_run_at      |
| created_at       |
| updated_at       |
+------------------+
```

---

## Table Definitions

### users

사용자 계정 정보

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| email | VARCHAR(255) | NOT NULL, UNIQUE | 이메일 주소 |
| hashed_password | VARCHAR(255) | NOT NULL | Bcrypt 해시 비밀번호 |
| display_name | VARCHAR(100) | NULL | 표시 이름 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 계정 활성 상태 |
| is_superuser | BOOLEAN | NOT NULL, DEFAULT FALSE | 관리자 권한 |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | 추가 메타데이터 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 생성 시각 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 수정 시각 |
| deleted_at | TIMESTAMPTZ | NULL | 삭제 시각 (Soft Delete) |

### workflows

DAG 기반 워크플로우 정의

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| owner_id | UUID | FK → users(id), NOT NULL | 소유자 |
| name | VARCHAR(255) | NOT NULL | 워크플로우 이름 |
| description | TEXT | NULL | 설명 |
| config | JSONB | NOT NULL, DEFAULT '{}' | 전역 설정 |
| variables | JSONB | NOT NULL, DEFAULT '{}' | 워크플로우 변수 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 실행 가능 여부 |
| version | INTEGER | NOT NULL, DEFAULT 1 | 낙관적 잠금용 버전 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 생성 시각 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 수정 시각 |
| deleted_at | TIMESTAMPTZ | NULL | 삭제 시각 |

### nodes

워크플로우 노드 (Tool, Agent, Condition, Adapter, Trigger, Aggregator)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| workflow_id | UUID | FK → workflows(id) ON DELETE CASCADE | 부모 워크플로우 |
| name | VARCHAR(255) | NOT NULL | 노드 이름 |
| node_type | VARCHAR(50) | NOT NULL, CHECK IN (...) | 노드 타입 |
| position_x | FLOAT | NOT NULL, DEFAULT 0 | UI X 좌표 |
| position_y | FLOAT | NOT NULL, DEFAULT 0 | UI Y 좌표 |
| config | JSONB | NOT NULL, DEFAULT '{}' | 노드별 설정 |
| input_schema | JSONB | NULL | 입력 JSON Schema |
| output_schema | JSONB | NULL | 출력 JSON Schema |
| tool_id | UUID | FK → tools(id), NULL | 연결된 도구 |
| agent_id | UUID | FK → agents(id), NULL | 연결된 에이전트 |
| timeout_seconds | INTEGER | NOT NULL, DEFAULT 300 | 실행 타임아웃 |
| retry_config | JSONB | NOT NULL, DEFAULT {...} | 재시도 설정 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 생성 시각 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 수정 시각 |

**Node Types**:
- `tool` - 외부 도구 실행
- `agent` - LLM 에이전트 호출
- `condition` - 조건부 분기
- `adapter` - 데이터 변환
- `trigger` - 트리거/이벤트
- `aggregator` - 결과 집계

### edges

노드 간 연결

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| workflow_id | UUID | FK → workflows(id) ON DELETE CASCADE | 부모 워크플로우 |
| source_node_id | UUID | FK → nodes(id) ON DELETE CASCADE | 출발 노드 |
| target_node_id | UUID | FK → nodes(id) ON DELETE CASCADE | 도착 노드 |
| source_handle | VARCHAR(50) | NULL | 출발 연결점 |
| target_handle | VARCHAR(50) | NULL | 도착 연결점 |
| condition | JSONB | NULL | 조건식 |
| priority | INTEGER | NOT NULL, DEFAULT 0 | 실행 우선순위 |
| label | VARCHAR(100) | NULL | UI 라벨 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 생성 시각 |

### tools

외부 도구 레지스트리

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| owner_id | UUID | FK → users(id), NOT NULL | 소유자 |
| name | VARCHAR(255) | NOT NULL | 도구 이름 |
| description | TEXT | NULL | 설명 |
| tool_type | VARCHAR(50) | NOT NULL, CHECK IN (...) | 도구 타입 |
| config | JSONB | NOT NULL, DEFAULT '{}' | 도구 설정 |
| input_schema | JSONB | NOT NULL, DEFAULT '{}' | 입력 스키마 |
| output_schema | JSONB | NULL | 출력 스키마 |
| auth_config | JSONB | NULL | 인증 설정 (암호화) |
| rate_limit | JSONB | NULL | 요청 제한 설정 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 활성 상태 |
| is_public | BOOLEAN | NOT NULL, DEFAULT FALSE | 공유 여부 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 생성 시각 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 수정 시각 |
| deleted_at | TIMESTAMPTZ | NULL | 삭제 시각 |

**Tool Types**:
- `http` - HTTP API 호출
- `mcp` - MCP 서버 도구
- `python` - Python 함수 실행
- `shell` - Shell 명령 실행
- `builtin` - 내장 도구

### agents

LLM 에이전트 설정

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| owner_id | UUID | FK → users(id), NOT NULL | 소유자 |
| name | VARCHAR(255) | NOT NULL | 에이전트 이름 |
| description | TEXT | NULL | 설명 |
| model_provider | VARCHAR(50) | NOT NULL, CHECK IN (...) | LLM 제공자 |
| model_name | VARCHAR(100) | NOT NULL | 모델 식별자 |
| system_prompt | TEXT | NULL | 시스템 프롬프트 |
| config | JSONB | NOT NULL, DEFAULT '{}' | 모델 파라미터 |
| tools | JSONB | NOT NULL, DEFAULT '[]' | 사용 가능한 도구 ID 목록 |
| memory_config | JSONB | NULL | 메모리/컨텍스트 설정 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 활성 상태 |
| is_public | BOOLEAN | NOT NULL, DEFAULT FALSE | 공유 여부 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 생성 시각 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 수정 시각 |
| deleted_at | TIMESTAMPTZ | NULL | 삭제 시각 |

**Model Providers**:
- `anthropic` - Claude models
- `openai` - GPT models
- `zhipuai` - GLM models

### workflow_executions

워크플로우 실행 이력

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| workflow_id | UUID | FK → workflows(id), NOT NULL | 실행된 워크플로우 |
| workflow_version | INTEGER | NOT NULL | 실행 시점 버전 |
| triggered_by | VARCHAR(50) | NOT NULL, CHECK IN (...) | 트리거 소스 |
| trigger_metadata | JSONB | NULL | 트리거 컨텍스트 |
| status | VARCHAR(50) | NOT NULL, DEFAULT 'pending' | 실행 상태 |
| input | JSONB | NULL | 입력 데이터 |
| output | JSONB | NULL | 최종 출력 |
| error | JSONB | NULL | 에러 상세 |
| context | JSONB | NOT NULL, DEFAULT '{}' | 런타임 컨텍스트 |
| started_at | TIMESTAMPTZ | NULL | 시작 시각 |
| completed_at | TIMESTAMPTZ | NULL | 완료 시각 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 생성 시각 |

**Trigger Types**:
- `manual` - 수동 실행
- `schedule` - 예약 실행
- `webhook` - 웹훅 트리거
- `api` - API 호출

**Execution Status**:
- `pending` - 대기 중
- `running` - 실행 중
- `completed` - 완료
- `failed` - 실패
- `cancelled` - 취소됨
- `timeout` - 타임아웃

### node_executions

개별 노드 실행 상태

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| execution_id | UUID | FK → workflow_executions(id) ON DELETE CASCADE | 부모 실행 |
| node_id | UUID | FK → nodes(id), NOT NULL | 실행된 노드 |
| status | VARCHAR(50) | NOT NULL, DEFAULT 'pending' | 노드 실행 상태 |
| input | JSONB | NULL | 노드 입력 |
| output | JSONB | NULL | 노드 출력 |
| error | JSONB | NULL | 에러 상세 |
| retry_count | INTEGER | NOT NULL, DEFAULT 0 | 재시도 횟수 |
| started_at | TIMESTAMPTZ | NULL | 시작 시각 |
| completed_at | TIMESTAMPTZ | NULL | 완료 시각 |
| duration_ms | INTEGER | NULL | 실행 시간 (ms) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 생성 시각 |

### execution_logs

상세 실행 로그

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| node_execution_id | UUID | FK → node_executions(id) ON DELETE CASCADE | 부모 노드 실행 |
| level | VARCHAR(20) | NOT NULL, DEFAULT 'info' | 로그 레벨 |
| message | TEXT | NOT NULL | 로그 메시지 |
| metadata | JSONB | NULL | 추가 컨텍스트 |
| timestamp | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 로그 시각 |

**Log Levels**:
- `debug`, `info`, `warning`, `error`

### schedules

APScheduler 작업 설정

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 고유 식별자 |
| workflow_id | UUID | FK → workflows(id) ON DELETE CASCADE | 대상 워크플로우 |
| name | VARCHAR(255) | NULL | 스케줄 이름 |
| schedule_type | VARCHAR(20) | NOT NULL, CHECK IN (...) | 스케줄 타입 |
| cron_expression | VARCHAR(100) | NULL | Cron 표현식 |
| interval_seconds | INTEGER | NULL | 간격 (초) |
| run_date | TIMESTAMPTZ | NULL | 특정 실행 일시 |
| timezone | VARCHAR(50) | NOT NULL, DEFAULT 'UTC' | 타임존 |
| config | JSONB | NOT NULL, DEFAULT '{}' | 추가 설정 |
| input | JSONB | NULL | 기본 입력값 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 활성 상태 |
| next_run_at | TIMESTAMPTZ | NULL | 다음 실행 시각 |
| last_run_at | TIMESTAMPTZ | NULL | 마지막 실행 시각 |
| last_run_status | VARCHAR(50) | NULL | 마지막 실행 상태 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 생성 시각 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 수정 시각 |

**Schedule Types**:
- `cron` - Cron 표현식 기반
- `interval` - 고정 간격
- `date` - 특정 일시 1회

---

## Index Strategy

### Primary Lookup Indexes

```sql
-- Users
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;

-- Workflows
CREATE INDEX idx_workflows_owner ON workflows(owner_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_workflows_owner_active ON workflows(owner_id, is_active) WHERE deleted_at IS NULL;

-- Nodes
CREATE INDEX idx_nodes_workflow ON nodes(workflow_id);
CREATE INDEX idx_nodes_type ON nodes(workflow_id, node_type);

-- Edges
CREATE INDEX idx_edges_workflow ON edges(workflow_id);
CREATE INDEX idx_edges_source ON edges(source_node_id);
CREATE INDEX idx_edges_target ON edges(target_node_id);
CREATE UNIQUE INDEX idx_edges_unique_connection ON edges(source_node_id, target_node_id, source_handle, target_handle);
```

### Execution Tracking Indexes

```sql
-- Workflow Executions
CREATE INDEX idx_executions_workflow ON workflow_executions(workflow_id);
CREATE INDEX idx_executions_status ON workflow_executions(status);
CREATE INDEX idx_executions_created ON workflow_executions(created_at DESC);
CREATE INDEX idx_executions_running ON workflow_executions(workflow_id) WHERE status = 'running';

-- Node Executions
CREATE INDEX idx_node_exec_execution ON node_executions(execution_id);
CREATE INDEX idx_node_exec_node ON node_executions(node_id);

-- Execution Logs
CREATE INDEX idx_exec_logs_node_exec ON execution_logs(node_execution_id);
CREATE INDEX idx_exec_logs_timestamp ON execution_logs(timestamp DESC);

-- Schedules
CREATE INDEX idx_schedules_workflow ON schedules(workflow_id);
CREATE INDEX idx_schedules_next_run ON schedules(next_run_at) WHERE is_active = TRUE;
```

### JSONB Indexes

```sql
-- GIN indexes for flexible JSONB queries
CREATE INDEX idx_workflows_config ON workflows USING GIN (config jsonb_path_ops);
CREATE INDEX idx_nodes_config ON nodes USING GIN (config jsonb_path_ops);
CREATE INDEX idx_tools_config ON tools USING GIN (config jsonb_path_ops);
CREATE INDEX idx_agents_config ON agents USING GIN (config jsonb_path_ops);
```

---

## Design Decisions

### 1. JSONB Usage Strategy

**config 컬럼**: 스키마 변경 없이 진화할 수 있는 유연한 설정 저장. GIN 인덱스로 효율적 쿼리 지원.

**input_schema/output_schema**: JSON Schema 정의로 유효성 검증.

**metadata/context**: 실행별로 다른 런타임 데이터 저장.

### 2. Soft Delete

`deleted_at` 타임스탬프와 부분 인덱스(`WHERE deleted_at IS NULL`)로 구현. 감사 추적 보존하면서 쿼리 성능 유지.

### 3. Optimistic Locking

`workflows.version` 컬럼으로 동시 편집 시 충돌 감지.

### 4. Cascade Strategy

- 자식 엔티티(nodes, edges, schedules, node_executions, logs): `ON DELETE CASCADE`
- 실행 이력: 워크플로우 삭제 시에도 보존

### 5. Performance Considerations

- 부분 인덱스로 Soft Delete된 레코드 제외
- 복합 인덱스로 공통 쿼리 패턴 최적화
- `execution_logs`는 대규모 시 시간 기반 파티셔닝 고려

---

## Migration Notes

### Initial Migration

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create update trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to tables with updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- (repeat for other tables)
```

### Alembic Configuration

```python
# alembic/env.py
from sqlalchemy.ext.asyncio import create_async_engine

target_metadata = Base.metadata

def run_migrations_online():
    connectable = create_async_engine(settings.database_url)
    # async migration support
```

---

*Generated by MoAI-ADK • PasteTrader Database Architecture*
