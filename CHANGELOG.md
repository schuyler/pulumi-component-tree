# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-02-17

### Added
- Initial release of pulumi-component-tree
- Core functionality for building tree-structured Pulumi components
- Type-safe properties using TypedDict
- Automatic parent-child dependency management
- Property inheritance from parent to child components
- Fluent API using `<<` operator
- Context manager support for automatic construction
- Full type hints and mypy compatibility
- Basic test suite covering core functionality
- Pre-commit hooks for basic file checks

### Dependencies
- Python 3.8+
- Pulumi 3.0.0+
- typing-extensions 4.0.0+
