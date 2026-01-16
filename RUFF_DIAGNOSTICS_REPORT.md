# Ruff Diagnostics Complete (uv environment)

## Command Used
```bash
uv run --dev ruff check app/ --output-format=full
```

## Summary
- **Total Issues:** 81
- **Auto-fixable (safe):** 50
- **Auto-fixable (unsafe):** 16
- **Manual fixes required:** 15

## Issues by Error Code

| Code | Count | Description | Auto-fixable |
|------|-------|-------------|--------------|
| F401 | 17 | Unused imports | Yes |
| I001 | 11 | Unsorted imports | Yes |
| W293 | 6 | Blank lines with whitespace | Yes |
| ARG002 | 6 | Unused method arguments | No |
| TC003 | 4 | Typing-only std lib imports | Yes |
| UP046 | 4 | Non-PEP695 generic class | Yes |
| RUF022 | 4 | Unsorted `__all__` | Yes |
| RET504 | 4 | Unnecessary assignment | Yes (unsafe) |
| PIE790 | 3 | Unnecessary placeholder | Yes |
| RET505 | 3 | Superfluous else return | Yes |
| RUF012 | 3 | Mutable class default | No |
| UP017 | 2 | datetime timezone UTC | Yes |
| UP037 | 2 | Quoted annotation | Yes |
| UP041 | 2 | Timeout error alias | Yes |
| UP043 | 2 | Unnecessary default type args | Yes |
| SIM102 | 2 | Collapsible if | No |
| B007 | 1 | Unused loop control variable | No |
| N811 | 1 | Constant imported as non-constant | No |
| SIM103 | 1 | Needless bool | No |
| SIM118 | 1 | In dict keys | Yes |
| TC005 | 1 | Empty type-checking block | Yes |
| UP040 | 1 | Non-PEP695 type alias | Yes (unsafe) |

## Top Files by Issue Count

1. **services/tool_service.py** - 9 issues
2. **services/workflow/processors/base.py** - 8 issues  
3. **services/workflow/processors/registry.py** - 8 issues
4. **services/workflow/validator.py** - 7 issues
5. **core/jwt.py** - 5 issues

## Auto-Fix Plan

### Phase 1: Safe Auto-Fix (50 issues)
```bash
uv run ruff check app/ --fix
```

This will fix:
- All unused imports (F401) - 17 issues
- All unsorted imports (I001) - 11 issues
- All whitespace issues (W293) - 6 issues
- Type annotation modernization (UP017, UP037, UP041, UP043, UP046) - 14 issues
- Unsorted `__all__` (RUF022) - 4 issues
- Unnecessary placeholders (PIE790) - 3 issues
- Superfluous else returns (RET505) - 3 issues
- Type checking improvements (TC003, TC005) - 5 issues
- Dictionary membership test (SIM118) - 1 issue

### Phase 2: Unsafe Auto-Fix (16 issues)
```bash
uv run ruff check app/ --fix --unsafe-fixes
```

This will additionally fix:
- Unnecessary assignments before return (RET504) - 4 issues
- Type alias modernization (UP040) - 1 issue

### Phase 3: Manual Fixes (15 issues)

#### High Priority (Code Quality)

**ARG002 - Unused method arguments (6 issues):**
- services/executors/http_executor.py:215 - `body` parameter
- services/workflow/processors/adapter.py:24 - `validated_input` parameter
- services/workflow/processors/agent.py:24 - `validated_input` parameter
- services/workflow/processors/aggregator.py:24 - `validated_input` parameter
- services/workflow/processors/condition.py:24 - `validated_input` parameter
- services/workflow/processors/trigger.py:24 - `validated_input` parameter

**RUF012 - Mutable class defaults (3 issues):**
- services/tool_service.py:58
- services/executors/http_executor.py:26
- services/executors/base.py:62

**SIM102 - Collapsible if statements (2 issues):**
- services/workflow/validator.py:827, 828

#### Medium Priority (Style)

**N811 - Constant naming (1 issue):**
- models/tool_spec009.py:30 - `SQLiteJSON` should be `JSON`

**SIM103 - Needless bool (1 issue):**
- services/workflow/validator.py:959

**B007 - Unused loop variable (1 issue):**
- services/tool_service.py:315 - `node` variable

## Files Summary
- **Total files affected:** 35
- **Files with 5+ issues:** 6 files
- **Most critical file:** services/workflow/processors/registry.py (8 unused imports)

## Recommended Action Plan
1. Run `uv run ruff check app/ --fix` to fix 50 safe issues
2. Review and apply unsafe fixes: `uv run ruff check app/ --fix --unsafe-fixes`
3. Manually fix remaining 15 issues, prioritizing ARG002 (unused arguments)
4. Re-run tests to ensure no regressions
5. Verify test coverage remains at 89.62% or higher
