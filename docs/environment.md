# Environment Notes

- Python 3.10+
- NetworkX 3.x
- Pandas 2.x
- NumPy 1.24+
- SciPy 1.10+

The default LLM backend uses OpenRouter through `requests`. Set `OPENROUTER_API_KEY` in the shell before running scripts.

The codebase is intentionally file-driven and does not depend on a job scheduler, experiment tracker, or database service.

