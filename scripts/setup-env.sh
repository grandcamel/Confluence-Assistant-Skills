#!/bin/bash
# ==============================================================================
# Environment Setup Script for Confluence Assistant Skills
# ==============================================================================
# Interactively configures environment variables needed for the project.
# Writes to ~/.env and configures shell to load them automatically.
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

ENV_FILE="$HOME/.env"
BACKUP_FILE="$HOME/.env.backup.$(date +%Y%m%d_%H%M%S)"

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║${NC}  ${BOLD}Confluence Assistant Skills - Environment Setup${NC}            ${BOLD}${BLUE}║${NC}"
    echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_tip() {
    echo -e "${DIM}  Tip: $1${NC}"
}

# Mask a secret value, showing only first 4 and last 4 characters
mask_secret() {
    local value="$1"
    local len=${#value}
    if [[ $len -le 8 ]]; then
        echo "********"
    else
        echo "${value:0:4}...${value: -4}"
    fi
}

# Read existing value from ~/.env
get_existing_value() {
    local var_name="$1"
    if [[ -f "$ENV_FILE" ]]; then
        grep "^${var_name}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '"' || echo ""
    else
        echo ""
    fi
}

# Prompt for input with default value
prompt_value() {
    local var_name="$1"
    local description="$2"
    local default="$3"
    local is_secret="$4"
    local is_required="$5"

    local existing
    existing=$(get_existing_value "$var_name")

    local display_default="$default"
    if [[ -n "$existing" ]]; then
        if [[ "$is_secret" == "yes" ]]; then
            display_default=$(mask_secret "$existing")
        else
            display_default="$existing"
        fi
    fi

    echo ""
    echo -e "${BOLD}$var_name${NC}"
    echo -e "${DIM}$description${NC}"

    local prompt_text
    if [[ -n "$display_default" ]]; then
        prompt_text="Enter value [${display_default}]: "
    else
        prompt_text="Enter value: "
    fi

    local value
    if [[ "$is_secret" == "yes" ]]; then
        read -rsp "$prompt_text" value
        echo ""
    else
        read -rp "$prompt_text" value
    fi

    # Use existing value if empty input and existing value exists
    if [[ -z "$value" && -n "$existing" ]]; then
        value="$existing"
    # Use default if empty input and no existing value
    elif [[ -z "$value" && -n "$default" ]]; then
        value="$default"
    fi

    # Check required
    if [[ "$is_required" == "yes" && -z "$value" ]]; then
        print_error "This field is required"
        prompt_value "$var_name" "$description" "$default" "$is_secret" "$is_required"
        return
    fi

    echo "$value"
}

# Validate URL format
validate_url() {
    local url="$1"
    if [[ "$url" =~ ^https?:// ]]; then
        return 0
    else
        return 1
    fi
}

# Validate email format
validate_email() {
    local email="$1"
    if [[ "$email" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
        return 0
    else
        return 1
    fi
}

# ==============================================================================
# Configuration Variables
# ==============================================================================

declare -A CONFIG

prompt_confluence_url() {
    print_section "Confluence Site URL"
    print_tip "Your Atlassian Cloud URL, e.g., https://yourcompany.atlassian.net"

    while true; do
        local value
        value=$(prompt_value "CONFLUENCE_SITE_URL" "The URL of your Confluence Cloud instance" "https://yourcompany.atlassian.net" "no" "yes")

        if validate_url "$value"; then
            # Remove trailing slash if present
            CONFIG[CONFLUENCE_SITE_URL]="${value%/}"
            print_success "URL format valid"
            break
        else
            print_error "Invalid URL format. Must start with http:// or https://"
        fi
    done
}

prompt_confluence_email() {
    print_section "Confluence Email"
    print_tip "The email address associated with your Atlassian account"

    while true; do
        local value
        value=$(prompt_value "CONFLUENCE_EMAIL" "Your Atlassian account email address" "" "no" "yes")

        if validate_email "$value"; then
            CONFIG[CONFLUENCE_EMAIL]="$value"
            print_success "Email format valid"
            break
        else
            print_error "Invalid email format"
        fi
    done
}

prompt_confluence_token() {
    print_section "Confluence API Token"
    print_tip "Create a token at: https://id.atlassian.com/manage-profile/security/api-tokens"
    print_info "The token will be stored securely and masked in output"

    while true; do
        local value
        value=$(prompt_value "CONFLUENCE_API_TOKEN" "Your Atlassian API token (will be hidden)" "" "yes" "yes")

        if [[ -n "$value" ]]; then
            CONFIG[CONFLUENCE_API_TOKEN]="$value"
            print_success "API token set"
            break
        else
            print_error "API token is required"
        fi
    done
}

prompt_confluence_profile() {
    print_section "Confluence Profile (Optional)"
    print_tip "Use profiles to switch between multiple Confluence instances"
    print_info "Press Enter to use 'default'"

    local value
    value=$(prompt_value "CONFLUENCE_PROFILE" "Profile name for this configuration" "default" "no" "no")

    CONFIG[CONFLUENCE_PROFILE]="${value:-default}"
    print_success "Profile set to: ${CONFIG[CONFLUENCE_PROFILE]}"
}

# ==============================================================================
# Connection Test
# ==============================================================================

test_connection() {
    print_section "Connection Test"

    echo ""
    read -rp "Would you like to test the connection? [Y/n]: " test_choice

    if [[ "${test_choice,,}" == "n" ]]; then
        print_info "Skipping connection test"
        return 0
    fi

    echo ""
    print_info "Testing connection to Confluence..."

    local url="${CONFIG[CONFLUENCE_SITE_URL]}/wiki/api/v2/spaces?limit=1"
    local auth
    auth=$(echo -n "${CONFIG[CONFLUENCE_EMAIL]}:${CONFIG[CONFLUENCE_API_TOKEN]}" | base64)

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Basic $auth" \
        -H "Content-Type: application/json" \
        "$url" 2>/dev/null || echo "000")

    case "$http_code" in
        200)
            print_success "Connection successful! (HTTP $http_code)"
            return 0
            ;;
        401)
            print_error "Authentication failed (HTTP 401)"
            print_tip "Check your email and API token"
            return 1
            ;;
        403)
            print_error "Access forbidden (HTTP 403)"
            print_tip "Your token may not have the required permissions"
            return 1
            ;;
        404)
            print_error "Endpoint not found (HTTP 404)"
            print_tip "Verify your Confluence URL is correct"
            return 1
            ;;
        000)
            print_error "Connection failed - could not reach server"
            print_tip "Check your URL and network connection"
            return 1
            ;;
        *)
            print_warning "Unexpected response (HTTP $http_code)"
            return 1
            ;;
    esac
}

# ==============================================================================
# Shell Configuration
# ==============================================================================

LOADER_BLOCK='
# ============================================================================
# Load Environment Variables from ~/.env
# ============================================================================
if [ -f ~/.env ]; then
    set -a  # Automatically export all variables
    source ~/.env
    set +a  # Disable automatic export
fi'

configure_shell() {
    print_section "Shell Configuration"

    local shell_rc
    if [[ "$SHELL" == *"zsh"* ]]; then
        shell_rc="$HOME/.zshrc"
        print_info "Detected shell: zsh"
    else
        shell_rc="$HOME/.bashrc"
        print_info "Detected shell: bash"
    fi

    # Check if loader already exists
    if grep -q "Load Environment Variables from ~/.env" "$shell_rc" 2>/dev/null; then
        print_success "Shell already configured to load ~/.env"
        return 0
    fi

    echo ""
    read -rp "Add ~/.env loader to $shell_rc? [Y/n]: " add_loader

    if [[ "${add_loader,,}" != "n" ]]; then
        echo "$LOADER_BLOCK" >> "$shell_rc"
        print_success "Added loader block to $shell_rc"
    else
        print_warning "Skipped shell configuration"
        print_tip "You'll need to manually source ~/.env or add the loader block"
    fi
}

# ==============================================================================
# Save Configuration
# ==============================================================================

save_configuration() {
    print_section "Saving Configuration"

    # Backup existing file
    if [[ -f "$ENV_FILE" ]]; then
        cp "$ENV_FILE" "$BACKUP_FILE"
        print_info "Backed up existing config to: $BACKUP_FILE"
    fi

    # Read existing env file (excluding our variables)
    local other_vars=""
    if [[ -f "$ENV_FILE" ]]; then
        other_vars=$(grep -v "^CONFLUENCE_" "$ENV_FILE" 2>/dev/null || echo "")
    fi

    # Write new configuration
    {
        if [[ -n "$other_vars" ]]; then
            echo "$other_vars"
            echo ""
        fi
        echo "# Confluence Assistant Skills Configuration"
        echo "# Generated: $(date)"
        echo "CONFLUENCE_SITE_URL=\"${CONFIG[CONFLUENCE_SITE_URL]}\""
        echo "CONFLUENCE_EMAIL=\"${CONFIG[CONFLUENCE_EMAIL]}\""
        echo "CONFLUENCE_API_TOKEN=\"${CONFIG[CONFLUENCE_API_TOKEN]}\""
        echo "CONFLUENCE_PROFILE=\"${CONFIG[CONFLUENCE_PROFILE]}\""
    } > "$ENV_FILE"

    # Secure the file
    chmod 600 "$ENV_FILE"

    print_success "Configuration saved to $ENV_FILE"
    print_success "File permissions set to 600 (owner read/write only)"
}

# ==============================================================================
# Summary
# ==============================================================================

print_summary() {
    print_section "Configuration Summary"

    echo ""
    echo -e "  ${BOLD}CONFLUENCE_SITE_URL${NC}:  ${CONFIG[CONFLUENCE_SITE_URL]}"
    echo -e "  ${BOLD}CONFLUENCE_EMAIL${NC}:     ${CONFIG[CONFLUENCE_EMAIL]}"
    echo -e "  ${BOLD}CONFLUENCE_API_TOKEN${NC}: $(mask_secret "${CONFIG[CONFLUENCE_API_TOKEN]}")"
    echo -e "  ${BOLD}CONFLUENCE_PROFILE${NC}:   ${CONFIG[CONFLUENCE_PROFILE]}"
    echo ""
}

source_config() {
    echo ""
    read -rp "Source the configuration now? [Y/n]: " source_choice

    if [[ "${source_choice,,}" != "n" ]]; then
        set -a
        source "$ENV_FILE"
        set +a
        print_success "Configuration loaded into current shell"
    else
        print_info "Run 'source ~/.env' to load the configuration"
    fi
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    print_header

    print_info "This script will configure environment variables for Confluence Assistant Skills."
    print_info "Existing values will be shown as defaults (secrets will be masked)."
    echo ""

    # Gather configuration
    prompt_confluence_url
    prompt_confluence_email
    prompt_confluence_token
    prompt_confluence_profile

    # Test connection
    if ! test_connection; then
        echo ""
        read -rp "Connection test failed. Continue anyway? [y/N]: " continue_choice
        if [[ "${continue_choice,,}" != "y" ]]; then
            print_error "Setup cancelled"
            exit 1
        fi
    fi

    # Save configuration
    save_configuration

    # Configure shell
    configure_shell

    # Print summary
    print_summary

    # Offer to source
    source_config

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${BOLD}Setup Complete!${NC}                                            ${GREEN}║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    print_tip "Start a new terminal or run 'source ~/.env' to use the configuration"
    echo ""
}

main "$@"
