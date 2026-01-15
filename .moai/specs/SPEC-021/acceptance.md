# SPEC-021 인수 테스트 시나리오

## 1. 개요

| 항목 | 값 |
|------|-----|
| **SPEC ID** | SPEC-021 |
| **제목** | React Flow Canvas - ReactFlow 기반 워크플로우 편집기 |
| **작성일** | 2026-01-15 |

---

## 2. 테스트 시나리오

### 2.1 노드 생성 (드래그앤드롭)

#### TC-001: 팔레트에서 ToolNode 드래그앤드롭

```gherkin
Given 사용자가 워크플로우 편집기 페이지에 있다
  And 노드 팔레트가 화면 좌측에 표시되어 있다
When 사용자가 "Tool" 노드를 팔레트에서 드래그한다
  And 캔버스의 빈 영역에 드롭한다
Then 드롭 위치에 ToolNode가 생성된다
  And Zustand 스토어의 nodes 배열에 새 노드가 추가된다
  And 노드는 고유한 UUID를 가진다
```

#### TC-002: 6가지 노드 타입 모두 생성 가능

```gherkin
Given 사용자가 워크플로우 편집기 페이지에 있다
When 사용자가 각 노드 타입(trigger, tool, agent, condition, adapter, aggregator)을 차례로 드래그앤드롭한다
Then 6개의 노드가 캔버스에 표시된다
  And 각 노드는 해당 타입에 맞는 UI(색상, 핸들 개수)를 가진다
```

---

### 2.2 노드 연결 (엣지 생성)

#### TC-003: 두 노드 연결

```gherkin
Given 캔버스에 TriggerNode와 ToolNode가 있다
When 사용자가 TriggerNode의 출력 핸들을 클릭하고
  And ToolNode의 입력 핸들로 드래그한다
Then 두 노드 사이에 엣지가 생성된다
  And Zustand 스토어의 edges 배열에 새 엣지가 추가된다
  And 엣지는 화살표로 방향을 표시한다
```

#### TC-004: 순환 참조 방지

```gherkin
Given 캔버스에 NodeA → NodeB → NodeC 연결이 있다
When 사용자가 NodeC의 출력 핸들에서 NodeA의 입력 핸들로 연결을 시도한다
Then 연결이 거부된다
  And "순환 참조는 허용되지 않습니다" 경고 메시지가 표시된다
  And edges 배열에 새 엣지가 추가되지 않는다
```

#### TC-005: 자기 자신 연결 방지

```gherkin
Given 캔버스에 ToolNode가 있다
When 사용자가 ToolNode의 출력 핸들에서 같은 ToolNode의 입력 핸들로 연결을 시도한다
Then 연결이 거부된다
  And edges 배열에 새 엣지가 추가되지 않는다
```

#### TC-006: 중복 연결 방지

```gherkin
Given 캔버스에 NodeA → NodeB 연결이 이미 존재한다
When 사용자가 NodeA에서 NodeB로 다시 연결을 시도한다
Then 연결이 거부된다
  And 기존 엣지는 유지된다
```

---

### 2.3 노드 선택 및 삭제

#### TC-007: 노드 선택

```gherkin
Given 캔버스에 여러 노드가 있다
When 사용자가 특정 노드를 클릭한다
Then 해당 노드에 선택 스타일(파란색 테두리)이 적용된다
  And Zustand 스토어의 selectedNodeId가 업데이트된다
```

#### TC-008: 노드 삭제 (Delete 키)

```gherkin
Given 캔버스에서 ToolNode가 선택되어 있다
  And 해당 노드에 연결된 엣지가 2개 있다
When 사용자가 Delete 키를 누른다
Then 선택된 노드가 캔버스에서 제거된다
  And 연결된 2개의 엣지도 함께 제거된다
  And Zustand 스토어의 nodes, edges 배열이 업데이트된다
```

#### TC-009: 엣지 삭제

```gherkin
Given 캔버스에 NodeA → NodeB 엣지가 있다
When 사용자가 해당 엣지를 클릭하여 선택한다
  And Delete 키를 누른다
Then 선택된 엣지가 제거된다
  And NodeA와 NodeB는 그대로 유지된다
```

---

### 2.4 커스텀 노드 동작

#### TC-010: ConditionNode 다중 출력

```gherkin
Given 캔버스에 ConditionNode가 있다
  And 기본으로 "true", "false" 2개의 출력 핸들이 있다
When 사용자가 노드 속성 패널에서 "분기 추가" 버튼을 클릭한다
  And 새 분기 이름을 "custom"으로 입력한다
Then ConditionNode에 3개의 출력 핸들이 표시된다
  And 각 핸들에서 다른 노드로 개별 연결이 가능하다
```

#### TC-011: AggregatorNode 다중 입력

```gherkin
Given 캔버스에 AggregatorNode와 3개의 ToolNode가 있다
When 사용자가 3개의 ToolNode 출력을 각각 AggregatorNode의 입력 핸들에 연결한다
Then AggregatorNode에 3개의 입력 엣지가 연결된다
  And 모든 연결이 정상적으로 표시된다
```

---

### 2.5 UI 컨트롤

#### TC-012: 미니맵 표시

```gherkin
Given 캔버스에 10개 이상의 노드가 있다
When 편집기가 렌더링된다
Then 캔버스 우측 하단에 미니맵이 표시된다
  And 미니맵에서 현재 뷰포트 위치가 하이라이트된다
```

#### TC-013: 줌 인/아웃

```gherkin
Given 사용자가 워크플로우 편집기를 보고 있다
When 사용자가 마우스 휠을 위로 스크롤한다
Then 캔버스가 확대된다
When 사용자가 마우스 휠을 아래로 스크롤한다
Then 캔버스가 축소된다
```

#### TC-014: 캔버스 팬(이동)

```gherkin
Given 캔버스에 여러 노드가 있다
When 사용자가 캔버스 빈 영역을 클릭하고 드래그한다
Then 캔버스 전체가 드래그 방향으로 이동한다
  And 노드들의 상대적 위치는 유지된다
```

---

### 2.6 상태 동기화

#### TC-015: Zustand 스토어 실시간 동기화

```gherkin
Given 캔버스에 2개의 노드가 있다
When 사용자가 노드 위치를 드래그로 변경한다
Then Zustand 스토어의 해당 노드 position 값이 즉시 업데이트된다
  And 다른 컴포넌트에서 useWorkflowStore()로 조회 시 최신 위치가 반환된다
```

#### TC-016: 워크플로우 내보내기

```gherkin
Given 캔버스에 5개의 노드와 4개의 엣지가 있다
When exportWorkflow() 함수를 호출한다
Then { nodes: [...], edges: [...] } 형태의 객체가 반환된다
  And 모든 노드와 엣지 정보가 포함된다
```

---

## 3. 엣지 케이스

### EC-001: 빈 캔버스에서 Delete 키

```gherkin
Given 캔버스에 노드가 없다
When 사용자가 Delete 키를 누른다
Then 아무 동작도 발생하지 않는다
  And 에러가 발생하지 않는다
```

### EC-002: TriggerNode에 입력 연결 시도

```gherkin
Given 캔버스에 TriggerNode와 ToolNode가 있다
When 사용자가 ToolNode의 출력에서 TriggerNode로 연결을 시도한다
Then 연결이 거부된다 (TriggerNode는 입력 핸들이 없음)
```

### EC-003: 100개 노드 성능

```gherkin
Given 캔버스에 100개의 노드가 있다
When 사용자가 캔버스를 팬/줌 조작한다
Then 렌더링이 60fps 이상으로 부드럽게 유지된다
  And UI가 멈추거나 지연되지 않는다
```

---

## 4. 품질 게이트

### 4.1 필수 통과 조건

| 항목 | 기준 |
|------|------|
| 기능 테스트 | TC-001 ~ TC-016 모두 통과 |
| 엣지 케이스 | EC-001 ~ EC-003 모두 통과 |
| TypeScript | strict 모드 오류 0건 |
| ESLint | 오류 0건, 경고 5건 이하 |
| 브라우저 호환성 | Chrome, Firefox, Safari 최신 버전에서 동작 확인 |

### 4.2 권장 통과 조건

| 항목 | 기준 |
|------|------|
| 테스트 커버리지 | 80% 이상 |
| Lighthouse 성능 점수 | 90점 이상 |
| 접근성 점수 | 90점 이상 |

---

## 5. 테스트 환경

### 5.1 필수 환경

- Node.js 20+
- pnpm 9+
- Chrome 최신 버전

### 5.2 테스트 도구

| 도구 | 용도 |
|------|------|
| Vitest | 단위 테스트 |
| React Testing Library | 컴포넌트 테스트 |
| Playwright | E2E 테스트 |
