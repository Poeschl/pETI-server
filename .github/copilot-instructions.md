# Copilot Instructions for pETI-server

This document provides guidance for AI agents (like GitHub Copilot) working on the pETI-server codebase.

## Project Overview

pETI-server is a Python-based alternative to the official ETI sync server that manages game synchronization using Resilio Sync in a containerized environment. It provides additional features like configuration via YAML files, game deny lists, and predefined hosts for direct peer connections.

## Project Structure

```
pETI-server/
├── .github/                    # GitHub workflows and configuration
│   ├── workflows/
│   │   ├── pr-checks.yaml     # Pre-commit checks on PRs
│   │   └── release.yaml       # Release automation
│   └── dependabot.yaml        # Dependency update configuration
├── deploy/                     # Production deployment files
│   ├── docker-compose.yaml    # Docker Compose setup for production
│   ├── eti-config.yaml        # Production configuration template
│   ├── resilio-config.conf    # Resilio Sync configuration
│   ├── resilio-offline-config.sh # Offline mode configuration script
│   └── README.md              # Deployment documentation
├── peti_server/               # Main Python package
│   ├── __init__.py           # Package initialization
│   ├── models.py             # Configuration and data models
│   └── sync_script.py        # Main synchronization script
├── .pre-commit-config.yaml    # Pre-commit hooks configuration
├── dev-eti-config.yaml        # Development configuration template
├── Dockerfile                 # Container image definition
├── docker-compose.yaml        # Development Docker Compose setup
├── Pipfile                    # Python dependencies
├── Pipfile.lock              # Locked dependency versions
└── README.md                 # Main project documentation
```

## Architecture and Behavior

### Core Components

#### 1. Configuration Management (`peti_server/models.py`)

**Configuration Class**
- Loads and parses YAML configuration files
- Provides properties for accessing configuration values:
  - `resilio_auth`: Username and password for Resilio Sync API
  - `resilio_host`: Host and port for Resilio Sync API
  - `sync_dir`: Directory path for synchronized folders
  - `data_dir`: Directory for storing database and other files
  - `sync_options`: Resilio Sync folder options (note: `use_dht` is not supported by Resilio API and removed from default options)
  - `game_deny_list`: List of game folder IDs to exclude from sync
  - `predefined_hosts`: List of predefined host:port pairs for direct peer connections

**Important Notes on Tracker Servers:**
- Tracker server usage is controlled at the Resilio Sync configuration level via `folder_defaults.use_tracker`, not via the API
- To disable trackers when using `predefined_hosts`, set the environment variable `USE_PREDEFINED_HOSTS_ONLY=true` in the Docker deployment
- This ensures that all folders use only direct peer connections through predefined hosts
- The `resilio-offline-config.sh` script handles this configuration at container startup

**SyncFolder Class**
- Represents a folder to be synchronized
- Methods:
  - `sync()`: Adds or updates folder in Resilio Sync
  - `update_prefs()`: Updates folder preferences
  - `set_hosts()`: Sets predefined hosts for direct peer connections
  - `remove()`: Removes folder from Resilio Sync
- Communicates with Resilio Sync API via HTTP GET requests

**API Methods**
- `ADD_FOLDER`: Add or update a folder in sync
- `REMOVE_FOLDER`: Remove a folder from sync
- `SET_FOLDER_PREFS`: Update folder preferences
- `SET_FOLDER_HOSTS`: Set predefined hosts for a folder

#### 2. Synchronization Script (`peti_server/sync_script.py`)

**Main Operations**

1. **Update (`update` action)**
   - Downloads and processes ETI games database
   - Syncs system folders (eti_launcher)
   - Processes game folders:
     - Filters based on deny list
     - Adds/updates allowed games in parallel
     - Sets predefined hosts if configured
     - Removes denied games (optional)

2. **Cleanup (`cleanup` action)**
   - Removes all synchronized folders after confirmation
   - Cleans up local directories

**Workflow**
```
1. Load configuration
2. Get ETI database (download if missing)
3. Add system folders
4. Process games:
   - Query database for games and tools
   - Apply deny list filter
   - Sync allowed games in parallel
   - Set predefined hosts if configured
   - Remove denied games
5. Log completion
```

### Security Features

**Host Validation**
- Validates host:port format using regex
- Ensures port numbers are in valid range (1-65535)
- Rejects malformed hostnames (leading/trailing hyphens, consecutive dots, etc.)
- URL encodes parameters while preserving API-required format

**Configuration Safety**
- Type checking for configuration values
- Graceful error handling with detailed logging
- Validation before API calls

## Pre-commit Checks

The project uses pre-commit hooks to ensure code quality. These checks run automatically on `git commit` and also run in CI on pull requests.

### Configured Hooks

1. **Code Quality Checks**
   - `trailing-whitespace`: Removes trailing whitespace
   - `end-of-file-fixer`: Ensures files end with a newline
   - `check-merge-conflict`: Detects merge conflict markers
   - `check-added-large-files`: Prevents committing large files (>1MB)
   - `check-shebang-scripts-are-executable`: Ensures scripts with shebangs are executable
   - `mixed-line-ending`: Enforces LF line endings

2. **Code Formatting**
   - `yapf`: Python code formatter
   - `prettier`: YAML file formatter

3. **Custom Checks**
   - `yaml-extension-check`: Ensures YAML files use `.yaml` extension (not `.yml`)

### Running Pre-commit Manually

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Run specific hook
pre-commit run yapf --all-files
```

## Development Guidelines for AI Agents

### When Making Changes

1. **Always validate configuration changes**
   - When adding new config options, update both `dev-eti-config.yaml` and `deploy/eti-config.yaml`
   - Add comments explaining the purpose and format
   - Update the Configuration class with appropriate properties

2. **API interactions with Resilio Sync**
   - Use GET requests with proper URL encoding
   - Preserve comma separators in lists (use `safe=','` with `quote()`)
   - Encode colons as `%3A` for URL query parameters
   - Validate input before making API calls

3. **Code Style**
   - Follow PEP 8 style guidelines (enforced by yapf)
   - Use type hints for function parameters and return values
   - Write descriptive docstrings for classes and methods
   - Add inline comments for complex logic
   - Use English for all code, comments, and documentation

4. **Security Best Practices**
   - Validate all user input
   - Use URL encoding for API parameters
   - Log security-relevant events
   - Don't commit secrets or credentials
   - Add validation functions for complex inputs (like host:port format)

5. **Error Handling**
   - Provide clear, actionable error messages
   - Use appropriate exception types
   - Log errors with context
   - Fail fast when configuration is invalid

### Testing

Currently, the project uses manual testing with Docker. When making changes:

- Run Python syntax checks: `python3 -m py_compile peti_server/*.py`
- Validate YAML files: Load with `yaml.safe_load()` and check structure
- Test with Docker: `docker-compose up --build`
- Verify functionality with actual deployment when possible

### Configuration File Format

Example configuration structure:
```yaml
resilio_auth:
  user: username
  password: password

resilio_host: localhost:8080
resilio_sync_dir: /sync
resilio_sync_options: "force=1&search_lan=1&use_dht=1&use_hosts=1"

data_dir: /data

folders:
  folder_name:
    secret: "SECRET_KEY"

predefined_hosts:
  - "192.168.1.10:8888"
  - "10.0.0.5:55555"

games:
  denylist:
    - "game_id_to_exclude"
```

## Important Notes

### ⚠️ Update This Document

**When making architectural changes, always update this .copilot-instructions.md file to reflect:**
- New components or modules
- Changes to existing behavior
- New configuration options
- Modified workflows or processes
- New dependencies or requirements
- Changes to API interactions
- New validation rules or security measures

This ensures AI agents have accurate information about the codebase when making future changes.

### Common Patterns

**Adding a new configuration option:**
1. Add property to `Configuration` class in `models.py`
2. Update both config templates with commented examples
3. Add validation if needed
4. Update this document

**Adding a new API method:**
1. Add enum value to `ApiMethod` in `models.py`
2. Update `_make_sync_request()` if special handling needed
3. Add method to `SyncFolder` class if it's a folder operation
4. Test with actual Resilio Sync instance

**Adding validation:**
1. Create validation function with clear error messages
2. Add regex patterns as module constants
3. Call validation before API operations or config usage
4. Handle validation errors gracefully with logging

## Dependencies

- **Python 3.11+**: Core language
- **requests**: HTTP client for Resilio Sync API
- **pyyaml**: YAML configuration parsing
- **Docker**: Container runtime
- **Resilio Sync**: Synchronization backend

## CI/CD Pipeline

**Pull Request Checks** (`.github/workflows/pr-checks.yaml`)
- Runs all pre-commit hooks
- Must pass before merge

**Release Pipeline** (`.github/workflows/release.yaml`)
- Builds Docker image
- Publishes to GitHub Container Registry

## Resources

- **Project README**: Basic usage and overview
- **Deploy README**: Deployment instructions
- **Pre-commit config**: `.pre-commit-config.yaml` for hook details
- **Docker files**: `Dockerfile` and `docker-compose.yaml` for containerization
