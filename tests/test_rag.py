import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

import chromadb

from rag import KNOWLEDGE_DOCUMENTS, MAX_QUESTION_LENGTH, SQLRAG


class SQLRAGTests(unittest.TestCase):
    def setUp(self) -> None:
        self.openai = MagicMock()
        self.openai.embeddings.create.side_effect = (
            lambda model, input: SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.1, 0.2]) for _ in input]
            )
        )
        self.collection = MagicMock()
        self.collection.count.side_effect = [0, len(KNOWLEDGE_DOCUMENTS)]
        self.collection.query.return_value = {
            "documents": [
                [
                    "Schema: public.economic_indicators, inflation_rate numeric",
                    "Example: SELECT country FROM public.economic_indicators",
                ]
            ],
            "metadatas": [
                [{"source": "Database schema"}, {"source": "Quiz question 2"}]
            ],
        }
        self.vectors = MagicMock()
        self.vectors.get_or_create_collection.return_value = self.collection
        self.openai.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            "```sql\n"
                            "SELECT country FROM public.economic_indicators;\n"
                            "```"
                        )
                    )
                )
            ]
        )
        self.rag = SQLRAG(
            "test-key",
            openai_client=self.openai,
            vector_client=self.vectors,
        )

    def test_initializes_chroma_with_schema_and_quiz_example_vectors(self) -> None:
        self.vectors.get_or_create_collection.assert_called_once_with(
            name="economics_sql_knowledge_v1",
            metadata={"hnsw:space": "cosine"},
        )
        self.assertEqual(
            self.collection.add.call_args.kwargs["ids"],
            [document["id"] for document in KNOWLEDGE_DOCUMENTS],
        )
        self.assertEqual(
            len(self.collection.add.call_args.kwargs["embeddings"]),
            len(KNOWLEDGE_DOCUMENTS),
        )

    def test_retrieves_context_and_generates_valid_select_sql(self) -> None:
        sql, sources = self.rag.generate_sql(
            "Which countries have inflation above five percent?"
        )

        self.collection.query.assert_called_once_with(
            query_embeddings=[[0.1, 0.2]],
            n_results=4,
            include=["documents", "metadatas"],
        )
        self.assertIn(
            "inflation_rate",
            self.openai.chat.completions.create.call_args.kwargs["messages"][1][
                "content"
            ],
        )
        self.assertEqual(
            sql,
            "SELECT country FROM public.economic_indicators;",
        )
        self.assertEqual(sources, ["Database schema", "Quiz question 2"])

    def test_rejects_non_select_model_output(self) -> None:
        self.openai.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="DELETE FROM public.economic_indicators"
                    )
                )
            ]
        )
        with self.assertRaisesRegex(ValueError, "one SELECT query only"):
            self.rag.generate_sql("Delete the economics data.")

    def test_rejects_empty_and_oversized_questions(self) -> None:
        with self.assertRaisesRegex(ValueError, "Enter a natural-language question"):
            self.rag.generate_sql("  ")
        with self.assertRaisesRegex(ValueError, "1,000 characters"):
            self.rag.generate_sql("x" * (MAX_QUESTION_LENGTH + 1))

    def test_uses_real_chromadb_collection_for_vector_retrieval(self) -> None:
        vector_rag = SQLRAG(
            "test-key",
            openai_client=self.openai,
            vector_client=chromadb.Client(),
        )

        sql, sources = vector_rag.generate_sql("Show countries with high inflation.")

        self.assertEqual(sql, "SELECT country FROM public.economic_indicators;")
        self.assertTrue(sources)
        self.assertGreater(vector_rag.collection.count(), 0)


if __name__ == "__main__":
    unittest.main()
