#!/bin/bash

# Data Analysis VSCode Setup Script
# Optimized for Python, Jupyter, and Survey Analysis workflows

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${CYAN}${BOLD}========================================${NC}"
echo -e "${CYAN}${BOLD}  Data Analysis VSCode Setup${NC}"
echo -e "${CYAN}${BOLD}========================================${NC}"
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect Python environment
detect_python_env() {
    echo -e "${BLUE}→ Detecting Python environment...${NC}"
    
    # Check for conda ds-template environment first
    CONDA_BASE="/opt/homebrew/Caskroom/mambaforge/base"
    if [ -d "$CONDA_BASE/envs/ds-template" ]; then
        echo -e "${GREEN}  ✓ Found conda environment: ds-template${NC}"
        PYTHON_PATH="$CONDA_BASE/envs/ds-template/bin/python"
        CONDA_ENV="ds-template"
        CONDA_PATH="$CONDA_BASE/bin/conda"
    # Check for virtual environment
    elif [ -d "$PROJECT_ROOT/.venv" ]; then
        echo -e "${GREEN}  ✓ Found virtual environment at .venv${NC}"
        PYTHON_PATH="$PROJECT_ROOT/.venv/bin/python"
    elif [ -d "$PROJECT_ROOT/venv" ]; then
        echo -e "${GREEN}  ✓ Found virtual environment at venv${NC}"
        PYTHON_PATH="$PROJECT_ROOT/venv/bin/python"
    elif command_exists python3; then
        echo -e "${YELLOW}  ⚠ No virtual environment found, using system Python 3${NC}"
        PYTHON_PATH="$(which python3)"
    elif command_exists python; then
        echo -e "${YELLOW}  ⚠ No virtual environment found, using system Python${NC}"
        PYTHON_PATH="$(which python)"
    else
        echo -e "${RED}  ✗ Python not found!${NC}"
        echo -e "${YELLOW}  Please install Python 3.8+ or create conda environment ds-template${NC}"
        return 1
    fi
    
    # Get Python version
    PYTHON_VERSION=$($PYTHON_PATH --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}  ✓ Python version: $PYTHON_VERSION${NC}"
    
    if [ ! -z "$CONDA_ENV" ]; then
        echo -e "${GREEN}  ✓ Using conda environment: $CONDA_ENV${NC}"
    fi
}

# Function to check required packages
check_python_packages() {
    echo -e "${BLUE}→ Checking Python packages...${NC}"
    
    local packages=("pandas" "numpy" "matplotlib" "seaborn" "plotly" "jupyter" "notebook" "openai" "tiktoken")
    local missing_packages=()
    
    for package in "${packages[@]}"; do
        if $PYTHON_PATH -c "import $package" 2>/dev/null; then
            echo -e "${GREEN}  ✓ $package installed${NC}"
        else
            echo -e "${YELLOW}  ⚠ $package not installed${NC}"
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo
        echo -e "${YELLOW}Missing packages detected. Install with:${NC}"
        echo -e "${CYAN}  pip install ${missing_packages[*]}${NC}"
        echo
    fi
}

# Function to check environment variables
check_env_vars() {
    echo -e "${BLUE}→ Checking environment variables...${NC}"
    
    if [ -f "$PROJECT_ROOT/.env" ]; then
        echo -e "${GREEN}  ✓ .env file found${NC}"
        
        # Check for OPENAI_API_KEY
        if grep -q "OPENAI_API_KEY" "$PROJECT_ROOT/.env"; then
            echo -e "${GREEN}  ✓ OPENAI_API_KEY configured in .env${NC}"
        else
            echo -e "${YELLOW}  ⚠ OPENAI_API_KEY not found in .env${NC}"
            echo -e "${YELLOW}    Add: OPENAI_API_KEY=your_api_key_here${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠ No .env file found${NC}"
        echo -e "${YELLOW}    Create .env and add: OPENAI_API_KEY=your_api_key_here${NC}"
    fi
}

# Function to create VSCode directories
create_vscode_dirs() {
    echo -e "${BLUE}→ Creating VSCode configuration...${NC}"
    
    # Create .vscode directory if it doesn't exist
    if [ ! -d "$PROJECT_ROOT/.vscode" ]; then
        mkdir -p "$PROJECT_ROOT/.vscode"
        echo -e "${GREEN}  ✓ Created .vscode directory${NC}"
    else
        echo -e "${GREEN}  ✓ .vscode directory exists${NC}"
    fi
}

# Function to copy configuration files
copy_config_files() {
    echo -e "${BLUE}→ Copying configuration files...${NC}"
    
    # Copy settings.json
    if [ -f "$SCRIPT_DIR/settings.json" ]; then
        cp "$SCRIPT_DIR/settings.json" "$PROJECT_ROOT/.vscode/settings.json"
        echo -e "${GREEN}  ✓ Copied settings.json${NC}"
        
        # Update Python path in settings
        if [ ! -z "$PYTHON_PATH" ]; then
            sed -i.bak "s|\"python.defaultInterpreterPath\": .*|\"python.defaultInterpreterPath\": \"$PYTHON_PATH\",|" "$PROJECT_ROOT/.vscode/settings.json"
            rm -f "$PROJECT_ROOT/.vscode/settings.json.bak"
            echo -e "${GREEN}  ✓ Updated Python interpreter path${NC}"
        fi
    fi
    
    # Copy extensions.json
    if [ -f "$SCRIPT_DIR/extensions.json" ]; then
        cp "$SCRIPT_DIR/extensions.json" "$PROJECT_ROOT/.vscode/extensions.json"
        echo -e "${GREEN}  ✓ Copied extensions.json${NC}"
    fi
    
    # Copy launch.json for debugging
    if [ -f "$SCRIPT_DIR/launch.json" ]; then
        cp "$SCRIPT_DIR/launch.json" "$PROJECT_ROOT/.vscode/launch.json"
        echo -e "${GREEN}  ✓ Copied launch.json${NC}"
    fi
}

# Function to install VSCode extensions
install_extensions() {
    echo -e "${BLUE}→ Installing VSCode extensions...${NC}"
    
    if ! command_exists code; then
        echo -e "${YELLOW}  ⚠ VSCode CLI not found${NC}"
        echo -e "${YELLOW}    Install extensions manually from extensions.json${NC}"
        return
    fi
    
    # Core Python & Data Science extensions
    local extensions=(
        "ms-python.python"
        "ms-toolsai.jupyter"
        "ms-toolsai.jupyter-renderers"
        "mechatroner.rainbow-csv"
        "GrapeCity.gc-excelviewer"
        "RandomFractalsInc.vscode-data-preview"
        "yzhang.markdown-all-in-one"
        "njpwerner.autodocstring"
        "eamodio.gitlens"
        "usernamehw.errorlens"
        "Gruntfuggly.todo-tree"
        "GitHub.copilot"
        "redhat.vscode-yaml"
    )
    
    local installed=0
    local failed=0
    
    for ext in "${extensions[@]}"; do
        echo -e "${CYAN}  Installing $ext...${NC}"
        if code --install-extension "$ext" --force >/dev/null 2>&1; then
            ((installed++))
            echo -e "${GREEN}    ✓ Installed${NC}"
        else
            ((failed++))
            echo -e "${YELLOW}    ⚠ Failed to install${NC}"
        fi
    done
    
    echo -e "${GREEN}  ✓ Installed $installed extensions${NC}"
    if [ $failed -gt 0 ]; then
        echo -e "${YELLOW}  ⚠ Failed to install $failed extensions${NC}"
    fi
}

# Function to create helper scripts
create_helper_scripts() {
    echo -e "${BLUE}→ Creating helper scripts...${NC}"
    
    # Create Jupyter startup script with conda support
    cat > "$PROJECT_ROOT/start_jupyter.sh" << 'EOF'
#!/bin/bash
# Check if conda ds-template environment exists
if [ -d "/opt/homebrew/Caskroom/mambaforge/base/envs/ds-template" ]; then
    echo "Starting Jupyter with conda ds-template environment..."
    conda run --live-stream --name ds-template jupyter notebook --notebook-dir=notebooks
else
    source .venv/bin/python 2>/dev/null || source venv/bin/python 2>/dev/null || true
    jupyter notebook --notebook-dir=notebooks
fi
EOF
    chmod +x "$PROJECT_ROOT/start_jupyter.sh"
    echo -e "${GREEN}  ✓ Created start_jupyter.sh${NC}"
    
    # Create analysis runner script with conda support
    cat > "$PROJECT_ROOT/run_analysis.sh" << 'EOF'
#!/bin/bash
# Check if conda ds-template environment exists
if [ -d "/opt/homebrew/Caskroom/mambaforge/base/envs/ds-template" ]; then
    RUN_CMD="conda run --live-stream --name ds-template python"
else
    source .venv/bin/python 2>/dev/null || source venv/bin/python 2>/dev/null || true
    RUN_CMD="python"
fi

echo "Select analysis to run:"
echo "1) Likert Scale Analysis"
echo "2) Open-Ended Analysis"
echo "3) Executive Summary"
echo "4) Full Pipeline"
read -p "Enter choice (1-4): " choice

case $choice in
    1) $RUN_CMD saved_scripts/main_likert.py ;;
    2) $RUN_CMD saved_scripts/open_ended.py ;;
    3) conda run --live-stream --name ds-template jupyter nbconvert --execute notebooks/executive_summary.ipynb ;;
    4) $RUN_CMD saved_scripts/main_likert.py && $RUN_CMD saved_scripts/open_ended.py ;;
    *) echo "Invalid choice" ;;
esac
EOF
    chmod +x "$PROJECT_ROOT/run_analysis.sh"
    echo -e "${GREEN}  ✓ Created run_analysis.sh${NC}"
    
    # Create conda run wrapper script
    cat > "$PROJECT_ROOT/conda_run.sh" << 'EOF'
#!/bin/bash
# Wrapper script to run Python scripts with conda ds-template environment
if [ $# -eq 0 ]; then
    echo "Usage: ./conda_run.sh <python_script.py> [args...]"
    exit 1
fi

conda run --live-stream --name ds-template python "$@"
EOF
    chmod +x "$PROJECT_ROOT/conda_run.sh"
    echo -e "${GREEN}  ✓ Created conda_run.sh wrapper${NC}"
}

# Function to show summary
show_summary() {
    echo
    echo -e "${CYAN}${BOLD}========================================${NC}"
    echo -e "${CYAN}${BOLD}  Setup Complete!${NC}"
    echo -e "${CYAN}${BOLD}========================================${NC}"
    echo
    
    echo -e "${GREEN}✓ VSCode configuration files created${NC}"
    echo -e "${GREEN}✓ Extensions recommendations added${NC}"
    echo -e "${GREEN}✓ Python environment configured${NC}"
    echo
    
    echo -e "${CYAN}${BOLD}Next Steps:${NC}"
    echo -e "${CYAN}1. Reload VSCode window (Cmd+R or restart VSCode)${NC}"
    echo -e "${CYAN}2. Install recommended extensions when prompted${NC}"
    echo -e "${CYAN}3. Python interpreter configured: ${PYTHON_PATH}${NC}"
    
    if [ ! -z "$CONDA_ENV" ]; then
        echo -e "${CYAN}4. Using conda environment: ${CONDA_ENV}${NC}"
        echo -e "   ${YELLOW}To activate manually: conda activate ${CONDA_ENV}${NC}"
    else
        echo -e "${CYAN}4. Create/activate virtual environment if needed:${NC}"
        echo -e "   ${YELLOW}python3 -m venv .venv${NC}"
        echo -e "   ${YELLOW}source .venv/bin/activate${NC}"
        echo -e "   ${YELLOW}pip install -r requirements.txt${NC}"
    fi
    echo
    
    echo -e "${CYAN}${BOLD}Quick Commands:${NC}"
    echo -e "${CYAN}• Start Jupyter: ./start_jupyter.sh${NC}"
    echo -e "${CYAN}• Run analysis: ./run_analysis.sh${NC}"
    echo -e "${CYAN}• Run with conda: ./conda_run.sh script.py${NC}"
    echo -e "${CYAN}• Open notebook: code notebooks/likert_analysis.ipynb${NC}"
    
    if [ ! -z "$CONDA_ENV" ]; then
        echo -e "${CYAN}• Direct conda run: conda run --live-stream --name ${CONDA_ENV} python script.py${NC}"
    fi
    echo
    
    echo -e "${CYAN}${BOLD}Data Folders:${NC}"
    echo -e "${CYAN}• Input data: data/input/${NC}"
    echo -e "${CYAN}• Output results: data/output/${NC}"
    echo -e "${CYAN}• Notebooks: notebooks/${NC}"
    echo
}

# Main execution
main() {
    detect_python_env
    check_python_packages
    check_env_vars
    create_vscode_dirs
    copy_config_files
    
    # Ask about extension installation
    echo
    read -p "Install VSCode extensions now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_extensions
    fi
    
    create_helper_scripts
    show_summary
}

# Parse arguments
SKIP_INSTALL=false
for arg in "$@"; do
    case $arg in
        --skip-install)
            SKIP_INSTALL=true
            shift
            ;;
    esac
done

# Run main function
main