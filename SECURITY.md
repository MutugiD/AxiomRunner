# Security Policy

Report security issues privately to the repository owner rather than opening a
public issue.

AxiomRunner treats generated source as hostile. Local model output must not run
on the host during normal operation. Secrets belong in environment variables,
must never appear in reports, and must not be sent to Ollama prompts.
