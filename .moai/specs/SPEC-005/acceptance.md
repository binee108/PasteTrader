# SPEC-005 Acceptance Criteria: Execution Tracking Models

## Tags

`[SPEC-005]` `[ACCEPTANCE]` `[TESTING]`

---

## Overview

Execution Tracking Models의 완료 조건 및 테스트 시나리오를 정의합니다. WorkflowExecution, NodeExecution, ExecutionLog 모델의 기능 검증을 다룹니다.

---

## Acceptance Criteria

### AC-001: WorkflowExecution 모델 생성

**Given** 데이터베이스에 workflows 테이블이 존재하고
**When** WorkflowExecution 모델을 사용하여 새로운 실행 인스턴스를 생성하면
**Then** workflow_executions 테이블에 레코드가 저장되고 UUID id가 자동 생성된다

**Verification:**
```python
async def test_create_workflow_execution(db_session, test_workflow):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
        input_data={"market": "KOSPI", "threshold": 0.05},
        context={"variables": {}},
        metadata_={"triggered_by": "test_user"},
    )
    db_session.add(execution)
    await db_session.commit()

    assert execution.id is not None
    assert execution.status == ExecutionStatus.PENDING
    assert execution.created_at is not None
    assert execution.started_at is None
    assert execution.ended_at is None
```

---

### AC-002: NodeExecution 모델 생성

**Given** 데이터베이스에 workflow_executions 테이블과 nodes 테이블이 존재하고
**When** NodeExecution 모델을 사용하여 새로운 노드 실행을 생성하면
**Then** node_executions 테이블에 레코드가 저장되고 UUID id가 자동 생성된다

**Verification:**
```python
async def test_create_node_execution(db_session, test_workflow_execution, test_node):
    node_execution = NodeExecution(
        workflow_execution_id=test_workflow_execution.id,
        node_id=test_node.id,
        execution_order=1,
        input_data={"query": "SELECT * FROM stocks"},
    )
    db_session.add(node_execution)
    await db_session.commit()

    assert node_execution.id is not None
    assert node_execution.status == ExecutionStatus.PENDING
    assert node_execution.retry_count == 0
    assert node_execution.execution_order == 1
```

---

### AC-003: ExecutionLog 모델 생성

**Given** 데이터베이스에 workflow_executions 테이블이 존재하고
**When** ExecutionLog 모델을 사용하여 로그를 생성하면
**Then** execution_logs 테이블에 레코드가 저장된다

**Verification:**
```python
async def test_create_execution_log(db_session, test_workflow_execution):
    log = ExecutionLog(
        workflow_execution_id=test_workflow_execution.id,
        level=LogLevel.INFO,
        message="Workflow execution started",
        data={"step": "initialization"},
    )
    db_session.add(log)
    await db_session.commit()

    assert log.id is not None
    assert log.timestamp is not None
    assert log.level == LogLevel.INFO
```

---

### AC-004: WorkflowExecution-NodeExecution 관계

**Given** WorkflowExecution과 NodeExecution이 존재할 때
**When** WorkflowExecution의 node_executions를 조회하면
**Then** 해당 실행의 모든 NodeExecution 목록을 가져올 수 있다

**Verification:**
```python
async def test_workflow_execution_node_execution_relationship(
    db_session, test_workflow_execution, test_nodes
):
    # Create multiple node executions
    for idx, node in enumerate(test_nodes):
        node_execution = NodeExecution(
            workflow_execution_id=test_workflow_execution.id,
            node_id=node.id,
            execution_order=idx + 1,
        )
        db_session.add(node_execution)
    await db_session.commit()

    # Refresh to load relationships
    await db_session.refresh(test_workflow_execution)

    assert len(test_workflow_execution.node_executions) == len(test_nodes)
    # Verify ordering
    orders = [ne.execution_order for ne in test_workflow_execution.node_executions]
    assert orders == sorted(orders)
```

---

### AC-005: WorkflowExecution-ExecutionLog 관계

**Given** WorkflowExecution과 ExecutionLog가 존재할 때
**When** WorkflowExecution의 logs를 조회하면
**Then** 해당 실행의 모든 로그를 시간순으로 가져올 수 있다

**Verification:**
```python
async def test_workflow_execution_logs_relationship(db_session, test_workflow_execution):
    # Create multiple logs
    for i in range(5):
        log = ExecutionLog(
            workflow_execution_id=test_workflow_execution.id,
            level=LogLevel.INFO,
            message=f"Log message {i}",
        )
        db_session.add(log)
        await asyncio.sleep(0.01)  # Small delay for timestamp ordering
    await db_session.commit()

    await db_session.refresh(test_workflow_execution)

    assert len(test_workflow_execution.logs) == 5
    # Verify timestamp ordering
    timestamps = [log.timestamp for log in test_workflow_execution.logs]
    assert timestamps == sorted(timestamps)
```

---

### AC-006: NodeExecution-ExecutionLog 관계

**Given** NodeExecution과 ExecutionLog가 존재할 때
**When** NodeExecution의 logs를 조회하면
**Then** 해당 노드 실행의 로그만 가져올 수 있다

**Verification:**
```python
async def test_node_execution_logs_relationship(
    db_session, test_workflow_execution, test_node
):
    node_execution = NodeExecution(
        workflow_execution_id=test_workflow_execution.id,
        node_id=test_node.id,
        execution_order=1,
    )
    db_session.add(node_execution)
    await db_session.commit()

    # Create node-level log
    node_log = ExecutionLog(
        workflow_execution_id=test_workflow_execution.id,
        node_execution_id=node_execution.id,
        level=LogLevel.DEBUG,
        message="Node processing started",
    )
    db_session.add(node_log)

    # Create workflow-level log (no node_execution_id)
    workflow_log = ExecutionLog(
        workflow_execution_id=test_workflow_execution.id,
        level=LogLevel.INFO,
        message="Workflow level log",
    )
    db_session.add(workflow_log)
    await db_session.commit()

    await db_session.refresh(node_execution)

    assert len(node_execution.logs) == 1
    assert node_execution.logs[0].message == "Node processing started"
```

---

### AC-007: CASCADE 삭제 - WorkflowExecution 삭제 시 NodeExecution 삭제

**Given** WorkflowExecution과 연결된 NodeExecution이 존재할 때
**When** WorkflowExecution을 삭제하면
**Then** 연결된 모든 NodeExecution이 자동으로 삭제된다

**Verification:**
```python
async def test_cascade_delete_node_executions(db_session, test_workflow, test_nodes):
    # Create workflow execution
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
    )
    db_session.add(execution)
    await db_session.commit()

    execution_id = execution.id

    # Create node executions
    for idx, node in enumerate(test_nodes):
        node_execution = NodeExecution(
            workflow_execution_id=execution_id,
            node_id=node.id,
            execution_order=idx + 1,
        )
        db_session.add(node_execution)
    await db_session.commit()

    # Delete workflow execution
    await db_session.delete(execution)
    await db_session.commit()

    # Verify node executions are deleted
    result = await db_session.execute(
        select(NodeExecution).where(NodeExecution.workflow_execution_id == execution_id)
    )
    assert result.scalars().all() == []
```

---

### AC-008: CASCADE 삭제 - WorkflowExecution 삭제 시 ExecutionLog 삭제

**Given** WorkflowExecution과 연결된 ExecutionLog가 존재할 때
**When** WorkflowExecution을 삭제하면
**Then** 연결된 모든 ExecutionLog가 자동으로 삭제된다

**Verification:**
```python
async def test_cascade_delete_execution_logs(db_session, test_workflow):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
    )
    db_session.add(execution)
    await db_session.commit()

    execution_id = execution.id

    # Create logs
    for i in range(3):
        log = ExecutionLog(
            workflow_execution_id=execution_id,
            level=LogLevel.INFO,
            message=f"Log {i}",
        )
        db_session.add(log)
    await db_session.commit()

    # Delete workflow execution
    await db_session.delete(execution)
    await db_session.commit()

    # Verify logs are deleted
    result = await db_session.execute(
        select(ExecutionLog).where(ExecutionLog.workflow_execution_id == execution_id)
    )
    assert result.scalars().all() == []
```

---

### AC-009: 실행 상태 전이 - Pending to Running

**Given** WorkflowExecution이 PENDING 상태일 때
**When** start() 메서드를 호출하면
**Then** 상태가 RUNNING으로 변경되고 started_at이 설정된다

**Verification:**
```python
async def test_execution_state_pending_to_running(db_session, test_workflow):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
    )
    db_session.add(execution)
    await db_session.commit()

    assert execution.status == ExecutionStatus.PENDING
    assert execution.started_at is None

    execution.start()
    await db_session.commit()

    assert execution.status == ExecutionStatus.RUNNING
    assert execution.started_at is not None
```

---

### AC-010: 실행 상태 전이 - Running to Completed

**Given** WorkflowExecution이 RUNNING 상태일 때
**When** complete() 메서드를 호출하면
**Then** 상태가 COMPLETED로 변경되고 ended_at이 설정된다

**Verification:**
```python
async def test_execution_state_running_to_completed(db_session, test_workflow):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
    )
    db_session.add(execution)
    await db_session.commit()

    execution.start()
    await db_session.commit()

    assert execution.status == ExecutionStatus.RUNNING

    output_data = {"result": "success", "processed": 100}
    execution.complete(output_data=output_data)
    await db_session.commit()

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.ended_at is not None
    assert execution.output_data == output_data
```

---

### AC-011: 실행 상태 전이 - Running to Failed

**Given** WorkflowExecution이 RUNNING 상태일 때
**When** fail() 메서드를 호출하면
**Then** 상태가 FAILED로 변경되고 error_message가 설정된다

**Verification:**
```python
async def test_execution_state_running_to_failed(db_session, test_workflow):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
    )
    db_session.add(execution)
    await db_session.commit()

    execution.start()
    await db_session.commit()

    error_msg = "Connection timeout to external API"
    execution.fail(error_message=error_msg)
    await db_session.commit()

    assert execution.status == ExecutionStatus.FAILED
    assert execution.ended_at is not None
    assert execution.error_message == error_msg
```

---

### AC-012: 실행 상태 전이 - Cancel 실행

**Given** WorkflowExecution이 PENDING 또는 RUNNING 상태일 때
**When** cancel() 메서드를 호출하면
**Then** 상태가 CANCELLED로 변경된다

**Verification:**
```python
@pytest.mark.parametrize("initial_status", [
    ExecutionStatus.PENDING,
    ExecutionStatus.RUNNING,
])
async def test_execution_cancel(db_session, test_workflow, initial_status):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
    )
    db_session.add(execution)
    await db_session.commit()

    if initial_status == ExecutionStatus.RUNNING:
        execution.start()
        await db_session.commit()

    execution.cancel()
    await db_session.commit()

    assert execution.status == ExecutionStatus.CANCELLED
    assert execution.ended_at is not None
```

---

### AC-013: 잘못된 상태 전이 방지

**Given** WorkflowExecution이 COMPLETED 상태일 때
**When** start() 메서드를 호출하면
**Then** ValueError가 발생한다

**Verification:**
```python
async def test_invalid_state_transition(db_session, test_workflow):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
    )
    db_session.add(execution)
    await db_session.commit()

    execution.start()
    execution.complete()
    await db_session.commit()

    with pytest.raises(ValueError, match="Cannot start execution"):
        execution.start()
```

---

### AC-014: 실행 시간 계산

**Given** WorkflowExecution이 완료되었을 때
**When** duration_seconds 속성을 조회하면
**Then** 실행 시간이 초 단위로 반환된다

**Verification:**
```python
async def test_execution_duration(db_session, test_workflow):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
    )
    db_session.add(execution)
    await db_session.commit()

    execution.start()
    await asyncio.sleep(0.5)  # Simulate work
    execution.complete()
    await db_session.commit()

    assert execution.duration_seconds is not None
    assert execution.duration_seconds >= 0.5
```

---

### AC-015: NodeExecution 재시도 가능 여부 확인

**Given** NodeExecution이 FAILED 상태이고 retry_count가 max_retries 미만일 때
**When** can_retry 속성을 조회하면
**Then** True가 반환된다

**Verification:**
```python
async def test_node_execution_can_retry(db_session, test_workflow_execution, test_node):
    # Set node retry config
    test_node.retry_config = {"max_retries": 3, "delay": 1}
    await db_session.commit()

    node_execution = NodeExecution(
        workflow_execution_id=test_workflow_execution.id,
        node_id=test_node.id,
        execution_order=1,
        status=ExecutionStatus.FAILED,
        retry_count=1,
    )
    db_session.add(node_execution)
    await db_session.commit()

    await db_session.refresh(node_execution, ["node"])

    assert node_execution.can_retry is True

    # After max retries
    node_execution.retry_count = 3
    await db_session.commit()

    assert node_execution.can_retry is False
```

---

### AC-016: Workflow-WorkflowExecution 관계

**Given** Workflow와 WorkflowExecution이 존재할 때
**When** Workflow의 executions를 조회하면
**Then** 해당 워크플로우의 모든 실행 목록을 가져올 수 있다

**Verification:**
```python
async def test_workflow_executions_relationship(db_session, test_workflow):
    # Create multiple executions
    for trigger in [TriggerType.MANUAL, TriggerType.SCHEDULE, TriggerType.EVENT]:
        execution = WorkflowExecution(
            workflow_id=test_workflow.id,
            trigger_type=trigger,
        )
        db_session.add(execution)
    await db_session.commit()

    await db_session.refresh(test_workflow)

    assert len(test_workflow.executions) == 3
    trigger_types = {e.trigger_type for e in test_workflow.executions}
    assert trigger_types == {TriggerType.MANUAL, TriggerType.SCHEDULE, TriggerType.EVENT}
```

---

### AC-017: LogLevel Enum 검증

**Given** LogLevel enum이 정의되어 있을 때
**When** 각 로그 레벨 값을 사용하면
**Then** debug, info, warning, error가 지원된다

**Verification:**
```python
def test_log_level_enum():
    assert LogLevel.DEBUG.value == "debug"
    assert LogLevel.INFO.value == "info"
    assert LogLevel.WARNING.value == "warning"
    assert LogLevel.ERROR.value == "error"
```

---

### AC-018: TriggerType 검증

**Given** WorkflowExecution에 trigger_type 필드가 존재할 때
**When** 각 트리거 타입을 사용하면
**Then** schedule, event, manual이 지원된다

**Verification:**
```python
@pytest.mark.parametrize("trigger_type", [
    TriggerType.SCHEDULE,
    TriggerType.EVENT,
    TriggerType.MANUAL,
])
async def test_trigger_types(db_session, test_workflow, trigger_type):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=trigger_type,
    )
    db_session.add(execution)
    await db_session.commit()

    assert execution.trigger_type == trigger_type
```

---

### AC-019: JSONB Context 저장 및 조회

**Given** WorkflowExecution에 context JSONB 필드가 존재할 때
**When** 복잡한 컨텍스트 객체를 저장하면
**Then** 컨텍스트가 올바르게 저장되고 조회된다

**Verification:**
```python
async def test_jsonb_context_storage(db_session, test_workflow):
    context = {
        "variables": {
            "market": "KOSPI",
            "symbols": ["005930", "000660"],
        },
        "secrets": {
            "api_key": "encrypted_key_here",
        },
        "environment": {
            "mode": "production",
        },
        "retry_info": {
            "attempt": 1,
            "max_attempts": 3,
        },
    }

    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
        context=context,
    )
    db_session.add(execution)
    await db_session.commit()

    await db_session.refresh(execution)

    assert execution.context["variables"]["market"] == "KOSPI"
    assert len(execution.context["variables"]["symbols"]) == 2
    assert execution.context["retry_info"]["max_attempts"] == 3
```

---

### AC-020: Timestamp 자동 관리

**Given** WorkflowExecution이 생성/수정될 때
**When** 레코드가 저장되면
**Then** created_at과 updated_at이 자동으로 설정된다

**Verification:**
```python
async def test_timestamp_management(db_session, test_workflow):
    execution = WorkflowExecution(
        workflow_id=test_workflow.id,
        trigger_type=TriggerType.MANUAL,
    )
    db_session.add(execution)
    await db_session.commit()

    created = execution.created_at
    updated = execution.updated_at

    # Update the execution
    await asyncio.sleep(0.1)
    execution.start()
    await db_session.commit()
    await db_session.refresh(execution)

    assert execution.created_at == created
    assert execution.updated_at > updated
```

---

## Quality Gate Criteria

### Test Coverage

| Component | Required Coverage |
|-----------|------------------|
| WorkflowExecution Model | >= 90% |
| NodeExecution Model | >= 90% |
| ExecutionLog Model | >= 85% |
| State Transitions | 100% |
| LogLevel Enum | 100% |

### Code Quality

- [ ] ruff lint 통과
- [ ] mypy type check 통과
- [ ] 모든 public 메서드 docstring 작성
- [ ] 테스트 코드 작성 완료

### Performance Checklist

- [ ] 워크플로우 실행 목록 조회 500ms 이내
- [ ] 단일 실행 노드 목록 조회 200ms 이내
- [ ] 로그 조회 (최근 1000건) 300ms 이내
- [ ] 인덱스 적용 확인

### Migration Verification

- [ ] Alembic upgrade 성공
- [ ] Alembic downgrade 성공
- [ ] 기존 데이터 무결성 유지

---

## Definition of Done

1. **모델 구현 완료**
   - WorkflowExecution 모델 파일 생성
   - NodeExecution 모델 파일 생성
   - ExecutionLog 모델 파일 생성
   - LogLevel enum 추가
   - Workflow 모델 관계 업데이트

2. **마이그레이션 완료**
   - Alembic 마이그레이션 스크립트 생성
   - 테스트 환경에서 마이그레이션 검증

3. **테스트 완료**
   - 모든 AC 테스트 통과
   - 커버리지 목표 달성
   - 상태 전이 테스트 100% 커버리지

4. **코드 품질 검증**
   - Lint 통과
   - Type check 통과
   - 문서화 완료

5. **리뷰 완료**
   - PR 생성 및 코드 리뷰
   - 성능 검토 완료

---

## Related Documents

- [spec.md](spec.md) - 상세 요구사항
- [plan.md](plan.md) - 구현 계획
- [SPEC-003/spec.md](../SPEC-003/spec.md) - Workflow Domain Models
- [SPEC-001/acceptance.md](../SPEC-001/acceptance.md) - Database Foundation 인수 조건

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-12 | workflow-spec | 최초 인수 조건 작성 |
