# Changelog

All notable changes to this project will be documented in this file. See [Conventional Commits](https://conventionalcommits.org) for commit guidelines.

## [2.0.5](https://github.com/ShadowLib/shadowlib/compare/v2.0.4...v2.0.5) (2025-11-23)

### 🐛 Bug Fixes

* **query:** correct variable name in QueryRef.__getattr__ ([08e1021](https://github.com/ShadowLib/shadowlib/commit/08e10211073a95412c041623e67d8dac447720bc))

## [2.0.4](https://github.com/ShadowLib/shadowlib/compare/v2.0.3...v2.0.4) (2025-11-23)

### ♻️ Refactoring

* remove shadowlib/generated/ folder completely ([5a0a2ab](https://github.com/ShadowLib/shadowlib/commit/5a0a2ab41b47cc08a34b0011387f90f7b33036c9))

## [2.0.3](https://github.com/ShadowLib/shadowlib/compare/v2.0.2...v2.0.3) (2025-11-23)

### 📚 Documentation

* add release notes for v2.0.2 clean slate ([4e494c1](https://github.com/ShadowLib/shadowlib/commit/4e494c18222d1d7c20abd28a9f75a57365fd0d4b))

## 1.0.0 (2025-11-23)

### ⚠ BREAKING CHANGES

* Generated files and resources now stored in user cache
directory instead of package directory. Old data/ folder no longer used.

Changes:
- Add centralized CacheManager for path management
- Add dynamic loader for generated modules from cache
- Update all components to use cache paths (resources, scraper, updater)
- Fix circular imports with lazy-loading in query_builder
- Update proxy generator to use absolute imports
- Remove 7.5MB of generated files from package (84% size reduction)
- Package size: 1.8MB -> 296KB

Cache structure:
~/.cache/shadowlib/
├── generated/ (proxy classes, constants)
└── data/ (objects DB, varps, API data)

First import automatically downloads and generates all required files.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### ✨ Features

* migrate to XDG cache directory for generated files and resources ([c369c31](https://github.com/ShadowLib/shadowlib/commit/c369c319b83c87112a4619060f70b7a782604073))

### 🐛 Bug Fixes

* **ci:** correct version sync in release workflow ([5b7c794](https://github.com/ShadowLib/shadowlib/commit/5b7c794edd34866344889040e95f814ae62bff27))
* **ci:** enable tag fetching for semantic-release ([6bc83f1](https://github.com/ShadowLib/shadowlib/commit/6bc83f194220c30bb3a872961cfa1cb5d9cb5d3b))
* **ci:** prevent sed from modifying ruff target-version ([08b4b07](https://github.com/ShadowLib/shadowlib/commit/08b4b07179f8150ae77887629935011ad923f018))
* **lint:** add ignores for Python 3.12+ upgrade compatibility ([25bc9b3](https://github.com/ShadowLib/shadowlib/commit/25bc9b33ff373493c0b57005fd5419876cbc2df6))
* update project URLs and ruff version ([077da2d](https://github.com/ShadowLib/shadowlib/commit/077da2d47fbd56128ef3e8bb007c102444e08fe5))
* **version:** restore version to 2.0.1 after incorrect release ([1253aad](https://github.com/ShadowLib/shadowlib/commit/1253aada19d4e235dc4db14ad35548b791658298))

### 📚 Documentation

* add commit convention quick reference guide ([f23d39e](https://github.com/ShadowLib/shadowlib/commit/f23d39e7f12daaa9fdc887dc550d3495cb522970))

### ♻️ Refactoring

* **ci:** consolidate workflows and upgrade to Python 3.12+ ([c3283b5](https://github.com/ShadowLib/shadowlib/commit/c3283b536478f8d3c612f2f16fcd58f6dd37e784))

### 👷 CI/CD

* add semantic-release and quality check workflows ([51d420c](https://github.com/ShadowLib/shadowlib/commit/51d420c36510d7d3c54f573ee32bea64dfaf45e1))

## [1.0.1](https://github.com/ShadowLib/shadowlib/compare/v1.0.0...v1.0.1) (2025-11-23)

### 🐛 Bug Fixes

* **ci:** enable tag fetching for semantic-release ([6bc83f1](https://github.com/ShadowLib/shadowlib/commit/6bc83f194220c30bb3a872961cfa1cb5d9cb5d3b))

## 1.0.0 (2025-11-23)

### ⚠ BREAKING CHANGES

* Generated files and resources now stored in user cache
directory instead of package directory. Old data/ folder no longer used.

Changes:
- Add centralized CacheManager for path management
- Add dynamic loader for generated modules from cache
- Update all components to use cache paths (resources, scraper, updater)
- Fix circular imports with lazy-loading in query_builder
- Update proxy generator to use absolute imports
- Remove 7.5MB of generated files from package (84% size reduction)
- Package size: 1.8MB -> 296KB

Cache structure:
~/.cache/shadowlib/
├── generated/ (proxy classes, constants)
└── data/ (objects DB, varps, API data)

First import automatically downloads and generates all required files.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### ✨ Features

* migrate to XDG cache directory for generated files and resources ([c369c31](https://github.com/ShadowLib/shadowlib/commit/c369c319b83c87112a4619060f70b7a782604073))

### 🐛 Bug Fixes

* **ci:** correct version sync in release workflow ([5b7c794](https://github.com/ShadowLib/shadowlib/commit/5b7c794edd34866344889040e95f814ae62bff27))
* **ci:** prevent sed from modifying ruff target-version ([08b4b07](https://github.com/ShadowLib/shadowlib/commit/08b4b07179f8150ae77887629935011ad923f018))
* **lint:** add ignores for Python 3.12+ upgrade compatibility ([25bc9b3](https://github.com/ShadowLib/shadowlib/commit/25bc9b33ff373493c0b57005fd5419876cbc2df6))
* update project URLs and ruff version ([077da2d](https://github.com/ShadowLib/shadowlib/commit/077da2d47fbd56128ef3e8bb007c102444e08fe5))

### 📚 Documentation

* add commit convention quick reference guide ([f23d39e](https://github.com/ShadowLib/shadowlib/commit/f23d39e7f12daaa9fdc887dc550d3495cb522970))

### ♻️ Refactoring

* **ci:** consolidate workflows and upgrade to Python 3.12+ ([c3283b5](https://github.com/ShadowLib/shadowlib/commit/c3283b536478f8d3c612f2f16fcd58f6dd37e784))

### 👷 CI/CD

* add semantic-release and quality check workflows ([51d420c](https://github.com/ShadowLib/shadowlib/commit/51d420c36510d7d3c54f573ee32bea64dfaf45e1))

## 1.0.0 (2025-11-23)

### ⚠ BREAKING CHANGES

* Generated files and resources now stored in user cache
directory instead of package directory. Old data/ folder no longer used.

Changes:
- Add centralized CacheManager for path management
- Add dynamic loader for generated modules from cache
- Update all components to use cache paths (resources, scraper, updater)
- Fix circular imports with lazy-loading in query_builder
- Update proxy generator to use absolute imports
- Remove 7.5MB of generated files from package (84% size reduction)
- Package size: 1.8MB -> 296KB

Cache structure:
~/.cache/shadowlib/
├── generated/ (proxy classes, constants)
└── data/ (objects DB, varps, API data)

First import automatically downloads and generates all required files.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### ✨ Features

* migrate to XDG cache directory for generated files and resources ([c369c31](https://github.com/ShadowLib/shadowlib/commit/c369c319b83c87112a4619060f70b7a782604073))

### 🐛 Bug Fixes

* **ci:** correct version sync in release workflow ([5b7c794](https://github.com/ShadowLib/shadowlib/commit/5b7c794edd34866344889040e95f814ae62bff27))
* **ci:** prevent sed from modifying ruff target-version ([08b4b07](https://github.com/ShadowLib/shadowlib/commit/08b4b07179f8150ae77887629935011ad923f018))
* **lint:** add ignores for Python 3.12+ upgrade compatibility ([25bc9b3](https://github.com/ShadowLib/shadowlib/commit/25bc9b33ff373493c0b57005fd5419876cbc2df6))
* update project URLs and ruff version ([077da2d](https://github.com/ShadowLib/shadowlib/commit/077da2d47fbd56128ef3e8bb007c102444e08fe5))

### 📚 Documentation

* add commit convention quick reference guide ([f23d39e](https://github.com/ShadowLib/shadowlib/commit/f23d39e7f12daaa9fdc887dc550d3495cb522970))

### ♻️ Refactoring

* **ci:** consolidate workflows and upgrade to Python 3.12+ ([c3283b5](https://github.com/ShadowLib/shadowlib/commit/c3283b536478f8d3c612f2f16fcd58f6dd37e784))

### 👷 CI/CD

* add semantic-release and quality check workflows ([51d420c](https://github.com/ShadowLib/shadowlib/commit/51d420c36510d7d3c54f573ee32bea64dfaf45e1))

## 1.0.0 (2025-11-23)

### ⚠ BREAKING CHANGES

* Generated files and resources now stored in user cache
directory instead of package directory. Old data/ folder no longer used.

Changes:
- Add centralized CacheManager for path management
- Add dynamic loader for generated modules from cache
- Update all components to use cache paths (resources, scraper, updater)
- Fix circular imports with lazy-loading in query_builder
- Update proxy generator to use absolute imports
- Remove 7.5MB of generated files from package (84% size reduction)
- Package size: 1.8MB -> 296KB

Cache structure:
~/.cache/shadowlib/
├── generated/ (proxy classes, constants)
└── data/ (objects DB, varps, API data)

First import automatically downloads and generates all required files.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### ✨ Features

* migrate to XDG cache directory for generated files and resources ([c369c31](https://github.com/ShadowLib/shadowlib/commit/c369c319b83c87112a4619060f70b7a782604073))

### 🐛 Bug Fixes

* **ci:** correct version sync in release workflow ([5b7c794](https://github.com/ShadowLib/shadowlib/commit/5b7c794edd34866344889040e95f814ae62bff27))
* **ci:** prevent sed from modifying ruff target-version ([08b4b07](https://github.com/ShadowLib/shadowlib/commit/08b4b07179f8150ae77887629935011ad923f018))
* update project URLs and ruff version ([077da2d](https://github.com/ShadowLib/shadowlib/commit/077da2d47fbd56128ef3e8bb007c102444e08fe5))

### 📚 Documentation

* add commit convention quick reference guide ([f23d39e](https://github.com/ShadowLib/shadowlib/commit/f23d39e7f12daaa9fdc887dc550d3495cb522970))

### 👷 CI/CD

* add semantic-release and quality check workflows ([51d420c](https://github.com/ShadowLib/shadowlib/commit/51d420c36510d7d3c54f573ee32bea64dfaf45e1))

## 1.0.0 (2025-11-23)

### ⚠ BREAKING CHANGES

* Generated files and resources now stored in user cache
directory instead of package directory. Old data/ folder no longer used.

Changes:
- Add centralized CacheManager for path management
- Add dynamic loader for generated modules from cache
- Update all components to use cache paths (resources, scraper, updater)
- Fix circular imports with lazy-loading in query_builder
- Update proxy generator to use absolute imports
- Remove 7.5MB of generated files from package (84% size reduction)
- Package size: 1.8MB -> 296KB

Cache structure:
~/.cache/shadowlib/
├── generated/ (proxy classes, constants)
└── data/ (objects DB, varps, API data)

First import automatically downloads and generates all required files.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### ✨ Features

* migrate to XDG cache directory for generated files and resources ([c369c31](https://github.com/ShadowLib/shadowlib/commit/c369c319b83c87112a4619060f70b7a782604073))

### 🐛 Bug Fixes

* **ci:** correct version sync in release workflow ([5b7c794](https://github.com/ShadowLib/shadowlib/commit/5b7c794edd34866344889040e95f814ae62bff27))
* update project URLs and ruff version ([077da2d](https://github.com/ShadowLib/shadowlib/commit/077da2d47fbd56128ef3e8bb007c102444e08fe5))

### 📚 Documentation

* add commit convention quick reference guide ([f23d39e](https://github.com/ShadowLib/shadowlib/commit/f23d39e7f12daaa9fdc887dc550d3495cb522970))

### 👷 CI/CD

* add semantic-release and quality check workflows ([51d420c](https://github.com/ShadowLib/shadowlib/commit/51d420c36510d7d3c54f573ee32bea64dfaf45e1))

## [2.0.0](https://github.com/ShadowLib/shadowlib/compare/v1.0.1...v2.0.0) (2025-11-23)

### ⚠ BREAKING CHANGES

* Generated files and resources now stored in user cache
directory instead of package directory. Old data/ folder no longer used.

Changes:
- Add centralized CacheManager for path management
- Add dynamic loader for generated modules from cache
- Update all components to use cache paths (resources, scraper, updater)
- Fix circular imports with lazy-loading in query_builder
- Update proxy generator to use absolute imports
- Remove 7.5MB of generated files from package (84% size reduction)
- Package size: 1.8MB -> 296KB

Cache structure:
~/.cache/shadowlib/
├── generated/ (proxy classes, constants)
└── data/ (objects DB, varps, API data)

First import automatically downloads and generates all required files.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### ✨ Features

* migrate to XDG cache directory for generated files and resources ([c369c31](https://github.com/ShadowLib/shadowlib/commit/c369c319b83c87112a4619060f70b7a782604073))

## [1.0.1](https://github.com/ShadowLib/shadowlib/compare/v1.0.0...v1.0.1) (2025-11-22)

### 🐛 Bug Fixes

* update project URLs and ruff version ([077da2d](https://github.com/ShadowLib/shadowlib/commit/077da2d47fbd56128ef3e8bb007c102444e08fe5))

## 1.0.0 (2025-11-22)

### 📚 Documentation

* add commit convention quick reference guide ([f23d39e](https://github.com/osrs-chroma/shadowlib/commit/f23d39e7f12daaa9fdc887dc550d3495cb522970))

### 👷 CI/CD

* add semantic-release and quality check workflows ([51d420c](https://github.com/osrs-chroma/shadowlib/commit/51d420c36510d7d3c54f573ee32bea64dfaf45e1))
