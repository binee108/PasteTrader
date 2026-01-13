# SPEC-008: Execution API Endpoints - Implementation Plan

## 1. 구현 개요

### 1.1 현황 분석

| 구분 | 상태 | 항목 |
|------|------|------|
| ✅ 구현 완료 | 12개 | WorkflowExecution CRUD, NodeExecution 조회, 로그, 통계 |
| ⏳ 구현 필요 | 2개 | Retry, Delete 엔드포인트 |
| 📋 스키마 준비됨 | 3개 | ExecutionRetry, ExecutionResume, ExecutionCancel |

### 1.2 예상 작업 시간

**총 예상 시간: 5-8시간**

---

## 2. 태스크 분해

### Phase 1: 기존 구현 검증 (1-2시간)

| 태스크 ID | 태스크 | 우선순위 | 예상 시간 |
|-----------|--------|----------|-----------|
| T-001 | 기존 엔드포인트 동작 검증 | HIGH | 30분 |
| T-002 | 스키마 일관성 검토 | HIGH | 30분 |
| T-003 | 테스트 커버리지 확인 | MEDIUM | 30분 |

### Phase 2: 미구현 엔드포인트 구현 (3-4시간)

| 태스크 ID | 태스크 | 우선순위 | 예상 시간 | 의존성 |
|-----------|--------|----------|-----------|--------|
| T-004 | DELETE /executions/{id} 구현 | HIGH | 1시간 | - |
| T-005 | POST /executions/{id}/retry 구현 | HIGH | 2시간 | T-004 |
| T-006 | 에러 핸들링 통합 | MEDIUM | 1시간 | T-004, T-005 |

### Phase 3: 테스트 및 문서화 (1-2시간)

| 태스크 ID | 태스크 | 우선순위 | 예상 시간 | 의존성 |
|-----------|--------|----------|-----------|--------|
| T-007 | 단위 테스트 작성 | HIGH | 1시간 | T-005 |
| T-008 | 통합 테스트 작성 | MEDIUM | 30분 | T-007 |
| T-009 | API 문서 업데이트 | LOW | 30분 | T-008 |

---

## 3. 상세 구현 계획

### 3.1 DELETE /executions/{id} 구현

**파일**: `backend/app/api/v1/executions.py`

```python
@router.delete("/{execution_id}")
async def cancel_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ExecutionCancelResponse:
    """
    실행 중인 워크플로우를 취소하거나 완료된 실행을 삭제합니다.
    
    - running 상태: cancelled로 변경
    - pending 상태: 즉시 삭제
    - completed/failed: 레코드 삭제 (CASCADE)
    """
    execution = await execution_service.get_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if execution.status == ExecutionStatus.RUNNING:
        # 실행 중인 경우 취소 처리
        await execution_service.cancel_execution(db, execution_id)
        return ExecutionCancelResponse(
            id=execution_id,
            status="cancelled",
            message="Execution cancelled successfully"
        )
    else:
        # 완료/실패/대기 상태인 경우 삭제
        await execution_service.delete_execution(db, execution_id)
        return ExecutionCancelResponse(
            id=execution_id,
            status="deleted",
            message="Execution deleted successfully"
        )
```

### 3.2 POST /executions/{id}/retry 구현

**파일**: `backend/app/api/v1/executions.py`

```python
@router.post("/{execution_id}/retry")
async def retry_execution(
    execution_id: UUID,
    request: ExecutionRetryRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecutionRetryResponse:
    """
    실패한 워크플로우 실행을 재시도합니다.
    
    - failed 상태만 재시도 가능
    - from_node 지정 시 해당 노드부터 재시작
    - retry_count 자동 증가
    """
    execution = await execution_service.get_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if execution.status != ExecutionStatus.FAILED:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot retry execution with status: {execution.status}"
        )
    
    # 재시도 실행
    updated = await execution_service.retry_execution(
        db, 
        execution_id,
        from_node=request.from_node,
        reset_context=request.reset_context
    )
    
    return ExecutionRetryResponse(
        id=execution_id,
        status="pending",
        retry_count=updated.retry_count,
        message=f"Retry initiated from node {request.from_node or 'start'}"
    )
```

### 3.3 서비스 레이어 추가 메서드

**파일**: `backend/app/services/execution_service.py`

```python
async def cancel_execution(
    self, 
    db: AsyncSession, 
    execution_id: UUID
) -> WorkflowExecution:
    """실행 중인 워크플로우를 취소합니다."""
    execution = await self.get_execution(db, execution_id)
    
    # 실행 중인 노드에 취소 신호 전송
    await self._signal_cancellation(execution_id)
    
    # 상태 업데이트
    execution.status = ExecutionStatus.CANCELLED
    execution.completed_at = datetime.now(timezone.utc)
    
    await db.commit()
    return execution

async def delete_execution(
    self, 
    db: AsyncSession, 
    execution_id: UUID
) -> None:
    """워크플로우 실행 레코드를 삭제합니다."""
    # CASCADE로 node_executions도 함께 삭제
    await db.execute(
        delete(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    await db.commit()

async def retry_execution(
    self,
    db: AsyncSession,
    execution_id: UUID,
    from_node: str | None = None,
    reset_context: bool = False
) -> WorkflowExecution:
    """실패한 실행을 재시도합니다."""
    execution = await self.get_execution(db, execution_id)
    
    # retry_count 증가
    execution.retry_count += 1
    execution.status = ExecutionStatus.PENDING
    execution.error_message = None
    
    if reset_context:
        execution.context = {}
    
    # 실패한 노드 상태 리셋
    if from_node:
        await self._reset_nodes_from(db, execution_id, from_node)
    else:
        await self._reset_failed_nodes(db, execution_id)
    
    await db.commit()
    
    # 백그라운드 실행 재개
    await self._resume_execution(execution)
    
    return execution
```

---

## 4. 스키마 정의

**파일**: `backend/app/schemas/execution.py`

```python
class ExecutionRetryRequest(BaseModel):
    from_node: str | None = None
    reset_context: bool = False

class ExecutionRetryResponse(BaseModel):
    id: UUID
    status: str
    retry_count: int
    message: str

class ExecutionCancelResponse(BaseModel):
    id: UUID
    status: str
    message: str
```

---

## 5. 기술적 제약사항

### 5.1 제약사항

| 제약 | 설명 | 대응 방안 |
|------|------|-----------|
| 동시성 제어 | 동일 워크플로우 중복 실행 방지 | Redis 분산 락 사용 |
| 취소 지연 | 실행 중인 노드 즉시 중단 불가 | 노드 시작 전 상태 체크 패턴 |
| 트랜잭션 | 노드 실행 중 DB 트랜잭션 관리 | 노드별 독립 트랜잭션 |

### 5.2 의존성

| 라이브러리 | 버전 | 용도 |
|------------|------|------|
| FastAPI | >=0.115.0 | API 프레임워크 |
| SQLAlchemy | >=2.0.0 | ORM |
| asyncpg | >=0.30.0 | PostgreSQL 비동기 드라이버 |
| Redis | >=5.2.0 | 분산 락, 캐싱 |

---

## 6. 테스트 계획

### 6.1 단위 테스트

```python
# tests/unit/test_execution_service.py

async def test_cancel_running_execution():
    """running 상태 실행 취소 테스트"""
    pass

async def test_delete_completed_execution():
    """completed 상태 실행 삭제 테스트"""
    pass

async def test_retry_failed_execution():
    """failed 상태 실행 재시도 테스트"""
    pass

async def test_retry_non_failed_execution_raises_error():
    """failed 외 상태 재시도 시 에러 테스트"""
    pass
```

### 6.2 통합 테스트

```python
# tests/integration/test_execution_api.py

async def test_full_execution_lifecycle():
    """실행 생성 → 진행 → 완료 전체 플로우 테스트"""
    pass

async def test_execution_retry_flow():
    """실행 실패 → 재시도 → 완료 플로우 테스트"""
    pass
```

---

## 7. 롤아웃 계획

### 7.1 단계별 배포

| 단계 | 내용 | 검증 항목 |
|------|------|-----------|
| 1 | 개발 환경 배포 | 기능 테스트 |
| 2 | 스테이징 환경 배포 | 통합 테스트, 성능 테스트 |
| 3 | 프로덕션 배포 | 모니터링, 롤백 준비 |

### 7.2 롤백 계획

- 문제 발생 시 이전 버전으로 즉시 롤백
- 데이터베이스 마이그레이션은 backward compatible하게 설계

---

## 8. 성공 기준

| 기준 | 목표 |
|------|------|
| 기능 완성도 | 모든 엔드포인트 정상 동작 |
| 테스트 커버리지 | 80% 이상 |
| API 응답 시간 | P95 < 200ms |
| 에러율 | < 0.1% |
