# LLM Provider 아키텍처 가이드

> **OhMyStock** 프로젝트의 LLM Provider 시스템에 대한 종합 레퍼런스 문서

**버전**: 1.0.0
**최종 수정**: 2025-01-11
**대상 독자**: Python 백엔드 개발자

---

## 목차

1. [개요](#1-개요)
2. [아키텍처 다이어그램](#2-아키텍처-다이어그램)
3. [핵심 개념](#3-핵심-개념)
4. [클래스 계층 구조와 인터페이스](#4-클래스-계층-구조와-인터페이스)
5. [설정 시스템](#5-설정-시스템)
6. [사용 예제](#6-사용-예제)
7. [사용된 디자인 패턴](#7-사용된-디자인-패턴)
8. [확장 포인트](#8-확장-포인트)

---

## 1. 개요

### 해결하는 문제

현대 AI 애플리케이션은 여러 LLM 제공자(Anthropic, OpenAI, Google, Z.AI 등)를 동시에 활용해야 하는 경우가 많습니다. 각 제공자는 서로 다른 인증 방식, API 형식, SDK를 사용하며, 이로 인해 다음과 같은 문제가 발생합니다.

**문제점**:
- 각 제공자별로 다른 인증 로직 구현 필요
- API 형식 차이로 인한 중복 코드 발생
- 제공자 간 전환 시 클라이언트 코드 수정 필요
- 토큰 갱신, 에러 처리 등 공통 로직의 분산

**해결책**:
OhMyStock의 LLM Provider 시스템은 **추상화 계층**을 통해 이러한 문제를 해결합니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLMClient                                │
│  (통합 인터페이스 - 모델명 기반 자동 제공자 선택)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ProviderRegistry                            │
│  (제공자 관리 - 지연 초기화, 캐싱)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ProviderFactory                             │
│  (제공자 생성 - 설정 기반 인스턴스화)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ OAuth    │        │Standalone│        │   SDK    │
    │ Provider │        │ Provider │        │ Provider │
    └──────────┘        └──────────┘        └──────────┘
```

### 주요 특징

- **다중 인증 모드**: OAuth, API Key, SDK, GLM 4가지 인증 방식 지원
- **다중 제공자 통합**: Anthropic, OpenAI, Google, Z.AI GLM 지원
- **자동 제공자 선택**: 모델명 prefix 기반 자동 라우팅
- **토큰 자동 갱신**: OAuth 토큰 만료 시 자동 refresh
- **Tool Loop 지원**: 다중 턴 도구 호출 자동 처리
- **스트리밍 지원**: SSE 기반 실시간 응답 스트리밍

---

## 2. 아키텍처 다이어그램

### 전체 시스템 구조

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              LLMClient                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  - chat() / chat_stream() / generate()                              │   │
│  │  - Tool Loop 관리 (max_tool_iterations)                             │   │
│  │  - 자동 제공자 선택 (model prefix 기반)                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           ProviderRegistry                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  - 제공자 등록 (provider 또는 config)                                 │   │
│  │  - 지연 초기화 (Lazy Initialization)                                 │   │
│  │  - 모델명 기반 제공자 조회                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           ProviderFactory                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  create(config) ──┬── AuthMode.OAUTH      → OAuthProvider           │   │
│  │                   ├── AuthMode.STANDALONE → StandaloneProvider      │   │
│  │                   ├── AuthMode.SDK        → SDKProvider             │   │
│  │                   └── AuthMode.GLM        → GLMProvider             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────────┐         ┌───────────────┐
│ OAuthProvider │         │ StandaloneProvider│         │  GLMProvider  │
├───────────────┤         ├───────────────────┤         ├───────────────┤
│ - Anthropic   │         │ - Anthropic SDK   │         │ - Z.AI GLM    │
│ - OpenAI      │         │ - OpenAI SDK      │         │ - Direct HTTP │
│ - Token Refresh│        │ - Google GenAI    │         │ - OpenAI 호환  │
│ - Claude Code │         │                   │         │               │
│   Beta Headers│         │                   │         │               │
└───────────────┘         └───────────────────┘         └───────────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │    SDKProvider    │
                          ├───────────────────┤
                          │ - Claude Code SDK │
                          │ - 내부 Tool 처리   │
                          │ - bypassPermissions│
                          └───────────────────┘
```

### 데이터 흐름

```
사용자 요청
     │
     ▼
┌─────────────────┐
│   LLMClient     │
│   .chat()       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ 1. 메시지 변환: str → list[Message]                       │
│ 2. 제공자 선택: model prefix → ProviderRegistry           │
│ 3. Provider.chat() 호출                                  │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ Provider 내부 처리:                                      │
│ 1. 메시지 형식 변환 (Provider별 포맷)                      │
│ 2. 도구 정의 변환                                        │
│ 3. HTTP/SDK 요청 실행                                   │
│ 4. 응답 파싱 → LLMResponse                              │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ Tool Loop (LLMClient):                                  │
│ if response.has_tool_calls:                             │
│   1. tool_executor 실행                                 │
│   2. 결과를 메시지에 추가                                  │
│   3. 다음 턴 요청 (최대 max_tool_iterations)              │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
     최종 응답
```

---

## 3. 핵심 개념

### 3.1 인증 모드 (AuthMode)

시스템은 4가지 인증 모드를 지원하며, 각각 다른 사용 사례에 적합합니다.

| AuthMode | 설명 | 사용 사례 | 지원 제공자 |
|----------|------|----------|------------|
| `OAUTH` | OAuth 토큰 기반 인증 | Claude Pro/Max 구독자 | Anthropic, OpenAI |
| `STANDALONE` | API 키 직접 사용 | 일반 API 사용자 | Anthropic, OpenAI, Google |
| `SDK` | Claude Code SDK | Claude Code 확장 기능 | Anthropic |
| `GLM` | Z.AI GLM 전용 | Z.AI 코딩 플랜 | Z.AI GLM |

```python
from src.llm.providers.base import AuthMode

class AuthMode(str, Enum):
    OAUTH = "oauth"          # OAuth token-based (auth.json)
    STANDALONE = "standalone" # API key-based
    SDK = "sdk"              # Claude Code SDK
    GLM = "glm"              # Z.AI GLM direct HTTP
```

#### OAuth 모드 상세

OAuth 모드는 `~/.local/share/opencode/auth.json` 파일에서 토큰을 로드합니다.

**토큰 구조**:
```json
{
  "anthropic": {
    "type": "oauth",
    "access": "access_token_here",
    "refresh": "refresh_token_here",
    "expires": 1704067200000
  },
  "openai": {
    "type": "oauth",
    "access": "access_token_here",
    "refresh": "refresh_token_here",
    "expires": 1704067200000
  }
}
```

**자동 토큰 갱신**:
- 토큰 만료 시 refresh_token을 사용하여 자동 갱신
- 갱신된 토큰은 auth.json에 저장
- Anthropic/OpenAI 각각 전용 refresh 엔드포인트 사용

#### Standalone 모드 상세

환경 변수 또는 직접 전달된 API 키를 사용합니다.

**환경 변수**:
- `OMS_ANTHROPIC_API_KEY`: Anthropic API 키
- `OMS_OPENAI_API_KEY`: OpenAI API 키
- `OMS_GOOGLE_API_KEY`: Google API 키
- `OMS_GLM_API_KEY`: Z.AI GLM API 키

#### SDK 모드 상세

Claude Code SDK를 통해 확장된 기능에 접근합니다.

**특징**:
- `bypassPermissions` 모드로 실행
- 내부적으로 도구 실행 처리
- OAuth 토큰 또는 API 키 지원

#### GLM 모드 상세

Z.AI GLM 모델에 직접 HTTP로 접근합니다.

**API 엔드포인트**: `https://api.z.ai/api/coding/paas/v4/chat/completions`

**환경 변수**:
- `OMS_GLM_API_KEY`: API 키
- `OMS_GLM_BASE_URL`: 베이스 URL (기본값: `https://api.z.ai/api/coding/paas/v4`)

---

### 3.2 제공자 추상화 패턴

모든 제공자는 `BaseLLMProvider` 추상 클래스를 상속하여 동일한 인터페이스를 제공합니다.

#### 책임 분리 원칙

| 컴포넌트 | 담당 | 미담당 |
|----------|------|--------|
| **Provider** | 인증, API 형식 변환, 응답 파싱 | 도구 실행, 재시도, 설정 로드 |
| **Client** | 도구 루프, 메시지 관리, 제공자 선택 | 인증, API 호출 |
| **Factory** | 설정 로드, 제공자 인스턴스화 | 실제 API 호출 |

```python
class BaseLLMProvider(ABC):
    """추상 기본 클래스 - 모든 제공자가 구현해야 하는 인터페이스.

    제공자가 처리하는 것:
    - 인증 (API key 또는 OAuth token)
    - API 요청 형식 변환
    - 응답 파싱
    - Tool call 추출

    제공자가 처리하지 않는 것:
    - 도구 실행 (클라이언트의 역할)
    - 재시도 로직 (클라이언트의 역할)
    - 설정 로딩 (팩토리의 역할)
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str: ...

    @abstractmethod
    async def generate_structured(self, prompt: str, schema: Type[T], **kwargs) -> T: ...

    @abstractmethod
    async def chat(self, messages: list[Message], *, system: str | None = None,
                   model: str | None = None, max_tokens: int = 4096,
                   tools: list[ToolDefinition] | None = None,
                   temperature: float | None = None) -> LLMResponse: ...

    @abstractmethod
    async def chat_stream(self, messages: list[Message], *,
                          system: str | None = None, model: str | None = None,
                          max_tokens: int = 4096) -> AsyncIterator[str]: ...
```

---

## 4. 클래스 계층 구조와 인터페이스

### 4.1 데이터 모델

```python
# 역할 타입 정의
Role = Literal["system", "user", "assistant", "tool"]

@dataclass
class Message:
    """대화 메시지."""
    role: Role                      # 발신자 역할
    content: str                    # 메시지 내용
    tool_call_id: str | None = None # 도구 응답 시 호출 ID
    name: str | None = None         # 도구 이름 (tool 역할용)

@dataclass
class ToolCall:
    """LLM이 요청한 도구 호출."""
    id: str                         # 고유 식별자
    name: str                       # 도구 이름
    arguments: dict[str, Any]       # 인자

@dataclass
class LLMResponse:
    """LLM 응답."""
    content: str                    # 텍스트 응답
    tool_calls: list[ToolCall]      # 도구 호출 목록
    finish_reason: str | None       # 종료 이유 (stop, tool_use 등)
    model: str | None               # 사용된 모델
    usage: dict[str, int] | None    # 토큰 사용량

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

@dataclass
class ToolDefinition:
    """도구 정의 스키마."""
    name: str                       # 도구 이름
    description: str                # 도구 설명
    parameters: dict[str, Any]      # JSON Schema 파라미터

@dataclass
class ProviderConfig:
    """제공자 설정."""
    provider_type: ProviderType     # 제공자 종류
    auth_mode: AuthMode = AuthMode.STANDALONE
    api_key: str | None = None
    base_url: str | None = None
    default_model: str | None = None
    access_token: str | None = None  # OAuth용
    refresh_token: str | None = None # OAuth용
    max_turns: int = 10              # SDK용
    system_prompt: str | None = None
```

### 4.2 제공자 계층 구조

```
BaseLLMProvider (ABC)
    │
    ├── OAuthProvider
    │   ├── Anthropic OAuth 지원
    │   │   └── Claude Code 호환 헤더
    │   └── OpenAI Codex OAuth 지원
    │       └── JWT 기반 account_id 추출
    │
    ├── StandaloneProvider
    │   ├── Anthropic SDK (anthropic)
    │   ├── OpenAI SDK (openai)
    │   └── Google GenAI SDK (google-genai)
    │
    ├── SDKProvider
    │   └── Claude Code SDK (claude-code-sdk)
    │
    └── GLMProvider
        └── Z.AI GLM Direct HTTP
```

### 4.3 제공자별 메시지 형식

각 제공자는 내부적으로 메시지를 자신의 API 형식으로 변환합니다.

#### Anthropic 형식
```python
# 입력 (내부 Message)
Message(role="user", content="Hello")

# 변환 후 (Anthropic API)
{
    "role": "user",
    "content": [{
        "type": "text",
        "text": "Hello",
        "cache_control": {"type": "ephemeral"}
    }]
}
```

#### OpenAI 형식
```python
# 입력 (내부 Message)
Message(role="user", content="Hello")

# 변환 후 (OpenAI API)
{"role": "user", "content": "Hello"}
```

#### Google 형식
```python
# 입력 (내부 Message)
Message(role="user", content="Hello")

# 변환 후 (Google API)
{
    "role": "user",
    "parts": [{"text": "Hello"}]
}
```

---

## 5. 설정 시스템

### 5.1 환경 변수

| 변수명 | 용도 | 기본값 |
|--------|------|--------|
| `OMS_LLM_AUTH_MODE` | 기본 인증 모드 | `standalone` |
| `OMS_ANTHROPIC_API_KEY` | Anthropic API 키 | - |
| `OMS_OPENAI_API_KEY` | OpenAI API 키 | - |
| `OMS_GOOGLE_API_KEY` | Google API 키 | - |
| `OMS_GLM_API_KEY` | Z.AI GLM API 키 | - |
| `OMS_GLM_BASE_URL` | Z.AI GLM 베이스 URL | `https://api.z.ai/api/coding/paas/v4` |

### 5.2 기본 모델

| 제공자 | Standalone 기본 모델 | OAuth 기본 모델 |
|--------|---------------------|-----------------|
| Anthropic | `claude-sonnet-4-20250514` | `claude-opus-4-5-20251101` |
| OpenAI | `gpt-4.1` | `gpt-5.2` |
| Google | `gemini-2.0-flash` | - |
| GLM | `glm-4.7` | - |

### 5.3 ProviderConfig 활용

```python
from src.llm.providers.base import ProviderConfig, ProviderType, AuthMode

# 기본 설정
config = ProviderConfig(
    provider_type=ProviderType.ANTHROPIC,
    auth_mode=AuthMode.STANDALONE,
    api_key="sk-ant-...",
    default_model="claude-sonnet-4-20250514",
)

# OAuth 설정
oauth_config = ProviderConfig(
    provider_type=ProviderType.ANTHROPIC,
    auth_mode=AuthMode.OAUTH,
    # access_token은 auth.json에서 자동 로드
)

# SDK 설정 (with system prompt)
sdk_config = ProviderConfig(
    provider_type=ProviderType.ANTHROPIC,
    auth_mode=AuthMode.SDK,
    system_prompt="You are a helpful assistant.",
    max_turns=20,
)

# GLM 설정
glm_config = ProviderConfig(
    provider_type=ProviderType.GLM,
    auth_mode=AuthMode.GLM,
    api_key="your-zai-api-key",
    base_url="https://api.z.ai/api/coding/paas/v4",
)
```

---

## 6. 사용 예제

### 6.1 기본 사용

```python
from src.llm.client import create_client

# 간단한 생성
client = create_client(
    provider_type="anthropic",
    api_key="sk-ant-...",
)

# 대화
response = await client.chat("안녕하세요!")
print(response)

# 시스템 프롬프트 포함
response = await client.chat(
    "주식 분석을 해주세요.",
    system="당신은 금융 전문가입니다.",
    model="claude-sonnet-4-20250514",
)
```

### 6.2 도구 사용 (Tool Use)

```python
from src.llm.client import create_client, ToolExecutor
from src.llm.providers.base import ToolDefinition

# 도구 정의
search_tool = ToolDefinition(
    name="search_stock",
    description="주식 정보를 검색합니다.",
    parameters={
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "주식 심볼"}
        },
        "required": ["symbol"]
    }
)

# 도구 실행기
async def execute_tool(name: str, args: dict) -> str:
    if name == "search_stock":
        # 실제 주식 정보 조회 로직
        return f"AAPL: $150.00 (+2.5%)"
    return "Unknown tool"

# 클라이언트 생성
client = create_client(
    provider_type="anthropic",
    api_key="sk-ant-...",
    tool_executor=execute_tool,
)

# 도구를 사용한 대화
response = await client.chat(
    "AAPL 주식 가격을 알려주세요.",
    tools=[search_tool],
)
```

### 6.3 다중 제공자 클라이언트

```python
from src.llm.client import create_multi_provider_client
from src.llm.providers.base import ProviderConfig, ProviderType, AuthMode

# 여러 제공자 설정
client = create_multi_provider_client({
    "anthropic": ProviderConfig(
        provider_type=ProviderType.ANTHROPIC,
        auth_mode=AuthMode.STANDALONE,
        api_key="sk-ant-...",
    ),
    "openai": ProviderConfig(
        provider_type=ProviderType.OPENAI,
        auth_mode=AuthMode.STANDALONE,
        api_key="sk-...",
    ),
    "google": ProviderConfig(
        provider_type=ProviderType.GOOGLE,
        auth_mode=AuthMode.STANDALONE,
        api_key="...",
    ),
})

# 모델명으로 자동 제공자 선택
response = await client.chat("Hello", model="claude-3-opus")  # Anthropic 사용
response = await client.chat("Hello", model="gpt-4")          # OpenAI 사용
response = await client.chat("Hello", model="gemini-pro")     # Google 사용
```

### 6.4 스트리밍 응답

```python
async for chunk in client.chat_stream("긴 이야기를 해주세요."):
    print(chunk, end="", flush=True)
```

### 6.5 구조화된 응답

```python
from pydantic import BaseModel
from src.llm.providers.factory import ProviderFactory

class StockAnalysis(BaseModel):
    symbol: str
    price: float
    recommendation: str
    confidence: float

provider = ProviderFactory.create_anthropic(
    api_key="sk-ant-...",
)

analysis = await provider.generate_structured(
    "AAPL 주식을 분석해주세요.",
    schema=StockAnalysis,
)
print(f"추천: {analysis.recommendation} (신뢰도: {analysis.confidence})")
```

### 6.6 OAuth 제공자 사용

```python
from src.llm.providers.factory import ProviderFactory
from src.llm.providers.base import AuthMode

# OAuth 제공자 생성 (auth.json에서 토큰 로드)
provider = ProviderFactory.create_anthropic(
    auth_mode=AuthMode.OAUTH,
)

# 사용
response = await provider.chat([
    Message(role="user", content="Hello!")
])
```

### 6.7 GLM 제공자 사용

```python
from src.llm.providers.factory import ProviderFactory

# GLM 제공자 생성
provider = ProviderFactory.create_glm(
    api_key="your-zai-api-key",
    model="glm-4.7",
)

response = await provider.generate("안녕하세요!")
```

---

## 7. 사용된 디자인 패턴

### 7.1 Factory 패턴

`ProviderFactory`는 설정에 따라 적절한 제공자 인스턴스를 생성합니다.

```python
class ProviderFactory:
    @staticmethod
    def create(config: ProviderConfig) -> BaseLLMProvider:
        if config.auth_mode == AuthMode.OAUTH:
            return OAuthProvider(config)
        elif config.auth_mode == AuthMode.STANDALONE:
            return StandaloneProvider(config)
        elif config.auth_mode == AuthMode.SDK:
            return SDKProvider(config)
        elif config.auth_mode == AuthMode.GLM:
            return GLMProvider(config)
```

**장점**:
- 생성 로직 캡슐화
- 조건부 생성 중앙 관리
- 클라이언트 코드와 생성 로직 분리

### 7.2 Strategy 패턴

각 제공자는 동일한 인터페이스(`BaseLLMProvider`)를 구현하며, 런타임에 교체 가능합니다.

```python
# 클라이언트는 제공자 구현을 알 필요 없음
class LLMClient:
    def __init__(self, provider: BaseLLMProvider):
        self._provider = provider

    async def chat(self, messages):
        # 어떤 제공자든 동일하게 호출
        return await self._provider.chat(messages)
```

**장점**:
- 제공자 간 교체 용이
- 새로운 제공자 추가 시 기존 코드 수정 불필요

### 7.3 Registry 패턴

`ProviderRegistry`는 여러 제공자를 관리하고 지연 초기화를 지원합니다.

```python
class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}
        self._configs: dict[str, ProviderConfig] = {}

    def register(self, name, provider=None, config=None):
        if provider:
            self._providers[name] = provider
        elif config:
            self._configs[name] = config  # 지연 초기화용

    def get_provider(self, name) -> BaseLLMProvider:
        if name in self._providers:
            return self._providers[name]
        if name in self._configs:
            # 최초 요청 시 초기화
            provider = ProviderFactory.create(self._configs[name])
            self._providers[name] = provider
            return provider
```

**장점**:
- 리소스 절약 (필요 시에만 초기화)
- 중앙화된 제공자 관리

### 7.4 Template Method 패턴

`BaseLLMProvider`는 공통 로직을 정의하고, 구체적인 구현은 하위 클래스에 위임합니다.

```python
class BaseLLMProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self._config = config
        self._default_model = config.default_model

    @property
    def provider_type(self) -> ProviderType:
        return self._config.provider_type  # 공통 로직

    @abstractmethod
    async def chat(self, messages, **kwargs) -> LLMResponse:
        pass  # 하위 클래스에서 구현
```

### 7.5 Adapter 패턴

각 제공자는 외부 API/SDK를 내부 메시지 형식으로 변환합니다.

```python
class StandaloneProvider(BaseLLMProvider):
    def _convert_anthropic_messages(self, messages: list[Message]):
        # 내부 Message → Anthropic API 형식
        ...

    def _parse_anthropic_response(self, response) -> LLMResponse:
        # Anthropic API 응답 → 내부 LLMResponse
        ...
```

---

## 8. 확장 포인트

### 8.1 새 제공자 추가하기

새로운 LLM 제공자를 추가하려면 다음 단계를 따릅니다.

#### Step 1: ProviderType 추가

```python
# src/llm/providers/base.py
class ProviderType(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    GLM = "glm"
    NEW_PROVIDER = "new_provider"  # 추가
```

#### Step 2: AuthMode 추가 (필요 시)

```python
class AuthMode(str, Enum):
    OAUTH = "oauth"
    STANDALONE = "standalone"
    SDK = "sdk"
    GLM = "glm"
    NEW_AUTH = "new_auth"  # 필요 시 추가
```

#### Step 3: Provider 클래스 구현

```python
# src/llm/providers/new_provider.py
from src.llm.providers.base import (
    BaseLLMProvider,
    LLMResponse,
    Message,
    ProviderConfig,
    ToolCall,
    ToolDefinition,
)

class NewProvider(BaseLLMProvider):
    """새로운 LLM 제공자."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # 초기화 로직
        self._client = self._init_client()

    def _init_client(self):
        """SDK 클라이언트 초기화."""
        pass

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """내부 Message를 API 형식으로 변환."""
        result = []
        for msg in messages:
            # 변환 로직
            result.append({"role": msg.role, "content": msg.content})
        return result

    def _parse_response(self, response) -> LLMResponse:
        """API 응답을 LLMResponse로 변환."""
        return LLMResponse(
            content=response.text,
            tool_calls=[],
            finish_reason=response.finish_reason,
            model=response.model,
            usage=response.usage,
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        messages = [Message(role="user", content=prompt)]
        response = await self.chat(messages, **kwargs)
        return response.content

    async def generate_structured(self, prompt: str, schema: Type[T], **kwargs) -> T:
        # 구조화된 출력 구현
        pass

    async def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        if system:
            messages = [Message(role="system", content=system)] + messages

        converted = self._convert_messages(messages)
        response = await self._client.chat(converted, model=model or self._default_model)
        return self._parse_response(response)

    async def chat_stream(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        # 스트리밍 구현
        async for chunk in self._client.stream(...):
            yield chunk.text
```

#### Step 4: Factory에 등록

```python
# src/llm/providers/factory.py
from src.llm.providers.new_provider import NewProvider

class ProviderFactory:
    @staticmethod
    def create(config: ProviderConfig) -> BaseLLMProvider:
        if config.auth_mode == AuthMode.OAUTH:
            return OAuthProvider(config)
        elif config.auth_mode == AuthMode.STANDALONE:
            return StandaloneProvider(config)
        elif config.auth_mode == AuthMode.SDK:
            return SDKProvider(config)
        elif config.auth_mode == AuthMode.GLM:
            return GLMProvider(config)
        elif config.auth_mode == AuthMode.NEW_AUTH:  # 추가
            return NewProvider(config)
```

#### Step 5: 모델 prefix 등록 (자동 라우팅용)

```python
# src/llm/client.py
NEW_PROVIDER_MODEL_PREFIXES = ("newmodel",)

def detect_provider_from_model(model: str) -> ProviderName:
    model_lower = model.lower()
    if model_lower.startswith(ANTHROPIC_MODEL_PREFIXES):
        return "anthropic"
    if model_lower.startswith(NEW_PROVIDER_MODEL_PREFIXES):  # 추가
        return "new_provider"
    # ...
```

### 8.2 새 인증 모드 추가하기

#### Step 1: AuthMode 추가

```python
class AuthMode(str, Enum):
    # 기존 모드들...
    CUSTOM_AUTH = "custom_auth"
```

#### Step 2: 인증 로직 구현

기존 제공자 클래스를 수정하거나 새 클래스를 생성하여 인증 로직을 추가합니다.

```python
class CustomAuthProvider(BaseLLMProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._auth_token = self._authenticate()

    def _authenticate(self) -> str:
        """커스텀 인증 로직."""
        # 예: API 호출로 토큰 획득
        response = httpx.post("https://auth.example.com/token", ...)
        return response.json()["access_token"]
```

### 8.3 커스텀 Tool Executor 구현

```python
from src.llm.client import LLMClient, ToolExecutor

class MyToolExecutor:
    """커스텀 도구 실행기."""

    def __init__(self):
        self.tools = {}

    def register_tool(self, name: str, func):
        self.tools[name] = func

    async def __call__(self, name: str, args: dict) -> str:
        if name not in self.tools:
            return f"Unknown tool: {name}"
        return await self.tools[name](**args)

# 사용
executor = MyToolExecutor()
executor.register_tool("search", search_function)
executor.register_tool("calculate", calculate_function)

client = LLMClient(provider=provider, tool_executor=executor)
```

---

## 부록: 파일 구조

```
src/llm/
├── __init__.py
├── client.py              # LLMClient, ProviderRegistry, 유틸리티 함수
└── providers/
    ├── __init__.py
    ├── base.py            # BaseLLMProvider, 데이터 모델
    ├── factory.py         # ProviderFactory
    ├── oauth.py           # OAuthProvider (Anthropic, OpenAI)
    ├── standalone.py      # StandaloneProvider (SDK 기반)
    ├── sdk.py             # SDKProvider (Claude Code SDK)
    └── glm.py             # GLMProvider (Z.AI)
```

---

## 참고 자료

- [Anthropic API 문서](https://docs.anthropic.com/)
- [OpenAI API 문서](https://platform.openai.com/docs/)
- [Google AI API 문서](https://ai.google.dev/docs)
- [Claude Code SDK](https://github.com/anthropics/claude-code-sdk)

---

**작성자**: OhMyStock Team
**라이선스**: MIT
