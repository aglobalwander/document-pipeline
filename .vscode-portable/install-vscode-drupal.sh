#!/bin/bash

# Portable VS Code Drupal Development Setup
# Can be applied to any Drupal project

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(pwd)"

echo "🚀 VS Code Drupal Development Setup"
echo "=================================="
echo "Project: $PROJECT_ROOT"
echo ""

# Check if VS Code is installed
if ! command -v code &> /dev/null; then
    echo "❌ VS Code CLI not found. Please install VS Code first."
    echo "   Visit: https://code.visualstudio.com/"
    exit 1
fi

# Function to install extensions
install_extensions() {
    echo "📦 Installing VS Code Extensions..."
    
    # PHP & Drupal Core
    code --install-extension bmewburn.vscode-intelephense-client
    code --install-extension xdebug.php-debug
    code --install-extension neilbrayfield.php-docblocker
    code --install-extension ikappas.composer
    code --install-extension mblode.twig-language-2
    code --install-extension tsega.drupal-8-twig-snippets
    
    # Database & Docker
    code --install-extension mtxr.sqltools
    code --install-extension mtxr.sqltools-driver-mysql
    code --install-extension ms-azuretools.vscode-docker
    
    # Git & Deployment
    code --install-extension eamodio.gitlens
    code --install-extension mhutchie.git-graph
    code --install-extension github.vscode-pull-request-github
    code --install-extension github.vscode-github-actions
    code --install-extension ms-vscode.remote-ssh
    
    # Testing & Quality
    code --install-extension recca0120.vscode-phpunit
    code --install-extension wongjn.php-sniffer
    code --install-extension valeryanm.vscode-phpsab
    code --install-extension streetsidesoftware.code-spell-checker
    
    # Documentation & Project Management
    code --install-extension yzhang.markdown-all-in-one
    code --install-extension gruntfuggly.todo-tree
    code --install-extension alefragnani.project-manager
    code --install-extension hediet.vscode-drawio
    
    # Utilities
    code --install-extension wayou.vscode-todo-highlight
    code --install-extension usernamehw.errorlens
    code --install-extension christian-kohler.path-intellisense
    code --install-extension esbenp.prettier-vscode
    code --install-extension dbaeumer.vscode-eslint
    
    echo "✅ Extensions installed!"
}

# Function to detect environment
detect_environment() {
    echo "🔍 Detecting environment..."
    
    # Detect PHP version
    if command -v php &> /dev/null; then
        PHP_PATH=$(which php)
        PHP_VERSION=$(php -v | head -n 1 | cut -d " " -f 2 | cut -d "." -f 1,2)
        echo "   PHP: $PHP_VERSION at $PHP_PATH"
    else
        PHP_PATH="/usr/bin/php"
        PHP_VERSION="8.3"
        echo "   PHP: Not found, using defaults"
    fi
    
    # Detect DDEV
    if command -v ddev &> /dev/null && ddev describe 2>/dev/null | grep -q "OK"; then
        DDEV_STATUS="active"
        # Get MySQL port from ddev describe
        MYSQL_PORT=$(ddev describe -j 2>/dev/null | grep -oP '"Host":"db:\K[0-9]+' | head -1 || echo "32773")
        echo "   DDEV: Active (MySQL port: $MYSQL_PORT)"
    else
        DDEV_STATUS="inactive"
        MYSQL_PORT="3306"
        echo "   DDEV: Not active"
    fi
    
    # Detect Drupal version
    if [ -f "composer.json" ]; then
        DRUPAL_VERSION=$(grep '"drupal/core"' composer.json | grep -oP '\d+\.\d+' | head -1 || echo "11")
        echo "   Drupal: $DRUPAL_VERSION"
    else
        DRUPAL_VERSION="11"
        echo "   Drupal: Not detected"
    fi
}

# Function to create VS Code settings
create_settings() {
    echo "⚙️  Creating VS Code settings..."
    
    mkdir -p .vscode
    
    # Check if settings.json exists
    if [ -f ".vscode/settings.json" ]; then
        echo "   Backing up existing settings.json to settings.json.backup"
        cp .vscode/settings.json .vscode/settings.json.backup
    fi
    
    # Create settings with detected values
    cat > .vscode/settings.json << EOF
{
    // === PHP & DRUPAL DEVELOPMENT ===
    "php.validate.executablePath": "$PHP_PATH",
    "intelephense.environment.phpVersion": "$PHP_VERSION.0",
    "intelephense.files.maxSize": 10000000,
    "intelephense.stubs": [
      "apache", "bcmath", "Core", "ctype", "curl", "date", "dom", "fileinfo",
      "filter", "hash", "iconv", "json", "libxml", "mbstring", "mysqli", "openssl",
      "pcre", "PDO", "pdo_mysql", "Phar", "posix", "Reflection", "session",
      "SimpleXML", "SPL", "standard", "tokenizer", "xml", "xmlreader", "xmlwriter", "zip"
    ],
    
    // === DATABASE TOOLS ===
    "sqltools.connections": [{
      "name": "Local Database",
      "driver": "MySQL",
      "server": "127.0.0.1",
      "port": $MYSQL_PORT,
      "database": "db",
      "username": "db",
      "password": "db"
    }],
    
    // === GIT & SOURCE CONTROL ===
    "git.autofetch": true,
    "git.confirmSync": false,
    "git.enableSmartCommit": true,
    "gitlens.advanced.messages": {
      "suppressLineUncommittedWarning": true
    },
    
    // === TESTING & CODE QUALITY ===
    "phpunit.execPath": "vendor/bin/phpunit",
    "phpunit.args": ["--configuration", "phpunit.xml"],
    "phpSniffer.executablesFolder": "vendor/bin/",
    "phpSniffer.standard": "Drupal,DrupalPractice",
    "phpsab.executablePathCBF": "vendor/bin/phpcbf",
    "phpsab.executablePathCS": "vendor/bin/phpcs",
    "phpsab.standard": "Drupal,DrupalPractice",
    
    // === EDITOR SETTINGS ===
    "editor.formatOnSave": false,
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": "explicit"
    },
    "[php]": {
      "editor.defaultFormatter": "bmewburn.vscode-intelephense-client",
      "editor.tabSize": 2
    },
    "[twig]": {
      "editor.tabSize": 2
    },
    "[yaml]": {
      "editor.tabSize": 2
    },
    
    // === FILE ASSOCIATIONS ===
    "files.associations": {
      "*.module": "php",
      "*.install": "php",
      "*.inc": "php",
      "*.theme": "php",
      "*.profile": "php",
      "*.test": "php"
    },
    
    // === TODO TREE ===
    "todo-tree.highlights.customHighlight": {
      "TODO": { "icon": "check", "iconColour": "yellow" },
      "FIXME": { "foreground": "white", "background": "red", "iconColour": "red" },
      "HACK": { "iconColour": "purple" },
      "NOTE": { "iconColour": "blue" }
    },
    
    // === FILE EXCLUSIONS ===
    "files.exclude": {
      "**/sites/default/files": true,
      "**/.git": false
    },
    
    // === SEARCH EXCLUSIONS ===
    "search.exclude": {
      "**/node_modules": true,
      "**/vendor": true,
      "**/sites/default/files": true,
      "**/sites/simpletest": true
    }
}
EOF
    
    echo "✅ Settings created!"
}

# Function to create extensions.json
create_extensions_json() {
    echo "📋 Creating extensions.json..."
    
    cat > .vscode/extensions.json << 'EOF'
{
  "recommendations": [
    // PHP & Drupal Core Development
    "bmewburn.vscode-intelephense-client",
    "xdebug.php-debug",
    "neilbrayfield.php-docblocker",
    "ikappas.composer",
    "mblode.twig-language-2",
    "tsega.drupal-8-twig-snippets",
    
    // Database & Docker/DDEV
    "mtxr.sqltools",
    "mtxr.sqltools-driver-mysql",
    "formulahendry.docker",
    "ms-azuretools.vscode-docker",
    
    // Git & Deployment
    "eamodio.gitlens",
    "mhutchie.git-graph",
    "github.vscode-pull-request-github",
    "github.vscode-github-actions",
    "ms-vscode.remote-ssh",
    
    // Testing & Quality Assurance
    "recca0120.vscode-phpunit",
    "wongjn.php-sniffer",
    "valeryanm.vscode-phpsab",
    "streetsidesoftware.code-spell-checker",
    
    // Documentation & Project Management
    "yzhang.markdown-all-in-one",
    "gruntfuggly.todo-tree",
    "alefragnani.project-manager",
    "hediet.vscode-drawio",
    
    // Utilities
    "wayou.vscode-todo-highlight",
    "usernamehw.errorlens",
    "christian-kohler.path-intellisense",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint"
  ],
  
  "unwantedRecommendations": [
    "felixfbecker.php-intellisense"
  ]
}
EOF
    
    echo "✅ Extensions.json created!"
}

# Main execution
main() {
    echo ""
    
    # Check for --skip-install flag
    if [[ "$1" == "--skip-install" ]]; then
        echo "⏩ Skipping extension installation"
    else
        install_extensions
    fi
    
    echo ""
    detect_environment
    echo ""
    create_settings
    echo ""
    create_extensions_json
    
    echo ""
    echo "🎉 VS Code Drupal setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Open VS Code in this directory: code ."
    echo "2. Review .vscode/settings.json for your environment"
    echo "3. Update MySQL port if needed (current: $MYSQL_PORT)"
    echo "4. Terminal commands still work: ddev drush cr, etc."
    echo ""
    echo "📚 Documentation: .vscode-portable/INTEGRATION.md"
}

# Run main function
main "$@"