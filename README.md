# Dynamic Ensemble Reasoning (DER)

## What this is

This repo contains the **DER runtime**: a deterministic orchestration loop that coordinates multiple LLM “agents” (roles × models), merges their outputs via a chairman step, applies approved code edits to a workspace, and persists state so runs are **replayable and auditable**.

DER is implemented as a **LangGraph** pipeline (see `run_graph.py`) with explicit, versioned state written to disk under your working directory.

---

## Quickstart

### 1) Install

```bash
pip install -r requirements.txt
```

`requirements.txt` includes (non-exhaustive): `langgraph`, `openai`, `anthropic`, `google-generativeai`. DER will call the providers’ official SDKs.

### 2) Set API keys

DER uses provider SDK defaults, so set the standard environment variables used by each SDK:

* OpenAI: `OPENAI_API_KEY`
* Anthropic: `ANTHROPIC_API_KEY`
* Google Gemini (google-genai): `GEMINI_API_KEY`

If a provider key is missing, that provider call will error and the run will produce empty output for that call.

### 3) Run DER (interactive on first run)

**Important:** DER uses absolute imports like `from memory.store import ...`, so run it from inside the `der/` directory.

```bash
cd der
python run_graph.py
```

On the first run, DER will prompt you for:

* phase (bootstrap/iterate)
* goal (free-form)
* language (python/java/c++)
* style (clean/minimal/performance)

Those values are written to `./task/task.json`.

---

## How DER runs

The entry point is **`run_graph.py`**, which builds and executes a LangGraph `StateGraph` with these nodes (in order):

1. **`load_memory`** (`memory/store.py`)

   * Root is the current working directory (`Path(os.getcwd())`).
   * Creates/repairs `./memory/memory.json`.
   * Sets default model pool and chairman pool if missing.

2. **`normalize_task`** (`task/state.py`)

   * Creates/updates `./task/task.json`.
   * On first run, collects values interactively.
   * On later runs, phase is computed from memory (`runs_completed >= warmup_runs` → `iterate`, else `bootstrap`).

3. **`load_prompts`** (`orchestration/prompts.py`)

   * Loads prompt templates from `./prompts/*.txt`.

4. **`select_role_assignments`** (`task/select.py`)

   * Chooses which models to use per role (default roles are `architect`, `implementer`).

5. **`build_agent_inputs`** (`orchestration/inputs.py`)

   * Builds provider payloads for each agent call.

6. **`run_agents`** (`orchestration/runner.py`)

   * Invokes providers (OpenAI/Anthropic/Gemini) via `orchestration/provider.py`.

7. **`chairman_merge`** (`orchestration/chairman.py`)

   * Chairman consolidates/approves edits.

8. **`update_files`** (`orchestration/persist.py`)

   * Writes/patches code into the workspace.

9. **`update_directory_structure`** (`orchestration/persist.py`)

   * Maintains a structured index of the generated code tree.

10. **`write_memory`** (`orchestration/persist.py`)

* Versions task + memory and advances run IDs.

At the end, `run_graph.py` prints `Run complete.`

---

## Outputs and on-disk state

DER persists everything relative to your working directory (the `der/` folder when you run from there):

* `./memory/memory.json`
  Persistent DER state (model pools, routing stats, run IDs, chairman summaries, etc.).

* `./task/task.json`
  The current task definition.

* `./task/previous_task.json`
  The previous task snapshot (rotated on each run).

* `./code/`
  The generated/edited code workspace. By default, DER writes per-model subdirectories like:

  * `./code/M1/`
  * `./code/M2/`

> Note: The repo also contains `example_der_output/`, which is **an artifact of a prior DER run** bundled for inspection. It is not used by the runtime unless you explicitly copy/point DER’s working directory to it.

---

## Defaults you should know

### Roles

DER uses two roles:

* `architect`
* `implementer`

### Default models

In `memory/store.py`, DER initializes a default model pool:

* `M1`: Gemini (`provider: gemini`, `provider_model: gemini-2.5-pro`)
* `M2`: Anthropic (`provider: anthropic`, `provider_model: claude-sonnet-4-5-20250929`)

and a default chairman:

* `C1`: OpenAI (`provider: openai`, `provider_model: gpt-4.1`)

You can change these by editing `./memory/memory.json` **between runs**.

### Phase switching

DER computes phase from memory:

* `bootstrap` while `runs_completed < warmup_runs`
* `iterate` after warmup

`warmup_runs` defaults to 3.

---

## Customization

### Change where code is written

DER defaults `directory_structure.base_path` to `./code`. You can override this by editing `memory.json` (under `directory_structure.base_path`) before running.

### Change model routing / weights

`memory.json` contains:

* `weighted_inputs` (role weighting)
* `routing_policy` (e.g., UCB exploration coefficient and cost penalty)
* `model_pool` / `chairman_pool`

DER repairs/normalizes these values on startup.
