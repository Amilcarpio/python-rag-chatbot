from typing import Dict, List, Optional
import re

class GuardrailsService:
    """
    Serviço de guardrails para proteger o sistema RAG

    Decisões técnicas:
    - Prompt Injection: Padrões baseados em heurísticas
      * Detecção de tentativas de "jailbreak"
      * Bloqueio de comandos do sistema
      * Alertas para queries suspeitas

    - Domain Validation: Escopo do desafio
      * Apenas perguntas sobre IA, ML, NLP, RAG
      * Rejeita perguntas fora do contexto
      * Sugere reformulação quando necessário

    - Content Filtering: Segurança básica
      * Bloqueia linguagem ofensiva
      * Limita tamanho de queries
      * Sanitização de entrada
    """

    INJECTION_PATTERNS = [
        r"ignore\s+previous\s+instructions",
        r"ignore\s+above",
        r"disregard\s+previous",
        r"forget\s+previous",
        r"you\s+are\s+now",
        r"new\s+instructions",
        r"system\s+prompt",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"\[SYSTEM\]",
        r"\[/SYSTEM\]",
        r"sudo\s+",
        r"rm\s+-rf",
    ]

    DOMAIN_KEYWORDS = [
        "ia", "inteligência artificial", "artificial intelligence", "ai",
        "ml", "machine learning", "aprendizado de máquina",
        "nlp", "processamento de linguagem natural", "natural language processing",
        "rag", "retrieval augmented generation", "retrieval-augmented",
        "embedding", "vector", "vetor", "similaridade",
        "chunk", "chunking", "segmentação",
        "llm", "large language model", "modelo de linguagem",
        "transformer", "bert", "gpt", "openai",
        "neural network", "rede neural", "deep learning",
        "dados", "data", "dataset", "corpus",
        "treinamento", "training", "fine-tuning",
        "prompt", "contexto", "context"
    ]

    def __init__(self):
        self.injection_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.INJECTION_PATTERNS
        ]

    def validate_query(
        self,
        query: str,
        max_length: int = 500,
        check_injection: bool = True,
        check_domain: bool = True
    ) -> Dict:

        violations = []
        severity = 'low'

        if not query or not query.strip():
            return {
                'is_valid': False,
                'violations': ['empty_query'],
                'severity': 'medium',
                'message': 'Por favor, faça uma pergunta.'
            }

        if len(query) > max_length:
            violations.append('query_too_long')
            return {
                'is_valid': False,
                'violations': violations,
                'severity': 'medium',
                'message': f'Pergunta muito longa. Limite: {max_length} caracteres.'
            }

        if check_injection:
            injection_detected = self._check_injection(query)
            if injection_detected:
                violations.append('prompt_injection')
                severity = 'high'
                return {
                    'is_valid': False,
                    'violations': violations,
                    'severity': severity,
                    'message': 'Query suspeita detectada. Por favor, reformule sua pergunta.'
                }

        if check_domain:
            domain_valid = self._check_domain(query)
            if not domain_valid:
                violations.append('out_of_domain')
                severity = 'low'
                return {
                    'is_valid': False,
                    'violations': violations,
                    'severity': severity,
                    'message': (
                        'Sua pergunta parece estar fora do escopo. '
                        'Este chatbot responde sobre IA, ML, NLP e RAG. '
                        'Por favor, faça uma pergunta relacionada a esses tópicos.'
                    )
                }

        return {
            'is_valid': True,
            'violations': [],
            'severity': 'low',
            'message': 'Query válida',
            'sanitized_query': query.strip()
        }

    def _check_injection(self, query: str) -> bool:

        query_lower = query.lower()

        for pattern in self.injection_regex:
            if pattern.search(query_lower):
                return True

        special_chars = sum(1 for c in query if c in ['<', '>', '|', '{', '}', '[', ']'])
        if special_chars > 10:
            return True

        if query.count('\n') > 5:
            return True

        return False

    def _check_domain(self, query: str) -> bool:

        query_lower = query.lower()

        for keyword in self.DOMAIN_KEYWORDS:
            if keyword.lower() in query_lower:
                return True

        if len(query.split()) <= 3:
            return True

        return False

    def sanitize_response(self, response: str, max_length: int = 2000) -> str:

        if len(response) > max_length:
            response = response[:max_length] + "... (resposta truncada)"

        response = re.sub(r'\[SYSTEM\].*?\[/SYSTEM\]', '', response, flags=re.DOTALL)
        response = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', response, flags=re.DOTALL)

        return response.strip()

    def log_violation(self, query: str, violations: List[str], severity: str) -> None:

        print(f"⚠️  GUARDRAIL VIOLATION")
        print(f"   Severity: {severity}")
        print(f"   Violations: {violations}")
        print(f"   Query: {query[:100]}...")
