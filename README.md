# PasteTrader

워크플로우 자동화 및 에이전트 실행 플랫폼

## 프로젝트 개요

PasteTrader는 워크플로우 기반 자동화 플랫폼으로, 사용자가 시각적 흐름도를 통해 복잡한 작업을 자동화할 수 있습니다.

### 핵심 기능

- 시각적 워크플로우 디자이너
- 다양한 도구 통합 (HTTP, MCP, Python, Shell)
- LLM 기반 에이전트 실행
- 실시간 실행 추적
- 이벤트 기반 트리거

## 기술 스택

### 백엔드

- **Python 3.12+**: 핵심 언어
- **FastAPI**: 비동기 웹 프레임워크
- **SQLAlchemy 2.0**: Async ORM
- **PostgreSQL 16**: 기본 데이터베이스
- **Alembic**: 데이터베이스 마이그레이션
- **Pydantic 2.10**: 데이터 검증
- **passlib[bcrypt]**: 비밀번호 해싱
- **python-jose**: JWT 토큰 처리

### 프론트엔드

- **Next.js 15**: React 프레임워크
- **TypeScript 5**: 타입 안전성
- **Tailwind CSS**: 스타일링
- **ReactFlow**: 시각적 워크플로우 편집기

### 인프라

- **Docker**: 컨테이너화
- **GitHub Actions**: CI/CD

## 데이터베이스 아키텍처

PasteTrader는 PostgreSQL 16과 SQLAlchemy 2.0 async ORM을 사용하여 데이터를 관리합니다.

### 핵심 패턴

#### 1. UUID 기반 기본 키

모든 모델은 UUID 기본 키를 사용합니다:

```python
from app.models.base import UUIDMixin, Base

class MyModel(UUIDMixin, Base):
    __tablename__ = "my_models"
    # id 필드는 UUIDMixin에서 자동 제공
```

**이점:**
- 분산 시스템 준비
- 자동 증가 ID 충돌 방지
- 보안성 향상 (URL에서 ID 추론 어려움)

#### 2. 타임스탬프 자동 관리

모든 레코드는 생성 및 수정 시간을 자동으로 추적합니다:

```python
from app.models.base import TimestampMixin

class MyModel(TimestampMixin, Base):
    # created_at: 생성 시간 (자동 설정)
    # updated_at: 수정 시간 (자동 업데이트)
```

**특징:**
- UTC 타임존
- 서버 측 기본값
- 감사 추적 지원

#### 3. 소프트 삭제 패턴

데이터는 영구 삭제되지 않고 삭제 마크만 표시됩니다:

```python
from app.models.base import SoftDeleteMixin

class MyModel(SoftDeleteMixin, Base):
    # deleted_at: 삭제 타임스탬프
    # is_deleted: 삭제 상태 프로퍼티

# 사용 예시
instance.soft_delete()  # 삭제 마크
instance.restore()      # 복원
```

**이점:**
- 데이터 복구 가능
- 감사 추적 유지
- CASCADE 문제 방지

### SQLAlchemy 2.0 Async 패턴

#### 세션 관리

```python
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()
```

**특징:**
- 비동기 세션 팩토리
- 커넥션 풀링
- 자동 커밋/롤백

#### 모델 쿼리

```python
from sqlalchemy import select

# 기본 쿼리
stmt = select(User).where(User.is_active == True)
result = await db.execute(stmt)
users = result.scalars().all()

# 관계 로딩
stmt = select(Workflow).options(selectinload(Workflow.nodes))
```

### Enum 타입 사용

도메인 값에는 타입 안전한 Enum을 사용합니다:

```python
from app.models.enums import NodeType, ExecutionStatus

# 모델에서 사용
class Node(Base):
    node_type: Mapped[NodeType] = mapped_column(
        String(50),
        default=NodeType.TOOL,
        nullable=False,
    )

# 쿼리에서 사용
stmt = select(Node).where(Node.node_type == NodeType.AGENT)
```

**제공 Enum:**
- `NodeType`: 워크플로우 노드 유형
- `ToolType`: 도구 실행 유형
- `ModelProvider`: LLM 제공자
- `ExecutionStatus`: 실행 상태
- `AuthMode`: 인증 모드
- `TriggerType`: 트리거 유형
- `LogLevel`: 로그 레벨

### 베이스 모델 및 Mixin 사용 가이드

모든 새 모델은 베이스 클래스와 Mixin을 상속받아야 합니다:

```python
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

class Product(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
```

**상속 순서:** `UUIDMixin` → `TimestampMixin` → `SoftDeleteMixin` → `Base`

## 프로젝트 구조

```
PasteTrader/
├── backend/              # FastAPI 백엔드
│   ├── app/
│   │   ├── models/      # SQLAlchemy 모델
│   │   ├── db/          # 데이터베이스 세션
│   │   ├── api/         # API 라우트
│   │   ├── core/        # 설정 및 의존성
│   │   └── services/    # 비즈니스 로직
│   ├── tests/           # 테스트 코드
│   └── alembic/         # 데이터베이스 마이그레이션
├── frontend/            # Next.js 프론트엔드
│   ├── app/             # App Router 페이지
│   ├── components/      # React 컴포넌트
│   └── lib/             # 유틸리티
├── docs/                # 프로젝트 문서
│   └── database/        # 데이터베이스 가이드
└── .moai/               # MoAI 설정 및 SPEC
```

## 시작하기

### 사전 요구사항

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Docker (선택)

### 설치

```bash
# 백엔드 설정
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 데이터베이스 설정
cp .env.example .env
# .env 파일에서 DATABASE_URL 설정

# 마이그레이션 실행
alembic upgrade head

# 프론트엔드 설정
cd ../frontend
npm install
```

### 실행

```bash
# 백엔드 (개발)
cd backend
uvicorn app.main:app --reload --port 8000

# 프론트엔드 (개발)
cd frontend
npm run dev
```

## 문서

### 데이터베이스 가이드

- [모델 생성 가이드](docs/database/models.md)
- [마이그레이션 가이드](docs/database/migrations.md)

### SPEC 문서

- [SPEC-001: Database Foundation](.moai/specs/SPEC-001/spec.md) - 구현 완료
- [SPEC-002: User Authentication Model](.moai/specs/SPEC-002/spec.md) - 구현 완료
- [SPEC-003: Workflow Domain Models](.moai/specs/SPEC-003/spec.md) - 구현 완료
- [SPEC-005: Execution Tracking Models](.moai/specs/SPEC-005/spec.md) - 구현 완료
- [SPEC-007: Workflow Execution Engine](.moai/specs/SPEC-007/spec.md) - 구현 완료

## 테스트

```bash
# 백엔드 테스트
cd backend
pytest --cov=app --cov-report=html

# 테스트 커버리지 확인
open htmlcov/index.html
```

## 기여

기여를 환영합니다! 다음 단계를 따라주세요:

1. Fork本项目
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'feat: Add amazing feature'`)
4. 브랜치 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 라이선스

이 프로젝트는 MIT 라이선스 하에 라이선스됩니다.

## 상태

- [x] Phase 0: 데이터베이스 기반 구축 (SPEC-001, SPEC-002)
- [x] Phase 1: 워크플로우 코어 모델 (SPEC-003, SPEC-007)
- [x] Phase 2: 실행 추적 모델 (SPEC-005)
- [ ] Phase 3: API 파운데이션
- [ ] Phase 4: 프론트엔드 개발

### 완료된 SPEC

- **SPEC-001**: Database Foundation Setup (베이스 모델 및 Mixin 구현)
- **SPEC-002**: User Authentication Model (사용자 인증 모델 및 보안 유틸리티)
- **SPEC-003**: Workflow Domain Models (Workflow, Node, Edge 도메인 모델)
- **SPEC-005**: Execution Tracking Models (WorkflowExecution, NodeExecution, ExecutionLog)
- **SPEC-007**: Workflow Execution Engine (워크플로우 실행 엔진)

## 연락처

프로젝트 관련 문의사항은 Issue를 통해 제출해주세요.
