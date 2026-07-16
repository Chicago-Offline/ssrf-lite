# SSRF-Lite Makefile

.PHONY: help install test docs schema stamp-headers validate-schema site serve-site clean

help: ## Show this help message
	@echo "SSRF-Lite - Development Commands"
	@echo "================================"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync

test: ## Run tests
	uv run python -m pytest tests/

docs: ## Generate SSRF data library documentation
	@echo "📡 Generating SSRF documentation..."
	uv run python generate_ssrf_docs.py

site: ## Generate data.json for the GitHub Pages site
	@echo "🌐 Generating site data..."
	uv run python generate_ssrf_site.py

serve-site: site ## Build and serve the GitHub Pages site locally
	@echo "🌐 Serving site at http://localhost:8000 ..."
	uv run python -m http.server 8000 --directory site

schema: ## Regenerate the versioned SSRF-Lite JSON Schema from the models
	@echo "🧬 Generating SSRF-Lite JSON Schema..."
	uv run python generate_ssrf_schema.py

stamp-headers: ## Stamp $$schema + ssrf_lite_version headers onto SSRF-Lite YAML
	@echo "🏷️  Stamping SSRF-Lite schema headers..."
	uv run python stamp_ssrf_headers.py

validate-schema: ## Verify the committed schema and YAML headers are up to date
	@echo "🔍 Validating SSRF-Lite schema and headers..."
	uv run python generate_ssrf_schema.py --check
	uv run python stamp_ssrf_headers.py --check

clean: ## Clean caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
