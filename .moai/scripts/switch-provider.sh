#!/bin/bash
# LLM Provider Switcher for Claude Code (Project-Specific)
# Switches between Claude (Anthropic) and GLM (Z.AI) providers
#
# This script modifies .claude/settings.local.json to apply LLM provider settings
# ONLY for the current project.
#
# Usage:
#   ./switch-provider.sh           # Toggle provider (claude <-> glm)
#   ./switch-provider.sh claude    # Switch to Claude (Anthropic)
#   ./switch-provider.sh glm       # Switch to GLM (Z.AI)
#   ./switch-provider.sh status    # Show current provider

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Settings file path
SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.local.json"
ENV_GLM_FILE="$PROJECT_ROOT/.env.glm"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if settings file exists
check_settings_file() {
    if [[ ! -f "$SETTINGS_FILE" ]]; then
        log_error "Settings file not found: $SETTINGS_FILE"
        echo "Please ensure .claude/settings.local.json exists in your project."
        exit 1
    fi
}

# Get current provider from settings.local.json
get_current_provider() {
    check_settings_file

    local base_url
    base_url=$(jq -r '.env.ANTHROPIC_BASE_URL // "empty"' "$SETTINGS_FILE" 2>/dev/null || echo "empty")

    if [[ "$base_url" == *"api.z.ai"* ]]; then
        echo "glm"
    elif [[ "$base_url" == "empty" ]] || [[ -z "$base_url" ]] || [[ "$base_url" == *"anthropic.com"* ]] || [[ "$base_url" == "null" ]]; then
        echo "claude"
    else
        echo "unknown"
    fi
}

# Show current provider status
show_status() {
    local current
    current=$(get_current_provider)

    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}     Claude Code LLM Provider Status${NC}"
    echo -e "${CYAN}     (Project-Specific: ${PROJECT_ROOT##*/})${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo ""

    case "$current" in
        claude)
            echo -e "${GREEN}● Current Provider: Claude (Anthropic)${NC}"
            echo -e "  ${BLUE}API Endpoint:${NC} https://api.anthropic.com (default)"
            echo -e "  ${BLUE}Models:${NC} claude-opus-4-5-20251101, claude-sonnet-4-20250514"
            ;;
        glm)
            local base_url model
            base_url=$(jq -r '.env.ANTHROPIC_BASE_URL // "not set"' "$SETTINGS_FILE" 2>/dev/null)
            model=$(jq -r '.env.ANTHROPIC_DEFAULT_OPUS_MODEL // "not set"' "$SETTINGS_FILE" 2>/dev/null)
            echo -e "${GREEN}● Current Provider: GLM (Z.AI)${NC}"
            echo -e "  ${BLUE}API Endpoint:${NC} $base_url"
            echo -e "  ${BLUE}Models:${NC} $model"
            ;;
        unknown)
            echo -e "${YELLOW}● Current Provider: Unknown${NC}"
            echo -e "  ${YELLOW}Unable to determine provider from settings${NC}"
            ;;
    esac

    echo ""
    echo -e "${CYAN}Settings File:${NC} $SETTINGS_FILE"
    echo ""
    echo -e "${CYAN}Current env settings:${NC}"
    if jq -e '.env' "$SETTINGS_FILE" &> /dev/null; then
        jq -r '.env | to_entries[] | "  \(.key) = \(.value // "<not set>")"' "$SETTINGS_FILE" 2>/dev/null
    else
        echo "  No env settings found"
    fi
    echo ""
    echo -e "${CYAN}Usage:${NC} $0 [claude|glm|status]"
    echo ""
}

# Update settings.local.json with provider configuration
update_settings() {
    local provider="$1"

    check_settings_file

    if [[ "$provider" == "glm" ]]; then
        # Read ANTHROPIC_AUTH_TOKEN from .env.glm file
        if [[ ! -f "$ENV_GLM_FILE" ]]; then
            log_error "GLM env file not found: $ENV_GLM_FILE"
            exit 1
        fi

        local auth_token
        auth_token=$(grep "^ANTHROPIC_AUTH_TOKEN=" "$ENV_GLM_FILE" | cut -d'=' -f2 | tr -d ' \n\r"')

        if [[ -z "$auth_token" ]]; then
            log_error "ANTHROPIC_AUTH_TOKEN not found in $ENV_GLM_FILE"
            exit 1
        fi

        # Set GLM configuration - create complete env object
        jq --arg token "$auth_token" '
            .env = {
                "ANTHROPIC_AUTH_TOKEN": $token,
                "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
                "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-4.7",
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.7",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.7",
                "API_TIMEOUT_MS": "3000000"
            }
        ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    else
        # Remove entire env field for Claude mode (use default)
        jq 'del(.env)' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    fi
}

# Toggle provider (claude <-> glm)
toggle_provider() {
    local current_provider
    current_provider=$(get_current_provider)

    local target_provider
    case "$current_provider" in
        claude)
            target_provider="glm"
            ;;
        glm)
            target_provider="claude"
            ;;
        *)
            # Default to claude if unknown
            target_provider="claude"
            ;;
    esac

    switch_provider "$target_provider"
}

# Main switch function
switch_provider() {
    local target_provider="$1"
    local current_provider
    current_provider=$(get_current_provider)

    # Normalize provider names
    case "$target_provider" in
        claude|anthropic)
            target_provider="claude"
            ;;
        glm|zhipu|z.ai)
            target_provider="glm"
            ;;
        *)
            log_error "Invalid provider: $target_provider"
            echo "Valid providers: claude, glm"
            exit 1
            ;;
    esac

    # Check if already set
    if [[ "$current_provider" == "$target_provider" ]]; then
        log_warning "Already using provider: $target_provider"
        show_status
        exit 0
    fi

    # Apply changes
    log_info "Switching LLM provider: $current_provider → $target_provider"
    log_info "Project: ${PROJECT_ROOT##*/}"

    # Update settings.local.json
    update_settings "$target_provider"

    log_success "LLM Provider switched successfully!"
    echo ""
    echo -e "${YELLOW}IMPORTANT:${NC}"
    echo "  ✓ Settings updated: $SETTINGS_FILE"
    echo "  ✓ Project-specific only (does not affect other projects)"
    echo "  ✓ Restart Claude Code or start a new session to apply changes"
    echo ""

    show_status
}

# Main
main() {
    local command="${1:-}"

    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed."
        echo ""
        echo "Install jq:"
        echo "  brew install jq"
        exit 1
    fi

    # No argument: toggle mode
    if [[ -z "$command" ]]; then
        toggle_provider
        return
    fi

    case "$command" in
        status|--status|-s)
            show_status
            ;;
        claude|--claude|-c)
            switch_provider "claude"
            ;;
        glm|--glm|-g)
            switch_provider "glm"
            ;;
        *)
            log_error "Unknown command: $command"
            echo ""
            echo "Usage: $0 [claude|glm|status]"
            echo ""
            echo "Commands:"
            echo "  (no arg) Toggle between providers"
            echo "  claude   Switch to Claude (Anthropic) provider"
            echo "  glm      Switch to GLM (Z.AI) provider"
            echo "  status   Show current provider status"
            echo ""
            echo "Note: Changes only affect this project (.claude/settings.local.json)"
            exit 1
            ;;
    esac
}

main "$@"
