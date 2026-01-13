# SPEC-003: Acceptance Criteria

## Tags

`[SPEC-003]` `[WORKFLOW]` `[NODE]` `[EDGE]` `[DAG]` `[BACKEND]`

---

## Acceptance Criteria Overview

이 문서는 Workflow Domain Models 구현을 위한 인수 조건을 Given-When-Then (Gherkin) 형식으로 정의합니다.

---

## Feature: Workflow 모델

### AC-001: Workflow 생성

```gherkin
Feature: Workflow 모델 생성

  Scenario: 유효한 데이터로 Workflow 생성
    Given 유효한 owner_id와 name이 제공됨
    When 새 Workflow 객체가 생성됨
    Then id는 자동으로 UUID가 생성되어야 함
    And owner_id는 지정된 값이어야 함
    And name은 지정된 값이어야 함
    And config는 빈 딕셔너리여야 함
    And variables는 빈 딕셔너리여야 함
    And is_active는 True여야 함
    And version은 1이어야 함
    And created_at은 현재 시각이어야 함
    And updated_at은 현재 시각이어야 함
    And deleted_at은 None이어야 함

  Scenario: Workflow에 JSONB config 저장
    Given Workflow 객체가 존재함
    When config에 복잡한 JSON 구조가 저장됨
    Then config는 원본 구조를 그대로 유지해야 함
    And JSONB 쿼리로 내부 필드 접근이 가능해야 함

  Scenario: Workflow 비활성화
    Given is_active가 True인 Workflow가 존재함
    When is_active를 False로 변경함
    Then 변경이 데이터베이스에 저장되어야 함
    And updated_at이 갱신되어야 함
```

### AC-002: Workflow 낙관적 잠금

```gherkin
Feature: Workflow 낙관적 잠금

  Scenario: Workflow 업데이트 시 version 증가
    Given version이 1인 Workflow가 존재함
    When Workflow의 name을 변경하고 저장함
    Then version이 2로 증가해야 함

  Scenario: 동시 편집 충돌 감지
    Given version이 1인 Workflow가 존재함
    And 두 세션에서 동일 Workflow를 조회함
    When 첫 번째 세션이 먼저 업데이트를 수행함
    And 두 번째 세션이 업데이트를 시도함
    Then 두 번째 세션은 StaleDataError를 발생시켜야 함
```

### AC-003: Workflow Soft Delete

```gherkin
Feature: Workflow Soft Delete

  Scenario: Workflow soft delete 수행
    Given 활성 상태의 Workflow가 존재함
    When soft_delete() 메서드가 호출됨
    Then deleted_at이 현재 시각으로 설정되어야 함
    And is_deleted 속성이 True를 반환해야 함

  Scenario: 기본 쿼리에서 삭제된 Workflow 제외
    Given soft delete된 Workflow가 존재함
    When 표준 쿼리로 Workflow 목록을 조회함
    Then 삭제된 Workflow는 결과에 포함되지 않아야 함

  Scenario: 삭제된 Workflow 복원
    Given soft delete된 Workflow가 존재함
    When restore() 메서드가 호출됨
    Then deleted_at이 None으로 설정되어야 함
    And is_deleted 속성이 False를 반환해야 함
```

---

## Feature: Node 모델

### AC-004: Node 생성

```gherkin
Feature: Node 모델 생성

  Scenario: 유효한 데이터로 Node 생성
    Given 유효한 workflow_id, name, node_type이 제공됨
    When 새 Node 객체가 생성됨
    Then id는 자동으로 UUID가 생성되어야 함
    And workflow_id는 지정된 값이어야 함
    And node_type은 지정된 NodeType enum 값이어야 함
    And position_x는 0.0이어야 함
    And position_y는 0.0이어야 함
    And timeout_seconds는 300이어야 함
    And retry_config는 기본값 {"max_retries": 3, "delay": 1}이어야 함

  Scenario Outline: 6가지 Node 타입 생성
    Given workflow_id가 유효함
    When node_type이 <node_type>인 Node가 생성됨
    Then Node가 정상적으로 생성되어야 함
    And node_type이 <node_type>으로 저장되어야 함

    Examples:
      | node_type   |
      | trigger     |
      | tool        |
      | agent       |
      | condition   |
      | adapter     |
      | aggregator  |

  Scenario: Tool 타입 Node에 tool_id 설정
    Given tool_id가 유효한 UUID임
    When node_type이 tool인 Node가 생성됨
    And tool_id가 설정됨
    Then Node가 정상적으로 생성되어야 함
    And tool_id가 지정된 값이어야 함

  Scenario: Agent 타입 Node에 agent_id 설정
    Given agent_id가 유효한 UUID임
    When node_type이 agent인 Node가 생성됨
    And agent_id가 설정됨
    Then Node가 정상적으로 생성되어야 함
    And agent_id가 지정된 값이어야 함
```

### AC-005: Node 위치 저장

```gherkin
Feature: Node 위치 저장

  Scenario: Node 위치 업데이트
    Given position_x=0, position_y=0인 Node가 존재함
    When position_x=100.5, position_y=200.75로 변경됨
    Then 변경이 데이터베이스에 저장되어야 함
    And position_x가 100.5여야 함
    And position_y가 200.75여야 함

  Scenario: 음수 좌표 허용
    Given Node가 존재함
    When position_x=-50.0, position_y=-100.0으로 설정됨
    Then 변경이 정상적으로 저장되어야 함
```

### AC-006: Node CASCADE 삭제

```gherkin
Feature: Node CASCADE 삭제

  Scenario: Workflow 삭제 시 Node도 삭제
    Given Workflow에 3개의 Node가 존재함
    When Workflow가 데이터베이스에서 삭제됨
    Then 해당 Workflow의 모든 Node도 삭제되어야 함

  Scenario: Node 삭제 시 관련 Edge도 삭제
    Given Node A와 Node B가 Edge로 연결되어 있음
    When Node A가 삭제됨
    Then Node A를 source로 하는 모든 Edge가 삭제되어야 함
```

---

## Feature: Edge 모델

### AC-007: Edge 생성

```gherkin
Feature: Edge 모델 생성

  Scenario: 유효한 데이터로 Edge 생성
    Given 동일 Workflow 내에 source_node와 target_node가 존재함
    When 새 Edge 객체가 생성됨
    Then id는 자동으로 UUID가 생성되어야 함
    And workflow_id는 지정된 값이어야 함
    And source_node_id는 source_node의 id여야 함
    And target_node_id는 target_node의 id여야 함
    And priority는 0이어야 함
    And created_at은 현재 시각이어야 함

  Scenario: Edge에 condition 설정
    Given Edge가 존재함
    When condition에 JSON 조건식이 설정됨
    Then condition이 정상적으로 저장되어야 함
    And JSONB 쿼리로 조건 내용 접근이 가능해야 함

  Scenario: Edge에 handle 설정
    Given source_node가 다중 출력을 지원함
    When source_handle="output_a", target_handle="input_1"로 Edge 생성
    Then Edge가 정상적으로 생성되어야 함
    And handle 값이 저장되어야 함
```

### AC-008: Edge 유일성 제약

```gherkin
Feature: Edge 유일성 제약

  Scenario: 동일 연결 중복 생성 방지
    Given source_node A에서 target_node B로의 Edge가 존재함
    When 동일한 source_node A에서 target_node B로 Edge 생성 시도
    Then IntegrityError가 발생해야 함

  Scenario: handle이 다르면 동일 노드 쌍 허용
    Given source_node A에서 target_node B로 source_handle="out1" Edge 존재
    When source_handle="out2"로 A에서 B로 새 Edge 생성
    Then Edge가 정상적으로 생성되어야 함

  Scenario: NULL handle 처리
    Given source_node A에서 target_node B로 handle이 NULL인 Edge 존재
    When handle이 NULL인 동일 연결 생성 시도
    Then IntegrityError가 발생해야 함
```

### AC-009: Edge 자기 참조 방지

```gherkin
Feature: Edge 자기 참조 방지

  Scenario: 자기 참조 Edge 생성 방지
    Given Node A가 존재함
    When source_node_id와 target_node_id가 동일한 Edge 생성 시도
    Then CheckConstraint 위반 에러가 발생해야 함
```

### AC-010: Edge CASCADE 삭제

```gherkin
Feature: Edge CASCADE 삭제

  Scenario: Workflow 삭제 시 Edge도 삭제
    Given Workflow에 5개의 Edge가 존재함
    When Workflow가 데이터베이스에서 삭제됨
    Then 해당 Workflow의 모든 Edge도 삭제되어야 함

  Scenario: Node 삭제 시 연결된 Edge 삭제
    Given Node가 source로 2개, target으로 1개 Edge에 연결됨
    When 해당 Node가 삭제됨
    Then Node가 source인 2개 Edge가 삭제되어야 함
    And Node가 target인 1개 Edge가 삭제되어야 함
```

---

## Feature: Relationship 동작

### AC-011: Workflow-Node Relationship

```gherkin
Feature: Workflow-Node Relationship

  Scenario: Workflow에서 nodes 접근
    Given Workflow에 3개의 Node가 존재함
    When workflow.nodes를 접근함
    Then 3개의 Node 객체 리스트가 반환되어야 함

  Scenario: Node에서 workflow 접근
    Given Node가 Workflow에 속해 있음
    When node.workflow를 접근함
    Then 해당 Workflow 객체가 반환되어야 함

  Scenario: Workflow에 Node 추가
    Given 빈 Workflow가 존재함
    When workflow.nodes.append(new_node)로 Node 추가
    And 세션이 커밋됨
    Then Node가 데이터베이스에 저장되어야 함
    And node.workflow_id가 workflow.id와 일치해야 함
```

### AC-012: Workflow-Edge Relationship

```gherkin
Feature: Workflow-Edge Relationship

  Scenario: Workflow에서 edges 접근
    Given Workflow에 2개의 Edge가 존재함
    When workflow.edges를 접근함
    Then 2개의 Edge 객체 리스트가 반환되어야 함

  Scenario: Edge에서 source_node, target_node 접근
    Given Edge가 Node A에서 Node B로 연결됨
    When edge.source_node와 edge.target_node를 접근함
    Then source_node는 Node A여야 함
    And target_node는 Node B여야 함
```

---

## Feature: 인덱스 및 성능

### AC-013: 인덱스 동작 확인

```gherkin
Feature: 인덱스 동작

  Scenario: owner_id로 Workflow 조회 성능
    Given 100개의 Workflow가 여러 owner에게 분산됨
    When 특정 owner_id로 Workflow 목록 조회
    Then 쿼리가 idx_workflows_owner 인덱스를 사용해야 함
    And 조회 시간이 100ms 미만이어야 함

  Scenario: workflow_id로 Node 조회 성능
    Given 50개 Node가 있는 Workflow가 존재함
    When workflow_id로 Node 목록 조회
    Then 쿼리가 idx_nodes_workflow 인덱스를 사용해야 함
    And 조회 시간이 50ms 미만이어야 함
```

---

## Quality Gate Criteria

### Code Quality

| Criterion | Requirement |
|-----------|-------------|
| Test Coverage | >= 85% line coverage |
| Linting | Zero ruff errors |
| Type Hints | Complete type annotations |
| Documentation | All public classes/methods documented |

### Functional Requirements

| Requirement | Verification Method |
|-------------|---------------------|
| REQ-001: Workflow 모델 | AC-001, AC-002, AC-003 |
| REQ-002: Node 모델 | AC-004, AC-005, AC-006 |
| REQ-003: Edge 모델 | AC-007, AC-010 |
| REQ-004: Workflow-Node 관계 | AC-006, AC-011 |
| REQ-005: Node-Edge 관계 | AC-006, AC-010 |
| REQ-006: 낙관적 잠금 | AC-002 |
| REQ-007: Edge 유일성 | AC-008 |
| REQ-008: Node 타입별 필수 필드 | AC-004 |
| REQ-009: 자기 참조 방지 | AC-009 |

### Performance Requirements

| Metric | Target |
|--------|--------|
| Workflow 생성 | < 50ms |
| Node 생성 (단일) | < 20ms |
| Edge 생성 (단일) | < 20ms |
| Workflow + 50 Nodes 조회 | < 200ms |
| 100 Workflow 목록 조회 | < 100ms |

---

## Test Scenarios

### Unit Tests

```python
# tests/unit/test_models/test_workflow.py

class TestWorkflow:
    def test_workflow_creation(self): ...
    def test_workflow_defaults(self): ...
    def test_workflow_config_jsonb(self): ...
    def test_workflow_variables_jsonb(self): ...
    def test_workflow_version_default(self): ...

class TestWorkflowSoftDelete:
    def test_soft_delete(self): ...
    def test_is_deleted_property(self): ...
    def test_restore(self): ...

class TestNode:
    def test_node_creation(self): ...
    def test_node_defaults(self): ...
    def test_node_type_trigger(self): ...
    def test_node_type_tool(self): ...
    def test_node_type_agent(self): ...
    def test_node_type_condition(self): ...
    def test_node_type_adapter(self): ...
    def test_node_type_aggregator(self): ...
    def test_node_position(self): ...
    def test_node_retry_config_default(self): ...

class TestEdge:
    def test_edge_creation(self): ...
    def test_edge_defaults(self): ...
    def test_edge_condition_jsonb(self): ...
    def test_edge_handle_fields(self): ...
```

### Integration Tests

```python
# tests/integration/test_models/test_workflow_integration.py

class TestWorkflowRelationships:
    async def test_workflow_nodes_relationship(self): ...
    async def test_workflow_edges_relationship(self): ...
    async def test_cascade_delete_workflow(self): ...

class TestNodeRelationships:
    async def test_node_workflow_relationship(self): ...
    async def test_cascade_delete_node_edges(self): ...

class TestEdgeConstraints:
    async def test_unique_edge_constraint(self): ...
    async def test_self_loop_prevention(self): ...
    async def test_edge_with_handles(self): ...

class TestOptimisticLocking:
    async def test_version_increment_on_update(self): ...
    async def test_concurrent_edit_conflict(self): ...

class TestComplexWorkflow:
    async def test_create_dag_workflow(self): ...
    async def test_workflow_with_50_nodes(self): ...
    async def test_workflow_with_parallel_branches(self): ...
```

---

## Verification Methods

| Method | Tool | Description |
|--------|------|-------------|
| Unit Testing | pytest | 개별 모델 테스트 |
| Integration Testing | pytest-asyncio | 관계 및 제약 조건 테스트 |
| Coverage Analysis | pytest-cov | 라인 커버리지 측정 |
| Linting | ruff | 코드 스타일 및 품질 |
| Type Checking | mypy | 정적 타입 분석 |
| Performance Testing | pytest-benchmark | 쿼리 성능 측정 |

---

## Definition of Done Checklist

- [ ] 모든 인수 조건 시나리오 통과
- [ ] 단위 테스트 커버리지 >= 85%
- [ ] 통합 테스트 통과
- [ ] ruff 린팅 에러 없음
- [ ] mypy 타입 체크 통과
- [ ] 모든 public API 문서화 완료
- [ ] Alembic 마이그레이션 성공 (upgrade/downgrade)
- [ ] 성능 요구사항 충족
- [ ] 코드 리뷰 승인
- [ ] 보안 취약점 없음
