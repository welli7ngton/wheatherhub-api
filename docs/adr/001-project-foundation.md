# 001: Keep pip and the existing application package

Status: accepted

## Context

The repository already uses a virtual environment, setuptools, pyproject.toml
and Taskipy. The first delivery needs consistent dependency versions and a
repeatable quality check without replacing this workflow.

## Decision

Keep `app/`, `.venv` and pip. Declare direct dependencies in pyproject.toml and
record tested dependency versions in constraints.txt. Use the constraints in
development, CI and Docker. Introduce no additional package manager.

Use pydantic-settings for validated environment configuration and pass settings
explicitly to the application factory. Tests can supply their own settings.
Keep only settings that have a consumer today.

Build a Python 3.12 image running as a non-root user. Start with the API alone;
database and cache services belong to later deliveries.

## Alternatives and consequences

A dedicated lockfile tool would automate dependency resolution and updates, but
adds a tool to the existing workflow. Pip constraints require maintaining pins
and checking platform-specific dependencies on Windows and Linux. They do not
provide artifact hashes or pin the container base image and build dependencies.

Separating API schemas and configuration keeps environment concerns outside
routes. A dependency injection framework is unnecessary at this stage.
