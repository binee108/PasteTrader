# 데이터베이스 모델 생성 가이드

이 가이드는 PasteTrader 프로젝트에서 SQLAlchemy 2.0 async 패턴을 사용하여 데이터베이스 모델을 생성하는 방법을 설명합니다.

## 목차

- [기본 개념](#기본-개념)
- [베이스 클래스](#베이스-클래스)
- [모델 생성 절차](#모델-생성-절차)
- [Enum 사용법](#enum-사용법)
- [관계 정의](#관계-정의)
- [모범 사례](#모범-사례)

---

## 기본 개념

PasteTrader는 PostgreSQL 16과 SQLAlchemy 2.0 async ORM을 사용합니다. 모든 모델은 다음 원칙을 따릅니다:

- **UUID 기반 기본 키**: 분산 시스템 준비를 위해 UUID 사용
- **타임스탬프 자동 관리**: 생성 및 수정 시간 자동 추적
- **소프트 삭제 패턴**: 데이터 복구를 위해 영구 삭제 대신 삭제 마크 사용

---

## 베이스 클래스

### UUIDMixin

모든 모델에 UUID 기본 키를 추가합니다:

```python
from app.models.base import UUIDMixin

class MyModel(UUIDMixin, Base):
    __tablename__ = "my_models"

    # id 필드는 UUIDMixin에서 자동으로 제공됩니다
    name: Mapped[str] = mapped_column(String(255), nullable=False)
```

**특징:**
- PostgreSQL에서는 네이티브 UUID 타입 사용
- SQLite에서는 CHAR(36)로 자동 변환
- Python 측에서 `uuid.uuid4()`로 자동 생성

### TimestampMixin

생성 및 수정 시간을 자동으로 추적합니다:

```python
from app.models.base import TimestampMixin

class MyModel(TimestampMixin, Base):
    __tablename__ = "my_models"

    # created_at, updated_at이 자동으로 추가됩니다
    name: Mapped[str] = mapped_column(String(255), nullable=False)
```

**필드:**
- `created_at`: 레코드 생성 시간 (수정되지 않음)
- `updated_at`: 레코드 수정 시간 (매번 자동 업데이트)

**특징:**
- 타임존 인식 (UTC)
- 서버 측 기본값 제공
- 수정 시 자동 업데이트

### SoftDeleteMixin

소프트 삭제 기능을 제공합니다:

```python
from app.models.base import SoftDeleteMixin

class MyModel(SoftDeleteMixin, Base):
    __tablename__ = "my_models"

    # deleted_at 필드와 is_deleted 프로퍼티가 추가됩니다
    name: Mapped[str] = mapped_column(String(255), nullable=False)
```

**필드:**
- `deleted_at`: 삭제 타임스탬프 (nullable)
- `is_deleted`: 삭제 상태 프로퍼티

**메서드:**
- `soft_delete()`: 레코드를 삭제 마크
- `restore()`: 삭제된 레코드 복원

**사용 예시:**
```python
# 레코드 삭제
await session.execute(update(MyModel).where(MyModel.id == id).values(deleted_at=datetime.now(UTC)))

# 또는 인스턴스 메서드 사용
instance.soft_delete()
await session.commit()

# 레코드 복원
instance.restore()
await session.commit()

# 삭제 상태 확인
if instance.is_deleted:
    print("이 레코드는 삭제되었습니다")
```

---

## 모델 생성 절차

### 1. 모델 파일 생성

`app/models/` 디렉토리에 새 모델 파일을 생성합니다:

```python
"""도메인 모델 설명.

TAG: [SPEC-XXX] [DOMAIN] [MODEL]
REQ: REQ-XXX - 요구사항 참조

이 모듈은 [도메인] 모델을 정의합니다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.other import OtherModel


class MyModel(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """모델 설명.

    Attributes:
        id: UUID 기본 키
        name: 모델 이름
        description: 상세 설명
        created_at: 생성 시간
        updated_at: 수정 시간
        deleted_at: 삭제 시간
    """

    __tablename__ = "my_models"

    # 필드 정의
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # 관계 정의
    other_models: Mapped[list[OtherModel]] = relationship(
        "OtherModel",
        back_populates="my_model",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """문자열 표현 반환."""
        return f"<MyModel(id={self.id}, name='{self.name}')>"


__all__ = ["MyModel"]
```

### 2. 모델 등록

`app/models/__init__.py`에 모델을 내보냅니다:

```python
from app.models.my_model import MyModel

__all__ = [
    "MyModel",
    # ... 다른 모델들
]
```

### 3. Alembic에 모델 등록

`alembic/env.py`에 모델을 임포트합니다:

```python
from app.models import (
    Base,
    MyModel,  # 추가
    # ... 다른 모델들
)
```

### 4. 마이그레이션 생성

```bash
cd backend
alembic revision --autogenerate -m "Add MyModel"
alembic upgrade head
```

---

## Enum 사용법

### 기본 Enum 정의

`app/models/enums.py`에 새 Enum을 정의합니다:

```python
from enum import Enum

class MyEnum(str, Enum):
    """Enum 설명."""

    VALUE1 = "value1"
    VALUE2 = "value2"

    def __str__(self) -> str:
        return self.value
```

### 모델에서 Enum 사용

```python
from app.models.enums import MyEnum
from sqlalchemy import String

class MyModel(Base):
    __tablename__ = "my_models"

    # VARCHAR에 Enum 값 저장
    status: Mapped[MyEnum] = mapped_column(
        String(50),
        default=MyEnum.VALUE1,
        nullable=False,
    )
```

### 기존 Enum 목록

PasteTrader에서 제공하는 기본 Enum:

| Enum 이름 | 값 | 용도 |
|-----------|------|------|
| NodeType | trigger, tool, agent, condition, adapter, parallel, aggregator | 워크플로우 노드 분류 |
| ToolType | http, mcp, python, shell, builtin | 도구 실행 유형 |
| ModelProvider | anthropic, openai, glm | LLM 제공자 |
| ExecutionStatus | pending, running, completed, failed, skipped, cancelled | 실행 상태 |
| AuthMode | oauth, standalone, sdk, glm | 인증 모드 |
| TriggerType | schedule, event, manual | 트리거 유형 |
| LogLevel | debug, info, warning, error | 로그 레벨 |

---

## 관계 정의

### 일대다 (One-to-Many)

```python
class Parent(Base):
    __tablename__ = "parents"

    children: Mapped[list[Child]] = relationship(
        "Child",
        back_populates="parent",
        passive_deletes=True,  # 소프트 삭제 지원
    )

class Child(Base):
    __tablename__ = "children"

    parent_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("parents.id", ondelete="CASCADE"),
        nullable=False,
    )

    parent: Mapped[Parent] = relationship(
        "Parent",
        back_populates="children",
    )
```

### 다대다 (Many-to-Many)

```python
class Association(Base):
    """연결 테이블."""

    __tablename__ = "associations"

    left_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("lefts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    right_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("rights.id", ondelete="CASCADE"),
        primary_key=True,
    )

    left: Mapped[Left] = relationship(back_populates="rights")
    right: Mapped[Right] = relationship(back_populates="lefts")
```

---

## 모범 사례

### 1. 타입 힌트 사용

항상 `Mapped[]` 타입 힌트를 사용하세요:

```python
# 좋은 예
name: Mapped[str] = mapped_column(String(255), nullable=False)

# 나쁜 예
name = Column(String(255), nullable=False)
```

### 2. TYPE_CHECKING 사용

순환 임포트를 방지하기 위해 `TYPE_CHECKING`을 사용하세요:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.other import OtherModel
```

### 3. nullable 명시

모든 필드에 `nullable`을 명시하세요:

```python
# 좋은 예
name: Mapped[str] = mapped_column(String(255), nullable=False)
description: Mapped[str | None] = mapped_column(Text, nullable=True)

# 나쁜 예
name: Mapped[str] = mapped_column(String(255))  # nullable이 암시적
```

### 4. 인덱스 활용

쿼리 성능을 위해 자주 조회하는 필드에 인덱스를 추가하세요:

```python
email: Mapped[str] = mapped_column(
    String(255),
    unique=True,
    nullable=False,
    index=True,  # 인덱스 추가
)
```

### 5. 문서화 작성

모든 모델과 중요한 필드에 독스트링을 작성하세요:

```python
class User(Base):
    """사용자 모델.

    인증 및 리소스 소유권을 위한 사용자 정보를 관리합니다.

    Attributes:
        id: UUID 기본 키
        email: 고유 이메일 주소
        is_active: 계정 활성화 상태
    """
```

### 6. 소프트 삭제 고려

소프트 삭제를 사용하는 모델에서는 관계를 정의할 때 `passive_deletes=True`를 사용하세요:

```python
workflows: Mapped[list[Workflow]] = relationship(
    "Workflow",
    back_populates="owner",
    passive_deletes=True,  # 소프트_delete 시 캐스케이드 방지
)
```

---

## 추가 참고자료

- [SQLAlchemy 2.0 문서](https://docs.sqlalchemy.org/en/20/)
- [Alembic 마이그레이션 가이드](./migrations.md)
- [프로젝트 SPEC-001](../../.moai/specs/SPEC-001/spec.md)
