from typing import Any

import chromadb
from openai import OpenAI

from quiz import QUESTIONS, validate_read_only_query


EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
MAX_QUESTION_LENGTH = 1_000
RETRIEVAL_COUNT = 4

SCHEMA_DOCUMENT = """Database schema: public.economic_indicators
One row per country for year 2024. Columns:
- country (text): country name.
- year (integer): observation year.
- gdp_per_capita (numeric): GDP per person.
- inflation_rate (numeric): inflation percentage, e.g. 24.5 means 24.5%.
- unemployment_rate (numeric): unemployment percentage.
- population (bigint): number of people, not millions.
Use public.economic_indicators for economics quiz queries. The database is PostgreSQL.
"""

KNOWLEDGE_DOCUMENTS = [
    {"id": "schema", "source": "Database schema", "text": SCHEMA_DOCUMENT},
    *[
        {
            "id": f"question-{question['number']}",
            "source": f"Quiz question {question['number']}",
            "text": (
                f"Question: {question['prompt']}\n"
                f"Example PostgreSQL query:\n{question['sql']}"
            ),
        }
        for question in QUESTIONS
    ],
]


class SQLRAG:
    def __init__(
        self,
        api_key: str,
        openai_client: Any | None = None,
        vector_client: Any | None = None,
    ) -> None:
        self.openai = openai_client or OpenAI(api_key=api_key)
        self.vectors = vector_client or chromadb.Client()
        self.collection = self.vectors.get_or_create_collection(
            name="economics_sql_knowledge_v1",
            metadata={"hnsw:space": "cosine"},
        )
        if self.collection.count() == 0:
            embeddings = self._embed([item["text"] for item in KNOWLEDGE_DOCUMENTS])
            self.collection.add(
                ids=[item["id"] for item in KNOWLEDGE_DOCUMENTS],
                embeddings=embeddings,
                documents=[item["text"] for item in KNOWLEDGE_DOCUMENTS],
                metadatas=[{"source": item["source"]} for item in KNOWLEDGE_DOCUMENTS],
            )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = self.openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def generate_sql(self, question: str) -> tuple[str, list[str]]:
        question = question.strip()
        if not question:
            raise ValueError("Enter a natural-language question.")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError(
                f"Questions must be {MAX_QUESTION_LENGTH:,} characters or fewer."
            )

        retrieved = self.collection.query(
            query_embeddings=self._embed([question]),
            n_results=min(RETRIEVAL_COUNT, self.collection.count()),
            include=["documents", "metadatas"],
        )
        documents = retrieved["documents"][0]
        metadatas = retrieved["metadatas"][0]
        if not documents:
            raise RuntimeError("ChromaDB did not retrieve any SQL knowledge.")

        context = "\n\n".join(
            f"Source: {metadata['source']}\n{document}"
            for document, metadata in zip(documents, metadatas)
        )
        response = self.openai.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0,
            max_tokens=500,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate one PostgreSQL SELECT query for the user's question. "
                        "Use the retrieved schema and examples; do not invent tables or "
                        "columns. Return only SQL, with no explanation or Markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Retrieved database knowledge:\n{context}\n\n"
                        f"Question: {question}"
                    ),
                },
            ],
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("The AI API returned an empty SQL response.")

        sql = content.strip()
        if sql.startswith("```"):
            lines = sql.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                sql = "\n".join(lines[1:-1]).strip()
        validate_read_only_query(sql)
        sources = list(dict.fromkeys(metadata["source"] for metadata in metadatas))
        return sql, sources
