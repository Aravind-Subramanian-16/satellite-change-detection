.PHONY: test run verify
test:
	./venv/bin/python -m pytest -q
run:
	./venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000
verify:
	bash scripts/verify.sh
