# SPEC-009: Tool/Agent API Endpoints - Implementation Plan

## 1. 구현 개요

### 1.1 범위

| 구분 | 항목 수 | 설명 |
|------|---------|------|
| Tool API | 6개 | CRUD + 테스트 실행 |
| Agent API | 7개 | CRUD + 도구 연결 + 테스트 실행 |
| 스키마 | 6개 | Tool, Agent, ModelConfig 등 |
| 서비스 | 2개 | ToolService, AgentService |

### 1.2 예상 작업 시간

**총 예상 시간: 8-12시간**

---

## 2. 태스크 분해

### Phase 1: 스키마 및 모델 정의 (2시간)

| 태스크 ID | 태스크 | 우선순위 | 예상 시간 |
|-----------|--------|----------|-----------|
| T-001 | Tool Pydantic 스키마 정의 | HIGH | 30분 |
| T-002 | Agent Pydantic 스키마 정의 | HIGH | 30분 |
| T-003 | Tool SQLAlchemy 모델 정의 | HIGH | 30분 |
| T-004 | Agent SQLAlchemy 모델 정의 | HIGH | 30분 |

### Phase 2: 서비스 레이어 구현 (3-4시간)

| 태스크 ID | 태스크 | 우선순위 | 예상 시간 | 의존성 |
|-----------|--------|----------|-----------|--------|
| T-005 | ToolService CRUD 구현 | HIGH | 1시간 | T-001, T-003 |
| T-006 | ToolService 테스트 실행 구현 | HIGH | 1시간 | T-005 |
| T-007 | AgentService CRUD 구현 | HIGH | 1시간 | T-002, T-004 |
| T-008 | AgentService 테스트 실행 구현 | MEDIUM | 1시간 | T-007 |

### Phase 3: API 라우터 구현 (2-3시간)

| 태스크 ID | 태스크 | 우선순위 | 예상 시간 | 의존성 |
|-----------|--------|----------|-----------|--------|
| T-009 | Tool API 엔드포인트 구현 | HIGH | 1시간 | T-005, T-006 |
| T-010 | Agent API 엔드포인트 구현 | HIGH | 1시간 | T-007, T-008 |
| T-011 | ToolRegistry 통합 | MEDIUM | 30분 | T-009 |
| T-012 | 에러 핸들링 통합 | MEDIUM | 30분 | T-009, T-010 |

### Phase 4: 테스트 및 문서화 (2시간)

| 태스크 ID | 태스크 | 우선순위 | 예상 시간 | 의존성 |
|-----------|--------|----------|-----------|--------|
| T-013 | Tool API 단위 테스트 | HIGH | 30분 | T-009 |
| T-014 | Agent API 단위 테스트 | HIGH | 30분 | T-010 |
| T-015 | 통합 테스트 | MEDIUM | 30분 | T-013, T-014 |
| T-016 | API 문서 업데이트 | LOW | 30분 | T-015 |

---

## 3. 상세 구현 계획

### 3.1 스키마 정의

**파일**: `backend/app/schemas/tool.py`

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Any


class ToolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    parameters: dict[str, Any]  # JSON Schema
    implementation_path: str | None = None


class ToolUpdate(BaseModel):
    description: str | None = None
    parameters: dict[str, Any] | None = None
    implementation_path: str | None = None
    is_active: bool | None = None


class ToolResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    parameters: dict[str, Any]
    implementation_path: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ToolDetailResponse(ToolResponse):
    used_by_agents: list[UUID] = []
    used_in_workflows: list[UUID] = []


class ToolTestRequest(BaseModel):
    params: dict[str, Any]
    timeout: int = Field(default=30, ge=1, le=120)


class ToolTestResponse(BaseModel):
    success: bool
    result: Any | None = None
    error: str | None = None
    execution_time_ms: int
    logs: list[str] = []
```

**파일**: `backend/app/schemas/agent.py`

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Any


class ModelConfig(BaseModel):
    provider: str = Field(..., pattern="^(anthropic|openai|glm)$")
    model: str
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=128000)


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str = Field(..., min_length=1)
    model_config: ModelConfig
    tool_ids: list[UUID] = []


class AgentUpdate(BaseModel):
    description: str | None = None
    system_prompt: str | None = None
    model_config: ModelConfig | None = None
    is_active: bool | None = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    system_prompt: str
    model_config: ModelConfig
    tool_ids: list[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class AgentToolsUpdate(BaseModel):
    tool_ids: list[UUID]


class AgentTestRequest(BaseModel):
    test_prompt: str = Field(..., min_length=1)
    timeout: int = Field(default=60, ge=1, le=300)


class AgentTestResponse(BaseModel):
    success: bool
    response: str | None = None
    error: str | None = None
    tool_calls: list[dict[str, Any]] = []
    execution_time_ms: int
    tokens_used: dict[str, int] | None = None
```

### 3.2 서비스 레이어

**파일**: `backend/app/services/tool_service.py`

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.tool import Tool
from app.schemas.tool import ToolCreate, ToolUpdate, ToolTestRequest, ToolTestResponse


class ToolService:
    async def create_tool(
        self, db: AsyncSession, tool_in: ToolCreate
    ) -> Tool:
        """새 도구를 생성합니다."""
        # 이름 중복 검사
        existing = await self.get_tool_by_name(db, tool_in.name)
        if existing:
            raise ValueError(f"Tool with name '{tool_in.name}' already exists")
        
        tool = Tool(**tool_in.model_dump())
        db.add(tool)
        await db.commit()
        await db.refresh(tool)
        return tool

    async def get_tool(self, db: AsyncSession, tool_id: UUID) -> Tool | None:
        """ID로 도구를 조회합니다."""
        result = await db.execute(select(Tool).where(Tool.id == tool_id))
        return result.scalar_one_or_none()

    async def get_tool_by_name(self, db: AsyncSession, name: str) -> Tool | None:
        """이름으로 도구를 조회합니다."""
        result = await db.execute(select(Tool).where(Tool.name == name))
        return result.scalar_one_or_none()

    async def list_tools(
        self,
        db: AsyncSession,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Tool]:
        """도구 목록을 조회합니다."""
        query = select(Tool)
        
        if is_active is not None:
            query = query.where(Tool.is_active == is_active)
        
        if search:
            query = query.where(
                Tool.name.ilike(f"%{search}%") | 
                Tool.description.ilike(f"%{search}%")
            )
        
        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_tool(
        self, db: AsyncSession, tool_id: UUID, tool_in: ToolUpdate
    ) -> Tool | None:
        """도구를 수정합니다."""
        tool = await self.get_tool(db, tool_id)
        if not tool:
            return None
        
        update_data = tool_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tool, field, value)
        
        await db.commit()
        await db.refresh(tool)
        return tool

    async def delete_tool(self, db: AsyncSession, tool_id: UUID) -> bool:
        """도구를 삭제합니다."""
        tool = await self.get_tool(db, tool_id)
        if not tool:
            return False
        
        # 사용 중인지 확인 (Agent, Workflow)
        # TODO: 사용 중이면 에러 반환
        
        await db.execute(delete(Tool).where(Tool.id == tool_id))
        await db.commit()
        return True

    async def test_tool(
        self, db: AsyncSession, tool_id: UUID, request: ToolTestRequest
    ) -> ToolTestResponse:
        """도구를 테스트 실행합니다."""
        import time
        from meta_llm.tools.registry import ToolRegistry
        
        tool = await self.get_tool(db, tool_id)
        if not tool:
            return ToolTestResponse(
                success=False,
                error="Tool not found",
                execution_time_ms=0
            )
        
        start_time = time.time()
        logs = []
        
        try:
            # ToolRegistry에서 도구 인스턴스 가져오기
            registry = ToolRegistry()
            tool_instance = registry.get(tool.name)
            
            logs.append(f"Executing tool: {tool.name}")
            result = await tool_instance.execute(request.params)
            logs.append("Execution completed successfully")
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ToolTestResponse(
                success=True,
                result=result,
                execution_time_ms=execution_time,
                logs=logs
            )
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logs.append(f"Error: {str(e)}")
            
            return ToolTestResponse(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                logs=logs
            )


tool_service = ToolService()
```

### 3.3 API 라우터

**파일**: `backend/app/api/v1/tools.py`

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.tool import (
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolDetailResponse,
    ToolTestRequest,
    ToolTestResponse,
)
from app.services.tool_service import tool_service

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("", response_model=ToolResponse, status_code=201)
async def create_tool(
    tool_in: ToolCreate,
    db: AsyncSession = Depends(get_db),
):
    """새 도구를 생성합니다."""
    try:
        tool = await tool_service.create_tool(db, tool_in)
        return tool
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[ToolResponse])
async def list_tools(
    is_active: bool | None = None,
    search: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """도구 목록을 조회합니다."""
    return await tool_service.list_tools(db, is_active, search, limit, offset)


@router.get("/{tool_id}", response_model=ToolDetailResponse)
async def get_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """도구 상세 정보를 조회합니다."""
    tool = await tool_service.get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: UUID,
    tool_in: ToolUpdate,
    db: AsyncSession = Depends(get_db),
):
    """도구를 수정합니다."""
    tool = await tool_service.update_tool(db, tool_id, tool_in)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """도구를 삭제합니다."""
    deleted = await tool_service.delete_tool(db, tool_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"id": tool_id, "deleted": True, "message": "Tool deleted successfully"}


@router.post("/{tool_id}/test", response_model=ToolTestResponse)
async def test_tool(
    tool_id: UUID,
    request: ToolTestRequest,
    db: AsyncSession = Depends(get_db),
):
    """도구를 테스트 실행합니다."""
    return await tool_service.test_tool(db, tool_id, request)
```

---

## 4. 기술적 제약사항

### 4.1 제약사항

| 제약 | 설명 | 대응 방안 |
|------|------|-----------|
| 이름 고유성 | 도구/에이전트 이름은 시스템 전체에서 고유 | DB UNIQUE 제약 + 서비스 레벨 검증 |
| 순환 참조 | 에이전트가 자신을 도구로 참조 방지 | 생성/수정 시 검증 로직 |
| 삭제 제한 | 사용 중인 도구/에이전트 삭제 방지 | 참조 검사 후 409 Conflict 반환 |
| 테스트 타임아웃 | 무한 실행 방지 | 최대 타임아웃 제한 (도구: 120초, 에이전트: 300초) |

### 4.2 의존성

| 라이브러리 | 버전 | 용도 |
|------------|------|------|
| FastAPI | >=0.115.0 | API 프레임워크 |
| SQLAlchemy | >=2.0.0 | ORM |
| Pydantic | >=2.10.0 | 스키마 검증 |

---

## 5. 테스트 계획

### 5.1 단위 테스트

```python
# tests/unit/test_tool_service.py

async def test_create_tool():
    """도구 생성 테스트"""
    pass

async def test_create_tool_duplicate_name():
    """중복 이름 도구 생성 시 에러 테스트"""
    pass

async def test_delete_tool_in_use():
    """사용 중인 도구 삭제 시 에러 테스트"""
    pass

async def test_tool_test_execution():
    """도구 테스트 실행 테스트"""
    pass
```

### 5.2 통합 테스트

```python
# tests/integration/test_tool_agent_api.py

async def test_tool_agent_workflow():
    """도구 생성 → 에이전트 생성 → 연결 전체 플로우"""
    pass

async def test_agent_tool_reference():
    """에이전트가 참조하는 도구 삭제 시 동작 확인"""
    pass
```

---

## 6. 롤아웃 계획

| 단계 | 내용 | 검증 항목 |
|------|------|-----------|
| 1 | 개발 환경 배포 | 기능 테스트 |
| 2 | 스테이징 환경 배포 | 통합 테스트, 성능 테스트 |
| 3 | 프로덕션 배포 | 모니터링, 롤백 준비 |

---

## 7. 성공 기준

| 기준 | 목표 |
|------|------|
| 기능 완성도 | 모든 13개 엔드포인트 정상 동작 |
| 테스트 커버리지 | 80% 이상 |
| API 응답 시간 | P95 < 200ms (CRUD) |
| 에러율 | < 0.1% |
