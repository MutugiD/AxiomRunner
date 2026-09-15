# Security and Sandbox Boundary

## Trust model

Challenge statements, model output, generated source, and generated tests are
untrusted. Local configuration and AxiomRunner source are trusted. Ollama is a
local processing dependency but its content remains untrusted.

## Static controls

- Parse candidate source as an AST and reject syntax errors.
- Permit imports only when their root appears in Python's standard-library
  module set; reject dangerous execution and process-control modules.
- Require the exact requested top-level function and reject top-level calls
  other than safe constant construction.
- Reject filesystem, network, subprocess, interactive input, and output calls.
- Compile without importing on the host.

Static controls reduce risk but are not a sandbox. Dynamic checks always use a
container.

## Dynamic controls

Candidate containers run with no network, a read-only root filesystem, a
read-only source mount, temporary writable storage, a non-root user, dropped
capabilities, no-new-privileges, bounded memory/CPU/processes, and a hard host
timeout. The harness serializes only test values and result evidence.

## Secret controls

Model prompts and reports never include environment dumps, Git credentials, or
host paths beyond normalized artifact labels. GitHub credentials are used only
by the delivery process and are not runtime configuration. Secret scanning and
push protection remain enabled on the repository.
