# Retrieval-Augmented Generation (RAG)

## Introdução ao RAG

Retrieval-Augmented Generation (RAG) é uma arquitetura que combina recuperação de informações com geração de texto para melhorar a qualidade e precisão das respostas de modelos de linguagem. Em vez de depender apenas do conhecimento pré-treinado do modelo, RAG recupera informações relevantes de uma base de conhecimento externa antes de gerar uma resposta.

RAG resolve problemas comuns de modelos de linguagem como:
- Alucinações (geração de informações incorretas)
- Conhecimento desatualizado
- Falta de acesso a informações específicas do domínio
- Dificuldade em citar fontes

## Arquitetura RAG

### Componentes Principais

**1. Retrieval (Recuperação)**
- Busca documentos relevantes de uma base de conhecimento
- Usa técnicas de busca semântica (vector search)
- Retorna os documentos mais relevantes para a query

**2. Augmentation (Aumento)**
- Combina a query original com os documentos recuperados
- Cria um contexto enriquecido para o modelo de linguagem

**3. Generation (Geração)**
- O modelo de linguagem gera resposta baseada no contexto aumentado
- Resposta é fundamentada nos documentos recuperados

### Fluxo Típico

```
Query → Embedding → Vector Search → Top-K Documents
                                              ↓
Response ← LLM Generation ← Context Assembly ← Documents
```

## Tipos de RAG

### RAG Denso (Dense RAG)

Usa embeddings densos (vetores contínuos) para busca semântica. Modelos como BERT ou modelos de embedding especializados convertem texto em vetores de alta dimensionalidade.

**Vantagens**:
- Captura similaridade semântica
- Não depende de palavras-chave exatas
- Funciona bem com sinônimos e variações

**Desvantagens**:
- Requer modelo de embedding treinado
- Pode ser computacionalmente caro

### RAG Esparso (Sparse RAG)

Usa representações esparsas como BM25 ou TF-IDF para busca baseada em palavras-chave.

**Vantagens**:
- Mais rápido e eficiente
- Não requer modelo de embedding
- Boa para queries com palavras-chave específicas

**Desvantagens**:
- Não captura semelhança semântica
- Falha com sinônimos

### RAG Híbrido

Combina busca densa e esparsa para obter melhor dos dois mundos.

## Pipeline de RAG

### Fase 1: Indexação (Offline)

**1. Ingestão de Documentos**
- Coleta documentos de fontes diversas
- Suporta múltiplos formatos (PDF, DOCX, TXT, MD, HTML)

**2. Chunking (Segmentação)**
- Divide documentos em chunks menores e gerenciáveis
- Estratégias comuns:
  - Chunks fixos com overlap
  - Chunking semântico (baseado em significado)
  - Chunking por parágrafo ou seção

**Decisões importantes**:
- **Tamanho do chunk**: Balanceia contexto vs especificidade
- **Overlap**: Previne perda de informação nas bordas
- **Boundary detection**: Tenta quebrar em limites naturais (parágrafos)

**3. Geração de Embeddings**
- Converte cada chunk em um vetor denso usando modelo de embedding
- Modelos populares: text-embedding-ada-002, text-embedding-3-small
- Embeddings capturam significado semântico do texto

**4. Armazenamento Vetorial**
- Armazena embeddings em banco de dados vetorial
- Opções populares:
  - **pgvector**: Extensão PostgreSQL para vetores
  - **Pinecone**: Serviço gerenciado de vector database
  - **Weaviate**: Banco de dados vetorial open-source
  - **Chroma**: Banco de dados vetorial leve

### Fase 2: Query (Online)

**1. Query Embedding**
- Converte a pergunta do usuário em embedding usando o mesmo modelo

**2. Similarity Search**
- Busca os K chunks mais similares usando distância de cosseno ou outras métricas
- Retorna documentos ordenados por relevância

**3. Context Assembly**
- Combina query com documentos recuperados
- Formata contexto para o modelo de linguagem

**4. Generation**
- Modelo de linguagem gera resposta baseada no contexto
- Resposta deve ser fundamentada nos documentos recuperados

## Técnicas Avançadas de RAG

### Re-ranking

Após recuperação inicial, re-rankeia resultados usando modelo mais sofisticado (cross-encoder) para melhorar precisão.

### Query Expansion

Expande query original com termos relacionados ou sinônimos para melhorar recall.

### Multi-Query RAG

Gera múltiplas versões da query e combina resultados para melhor cobertura.

### Parent-Child Chunking

Armazena chunks pequenos para busca, mas inclui contexto maior (parent chunk) na geração.

### Metadata Filtering

Filtra documentos por metadados (data, autor, tipo) antes ou depois da busca vetorial.

## Métricas de Avaliação

### Retrieval Metrics

- **Recall@K**: Proporção de documentos relevantes recuperados nos top K
- **Precision@K**: Proporção de documentos recuperados que são relevantes
- **MRR (Mean Reciprocal Rank)**: Média do inverso da posição do primeiro documento relevante

### Generation Metrics

- **BLEU**: Mede similaridade n-gram entre resposta gerada e referência
- **ROUGE**: Mede sobreposição de unidades entre resposta e referência
- **Semantic Similarity**: Usa embeddings para medir similaridade semântica

### End-to-End Metrics

- **Faithfulness**: Resposta está fundamentada nos documentos recuperados?
- **Answer Relevance**: Resposta responde à pergunta?
- **Context Precision**: Documentos recuperados são relevantes?

## Guardrails em RAG

### Validação de Domínio

Garante que queries estão dentro do escopo da base de conhecimento. Bloqueia perguntas fora do domínio.

### Detecção de Prompt Injection

Protege contra tentativas de manipular o sistema através de prompts maliciosos.

### Validação de Resposta

Verifica se a resposta gerada está realmente baseada nos documentos recuperados, não em conhecimento pré-treinado.

### Sanitização

Remove conteúdo potencialmente perigoso ou inadequado das respostas.

## Desafios e Limitações

### Qualidade da Recuperação

Se documentos relevantes não são recuperados, a resposta será limitada ou incorreta.

### Chunking Subótimo

Chunks muito pequenos perdem contexto; chunks muito grandes podem incluir informação irrelevante.

### Custo e Latência

RAG adiciona latência (busca + geração) e custo (embeddings + LLM) comparado a geração direta.

### Dependência de Base de Conhecimento

Qualidade do RAG depende diretamente da qualidade e completude da base de conhecimento.

## Otimizações

### Caching

Cache de embeddings e resultados de busca para queries similares.

### Batch Processing

Processa múltiplas queries em batch para eficiência.

### Indexação Incremental

Atualiza índice apenas com novos documentos, não reprocessa tudo.

### Compressão de Embeddings

Reduz dimensionalidade de embeddings para economizar espaço e acelerar busca.

## Aplicações Práticas

RAG é usado em:
- **Chatbots empresariais**: Acesso a documentação interna
- **Assistentes de pesquisa**: Busca em artigos científicos ou notícias
- **Sistemas de Q&A**: Responder perguntas sobre documentos específicos
- **Code assistants**: Buscar e usar código de repositórios
- **Customer support**: Acesso a base de conhecimento de produtos

## Tendências Futuras

- **RAG Multimodal**: Incorpora imagens, áudio e vídeo além de texto
- **RAG Adaptativo**: Ajusta estratégia de recuperação baseado na query
- **RAG com Memória**: Mantém contexto de conversações anteriores
- **RAG Especializado**: Modelos otimizados para domínios específicos
- **RAG Mais Eficiente**: Redução de custo e latência através de técnicas avançadas

## Best Practices

1. **Chunking Inteligente**: Use overlap e respeite limites naturais do texto
2. **Embeddings de Qualidade**: Use modelos de embedding bem treinados e atualizados
3. **Top-K Apropriado**: Balanceie cobertura (alto K) com relevância (baixo K)
4. **Prompt Engineering**: Crie prompts que guiem o LLM a usar o contexto
5. **Monitoramento**: Rastreie métricas de retrieval e generation para melhorias contínuas
6. **Validação**: Implemente guardrails para garantir qualidade e segurança

