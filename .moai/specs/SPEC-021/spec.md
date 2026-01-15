---
id: SPEC-021
version: "1.0.0"
status: "draft"
created: "2026-01-15"
updated: "2026-01-15"
author: "MoAI-ADK"
priority: "HIGH"
---

# SPEC-021: React Flow Canvas - ReactFlow 기반 워크플로우 편집기

## HISTORY

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 1.0.0 | 2026-01-15 | 초기 SPEC 작성 | MoAI-ADK |

---

## 1. 개요

### 1.1 목적

ReactFlow 라이브러리를 활용하여 시각적 워크플로우 편집기를 구현한다. 사용자는 드래그앤드롭으로 6가지 타입의 커스텀 노드를 캔버스에 배치하고, 노드 간 연결을 통해 DAG(Directed Acyclic Graph) 형태의 워크플로우를 설계할 수 있다.

### 1.2 범위

- ReactFlow 캔버스 컴포넌트 구현
- 6가지 커스텀 노드 타입 구현
- 드래그앤드롭 노드 생성 기능
- Zustand 기반 상태 관리
- 미니맵, 줌/팬 컨트롤

### 1.3 관련 문서

- `.moai/project/product.md` - 워크플로우 시각화 기능 정의
- `.moai/project/structure.md` - 프론트엔드 디렉토리 구조
- `.moai/project/tech.md` - ReactFlow, Zustand 기술 스택

---

## 2. 용어 정의

| 용어 | 정의 |
|------|------|
| **Node** | 워크플로우의 실행 단위. 도구, 에이전트, 조건 등을 나타낸다 |
| **Edge** | 노드 간의 연결선. 데이터 흐름 방향을 나타낸다 |
| **Handle** | 노드의 연결점. source(출력)와 target(입력)으로 구분된다 |
| **DAG** | Directed Acyclic Graph. 순환이 없는 방향 그래프 |
| **Palette** | 드래그앤드롭으로 노드를 생성할 수 있는 노드 목록 패널 |

---

## 3. 요구사항 (EARS 형식)

### 3.1 Ubiquitous Requirements (보편적 요구사항)

| ID | 요구사항 |
|----|----------|
| UBI-001 | 워크플로우 편집기는 ReactFlow 라이브러리(^11.10.0)를 사용해야 한다 |
| UBI-002 | 상태 관리는 Zustand(^5.0.0)를 사용해야 한다 |
| UBI-003 | 모든 노드는 고유한 UUID 식별자를 가져야 한다 |
| UBI-004 | 편집기는 다크 모드와 라이트 모드를 모두 지원해야 한다 |

### 3.2 Event-Driven Requirements (이벤트 기반 요구사항)

| ID | 트리거 | 요구사항 |
|----|--------|----------|
| EVT-001 | 사용자가 팔레트에서 노드를 드래그하여 캔버스에 드롭하면 | 해당 타입의 새 노드가 드롭 위치에 생성되어야 한다 |
| EVT-002 | 사용자가 노드의 source handle에서 다른 노드의 target handle로 드래그하면 | 두 노드 사이에 엣지가 생성되어야 한다 |
| EVT-003 | 사용자가 노드를 선택하면 | 노드 속성 패널이 표시되어야 한다 |
| EVT-004 | 사용자가 Delete 키를 누르면 | 선택된 노드/엣지가 삭제되어야 한다 |
| EVT-005 | 사용자가 캔버스를 더블클릭하면 | 노드 선택이 해제되어야 한다 |

### 3.3 State-Driven Requirements (상태 기반 요구사항)

| ID | 상태 조건 | 요구사항 |
|----|-----------|----------|
| STT-001 | 노드가 추가/수정/삭제되면 | Zustand 스토어의 nodes 배열이 즉시 업데이트되어야 한다 |
| STT-002 | 엣지가 추가/수정/삭제되면 | Zustand 스토어의 edges 배열이 즉시 업데이트되어야 한다 |
| STT-003 | 워크플로우가 10개 이상의 노드를 포함하면 | 미니맵이 자동으로 표시되어야 한다 |
| STT-004 | 노드가 선택된 상태이면 | 해당 노드에 선택 스타일(테두리 강조)이 적용되어야 한다 |

### 3.4 Unwanted Behavior Requirements (비정상 동작 방지 요구사항)

| ID | 비정상 상황 | 요구사항 |
|----|-------------|----------|
| UNW-001 | 순환 참조를 형성하는 연결 시도 시 | 연결을 거부하고 사용자에게 경고를 표시해야 한다 |
| UNW-002 | 동일한 노드 쌍 사이에 중복 연결 시도 시 | 연결을 거부해야 한다 |
| UNW-003 | 노드를 자기 자신에게 연결 시도 시 | 연결을 거부해야 한다 |
| UNW-004 | 호환되지 않는 노드 타입 간 연결 시도 시 | 연결을 거부해야 한다 (예: Trigger → Trigger) |

### 3.5 Complex Requirements (복합 요구사항)

| ID | 조건 | 요구사항 |
|----|------|----------|
| CMP-001 | 워크플로우 편집기가 로드되면 | 6가지 커스텀 노드 타입(trigger, tool, agent, condition, adapter, aggregator)이 등록되어야 한다 |
| CMP-002 | ConditionNode가 생성되면 | 기본 2개의 출력 핸들(true, false)이 포함되어야 하며, 사용자가 추가 분기를 정의할 수 있어야 한다 |
| CMP-003 | AggregatorNode가 생성되면 | 최소 2개의 입력 핸들이 포함되어야 하며, 사용자가 입력 개수를 조절할 수 있어야 한다 |

---

## 4. 커스텀 노드 타입 명세

### 4.1 TriggerNode

| 속성 | 값 |
|------|-----|
| **타입 ID** | `trigger` |
| **용도** | 워크플로우 시작점. 스케줄 또는 이벤트 트리거 |
| **입력 Handle** | 없음 |
| **출력 Handle** | 1개 (Position.Right) |
| **설정 가능 항목** | triggerType (schedule/event), cron expression, timezone |

### 4.2 ToolNode

| 속성 | 값 |
|------|-----|
| **타입 ID** | `tool` |
| **용도** | 코드로 정의된 도구 실행 |
| **입력 Handle** | 1개 (Position.Left) |
| **출력 Handle** | 1개 (Position.Right) |
| **설정 가능 항목** | toolId, config (JSON) |

### 4.3 AgentNode

| 속성 | 값 |
|------|-----|
| **타입 ID** | `agent` |
| **용도** | LLM 기반 에이전트 실행 |
| **입력 Handle** | 1개 (Position.Left) |
| **출력 Handle** | 1개 (Position.Right) |
| **설정 가능 항목** | agentId, model, systemPrompt (preview) |

### 4.4 ConditionNode

| 속성 | 값 |
|------|-----|
| **타입 ID** | `condition` |
| **용도** | 조건에 따른 분기 처리 |
| **입력 Handle** | 1개 (Position.Left) |
| **출력 Handle** | N개 (Position.Right, 동적) |
| **설정 가능 항목** | conditions 배열 (name, expression) |

### 4.5 AdapterNode

| 속성 | 값 |
|------|-----|
| **타입 ID** | `adapter` |
| **용도** | 데이터 형식 변환 |
| **입력 Handle** | 1개 (Position.Left) |
| **출력 Handle** | 1개 (Position.Right) |
| **설정 가능 항목** | inputType, outputType, mapping |

### 4.6 AggregatorNode

| 속성 | 값 |
|------|-----|
| **타입 ID** | `aggregator` |
| **용도** | 여러 입력의 결과 집계 |
| **입력 Handle** | N개 (Position.Left, 동적) |
| **출력 Handle** | 1개 (Position.Right) |
| **설정 가능 항목** | aggregationType (merge/concat/custom), sortBy, limit |

---

## 5. 기술적 제약사항

### 5.1 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `reactflow` | ^11.10.0 | 노드 기반 에디터 |
| `zustand` | ^5.0.0 | 상태 관리 |
| `uuid` | ^9.0.0 | 노드 ID 생성 |

### 5.2 브라우저 지원

- Chrome 90+
- Firefox 90+
- Safari 14+
- Edge 90+

### 5.3 성능 요구사항

| 항목 | 목표 |
|------|------|
| 최대 노드 수 | 100개 이상 지원 |
| 렌더링 FPS | 60fps 유지 |
| 초기 로드 시간 | 3초 이내 |

---

## 6. 비기능적 요구사항

### 6.1 접근성

- 키보드 네비게이션 지원
- ARIA 라벨 적용
- 고대비 모드 지원

### 6.2 반응형

- 최소 너비: 768px
- 터치 디바이스 기본 지원 (ReactFlow 내장)

---

## 7. 관련 SPEC

| SPEC ID | 관계 | 설명 |
|---------|------|------|
| SPEC-007 | 연동 | Workflow API 엔드포인트와 통신 |
| SPEC-003 | 연동 | Workflow 도메인 모델 구조 참조 |

---

## 8. 승인

| 역할 | 이름 | 날짜 | 서명 |
|------|------|------|------|
| 작성자 | MoAI-ADK | 2026-01-15 | - |
| 검토자 | - | - | - |
| 승인자 | - | - | - |
