.PHONY: fmt lint typecheck check

fmt:
	@uv run ruff check src --fix
	@uv run ruff format src

lint:
	@uv run ruff check src
	@uv run ruff format src --check

typecheck:
	@uv run mypy src

test:
	@uv run pytest tests

type-audit:
	@echo "=== Any / cast ==="
	@grep -RInE 'Any|cast\(' src/app --include='*.py' || true
	@echo ""
	@echo "=== Raw dict types ==="
	@grep -RInE 'dict\[|-> dict|list\[dict' src/app --include='*.py' || true
	@echo ""
	@echo "=== response.json() ==="
	@grep -RInE 'response\.json\(' src/app --include='*.py' || true
	
check:
	@$(MAKE) fmt
	@$(MAKE) lint
	@$(MAKE) typecheck
	@$(MAKE) test