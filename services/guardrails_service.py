from typing import Dict, List, Optional
import re

class GuardrailsService:
    """
    Guardrails service to protect the RAG system

    Technical decisions:
    - Prompt Injection: Heuristic-based patterns
      * Detection of "jailbreak" attempts
      * Blocking system commands
      * Alerts for suspicious queries

    - Domain Validation: Challenge scope
      * Only questions about AI, ML, NLP, RAG
      * Rejects questions outside context
      * Suggests reformulation when necessary

    - Content Filtering: Basic security
      * Blocks offensive language
      * Limits query size
      * Input sanitization
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
        r"override\s+system",
        r"bypass\s+security",
        r"jailbreak",
        r"roleplay",
        r"act\s+as",
        r"pretend\s+to\s+be",
        r"simulate",
        r"execute\s+code",
        r"run\s+command",
        r"cat\s+/etc/passwd",
        r"ls\s+-la",
        r"python\s+-c",
        r"eval\(",
        r"exec\(",
        r"__import__",
        r"subprocess",
        r"os\.system",
        r"shell\s+command",
        r"command\s+injection",
        r"script\s+tag",
        r"javascript:",
        r"onerror\s*=",
        r"onclick\s*=",
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
        "prompt", "contexto", "context",
        "tokenização", "tokenization", "tokenizar", "tokenize",
        "análise morfológica", "morphological analysis", "morfologia",
        "análise sintática", "syntactic analysis", "sintaxe", "syntax",
        "análise semântica", "semantic analysis", "semântica", "semantics",
        "stemming", "lemmatization", "lematização",
        "parsing", "parse", "parser",
        "word2vec", "glove", "fasttext", "word embedding",
        "bag of words", "bow", "tf-idf", "term frequency",
        "rnn", "lstm", "gru", "recurrent neural network",
        "attention", "self-attention", "attention mechanism",
        "classificação", "classification", "classificar",
        "sentimento", "sentiment", "análise de sentimento",
        "supervised learning", "aprendizado supervisionado",
        "unsupervised learning", "aprendizado não supervisionado",
        "reinforcement learning", "aprendizado por reforço",
        "decision tree", "árvore de decisão", "decision trees",
        "svm", "support vector machine", "support vector machines",
        "k-means", "kmeans", "clustering", "agrupamento",
        "cnn", "convolutional neural network", "rede neural convolucional",
        "narrow ai", "ia fraca", "general ai", "ia forte",
        "bias", "viés", "viés algorítmico", "algorithmic bias",
        "interpretability", "interpretabilidade", "explicabilidade",
        "retrieval", "recuperação", "busca", "search",
        "augmentation", "aumento", "enriquecimento",
        "generation", "geração", "gerar",
        "dense rag", "rag denso", "sparse rag", "rag esparso",
        "hybrid rag", "rag híbrido",
        "re-ranking", "reranking", "reordenar",
        "query expansion", "expansão de query", "expansão de consulta",
        "metadata filtering", "filtro de metadados",
        "recall", "precision", "mrr", "mean reciprocal rank",
        "bleu", "rouge", "faithfulness", "fidelidade",
        "answer relevance", "relevância da resposta",
        "context precision", "precisão do contexto",
        "chunking", "segmentação", "divisão de texto",
        "overlap", "sobreposição",
        "boundary detection", "detecção de limites",
        "vector search", "busca vetorial", "similarity search",
        "cosine similarity", "similaridade de cosseno",
        "pgvector", "pinecone", "weaviate", "chroma",
        "indexação", "indexing", "indexação incremental",
        "caching", "cache", "armazenamento em cache",
        "batch processing", "processamento em lote",
        "alucinação", "hallucination", "alucinações",
        "citação", "citation", "citações", "citations",
        "fonte", "source", "fontes", "sources"
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
                'message': 'Please ask a question.'
            }

        if len(query) > max_length:
            violations.append('query_too_long')
            return {
                'is_valid': False,
                'violations': violations,
                'severity': 'medium',
                'message': f'Question too long. Limit: {max_length} characters.'
            }

        if len(query.strip()) < 3:
            violations.append('query_too_short')
            return {
                'is_valid': False,
                'violations': violations,
                'severity': 'low',
                'message': 'Question too short. Please ask a more complete question.'
            }

        if re.search(r'http[s]?://', query, re.IGNORECASE):
            violations.append('url_detected')
            return {
                'is_valid': False,
                'violations': violations,
                'severity': 'medium',
                'message': 'URLs are not allowed in the question. Please reformulate.'
            }

        if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', query):
            violations.append('email_detected')
            return {
                'is_valid': False,
                'violations': violations,
                'severity': 'low',
                'message': 'Emails are not allowed in the question. Please reformulate.'
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
                    'message': 'Suspicious query detected. Please reformulate your question.'
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
                        'Your question seems to be outside the scope. '
                        'This chatbot answers about AI, ML, NLP and RAG. '
                        'Please ask a question related to these topics.'
                    )
                }

        return {
            'is_valid': True,
            'violations': [],
            'severity': 'low',
            'message': 'Valid query',
            'sanitized_query': query.strip()
        }

    def _check_injection(self, query: str) -> bool:

        query_lower = query.lower()

        for pattern in self.injection_regex:
            if pattern.search(query_lower):
                return True

        special_chars = sum(1 for c in query if c in ['<', '>', '|', '{', '}', '[', ']', '(', ')', ';', '=', '+', '*', '&', '%', '$', '#', '@', '!'])
        if special_chars > 10:
            return True

        if query.count('\n') > 5:
            return True

        if query.count('```') > 0:
            return True

        if re.search(r'\$\{.*?\}', query) or query.count('${') > 0:
            return True

        if re.search(r'<script', query_lower) or re.search(r'</script>', query_lower):
            return True

        if re.search(r'javascript:', query_lower):
            return True

        if re.search(r'on\w+\s*=', query_lower):
            return True

        if query.count('\\') > 10:
            return True

        if re.search(r'import\s+os|import\s+subprocess|import\s+sys', query_lower):
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
            response = response[:max_length] + "... (response truncated)"

        response = re.sub(r'\[SYSTEM\].*?\[/SYSTEM\]', '', response, flags=re.DOTALL)
        response = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', response, flags=re.DOTALL)

        return response.strip()

    def log_violation(self, query: str, violations: List[str], severity: str) -> None:

        print(f"⚠️  GUARDRAIL VIOLATION")
        print(f"   Severity: {severity}")
        print(f"   Violations: {violations}")
        print(f"   Query: {query[:100]}...")
