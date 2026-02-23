#!/bin/bash

# Create a portable VS Code setup package
# This script packages everything needed for easy distribution

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="vscode-portable-setup_${TIMESTAMP}"
PACKAGE_DIR="/tmp/${PACKAGE_NAME}"

echo "📦 Creating Portable VS Code Setup Package"
echo "========================================="

# Create package directory
mkdir -p "${PACKAGE_DIR}"

# Copy all portable files
cp -r "${SCRIPT_DIR}"/* "${PACKAGE_DIR}/"

# Create the main installer that will be run in target repos
cat > "${PACKAGE_DIR}/install.sh" << 'EOF'
#!/bin/bash

# Portable VS Code Setup Installer
# One-command setup for any repository

set -e

INSTALLER_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_DIR="$(pwd)"

echo "🚀 Installing Portable VS Code Setup"
echo "===================================="
echo "Target: ${TARGET_DIR}"
echo ""

# Check if .vscode-portable already exists
if [ -d "${TARGET_DIR}/.vscode-portable" ]; then
    echo "⚠️  .vscode-portable already exists. Backing up to .vscode-portable.backup"
    rm -rf "${TARGET_DIR}/.vscode-portable.backup"
    mv "${TARGET_DIR}/.vscode-portable" "${TARGET_DIR}/.vscode-portable.backup"
fi

# Copy portable files to target
echo "📁 Copying portable files..."
cp -r "${INSTALLER_DIR}/.vscode-portable" "${TARGET_DIR}/"

# Make scripts executable
chmod +x "${TARGET_DIR}/.vscode-portable"/*.sh

# Auto-detect Conda/Mamba installation
echo "🔍 Detecting Python environments..."

detect_conda_base() {
    # Check common conda/mamba locations
    if [ -n "$CONDA_PREFIX" ]; then
        echo "$(dirname $(dirname $CONDA_PREFIX))"
    elif [ -d "/opt/homebrew/Caskroom/mambaforge/base" ]; then
        echo "/opt/homebrew/Caskroom/mambaforge/base"
    elif [ -d "/opt/homebrew/Caskroom/miniforge/base" ]; then
        echo "/opt/homebrew/Caskroom/miniforge/base"
    elif [ -d "$HOME/mambaforge" ]; then
        echo "$HOME/mambaforge"
    elif [ -d "$HOME/miniforge" ]; then
        echo "$HOME/miniforge"
    elif [ -d "$HOME/anaconda3" ]; then
        echo "$HOME/anaconda3"
    elif [ -d "$HOME/miniconda3" ]; then
        echo "$HOME/miniconda3"
    else
        echo ""
    fi
}

CONDA_BASE=$(detect_conda_base)

if [ -n "$CONDA_BASE" ]; then
    echo "✅ Found Conda/Mamba at: $CONDA_BASE"
    
    # Update switch-environment.sh with correct paths
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|/opt/homebrew/Caskroom/mambaforge/base|${CONDA_BASE}|g" "${TARGET_DIR}/.vscode-portable/switch-environment.sh"
    else
        sed -i "s|/opt/homebrew/Caskroom/mambaforge/base|${CONDA_BASE}|g" "${TARGET_DIR}/.vscode-portable/switch-environment.sh"
    fi
else
    echo "⚠️  Conda/Mamba not found. Python environment switching may require manual configuration."
fi

# Run the main installer
echo ""
echo "📦 Running VS Code configuration..."
"${TARGET_DIR}/.vscode-portable/install-vscode-drupal.sh" "$@"

# Add .gitignore entries
if [ -f "${TARGET_DIR}/.gitignore" ]; then
    # Check if already in gitignore
    if ! grep -q "^.current_environment" "${TARGET_DIR}/.gitignore"; then
        echo "" >> "${TARGET_DIR}/.gitignore"
        echo "# VS Code portable environment tracking" >> "${TARGET_DIR}/.gitignore"
        echo ".current_environment" >> "${TARGET_DIR}/.gitignore"
        echo ".vscode/settings.json.backup" >> "${TARGET_DIR}/.gitignore"
        echo "✅ Added environment files to .gitignore"
    fi
else
    # Create .gitignore if it doesn't exist
    cat > "${TARGET_DIR}/.gitignore" << 'GITIGNORE'
# VS Code portable environment tracking
.current_environment
.vscode/settings.json.backup
GITIGNORE
    echo "✅ Created .gitignore with environment entries"
fi

echo ""
echo "✅ Installation Complete!"
echo ""
echo "Quick Start:"
echo "1. Open VS Code: code ."
echo "2. Switch Python environment: ./.vscode-portable/switch-environment.sh list"
echo "3. Select environment: ./.vscode-portable/switch-environment.sh [env-name]"
echo ""
echo "For help: cat .vscode-portable/README.md"
EOF

# Create the .vscode-portable directory in package
mkdir -p "${PACKAGE_DIR}/.vscode-portable"

# Copy all current portable files
cp "${SCRIPT_DIR}"/*.sh "${PACKAGE_DIR}/.vscode-portable/" 2>/dev/null || true
cp "${SCRIPT_DIR}"/*.md "${PACKAGE_DIR}/.vscode-portable/" 2>/dev/null || true
cp "${SCRIPT_DIR}"/*.json "${PACKAGE_DIR}/.vscode-portable/" 2>/dev/null || true

# Make installer executable
chmod +x "${PACKAGE_DIR}/install.sh"

# Create quick start script
cat > "${PACKAGE_DIR}/quick-install.sh" << 'EOF'
#!/bin/bash
# Quick installer - downloads and runs the portable setup

echo "🚀 Quick Install - VS Code Portable Setup"
echo "========================================"

# Run the installer
./install.sh

echo "✅ Quick install complete!"
EOF

chmod +x "${PACKAGE_DIR}/quick-install.sh"

# Create README for the package
cat > "${PACKAGE_DIR}/README.md" << 'EOF'
# VS Code Portable Setup

## Quick Install (One Command)

```bash
./install.sh
```

## What This Does

1. **Installs VS Code Extensions** for:
   - PHP/Drupal development
   - Python multi-environment support
   - Database management
   - Git integration (optional)

2. **Configures Environment Switching**:
   - Auto-detects Conda/Mamba environments
   - Enables quick switching between Python versions
   - Maintains PHP environment for Drupal

3. **Preserves Existing Workflow**:
   - All terminal commands continue to work
   - Adds visual tools without removing CLI access

## Installation Options

### Default Install (Recommended)
```bash
./install.sh
```

### Without Installing Extensions
```bash
./install.sh --skip-install
```

## After Installation

### List Available Environments
```bash
./.vscode-portable/switch-environment.sh list
```

### Switch Python Environment
```bash
./.vscode-portable/switch-environment.sh ds-template
./.vscode-portable/switch-environment.sh my-crawler
```

### Open VS Code
```bash
code .
```

## Features

- ✅ Multi-environment Python support
- ✅ PHP/Drupal development tools
- ✅ Database GUI (SQLTools)
- ✅ Git visualization (optional)
- ✅ Terminal commands unchanged
- ✅ Agent/LLM awareness

## Customization

Edit `.vscode/settings.json` after installation to customize.

## Support

See `.vscode-portable/` directory for detailed documentation:
- `README.md` - Overview
- `INTEGRATION.md` - Workflow details
- `ENVIRONMENT_MANAGEMENT.md` - Python environments
- `GITHUB_CLI_INTEGRATION.md` - Git workflow
EOF

# Create tarball
cd /tmp
tar -czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}"

# Create standalone installer script
cat > "/tmp/install-vscode-portable.sh" << 'EOF'
#!/bin/bash

# Standalone installer for VS Code Portable Setup
# Can be run with: curl -sL [url] | bash

set -e

echo "📦 VS Code Portable Setup - Standalone Installer"
echo "==============================================="

# Download and extract package
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Check if running from curl/wget or local
if [ -t 0 ]; then
    # Running locally - look for package
    if [ -f "$1" ]; then
        tar -xzf "$1"
    else
        echo "❌ Please provide package path or use curl installer"
        exit 1
    fi
else
    # Running from curl - package should be embedded or downloaded
    echo "⚠️  Curl installation requires package URL"
    echo "Usage: curl -sL [package-url] -o package.tar.gz && tar -xzf package.tar.gz && cd vscode-portable-* && ./install.sh"
    exit 1
fi

# Find extracted directory
PACKAGE_DIR=$(find . -maxdepth 1 -type d -name "vscode-portable-*" | head -1)

if [ -z "$PACKAGE_DIR" ]; then
    echo "❌ Could not find package directory"
    exit 1
fi

# Run installer
cd "$PACKAGE_DIR"
./install.sh

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo "✅ Installation complete!"
EOF

chmod +x "/tmp/install-vscode-portable.sh"

echo ""
echo "✅ Package created successfully!"
echo ""
echo "📦 Package location: /tmp/${PACKAGE_NAME}.tar.gz"
echo "📄 Standalone installer: /tmp/install-vscode-portable.sh"
echo ""
echo "To use in another repo:"
echo "1. Copy the package: cp /tmp/${PACKAGE_NAME}.tar.gz /path/to/repo/"
echo "2. Extract: tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "3. Install: cd ${PACKAGE_NAME} && ./install.sh"
echo ""
echo "Or distribute the tarball to other developers!"