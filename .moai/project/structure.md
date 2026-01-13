# Paste Trader - System Architecture

## 아키텍처 개요

paste-trader는 **3-Tier 아키텍처**를 기반으로, 프론트엔드(Next.js), 백엔드 API(FastAPI), 그리고 메타 LLM 엔진이 유기적으로 연동되는 구조를 채택한다.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 15)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Workflow    │  │ Dashboard   │  │ Settings & Management  │  │
│  │ Editor      │  │ & Analytics │  │ Panel                   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Workflow    │  │ Tool/Agent  │  │ Scheduler & Execution  │  │
│  │ Management  │  │ Registry    │  │ Engine                  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Meta LLM Engine (ReAct)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Reasoning   │  │ Agent       │  │ Tool Orchestration     │  │
│  │ Controller  │  │ Manager     │  │ Layer                   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data & Storage Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ PostgreSQL  │  │ Redis       │  │ External APIs          │  │
│  │ (Workflows) │  │ (Cache)     │  │ (Market Data)           │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 디렉토리 구조

```
paste-trader/
├── frontend/                      # Next.js 15 프론트엔드
│   ├── app/                       # App Router
│   │   ├── (auth)/               # 인증 관련 라우트
│   │   ├── dashboard/            # 대시보드
│   │   ├── workflows/            # 워크플로우 관리
│   │   │   ├── [id]/            # 개별 워크플로우
│   │   │   └── new/             # 새 워크플로우 생성
│   │   ├── tools/               # 도구 관리
│   │   ├── agents/              # 에이전트 관리
│   │   └── settings/            # 설정
│   ├── components/               # 재사용 컴포넌트
│   │   ├── ui/                  # shadcn/ui 컴포넌트
│   │   ├── workflow/            # 워크플로우 에디터 (React Flow)
│   │   │   ├── WorkflowEditor.tsx    # 메인 에디터 컴포넌트
│   │   │   ├── WorkflowCanvas.tsx    # React Flow 캔버스
│   │   │   └── nodes/               # 커스텀 노드 컴포넌트
│   │   │       ├── ToolNode.tsx     # 도구 실행 노드
│   │   │       ├── AgentNode.tsx    # LLM 에이전트 노드
│   │   │       ├── ConditionNode.tsx # 분기 조건 노드
│   │   │       ├── AdapterNode.tsx  # 데이터 변환 노드
│   │   │       └── TriggerNode.tsx  # 스케줄 트리거 노드
│   │   ├── paste-input/         # 입력 소스 컴포넌트
│   │   │   ├── TextPasteInput.tsx   # 텍스트 입력
│   │   │   ├── PdfUploader.tsx      # PDF 업로드
│   │   │   └── YoutubeUrlInput.tsx  # YouTube URL 입력
│   │   ├── chart/               # 차트 컴포넌트
│   │   └── common/              # 공통 컴포넌트
│   ├── stores/                   # Zustand 상태 관리
│   │   ├── workflow-store.ts    # 워크플로우 상태 (nodes, edges)
│   │   └── ui-store.ts          # UI 상태
│   ├── lib/                      # 유틸리티
│   │   ├── api/                 # API 클라이언트
│   │   └── utils/               # 헬퍼 함수
│   └── styles/                   # 스타일
│
├── backend/                       # FastAPI 백엔드
│   ├── app/
│   │   ├── api/                  # API 라우터
│   │   │   ├── v1/
│   │   │   │   ├── workflows.py
│   │   │   │   ├── tools.py
│   │   │   │   ├── agents.py
│   │   │   │   └── executions.py
│   │   │   └── deps.py          # 의존성
│   │   ├── core/                 # 핵심 설정
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── logging.py
│   │   ├── models/               # SQLAlchemy 모델
│   │   │   ├── workflow.py
│   │   │   ├── tool.py
│   │   │   ├── agent.py
│   │   │   └── execution.py
│   │   ├── schemas/              # Pydantic 스키마
│   │   ├── services/             # 비즈니스 로직
│   │   │   ├── workflow_service.py
│   │   │   ├── execution_service.py
│   │   │   └── scheduler_service.py
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
│
├── meta_llm/                      # 메타 LLM 엔진
│   ├── core/
│   │   ├── react_controller.py   # ReAct 패턴 컨트롤러
│   │   ├── reasoning.py          # 추론 엔진
│   │   └── action.py             # 행동 실행기
│   ├── agents/
│   │   ├── base_agent.py         # 에이전트 베이스
│   │   ├── workflow_generator.py # 워크플로우 생성 에이전트
│   │   ├── analyzer.py           # 분석 에이전트
│   │   └── executor.py           # 실행 에이전트
│   ├── tools/
│   │   ├── registry.py           # 도구 레지스트리
│   │   ├── base_tool.py          # 도구 베이스
│   │   ├── data_fetcher.py       # 데이터 수집 도구
│   │   ├── indicator.py          # 기술적 지표 도구
│   │   ├── screener.py           # 종목 스크리닝 도구
│   │   └── code_analyzer.py      # grep/ast-grep 래퍼
│   ├── providers/                # LLM Provider
│   │   ├── base.py
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   └── glm.py
│   └── tests/
│
├── workflow_engine/               # 워크플로우 엔진
│   ├── core/
│   │   ├── dag.py                # DAG 구조
│   │   ├── node.py               # 노드 정의
│   │   ├── edge.py               # 엣지 정의
│   │   └── executor.py           # 실행기
│   ├── nodes/
│   │   ├── tool_node.py          # 도구 노드
│   │   ├── agent_node.py         # 에이전트 노드
│   │   ├── condition_node.py     # 조건 노드
│   │   └── adapter_node.py       # 어댑터 노드
│   ├── adapters/
│   │   ├── base.py               # 어댑터 베이스
│   │   ├── json_adapter.py
│   │   └── dataframe_adapter.py
│   └── scheduler/
│       ├── apscheduler.py        # APScheduler 래퍼
│       └── triggers.py           # 트리거 정의
│
├── shared/                        # 공유 모듈
│   ├── types/                    # 타입 정의
│   └── utils/                    # 공통 유틸리티
│
├── config/                        # 설정 파일
│   ├── workflows/                # 워크플로우 YAML
│   └── agents/                   # 에이전트 템플릿
│
├── docker/                        # Docker 설정
│   ├── Dockerfile.frontend
│   ├── Dockerfile.backend
│   └── docker-compose.yml
│
├── .moai/                         # MoAI 프로젝트 설정
│   └── project/
│
└── docs/                          # 문서
```

---

## 핵심 컴포넌트

### 1. 워크플로우 엔진

n8n 스타일의 선형/분기 워크플로우 엔진. LangGraph를 사용하지 않고 직접 Python으로 구현.

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Engine                          │
│                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐ │
│  │ Parser  │───▶│ DAG     │───▶│ Executor│───▶│ Output  │ │
│  │ (YAML)  │    │ Builder │    │         │    │ Handler │ │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘ │
│       │                             │                       │
│       ▼                             ▼                       │
│  ┌─────────┐                   ┌─────────┐                 │
│  │ Schema  │                   │ State   │                 │
│  │ Validator│                  │ Manager │                 │
│  └─────────┘                   └─────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

#### 노드 타입

| 노드 타입 | 설명 | 예시 |
|-----------|------|------|
| `tool` | 코드로 정의된 도구 실행 | 가격 조회, 지표 계산 |
| `agent` | LLM 기반 에이전트 실행 | 분석, 판단 |
| `condition` | 조건 분기 | if/else 로직 |
| `adapter` | 데이터 형식 변환 | JSON → DataFrame |
| `parallel` | 병렬 실행 그룹 | 다중 종목 동시 분석 |
| `aggregator` | 결과 집계 | 종목 순위화 |

### 2. 메타 LLM 엔진

Oh-My-OpenCode 스타일의 다중 에이전트 시스템. ReAct 패턴 기반.

```
┌─────────────────────────────────────────────────────────────┐
│                    Meta LLM Engine                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ReAct Controller                        │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │   │
│  │  │ Thought │─▶│ Action  │─▶│ Observe │◀───────┐    │   │
│  │  └─────────┘  └─────────┘  └─────────┘        │    │   │
│  │       ▲                                        │    │   │
│  │       └────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                   │
│           ┌─────────────┴─────────────┐                    │
│           ▼                           ▼                    │
│  ┌─────────────────┐         ┌─────────────────┐          │
│  │ Agent Manager   │         │ Tool Registry   │          │
│  │ - Create        │         │ - grep          │          │
│  │ - Execute       │         │ - ast-grep      │          │
│  │ - Manage        │         │ - data_fetcher  │          │
│  └─────────────────┘         └─────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

#### ReAct 루프

1. **Thought**: 현재 상태 분석 및 다음 행동 계획
2. **Action**: 도구 호출 또는 에이전트 위임
3. **Observation**: 결과 수집 및 평가
4. **Loop**: 목표 달성까지 반복

### 3. LLM Provider 아키텍처

Multi-Provider 지원으로 비용 및 성능 최적화.

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Client Layer                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   LLMClient                          │   │
│  │  - get_provider(name: str)                          │   │
│  │  - route_by_purpose(purpose: str)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Provider Registry                      │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │   │
│  │  │Anthropic│  │ OpenAI  │  │ Z.AI GLM│             │   │
│  │  └─────────┘  └─────────┘  └─────────┘             │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Provider Factory                       │   │
│  │  - create(config: ProviderConfig)                   │   │
│  │  - validate_credentials()                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 4. 워크플로우 시각화 (React Flow)

React Flow 라이브러리를 활용한 인터랙티브 워크플로우 에디터 구현.

```
┌─────────────────────────────────────────────────────────────────┐
│                 Workflow Visualization Architecture              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    WorkflowEditor                           │ │
│  │  - 메인 컨테이너 컴포넌트                                     │ │
│  │  - 툴바, 사이드바, 캔버스 레이아웃                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           │                                      │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   ReactFlow Canvas                          │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │ │
│  │  │ Nodes       │  │ Edges       │  │ Controls    │        │ │
│  │  │ (커스텀)    │  │ (연결선)    │  │ (줌/미니맵) │        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           │                                      │
│           ┌───────────────┼───────────────┐                     │
│           ▼               ▼               ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  ToolNode   │  │ AgentNode   │  │ConditionNode│             │
│  │  - 입력포트 │  │ - 프롬프트  │  │ - 다중출력  │             │
│  │  - 출력포트 │  │ - 모델선택  │  │ - 조건식    │             │
│  │  - 설정UI   │  │ - 도구목록  │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                           │                                      │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 Zustand Workflow Store                      │ │
│  │  - nodes: Node[]                                            │ │
│  │  - edges: Edge[]                                            │ │
│  │  - onNodesChange: (changes) => void                        │ │
│  │  - onEdgesChange: (changes) => void                        │ │
│  │  - onConnect: (connection) => void                         │ │
│  │  - addNode: (type, position) => void                       │ │
│  │  - updateNodeData: (id, data) => void                      │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### 커스텀 노드 타입

| 노드 타입 | 컴포넌트 | 입력 포트 | 출력 포트 | 설명 |
|-----------|----------|-----------|-----------|------|
| `trigger` | TriggerNode | 없음 | 1개 | 스케줄/이벤트 트리거 |
| `tool` | ToolNode | 1개 | 1개 | 도구 실행 |
| `agent` | AgentNode | 1개 | 1개 | LLM 에이전트 |
| `condition` | ConditionNode | 1개 | N개 | 분기 조건 |
| `adapter` | AdapterNode | 1개 | 1개 | 데이터 변환 |
| `aggregator` | AggregatorNode | N개 | 1개 | 결과 집계 |

#### Handle (연결점) 구성

```tsx
// 커스텀 노드에서 Handle 컴포넌트 사용
<Handle type="target" position={Position.Left} />   // 입력 포트
<Handle type="source" position={Position.Right} />  // 출력 포트

// 다중 출력 (Condition Node)
<Handle type="source" position={Position.Right} id="true" />
<Handle type="source" position={Position.Right} id="false" />
```

### 5. 입력 소스 처리 아키텍처

3가지 입력 소스를 처리하는 파싱 레이어:

```
┌─────────────────────────────────────────────────────────────────┐
│                  Input Source Processing Layer                   │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Text     │  │    PDF      │  │  YouTube    │             │
│  │   Input     │  │  Uploader   │  │  URL Input  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Direct    │  │ PDF Parser  │  │  Subtitle   │             │
│  │   Pass      │  │ (pdfplumber)│  │  Extractor  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Unified Text Output                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Meta LLM Analysis                         │ │
│  │  - 전략 요소 추출                                            │ │
│  │  - 워크플로우 생성                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 6. 도구(Tool) 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Tool System                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 Tool Registry                        │   │
│  │  - register(tool: BaseTool)                         │   │
│  │  - get(name: str) -> BaseTool                       │   │
│  │  - list_all() -> List[ToolInfo]                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                   │
│      ┌──────────────────┼──────────────────┐               │
│      ▼                  ▼                  ▼               │
│  ┌─────────┐      ┌─────────┐       ┌─────────┐           │
│  │ Data    │      │Technical│       │ Market  │           │
│  │ Fetcher │      │Indicator│       │Screener │           │
│  └─────────┘      └─────────┘       └─────────┘           │
│      │                │                   │                │
│      └────────────────┴───────────────────┘                │
│                       │                                     │
│                       ▼                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Adapter Layer                           │   │
│  │  - Input validation                                 │   │
│  │  - Output formatting                                │   │
│  │  - Error handling                                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 워크플로우 구성 예시

### YAML 기반 워크플로우 정의

```yaml
workflow_id: trading-workflow-001
name: RSI 기반 매매 전략
description: RSI 과매수/과매도 신호를 활용한 단기 매매 전략
version: 1.0.0
author: paste-trader

trigger:
  type: schedule
  cron: "30 9,15 * * 1-5"  # 평일 9:30, 15:00
  timezone: Asia/Seoul

variables:
  rsi_period: 14
  overbought: 70
  oversold: 30
  target_markets:
    - KOSPI
    - KOSDAQ

nodes:
  # 1. 종목 리스트 조회
  - id: n1
    type: tool
    tool_id: market_screener
    name: 종목 리스트 조회
    config:
      markets: "{{ variables.target_markets }}"
      min_volume: 100000
      min_market_cap: 1000000000  # 10억 이상
    outputs:
      - name: stock_list
        type: list[string]

  # 2. 병렬 데이터 수집
  - id: n2
    type: parallel
    name: 가격 데이터 수집
    depends_on: [n1]
    input: "{{ n1.outputs.stock_list }}"
    node_template:
      type: tool
      tool_id: price_fetcher
      config:
        period: 30d
        interval: 1d
    outputs:
      - name: price_data
        type: list[dataframe]

  # 3. RSI 계산
  - id: n3
    type: tool
    tool_id: technical_indicator
    name: RSI 계산
    depends_on: [n2]
    config:
      indicator: RSI
      period: "{{ variables.rsi_period }}"
    input: "{{ n2.outputs.price_data }}"
    outputs:
      - name: rsi_values
        type: list[object]

  # 4. 조건 분기 - 과매수/과매도 필터링
  - id: n4
    type: condition
    name: 시그널 분류
    depends_on: [n3]
    input: "{{ n3.outputs.rsi_values }}"
    conditions:
      - name: oversold
        expression: "rsi < {{ variables.oversold }}"
        target: n5_buy
      - name: overbought
        expression: "rsi > {{ variables.overbought }}"
        target: n5_sell
      - name: neutral
        expression: "else"
        target: n6

  # 5a. 매수 신호 분석
  - id: n5_buy
    type: agent
    agent_id: buy_signal_analyzer
    name: 매수 신호 분석
    config:
      analysis_depth: detailed
      include_fundamentals: true
    outputs:
      - name: buy_signals
        type: list[signal]

  # 5b. 매도 신호 분석
  - id: n5_sell
    type: agent
    agent_id: sell_signal_analyzer
    name: 매도 신호 분석
    config:
      analysis_depth: detailed
    outputs:
      - name: sell_signals
        type: list[signal]

  # 6. 결과 집계
  - id: n6
    type: aggregator
    name: 시그널 집계
    depends_on: [n5_buy, n5_sell]
    config:
      sort_by: confidence
      limit: 10
    outputs:
      - name: final_signals
        type: list[signal]

  # 7. 리포트 생성
  - id: n7
    type: agent
    agent_id: report_generator
    name: 분석 리포트 생성
    depends_on: [n6]
    config:
      format: markdown
      include_charts: true
    outputs:
      - name: report
        type: string

  # 8. 알림 발송
  - id: n8
    type: tool
    tool_id: notification_sender
    name: 알림 발송
    depends_on: [n7]
    config:
      channels:
        - slack
        - email
    input: "{{ n7.outputs.report }}"

error_handling:
  on_node_failure: continue
  retry:
    max_attempts: 3
    delay_seconds: 5
  fallback:
    - node_id: n2
      fallback_tool: cached_price_fetcher

logging:
  level: INFO
  destinations:
    - console
    - file
  include_metrics: true
```

### 어댑터 노드 예시

```yaml
# 노드 간 데이터 변환
- id: adapter_1
  type: adapter
  name: DataFrame to Signal List
  depends_on: [n3]
  config:
    input_type: dataframe
    output_type: list[signal]
    mapping:
      symbol: "{{ row.ticker }}"
      value: "{{ row.rsi }}"
      timestamp: "{{ row.date }}"
      metadata:
        indicator: RSI
        period: "{{ variables.rsi_period }}"
```

### 에이전트 정의 예시

```yaml
agent_id: buy_signal_analyzer
name: 매수 신호 분석 에이전트
version: 1.0.0

model:
  provider: anthropic
  model: claude-sonnet-4-20250514
  temperature: 0.3
  max_tokens: 4096

system_prompt: |
  당신은 주식 매수 신호를 분석하는 전문 트레이딩 분석가입니다.

  주어진 기술적 지표와 시장 데이터를 분석하여:
  1. 매수 신호의 강도를 평가합니다 (Strong/Medium/Weak)
  2. 진입 가격과 손절 가격을 제안합니다
  3. 예상 리스크/리워드 비율을 계산합니다
  4. 분석 근거를 상세히 설명합니다

tools:
  - price_fetcher
  - fundamental_data
  - news_sentiment

output_schema:
  type: object
  properties:
    symbol:
      type: string
    signal_strength:
      type: string
      enum: [Strong, Medium, Weak]
    entry_price:
      type: number
    stop_loss:
      type: number
    target_price:
      type: number
    risk_reward_ratio:
      type: number
    confidence:
      type: number
      minimum: 0
      maximum: 100
    analysis:
      type: string
```

---

## 데이터 흐름

### 워크플로우 실행 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow Execution Flow                       │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Schedule │───▶│ Trigger  │───▶│ Execute  │───▶│ Complete │  │
│  │ (APSched)│    │ Handler  │    │ DAG      │    │ Handler  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                        │                        │
│                           ┌────────────┼────────────┐           │
│                           ▼            ▼            ▼           │
│                    ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│                    │ Tool     │ │ Agent    │ │ Adapter  │       │
│                    │ Executor │ │ Executor │ │ Executor │       │
│                    └──────────┘ └──────────┘ └──────────┘       │
│                           │            │            │           │
│                           └────────────┼────────────┘           │
│                                        ▼                        │
│                                 ┌──────────┐                    │
│                                 │ State    │                    │
│                                 │ Manager  │                    │
│                                 └──────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

### 상태 관리

```yaml
# Execution State
execution:
  id: exec-20250111-093000-001
  workflow_id: trading-workflow-001
  status: running  # pending | running | completed | failed
  started_at: 2025-01-11T09:30:00+09:00
  current_node: n3

  node_states:
    n1:
      status: completed
      started_at: 2025-01-11T09:30:00+09:00
      completed_at: 2025-01-11T09:30:05+09:00
      output:
        stock_list: [AAPL, GOOGL, MSFT, ...]
    n2:
      status: completed
      parallel_executions:
        - symbol: AAPL
          status: completed
        - symbol: GOOGL
          status: completed
    n3:
      status: running
      started_at: 2025-01-11T09:30:15+09:00
      progress: 45%
```

---

## 외부 시스템 연동

### API 통합

```
┌─────────────────────────────────────────────────────────────┐
│                 External API Integration                     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              API Gateway Layer                       │    │
│  └─────────────────────────────────────────────────────┘    │
│           │              │              │                    │
│           ▼              ▼              ▼                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Market Data │ │ LLM APIs    │ │ Notification│           │
│  │ - KIS       │ │ - Anthropic │ │ - Slack     │           │
│  │ - FinanceDB │ │ - OpenAI    │ │ - Discord   │           │
│  │ - Yahoo     │ │ - Z.AI GLM  │ │ - Email     │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 인증 모드

| 모드 | 설명 | 사용 사례 |
|------|------|-----------|
| OAuth | OAuth 2.0 기반 인증 | 사용자 계정 연동 |
| Standalone | API 키 직접 입력 | 개인 API 키 사용 |
| SDK | SDK 기반 인증 | 공식 SDK 활용 |
| GLM | Z.AI GLM 전용 인증 | Z.AI 서비스 연동 |

---

## 확장성 고려사항

### 수평적 확장

- **워크플로우 분산**: 여러 워커에서 병렬 실행
- **Redis 클러스터**: 캐시 및 상태 분산
- **DB 레플리카**: 읽기 부하 분산

### 수직적 확장

- **노드 타입 추가**: 새로운 노드 타입 플러그인
- **도구 확장**: 커스텀 도구 등록
- **Provider 추가**: 새로운 LLM 제공자 통합

---

## 보안 고려사항

### 데이터 보안

- API 키 암호화 저장
- 사용자 데이터 격리
- 실행 로그 마스킹

### 접근 제어

- 워크플로우별 권한 관리
- API 엔드포인트 인증
- Rate limiting

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 0.1.0 | 2025-01-11 | 초기 아키텍처 설계 |
| 0.2.0 | 2025-01-11 | React Flow 워크플로우 시각화 아키텍처 추가, 입력 소스 처리 아키텍처 추가, 커스텀 노드/Zustand 스토어 구조 추가 |
