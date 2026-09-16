# Google Colab T4 Acceptance Runbook

## Purpose

This runbook reruns the unchanged AxiomRunner acceptance gate on a hosted
NVIDIA GPU. It does not relax the 300-second problem deadlines, change the
model, retain generated solutions, or publish the private ChallengeBox corpus.

The companion notebook is
[`notebooks/axiomrunner_t4_acceptance.ipynb`](../notebooks/axiomrunner_t4_acceptance.ipynb).
[Open it directly in Google Colab](https://colab.research.google.com/github/MutugiD/AxiomRunner/blob/main/notebooks/axiomrunner_t4_acceptance.ipynb)
and run the cells in order.

## Before starting

Keep the ten original JSON files from `ChallengeBox/samples` available on your
computer. The expected corpus is six Python challenges and four Rust
challenges. Upload only those ten files when prompted; the notebook validates
the counts, unique problem IDs, Python entrypoints, and 300-second deadlines.

In Colab:

1. Select **Runtime > Change runtime type**.
2. Select **T4 GPU** as the hardware accelerator. If Colab assigns another
   NVIDIA GPU, set `REQUIRE_T4 = False` in the configuration cell only if the
   run should be recorded as a different GPU profile.
3. Select the latest runtime version and connect.
4. Open the notebook from GitHub or upload the notebook file.
5. Run every cell from top to bottom. Do not run multiple benchmark cells in
   parallel.

Colab hardware availability and runtime duration are not guaranteed. Keep the
browser tab connected while the benchmark is active. A fresh runtime is
recommended for each official acceptance run.

## What the notebook installs

The notebook works only inside the temporary Colab VM. It:

- confirms the assigned GPU with `nvidia-smi`;
- installs Docker for the existing verification sandbox;
- installs Ollama from its official Linux installer and binds it to loopback;
- installs pinned `uv`, clones the public AxiomRunner repository, and records
  the resolved commit;
- pulls `qwen3:8b`, warms it, and requires `ollama ps` to report GPU use;
- pulls the pinned Python 3.12 sandbox image and runs the Docker integration
  tests before accepting corpus input.

No GitHub token is needed because the repository is public. Do not add tokens,
API keys, or private repository credentials to the notebook.

## Acceptance execution

The benchmark uses the release profile:

- model `qwen3:8b`;
- seed `7`;
- one initial candidate;
- one repair;
- each challenge's declared 300-second deadline;
- one model request at a time;
- the existing Docker verification boundary.

The four Rust files must be rejected before inference. Each of the six Python
files must produce a verified solution inside its own deadline. The benchmark
exit code may be `4` when the gate fails; the notebook still collects the
evidence so the failure can be diagnosed.

## Evidence to return

The final cell downloads `axiomrunner-t4-evidence.zip`. Keep it outside the Git
repository and return that file for review. It contains:

- `benchmark.json`: redacted machine-readable outcomes;
- `summary.md`: gate decision and per-problem table;
- `environment.json`: GPU and tool versions, resolved Git commit, and run
  configuration;
- `benchmark.log`: concise benchmark console output;
- `ollama.log.tail.txt`: the final bounded Ollama log tail for runtime
  diagnosis.

The bundle contains no generated candidate source and no uploaded challenge
JSON. The notebook checks the benchmark report recursively for source-bearing
keys before packaging it.

## Interpreting the result

`summary.md` reports **PASS** only when all ten records are accepted, exactly
six are successful Python solves, and exactly four are unsupported-language
rejections. Anything else is a failed release gate, even if the GPU was used.

After the bundle is reviewed:

- if the gate passes, publish a new benchmark record and create the `v0.1.0`
  tag in a separate release change;
- if it fails, classify the failure from the report and logs, fix it on a new
  branch, and rerun the complete corpus;
- if Colab terminates the VM or Docker is unavailable, treat the run as an
  invalid environment attempt rather than product acceptance evidence.

## Troubleshooting

- **No T4 detected:** reconnect after selecting the T4 accelerator. GPU types
  are subject to Colab availability.
- **Ollama reports CPU:** stop. Do not spend the corpus run on a CPU fallback;
  restart the runtime and rerun setup.
- **Docker preflight fails:** inspect `/content/dockerd.log`. The acceptance
  sandbox must not be bypassed.
- **Runtime disconnects:** start again with a fresh runtime. Partial corpus
  results do not meet the release gate.
- **Model download fails:** confirm the runtime has outbound access and rerun
  only the model-install cell.

## Platform references

- [Google Colab FAQ](https://research.google.com/colaboratory/faq.html) for GPU
  availability, changing runtime type, and runtime-duration limitations.
- [Ollama Linux installation](https://docs.ollama.com/linux) for the installer
  and service commands used by the notebook.
- [Ollama hardware support](https://docs.ollama.com/gpu) for NVIDIA support;
  the T4 is listed with compute capability 7.5.
- [Ollama FAQ](https://docs.ollama.com/faq) for interpreting the processor
  column produced by `ollama ps`.
