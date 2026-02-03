# Contributing to pETI-server

This document describes the project structure, behavior, and development guidelines for the pETI-server project.

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
  - `sync_options`: Resilio Sync folder options
  - `game_deny_list`: List of game folder IDs to exclude from sync
  - `game_predefined_hosts`: List of predefined host:port pairs for direct peer connections

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

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- pipenv for dependency management

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Poeschl/pETI-server.git
   cd pETI-server
   ```

2. **Install dependencies**
   ```bash
   pipenv install --dev
   pipenv shell
   ```

3. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

4. **Configure for development**
   - Edit `dev-eti-config.yaml` with your settings
   - Start the development environment:
     ```bash
     docker-compose up -d
     ```

### Running the Application

**Via Docker (recommended)**
```bash
docker-compose up -d
```

**Via Python (development)**
```bash
pipenv shell
python peti_server/sync_script.py update --config dev-eti-config.yaml
```

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

### CI/CD Pipeline

**Pull Request Checks** (`.github/workflows/pr-checks.yaml`)
- Runs all pre-commit hooks
- Must pass before merge

**Release Pipeline** (`.github/workflows/release.yaml`)
- Builds Docker image
- Publishes to GitHub Container Registry

## Making Changes

### Code Modifications

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow existing code style
   - Add validation and error handling
   - Update documentation if needed

3. **Test your changes**
   - Run pre-commit checks: `pre-commit run --all-files`
   - Test with Docker: `docker-compose up --build`
   - Verify functionality

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```
   Pre-commit hooks will run automatically.

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Configuration Changes

When adding new configuration options:

1. Update `Configuration` class in `peti_server/models.py`
2. Add property or method to access the new option
3. Update both config templates:
   - `dev-eti-config.yaml`
   - `deploy/eti-config.yaml`
4. Add comments explaining the new option
5. Update this documentation

### API Changes

When modifying Resilio Sync API interactions:

1. Add new `ApiMethod` enum value if needed
2. Update `SyncFolder._make_sync_request()` for new parameters
3. Add validation for new parameters
4. Test with actual Resilio Sync instance

## Testing

Currently, the project uses manual testing with Docker. Automated tests should be added in future contributions.

### Manual Testing Checklist

- [ ] Configuration loading works correctly
- [ ] Game folders sync successfully
- [ ] Deny list filters games properly
- [ ] Predefined hosts are set correctly (if configured)
- [ ] Error handling works for invalid configurations
- [ ] Docker container builds and runs
- [ ] Pre-commit hooks pass

## Important Notes

### ⚠️ Update This Document

**When making architectural changes, always update this CONTRIBUTING.md file to reflect:**
- New components or modules
- Changes to existing behavior
- New configuration options
- Modified workflows or processes
- New dependencies or requirements

This ensures the documentation stays synchronized with the codebase.

### Code Style

- Follow PEP 8 style guidelines (enforced by yapf)
- Use type hints for function parameters and return values
- Write descriptive docstrings for classes and methods
- Add inline comments for complex logic
- Use English for all code, comments, and documentation

### Security

- Validate all user input
- Use URL encoding for API parameters
- Log security-relevant events
- Don't commit secrets or credentials
- Use environment variables for sensitive configuration

## Getting Help

- **Issues**: Open an issue on GitHub for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check README.md and this CONTRIBUTING.md file

## License

This project is licensed under the terms specified in the LICENSE file.
