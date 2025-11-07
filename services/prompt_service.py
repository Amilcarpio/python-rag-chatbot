from typing import List, Dict

class PromptService:

    SYSTEM_MESSAGE = """You are an assistant specialized in Artificial Intelligence, Machine Learning, Natural Language Processing (NLP) and Retrieval-Augmented Generation (RAG).

Your responsibilities:
1. Answer questions ONLY about AI, ML, NLP and RAG
2. Base your answers on the provided CONTEXT
3. Cite sources using [Source N] at the end of each piece of information
4. Be precise, technical and objective
5. Admit when there is not enough information in the context

Important rules:
- If the question is OUTSIDE the scope (AI/ML/NLP/RAG), politely respond that you cannot help
- If the context does not contain relevant information, say that you don't have enough data
- NEVER invent information that is not in the context
- Keep responses concise (maximum 3 paragraphs)
- Use appropriate technical language, but accessible"""

    def __init__(self):
        self.system_message = self.SYSTEM_MESSAGE

    def _format_context(
        self,
        retrieval_results: List[Dict]
    ) -> str:

        context_parts = []

        for i, result in enumerate(retrieval_results, 1):
            doc = result['document']
            content = result.get('full_context', result.get('content', ''))
            similarity = result.get('similarity', 0)

            source_text = f"""--- Source {i} ---
Document: {doc.filename}
Relevance: {similarity:.2%}

{content}
"""
            context_parts.append(source_text)

        full_context = "\n".join(context_parts)

        return full_context

    def create_conversation_prompt(
        self,
        question: str,
        retrieval_results: List[Dict]
    ) -> List[Dict[str, str]]:
        """
        Creates a conversation prompt (for chat completions)

        Returns:
            List of messages in OpenAI format:
            [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
            ]
        """
        messages = [
            {"role": "system", "content": self.system_message}
        ]

        context = self._format_context(retrieval_results)

        user_message = f"""CONTEXT:
{context}

QUESTION:
{question}

Please answer using the information from the context and cite the sources."""

        messages.append({"role": "user", "content": user_message})

        return messages
