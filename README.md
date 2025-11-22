# ShadowLib

A Python SDK for Old School RuneScape (OSRS) bot development with an intuitive structure that mirrors the game's interface.

## Features

- **Game-Native Structure**: Directory layout based on OSRS client interface (world, tabs, interfaces)
- **Type-Safe**: Full type hints for better IDE support and fewer runtime errors
- **Well-Tested**: Comprehensive test coverage with pytest
- **Clean Code**: Enforced coding standards with Ruff and custom naming convention checker
- **Easy to Use**: Intuitive API that matches how players think about the game

## Installation

### From Source

```bash
git clone https://github.com/shadowbot/shadowlib.git
cd shadowlib
pip install -e ".[dev]"
```

### For Development

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Quick Start

```python
from shadowlib import Client

# Create and connect to the client
client = Client()
client.connect()

# Check connection status
if client.isConnected():
    print("Connected to OSRS client!")

# Your bot logic here...

# Disconnect when done
client.disconnect()
```

## Project Structure

```
shadowlib/
├── world/              # Game viewport entities (NPCs, objects, players, ground items)
├── tabs/               # Side panel tabs (inventory, equipment, skills, prayers)
├── interfaces/         # Overlay windows (bank, GE, shop, dialogue)
├── navigation/         # Movement systems (walking, teleports, webwalking)
├── interactions/       # Interaction systems (menu, clicking, hovering)
├── input/              # OS-level input (mouse, keyboard)
├── types/              # Type definitions, enums, models
├── utilities/          # Helper functions (timing, calculations, geometry)
├── resources/          # Game data (varps, objects, items, NPCs)
└── _internal/          # Bridge implementation (transport, protocol, cache)
```

### Placement Rules

1. **Visible in the 3D world** → `world/`
2. **Side-panel tab** → `tabs/`
3. **Overlay window** → `interfaces/`
4. **Pathing/movement** → `navigation/`
5. **Interaction primitives** → `interactions/`

## Development

### Code Style

This project uses **camelCase** for function names (e.g., `getFoo()`, `doSomething()`), following the convention:

```python
# ✅ Correct
def getPlayerName():
    pass

def isInventoryFull():
    pass

# ❌ Incorrect
def get_player_name():
    pass

def is_inventory_full():
    pass
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=shadowlib

# Run specific test file
pytest tests/test_client.py

# Run tests matching a pattern
pytest -k "test_client"
```

### Linting and Formatting

```bash
# Run Ruff linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Check naming conventions
python check_naming.py
```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Naming Conventions

- **Functions/Methods**: `camelCase` (e.g., `getItem`, `moveToPosition`)
- **Classes**: `PascalCase` (e.g., `Client`, `QueryBuilder`)
- **Constants**: `UPPER_CASE` (e.g., `MAX_HEALTH`, `DEFAULT_TIMEOUT`)
- **Private functions**: `_camelCase` (e.g., `_internalHelper`)
- **Dunder methods**: `__method__` (e.g., `__init__`, `__repr__`)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the code style
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Quality Checklist

Before submitting a PR, ensure:

- [ ] All tests pass (`pytest`)
- [ ] Code follows naming conventions (`python check_naming.py`)
- [ ] Linting passes (`ruff check .`)
- [ ] Code is formatted (`ruff format .`)
- [ ] New features have tests
- [ ] Documentation is updated

## Architecture Decision Records (ADRs)

See `docs/adr/` for architectural decisions, including:

- ADR-003: OSRS-Native SDK Structure

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Inspired by OSBot, TRiBot, and other OSRS botting frameworks
- Built with love for the OSRS botting community
