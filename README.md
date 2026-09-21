# GRASP-SQL

GRASP-SQL is a graph-aware, LLM-based Text-to-SQL pipeline for SQLite databases.
It implements the LLM variant described in the paper through three stages:

1. **Graph-augmented schema linking** builds a heterogeneous table/column graph,
   identifies target and condition columns with an LLM, then connects them with a
   weighted Steiner tree.
2. **Rationale-first SQL generation** asks the LLM for a schema-grounded plan
   before generating a read-only SQLite query.
3. **AST-grounded iterative repair** executes the query locally and performs
   deterministic schema/value patches or a clause-level LLM repair when needed.

The implementation supports BIRD-style data and the original Spider JSON format.

## Installation

Python 3.11 is required.

```bash
conda create -n SQL python=3.11 -y
conda activate SQL
pip install -r requirements.txt
```

Copy the example configuration and fill in an OpenAI-compatible API endpoint.
The `.env` file is ignored by Git and is loaded automatically at runtime.

```bash
cp .env.example .env
```

Environment variables take precedence over values in `.env`, which is useful for
CI or scheduled runs.

## Dataset Layout

The dataset JSON and database root are passed independently, so no files need to
be copied into this repository.

For **BIRD**, use its `dev.json` and the matching `dev_databases` directory:

```text
BIRD/dev_data/dev.json
BIRD/dev_data/dev_databases/<db_id>/<db_id>.sqlite
```

For **Spider**, use the original `dev.json` and `database` (or
`test_database`) directory:

```text
Spider/dev.json
Spider/database/<db_id>/<db_id>.sqlite
```

Spider samples are normalized automatically: `query` becomes `SQL`, evidence is
empty, and the list index is used as `question_id`.

## Build Schema Graphs

Graph construction is a one-time preprocessing step. The resulting JSON graphs
can be shared by inference and evaluation runs.

```bash
python build_graphs.py \
  --dataset /path/to/Spider/dev.json \
  --database-root /path/to/Spider/database \
  --output-dir outputs/spider-dev-graphs
```

For BIRD, replace the two input paths with `dev_data/dev.json` and
`dev_data/dev_databases`.

## Run Inference

The following command runs the complete pipeline. `--resume` safely skips
question IDs already present in the output JSONL file.

```bash
python run_pipeline.py \
  --dataset /path/to/Spider/dev.json \
  --database-root /path/to/Spider/database \
  --graph-root outputs/spider-dev-graphs \
  --output outputs/spider-dev-predictions.jsonl \
  --max-repairs 2 \
  --resume
```

Use `--limit 10` for a small smoke run. If a graph is absent from `--graph-root`,
the pipeline builds it in memory for that run.

Each JSONL record contains the generated SQL, selected schema subgraph, rationale,
execution status, repair strategies, latency, and API token usage.

## Evaluate Execution Accuracy

Execution accuracy compares each predicted result with the reference SQL result on
the same SQLite database. Rows are compared as multisets unless the reference SQL
contains `ORDER BY`.

```bash
python evaluate.py \
  --dataset /path/to/Spider/dev.json \
  --predictions outputs/spider-dev-predictions.jsonl \
  --database-root /path/to/Spider/database
```

## Tests

The test suite is offline and does not call an LLM API.

```bash
python -m unittest discover -s tests -v
```

## Security and Safety

Only a single `SELECT` or `WITH` query is accepted for local execution. Databases
are opened in SQLite read-only mode, and non-query statements are rejected before
execution. Ground-truth SQL is used only by `evaluate.py`; it is never provided to
the inference or repair prompts.
