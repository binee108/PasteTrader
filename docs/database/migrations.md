# Alembic 마이그레이션 가이드

이 가이드는 PasteTrader 프로젝트에서 Alembic을 사용하여 데이터베이스 마이그레이션을 관리하는 방법을 설명합니다.

## 목차

- [기본 개념](#기본-개념)
- [마이그레이션 생성](#마이그레이션-생성)
- [마이그레이션 실행](#마이그레이션-실행)
- [롤백 절차](#롤백-절차)
- [안전 확인](#안전-확인)
- [마이그레이션 테스트](#마이그레이션-테스트)
- [문제 해결](#문제-해결)

---

## 기본 개념

### Alembic이란?

Alembic은 SQLAlchemy용 데이터베이스 마이그레이션 도구입니다:

- **버전 관리**: 데이터베이스 스키마 변경 사항을 버전으로 관리
- **자동 생성**: 모델 변경을 감지하여 마이그레이션 스크립트 자동 생성
- **Async 지원**: SQLAlchemy 2.0 async 패턴 완벽 지원
- **안전장치**: 프로덕션 환경에서의 실수 방지

### 디렉토리 구조

```
backend/
  alembic.ini              # Alembic 설정 파일
  alembic/
    env.py                 # 마이그레이션 환경 설정
    script.py.mako         # 마이그레이션 템플릿
    versions/              # 마이그레이션 파일 저장소
      001_*.py            # 마이그레이션 파일
```

---

## 마이그레이션 생성

### 자동 생성 (Autogenerate)

모델 변경 사항을 자동으로 감지하여 마이그레이션을 생성합니다:

```bash
cd backend
alembic revision --autogenerate -m "Add User model"
```

**절차:**

1. 모델 파일 수정 (`app/models/`)
2. `alembic/env.py`에 새 모델 임포트 확인
3. autogenerate 명령 실행
4. 생성된 마이그레이션 파일 검토
5. 필요한 경우 수동 수정

### 수동 생성

복잡한 데이터 변환이 필요한 경우 수동으로 생성합니다:

```bash
alembic revision -m "Custom data migration"
```

생성된 파일의 `upgrade()`와 `downgrade()` 함수를 직접 작성합니다.

---

## 마이그레이션 실행

### 개발 환경

```bash
cd backend

# 최신 버전으로 업그레이드
alembic upgrade head

# 특정 버전으로 업그레이드
alembic upgrade +1
alembic upgrade 001_phase1_workflow_core_models

# 현재 버전 확인
alembic current

# 이력 확인
alembic history
```

### 프로덕션 환경

프로덕션 환경에서는 추가 안전 확인이 필요합니다:

```bash
# 1. 환경 변수 설정
export ENVIRONMENT=production
export CONFIRM_PRODUCTION_MIGRATION=true

# 2. 마이그레이션 실행
alembic upgrade head
```

**안전 확인 사항:**

- `ENVIRONMENT=production`인 경우 `CONFIRM_PRODUCTION_MIGRATION=true` 필요
- 없으면 마이그레이션이 차단됨
- 실수로 프로덕션 DB 수정 방지

---

## 롤백 절차

### 단계별 롤백

```bash
# 한 버전 롤백
alembic downgrade -1

# 특정 버전으로 롤백
alembic downgrade 001_phase1_workflow_core_models

# 초기 상태로 롤백 (모든 마이그레이션 취소)
alembic downgrade base
```

### 롤백 시 주의사항

1. **데이터 손실 위험**: 롤백은 테이블/컬럼 삭제를 포함할 수 있음
2. **다운그레이드 로직**: 마이그레이션 파일에 `downgrade()` 함수가 올바르게 작성되어야 함
3. **백업 권장**: 중요한 롤백 전 데이터베이스 백업 권장

### 롤백 가능한 마이그레이션 작성

```python
def upgrade() -> None:
    # 컬럼 추가
    op.add_column('users', sa.Column('new_field', sa.String(), nullable=True))

def downgrade() -> None:
    # 컬럼 제거
    op.drop_column('users', 'new_field')
```

---

## 안전 확인

### 프로덕션 안전 장치

`alembic/env.py`의 `check_production_safety()` 함수가 프로덕션 환경에서의 마이그레이션을 보호합니다:

```python
def check_production_safety() -> None:
    """프로덕션 환경에서의 실수 방지."""
    env = os.getenv("ENVIRONMENT", "").lower()

    if env == "production":
        confirm = os.getenv("CONFIRM_PRODUCTION_MIGRATION", "").lower()
        if confirm != "true":
            raise RuntimeError(
                "Production migration requires CONFIRM_PRODUCTION_MIGRATION=true. "
                "This prevents accidental migrations to production database."
            )
```

### 마이그레이션 전 체크리스트

- [ ] 로컬 환경에서 마이그레이션 테스트 완료
- [ ] Autogenerate 결과 검토 및 수동 수정 완료
- [ ] `downgrade()` 함수 작성 및 테스트
- [ ] 프로덕션 환경 변수 확인 (`ENVIRONMENT`, `CONFIRM_PRODUCTION_MIGRATION`)
- [ ] 데이터베이스 백업 완료 (프로덕션)

---

## 마이그레이션 테스트

### 테스트 환경 설정

```python
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from alembic.config import Config
from alembic.script import ScriptDirectory

async def test_migrations():
    """마이그레이션 테스트."""
    # 테스트 데이터베이스 엔진 생성
    engine = create_async_engine(TEST_DATABASE_URL)

    # 마이그레이션 실행
    config = Config("alembic.ini")
    script_dir = ScriptDirectory.from_config(config)

    # 마이그레이션 테스트 로직
    # ...

    await engine.dispose()
```

### 테스트 케이스 예시

```python
async def test_user_model_migration():
    """User 모델 마이그레이션 테스트."""
    # 1. 마이그레이션 실행
    await run_migrations()

    # 2. 테이블 존재 확인
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_name='users'")
        )
        assert result.scalar() == "users"

    # 3. 컬럼 확인
    result = await conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='email'")
    )
    assert result.scalar() == "email"

    # 4. 롤백 테스트
    await rollback_migrations()
```

---

## 문제 해결

### 일반적인 문제

#### 1. Autogenerate가 변경을 감지하지 않음

**원인:** 모델이 `alembic/env.py`에 임포트되지 않음

**해결:**
```python
# alembic/env.py
from app.models import (
    Base,
    MyModel,  # 새 모델 추가
)
```

#### 2. 데이터베이스 URL 오류

**원인:** `DATABASE_URL`이 설정되지 않음

**해결:**
```bash
# .env 파일 설정
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/pastetrader
```

#### 3. 프로덕션 마이그레이션 차단

**원인:** `CONFIRM_PRODUCTION_MIGRATION` 설정되지 않음

**해결:**
```bash
export CONFIRM_PRODUCTION_MIGRATION=true
alembic upgrade head
```

#### 4. Async 드라이버 오류

**원인:** 데이터베이스 URL에 async 드라이버 지정되지 않음

**해결:** URL이 `postgresql+asyncpg://`로 시작하는지 확인

### 마이그레이션 충돌 해결

여러 개발자가 동시에 마이그레이션을 생성할 경우 충돌이 발생할 수 있습니다:

1. 최신 상태 확인: `git pull`
2. 마이그레이션 병합: 충돌하는 버전 번호 조정
3. 테스트: 로컬에서 마이그레이션 테스트
4. 리베이스: 마이그레이션 이력이 꼬인 경우

```bash
# 마이그레이션 리베이스 (주의: 데이터 손실 가능)
alembic stamp head
alembic downgrade base
alembic upgrade head
```

---

## 모범 사례

### 1. 자주 마이그레이션 생성

작은 단위로 자주 마이그레이션을 생성하세요:
- 변경사항당 하나의 마이그레이션
- 명확한 메시지 작성
- 검토 후 커밋

### 2. 마이그레이션 메시지 규칙

```bash
# 좋은 예
alembic revision --autogenerate -m "Add User model with email and is_active"

# 나쁜 예
alembic revision --autogenerate -m "update"
```

### 3. Autogenerate 결과 검토

자동 생성된 마이그레이션을 항상 검토하세요:
- 예상치 못한 변경이 없는지 확인
- 인덱스와 제약조건이 올바른지 확인
- nullable 설정이 올바른지 확인

### 4. 롤백 가능성 고려

모든 마이그레이션은 롤백 가능하도록 작성하세요:
- `downgrade()` 함수 작성
- 파괴적 작업 최소화
- 데이터 마이그레이션 시 백업 고려

---

## 추가 참고자료

- [Alembic 공식 문서](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [모델 생성 가이드](./models.md)
- [프로젝트 SPEC-001](../../.moai/specs/SPEC-001/spec.md)
