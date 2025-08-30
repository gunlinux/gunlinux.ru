# TODO List for gunlinux.ru Flask Blog Application

## Immediate Fixes (High Priority)

- [ ] Replace hardcoded secrets in `config.py` with proper secret management
- [ ] Fix typo in `blog/admin/__init__.py`: `"puslishedon"` → `"publishedon"`
- [ ] Update WTForms dependency from 2.3.3 to a more recent version in `pyproject.toml`
- [ ] Add proper error handling to all endpoints, especially `/md/` in `blog/post/views.py`
- [ ] Remove unused imports throughout the codebase

## Security Improvements

- [ ] Add password complexity requirements in `blog/user/models.py`
- [ ] Implement rate limiting for authentication endpoints
- [ ] Add CSRF protection to all forms
- [ ] Add validation for environment variable parsing in `blog/config.py`
- [ ] Add security headers to HTTP responses

## Code Quality & Architecture

- [ ] Implement a service layer to separate business logic from views
- [ ] Refactor `pages_gen` decorator in `blog/post/views.py` to eliminate code duplication
- [ ] Standardize blueprint naming conventions (`postb`, `userb`, `tagsb`)
- [ ] Add missing return type annotations to functions
- [ ] Improve validation on model fields (content length limits, etc.)
- [ ] Decouple admin interface configuration from main application initialization

## Testing Improvements

- [ ] Add tests for authentication flows in `tests/test_basics.py`
- [ ] Add tests for form validation
- [ ] Add tests for the markdown processing endpoint (`/md/`)
- [ ] Add tests for admin functionality
- [ ] Add tests for edge cases and error conditions
- [ ] Refactor test fixtures to share common setup code
- [ ] Improve test coverage for negative cases

## Configuration & Deployment

- [ ] Improve configuration management for production deployments
- [ ] Replace default SQLite database URI with more appropriate defaults for production
- [ ] Add validation of required configuration values
- [ ] Fix hardcoded file admin path in `blog/admin/__init__.py`

## Documentation & Maintainability

- [ ] Standardize on either flake8 or ruff for linting tools (align `.pre-commit-config.yaml` and `Makefile`)
- [ ] Add API documentation using Swagger/OpenAPI
- [ ] Create developer documentation for contributing to the project
- [ ] Add monitoring and logging for production deployments
- [ ] Implement proper CI/CD with automated security scanning

## Template Improvements

- [ ] Add template validation
- [ ] Verify CSRF protection implementation in templates
