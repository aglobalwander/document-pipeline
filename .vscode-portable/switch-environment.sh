#!/bin/bash

# Smart Environment Switcher for VS Code + Conda/Micromamba
# Usage: ./switch-environment.sh [environment-name|auto]

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to detect conda/mamba executable
detect_conda() {
    if command -v conda &> /dev/null; then
        echo "conda"
    elif command -v mamba &> /dev/null; then
        echo "mamba"
    elif command -v micromamba &> /dev/null; then
        echo "micromamba"
    else
        echo "none"
    fi
}

# Function to list available environments
list_environments() {
    echo -e "${GREEN}Available Python Environments:${NC}"
    
    CONDA_CMD=$(detect_conda)
    if [ "$CONDA_CMD" != "none" ]; then
        echo -e "${YELLOW}Conda/Mamba environments:${NC}"
        $CONDA_CMD env list | grep -v "^#" | awk '{print "  - "$1" ("$2")"}'
    fi
    
    echo -e "\n${YELLOW}Micromamba environments:${NC}"
    if [ -d "$HOME/micromamba/envs" ]; then
        ls -1 "$HOME/micromamba/envs" | while read env; do
            echo "  - micromamba:$env"
        done
    fi
    
    echo -e "\n${YELLOW}System Python:${NC}"
    which python3 &>/dev/null && echo "  - system ($(python3 --version 2>&1 | cut -d' ' -f2))"
    
    echo -e "\n${YELLOW}PHP (for Drupal):${NC}"
    which php &>/dev/null && echo "  - php ($(php -v | head -1 | cut -d' ' -f2))"
}

# Function to auto-detect environment based on file
auto_detect_environment() {
    local file_path="$1"
    
    # Check file extension and path
    case "$file_path" in
        */scripts/*.py|*/migration/*.py)
            echo "base"
            ;;
        */analysis/*.py|*/data-science/*.py)
            echo "ds-template"
            ;;
        */crawlers/*.py|*/scrapers/*.py)
            echo "my-crawler"
            ;;
        *.php|*.module|*.inc|*.theme)
            echo "php"
            ;;
        *.py)
            echo "drupal"  # Default Python env
            ;;
        *)
            echo "default"
            ;;
    esac
}

# Function to switch environment
switch_environment() {
    local env_name="$1"
    local settings_file="$PROJECT_ROOT/.vscode/settings.json"
    
    echo -e "${GREEN}Switching to environment: $env_name${NC}"
    
    case "$env_name" in
        base|ds-template|my-crawler)
            # Conda environments
            CONDA_CMD=$(detect_conda)
            if [ "$CONDA_CMD" != "none" ]; then
                # Find the conda env path
                ENV_PATH=$($CONDA_CMD env list | grep "^$env_name " | awk '{print $2}')
                if [ -z "$ENV_PATH" ]; then
                    ENV_PATH="$HOME/anaconda3/envs/$env_name"
                    [ ! -d "$ENV_PATH" ] && ENV_PATH="$HOME/miniconda3/envs/$env_name"
                fi
                PYTHON_PATH="$ENV_PATH/bin/python"
            else
                echo -e "${RED}Error: Conda/Mamba not found${NC}"
                exit 1
            fi
            ;;
        drupal)
            # Micromamba drupal environment
            PYTHON_PATH="$HOME/micromamba/envs/drupal/bin/python"
            ;;
        system)
            # System Python
            PYTHON_PATH=$(which python3)
            ;;
        php)
            echo -e "${YELLOW}PHP environment - no Python interpreter change needed${NC}"
            return 0
            ;;
        *)
            echo -e "${RED}Unknown environment: $env_name${NC}"
            list_environments
            exit 1
            ;;
    esac
    
    # Update VS Code settings
    if [ -f "$settings_file" ]; then
        # Create backup
        cp "$settings_file" "$settings_file.backup"
        
        # Update the defaultInterpreterPath
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|\"python.defaultInterpreterPath\":.*|\"python.defaultInterpreterPath\": \"$PYTHON_PATH\",|" "$settings_file"
        else
            # Linux
            sed -i "s|\"python.defaultInterpreterPath\":.*|\"python.defaultInterpreterPath\": \"$PYTHON_PATH\",|" "$settings_file"
        fi
        
        echo -e "${GREEN}✅ VS Code settings updated${NC}"
        echo -e "   Python interpreter: $PYTHON_PATH"
    else
        echo -e "${RED}Error: VS Code settings.json not found${NC}"
        exit 1
    fi
    
    # Create a marker file for agents to detect
    echo "$env_name" > "$PROJECT_ROOT/.current_environment"
    echo "PYTHON_PATH=$PYTHON_PATH" >> "$PROJECT_ROOT/.current_environment"
    
    # If VS Code is running, reload window
    if command -v code &> /dev/null; then
        echo -e "${YELLOW}Reload VS Code window to apply changes (Cmd+R)${NC}"
    fi
}

# Function for agents/LLMs to detect current environment
get_current_environment() {
    if [ -f "$PROJECT_ROOT/.current_environment" ]; then
        cat "$PROJECT_ROOT/.current_environment"
    else
        echo "default"
    fi
}

# Main execution
main() {
    case "$1" in
        list)
            list_environments
            ;;
        current)
            get_current_environment
            ;;
        auto)
            # Auto-detect based on current file
            if [ -n "$2" ]; then
                ENV=$(auto_detect_environment "$2")
                switch_environment "$ENV"
            else
                echo -e "${RED}Error: Please provide a file path for auto-detection${NC}"
                echo "Usage: $0 auto <file_path>"
            fi
            ;;
        "")
            echo "Usage: $0 [list|current|auto <file>|<environment-name>]"
            echo ""
            list_environments
            ;;
        *)
            switch_environment "$1"
            ;;
    esac
}

main "$@"