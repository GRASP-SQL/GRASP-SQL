# Datasets

GRASP-SQL is primarily trained and evaluated on two major Text-to-SQL benchmarks:

- [BIRD](https://bird-bench.github.io/)
- [Spider](https://yale-lily.github.io/spider)

Any other dataset that follows the same data format can also be seamlessly integrated into GRASP-SQL.

---

## Directory Structure

All dataset files should be placed under the `data/` directory:

```
data/
│
├── databases/
│   ├── database_name_1/
│   │   ├── database_name_1.sqlite
│   │   └── database_description/        (optional)
│   │       ├── table1.csv
│   │       └── table2.csv
│   │
│   ├── database_name_2/
│   │   ├── database_name_2.sqlite
│   │   └── database_description/        (optional)
│   │
│   └── ...
│
└── dataset.json
```

## Components Explanation

### 1. `databases/`

This folder contains all SQLite databases.

Each subfolder corresponds to **one database**, and must contain:

- A SQLite file `database_name.sqlite`
- (Optional) A `database_description/` folder containing CSV files with additional schema descriptions.

### 2. `dataset.json` (or custom filename)

This file contains the question-level annotations used for training and evaluation. 

Each entry includes:

- `question_id`: Unique identifier of the question
- `db_id`: Target database ID
- `question`: Natural language query
- `evidence` (optional): Additional hints or supporting information
- `SQL` (*required for training and evaluation*): Ground-truth SQL query

Example format:

```json
[
  {
    "question_id": 0,
    "db_id": "employees",
    "question": "List all employee names.",
    "evidence": "The employee name is stored in column 'name'.",
    "SQL": "SELECT name FROM employee;"
  }
]
```

---

## Using BIRD

Download **BIRD** datasets from [https://bird-bench.github.io/](https://bird-bench.github.io/)

Because our format is based on BIRD, you only need to place:

- SQLite databases into `data/databases/`
- JSON file as the JSON file.

## Using Spider

Download **Spider 1.0** datasets from [https://yale-lily.github.io/spider](https://yale-lily.github.io/spider)

Spider uses a different JSON schema format. You must convert it into our BIRD-style format before using. We provide a Python script `scripts/convert_spider_json.py` to facilitate this conversion.
