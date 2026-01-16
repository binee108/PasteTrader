# Schedule API Reference

## Overview

Schedule API는 워크플로우 자동화를 위한 스케줄 관리 기능을 제공합니다. APScheduler 기반의 지속성 있는 스케줄링 시스템으로, Cron 표현식과 간격 기반 스케줄링을 모두 지원합니다.

**기본 URL:** `/api/v1/schedules`

**인증:** JWT Bearer Token (모든 엔드포인트에 필요)

**태그:** [SPEC-013] [API] [SCHEDULE]

---

## 스케줄 기능

PasteTrader의 스케줄 시스템은 다음을 지원합니다:

- **Cron 표현식**: 유닉스 스타일 Cron 표현식으로 복잡한 스케줄링
- **간격 기반**: 초/분/시간/일/주 단위의 고정 간격 실행
- **지속성**: PostgreSQL Job Store로 서비스 재시작 후에도 스케줄 유지
- **일시정지/재개**: 스케줄 실행을 일시중지하고 나중에 재개
- **실행 이력**: 각 실행의 상태, 지속시간, 오류 메시지 추적

---

## 지원하는 트리거 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| `cron` | Cron 표현식 기반 | `0 9 * * 1-5` (주중 9시) |
| `interval` | 고정 간격 기반 | 300초마다 (5분) |

---

## 엔드포인트

### 1. 스케줄 목록 조회

필터링과 페이지네이션을 지원하는 스케줄 목록을 조회합니다.

```
GET /api/v1/schedules
```

**쿼리 파라미터:**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|-----------|------|------|---------|-------------|
| `skip` | integer | 아니오 | 0 | 건너뛸 레코드 수 |
| `limit` | integer | 아니오 | 20 | 페이지 크기 (최대 100) |
| `workflow_id` | UUID | 아니오 | - | 워크플로우로 필터링 |
| `is_active` | boolean | 아니오 | - | 활성 상태로 필터링 |
| `trigger_type` | string | 아니오 | - | 트리거 유형으로 필터링 |

**응답 (200 OK):**

```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440003",
      "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "일일 시장 분석",
      "description": "매일 장 마감 후 시장 분석 실행",
      "schedule_type": "cron",
      "schedule_config": {
        "cron_expression": "0 16 * * 1-5"
      },
      "timezone": "Asia/Seoul",
      "is_active": true,
      "next_run_at": "2026-01-17T07:00:00Z",
      "last_run_at": "2026-01-16T07:00:00Z",
      "run_count": 45,
      "created_at": "2026-01-01T09:00:00+09:00",
      "updated_at": "2026-01-16T09:00:00+09:00"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

---

### 2. 스케줄 생성

새로운 스케줄을 생성합니다.

```
POST /api/v1/schedules
```

**요청 본문 (Cron 트리거):**

```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "일일 시장 분석",
  "description": "매일 장 마감 후 시장 분석 실행",
  "trigger_type": "cron",
  "cron_expression": "0 16 * * 1-5",
  "timezone": "Asia/Seoul"
}
```

**요청 본문 (Interval 트리거):**

```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "5분간격 데이터 수집",
  "description": "5분마다 최신 데이터 수집",
  "trigger_type": "interval",
  "interval_minutes": 5,
  "timezone": "UTC"
}
```

**필드 설명:**

| 필드 | 타입 | 필수 | 설명 |
|-------|------|------|-------------|
| `workflow_id` | UUID | 예 | 대상 워크플로우 UUID |
| `name` | string | 예 | 스케줄 이름 (최대 255자) |
| `description` | string | 아니오 | 스케줄 설명 (최대 2000자) |
| `trigger_type` | string | 예 | `cron` 또는 `interval` |
| `cron_expression` | string | cron 시 | Cron 표현식 (5 또는 6 필드) |
| `interval_weeks` | integer | interval 시 | 주 간격 |
| `interval_days` | integer | interval 시 | 일 간격 |
| `interval_hours` | integer | interval 시 | 시간 간격 |
| `interval_minutes` | integer | interval 시 | 분 간격 |
| `interval_seconds` | integer | interval 시 | 초 간격 |
| `timezone` | string | 아니오 | 시간대 (기본값: UTC) |

**Cron 표현식 형식:**

```
분(0-59) 시(0-23) 일(1-31) 월(1-12) 요일(0-7) [년(4자리)]

예시:
0 9 * * 1-5     : 주중 매일 오전 9시
*/5 * * * *     : 5분마다
0 0 * * 1       : 매월 1일 자정
30 9,15 * * 1-5 : 주중 오전 9시30분, 오후 3시30분
```

**응답 (201 Created):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440003",
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "name": "일일 시장 분석",
  "description": "매일 장 마감 후 시장 분석 실행",
  "schedule_type": "cron",
  "schedule_config": {
    "cron_expression": "0 16 * * 1-5"
  },
  "timezone": "Asia/Seoul",
  "is_active": true,
  "job_id": "schedule-660e8400-e29b-41d4-a716-446655440003",
  "next_run_at": "2026-01-17T07:00:00Z",
  "last_run_at": null,
  "run_count": 0,
  "metadata": {},
  "created_at": "2026-01-16T09:00:00+09:00",
  "updated_at": "2026-01-16T09:00:00+09:00"
}
```

**에러 응답 (400 Bad Request):**

```json
{
  "detail": "cron_expression은 CRON 트리거 유형에 필요합니다"
}
```

---

### 3. 스케줄 상세 조회

스케줄 ID로 상세 정보와 통계를 조회합니다.

```
GET /api/v1/schedules/{schedule_id}
```

**경로 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|-----------|------|------|-------------|
| `schedule_id` | UUID | 예 | 스케줄 UUID |

**응답 (200 OK):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440003",
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "일일 시장 분석",
  "schedule_type": "cron",
  "schedule_config": {
    "cron_expression": "0 16 * * 1-5"
  },
  "timezone": "Asia/Seoul",
  "is_active": true,
  "next_run_at": "2026-01-17T07:00:00Z",
  "last_run_at": "2026-01-16T07:00:00Z",
  "run_count": 45,
  "statistics": {
    "total_runs": 45,
    "successful_runs": 44,
    "failed_runs": 1,
    "success_rate": 0.978,
    "average_duration_ms": 1520,
    "last_run_at": "2026-01-16T07:00:00Z",
    "last_status": "completed"
  },
  "created_at": "2026-01-01T09:00:00+09:00",
  "updated_at": "2026-01-16T09:00:00+09:00"
}
```

**에러 응답 (404 Not Found):**

```json
{
  "detail": "Schedule not found"
}
```

---

### 4. 스케줄 수정

기존 스케줄을 수정합니다. 모든 필드는 선택 사항입니다.

```
PUT /api/v1/schedules/{schedule_id}
```

**요청 본문:**

```json
{
  "name": "수정된 시장 분석",
  "description": "업데이트된 설명",
  "cron_expression": "0 17 * * 1-5",
  "timezone": "Asia/Seoul",
  "is_active": true
}
```

**응답 (200 OK):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440003",
  "name": "수정된 시장 분석",
  "schedule_type": "cron",
  "schedule_config": {
    "cron_expression": "0 17 * * 1-5"
  },
  "is_active": true,
  "updated_at": "2026-01-16T10:30:00+09:00"
}
```

---

### 5. 스케줄 삭제

스케줄을 삭제합니다. 기본적으로 소프트 삭제입니다.

```
DELETE /api/v1/schedules/{schedule_id}
```

**경로 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|-----------|------|------|-------------|
| `schedule_id` | UUID | 예 | 스케줄 UUID |

**쿼리 파라미터:**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|-----------|------|------|---------|-------------|
| `hard_delete` | boolean | 아니오 | false | 영구 삭제 (관리자만) |

**응답 (204 No Content):**

성공 시 응답 본문 없음.

---

### 6. 스케줄 일시정지

스케줄 실행을 일시중지합니다.

```
POST /api/v1/schedules/{schedule_id}/pause
```

**응답 (200 OK):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440003",
  "name": "일일 시장 분석",
  "is_active": false,
  "updated_at": "2026-01-16T11:00:00+09:00"
}
```

**에러 응답 (400 Bad Request):**

```json
{
  "detail": "Schedule is already paused"
}
```

---

### 7. 스케줄 재개

일시중지된 스케줄을 다시 활성화합니다.

```
POST /api/v1/schedules/{schedule_id}/resume
```

**응답 (200 OK):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440003",
  "name": "일일 시장 분석",
  "is_active": true,
  "next_run_at": "2026-01-17T07:00:00Z",
  "updated_at": "2026-01-16T12:00:00+09:00"
}
```

---

## 인증

모든 Schedule API 엔드포인트는 JWT 인증이 필요합니다. Authorization 헤더에 토큰을 포함하세요:

```
Authorization: Bearer <your-jwt-token>
```

JWT 획득 방법은 [Authentication Guide](./authentication.md)를 참고하세요.

---

## 권한

스케줄 작업에 대한 권한 규칙:

| 작업 | 필요한 권한 |
|------|-------------|
| 스케줄 생성 | 워크플로우 소유자 |
| 스케줄 조회 | 자신의 스케줄 또는 자신의 워크플로우 스케줄 |
| 스케줄 수정 | 스케줄 생성자 또는 워크플로우 소유자 |
| 스케줄 삭제 | 스케줄 생성자 또는 워크플로우 소유자 |
| 영구 삭제 | 관리자만 |
| 관리자 | 모든 스케줄에 전체 접근 |

---

## 에러 코드

| 상태 코드 | 설명 |
|-------------|-------------|
| 200 | 성공 |
| 201 | 리소스 생성됨 |
| 204 | 삭제됨 (콘텐츠 없음) |
| 400 | 잘못된 요청 (검증 오류) |
| 401 | 인증되지 않음 (토큰 없음/유효하지 않음) |
| 403 | 권한 없음 |
| 404 | 리소스를 찾을 수 없음 |
| 500 | 내부 서버 오류 |

---

## 예제

### Cron 스케줄 생성

```bash
curl -X POST https://api.pastetrader.com/api/v1/schedules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "일일 시장 분석",
    "description": "매일 장 마감 후 시장 분석 실행",
    "trigger_type": "cron",
    "cron_expression": "0 16 * * 1-5",
    "timezone": "Asia/Seoul"
  }'
```

### Interval 스케줄 생성

```bash
curl -X POST https://api.pastetrader.com/api/v1/schedules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "5분간격 수집",
    "trigger_type": "interval",
    "interval_minutes": 5,
    "timezone": "UTC"
  }'
```

### 스케줄 일시정지

```bash
curl -X POST https://api.pastetrader.com/api/v1/schedules/{schedule_id}/pause \
  -H "Authorization: Bearer <token>"
```

### 스케줄 재개

```bash
curl -X POST https://api.pastetrader.com/api/v1/schedules/{schedule_id}/resume \
  -H "Authorization: Bearer <token>"
```

---

## 관련 문서

- [Workflow API Reference](./workflows.md) - 워크플로우 관리 엔드포인트
- [Authentication Guide](./authentication.md) - JWT 인증 상세
- [Schedule Schema Documentation](../database/schemas/schedule-schema.md) - 데이터베이스 스키마
- [Schedule Architecture](../architecture/schedule-management.md) - 시스템 아키텍처
