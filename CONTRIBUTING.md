# Contributing

1. Pick a reviewed topic from HELLOFOSS.md and discuss scope with a maintainer before coding.
2. Fork this repository, create a focused branch, and use synthetic examples in tests.
3. Keep keys, `.env`, uploads and account/vector databases out of your commit and Docker build context.
4. Run `python tools/check_release.py .` and `python -m unittest discover -s tools/tests -v`.
5. Submit a PR with a problem statement, screenshots for UI changes, test commands/results, and any new environment variables documented with blank values.
6. Never post a real resume, account record or raw provider response containing personal/secret data in an issue or test log.

Frontend Jest/type/build checks and the complete provider-backed backend suite need separate setup; improving this is part of the HelloFOSS roadmap. Use public or genuinely synthetic evaluation fixtures. Existing numeric layout-model files may remain; new artifacts require maintainer review.
