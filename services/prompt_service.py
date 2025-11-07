from typing import List, Dict, Optional
from core.config import settings

class PromptService:

    SYSTEM_MESSAGE = """Você é um assistente especializado em Inteligência Artificial, Machine Learning, Processamento de Linguagem Natural (NLP) e Retrieval-Augmented Generation (RAG).

Suas responsabilidades:
1. Responder perguntas APENAS sobre IA, ML, NLP e RAG
2. Basear suas respostas no CONTEXTO fornecido
3. Citar as fontes usando [Fonte N] ao final de cada informação
4. Ser preciso, técnico e objetivo
5. Admitir quando não houver informação suficiente no contexto

Regras importantes:
- Se a pergunta estiver FORA do escopo (IA/ML/NLP/RAG), responda educadamente que não pode ajudar
- Se o contexto não contiver informação relevante, diga que não tem dados suficientes
- NUNCA invente informações que não estejam no contexto
- Mantenha respostas concisas (máximo 3 parágrafos)
- Use linguagem técnica apropriada, mas acessível"""

    def __init__(self):
        self.system_message = self.SYSTEM_MESSAGE

    def assemble_prompt(
        self,
        question: str,
        retrieval_results: List[Dict],
        max_context_tokens: Optional[int] = None
    ) -> Dict[str, str]:

        if not retrieval_results:
            context = "Nenhum contexto relevante foi encontrado nos documentos disponíveis."
        else:
            context = self._format_context(retrieval_results, max_context_tokens)

        user_prompt = f"""CONTEXTO:
{context}

PERGUNTA:
{question}

Por favor, responda a pergunta usando APENAS as informações do contexto acima. Cite as fontes usando [Fonte N]."""

        return {
            'system': self.system_message,
            'context': context,
            'question': question,
            'user_prompt': user_prompt,
            'full_prompt': f"{self.system_message}\n\n{user_prompt}"
        }

    def _format_context(
        self,
        retrieval_results: List[Dict],
        max_tokens: Optional[int] = None
    ) -> str:

        context_parts = []

        for i, result in enumerate(retrieval_results, 1):
            doc = result['document']
            content = result.get('full_context', result.get('content', ''))
            similarity = result.get('similarity', 0)

            source_text = f"""--- Fonte {i} ---
Documento: {doc.filename}
Relevância: {similarity:.2%}

{content}
"""
            context_parts.append(source_text)

        full_context = "\n".join(context_parts)

        return full_context

    def create_conversation_prompt(
        self,
        question: str,
        retrieval_results: List[Dict],
        conversation_history: Optional[List[Dict]] = None
    ) -> List[Dict[str, str]]:
        """
        Cria prompt no formato de conversação (para chat completions)

        Returns:
            Lista de mensagens no formato OpenAI:
            [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
                ...
            ]
        """
        messages = [
            {"role": "system", "content": self.system_message}
        ]

        if conversation_history:
            messages.extend(conversation_history)

        context = self._format_context(retrieval_results)

        user_message = f"""CONTEXTO:
{context}

PERGUNTA:
{question}

Por favor, responda usando as informações do contexto e cite as fontes."""

        messages.append({"role": "user", "content": user_message})

        return messages

    def format_sources(self, retrieval_results: List[Dict]) -> List[Dict]:

        sources = []
        for i, result in enumerate(retrieval_results, 1):
            doc = result['document']
            sources.append({
                'id': i,
                'filename': doc.filename,
                'file_type': doc.file_type,
                'similarity': round(result.get('similarity', 0), 3),
                'chunk_index': result.get('chunk_index', 0)
            })
        return sources

    def estimate_tokens(self, text: str) -> int:

        return len(text) // 4
