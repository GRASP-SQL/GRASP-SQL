
LINKER_SYSTEM = """You are an expert database engineer. Your task is to perform Schema Linking.
Given a database schema and a user question, identify two sets of columns:
1. **Target Columns**: STRICTLY for columns used in SELECT clauses.
2. **Condition Columns**: All other relevant columns (WHERE, JOIN, GROUP BY, ORDER BY, HAVING).

Please output the result in JSON format only, with keys "condition_columns" and "target_columns".
Format the column names strictly as "Table.Column".

Example Output:
{
  "condition_columns": ["schools.id", "schools.`County Name`"],
  "target_columns": ["frpm.`Free Meal Count`"]
}"""

LINKER_USER = """Database Schema:
{schema_text}

User Question: {question}
Evidence: {evidence}

Please provide the JSON output:"""

RATIONALE_L_SYSTEM = """You are an expert in SQL reasoning.
Given a database schema and a natural language question.
Your goal is to produce a clear, step-by-step reasoning process that logically leads to the correct SQL query.

**Think carefully about:**
1. Which tables contain the required data? Identify necessary JOIN paths using Foreign Keys.
2. Which columns map to the question's concepts? Check descriptions and examples.
3. Logic for filtering, grouping, and ordering.
4. SQLite specific syntax.

**Output format:**
Output ONLY your reasoning process inside <reasoning> tags.
Do NOT output the final SQL query code.
<reasoning>
Reasoning in English
</reasoning>"""

RATIONALE_C_SYSTEM = """You are an expert in SQL reasoning.
Given a database schema and a natural language question.
Your goal is to produce a VERY CONCISE reasoning process that logically leads to the correct SQL query.

**Think carefully about:**
1. Which tables contain the required data? Identify necessary JOIN paths using Foreign Keys.
2. Which columns map to the question's concepts? Check descriptions and examples.
3. Logic for filtering, grouping, and ordering.
4. SQLite specific syntax.

**Output format:**
Output ONLY your reasoning process inside <reasoning> tags.
Do NOT output the final SQL query code.
<reasoning>
CONCISE reasoning in English
</reasoning>"""

RATIONALE_USER = """[Database Schema]
{schema_text}

[Question] {question}
{evidence}

Please provide the reasoning process."""

SQL_SYSTEM = """You are an expert SQLite database engineer.
You will be provided with a database schema, a user question, and a step-by-step reasoning process.

### YOUR TASK:
Generate the valid SQLite SQL query after thinking.

### STRICT OUTPUT RULES:
- Output ONLY the SQL statement in a code block.
- Start directly with the keyword `SELECT`.
- Do not include SQL comments in your output."""

SQL_USER = """[Database Schema]
{schema_text}

[Reasoning] {reasoning}

-- Using valid SQLite, answer the question based on the reasoning above.
[Question] {question}
{evidence}

Generate the SQL:"""
