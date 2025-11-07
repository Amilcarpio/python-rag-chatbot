# Processamento de Linguagem Natural (NLP)

## O que é NLP?

Processamento de Linguagem Natural (NLP) é um campo da Inteligência Artificial que se concentra na interação entre computadores e linguagem humana. O objetivo é permitir que máquinas compreendam, interpretem e gerem texto e fala de forma semelhante aos humanos.

NLP combina técnicas de linguística computacional, machine learning e deep learning para processar grandes volumes de dados de linguagem natural.

## Componentes Fundamentais do NLP

### Tokenização

Tokenização é o processo de dividir texto em unidades menores chamadas tokens. Pode ser feita em nível de palavra, caractere ou subpalavra (subword).

**Exemplo**: "Machine Learning é incrível" → ["Machine", "Learning", "é", "incrível"]

### Análise Morfológica

Análise da estrutura interna das palavras, incluindo raízes, prefixos e sufixos. Útil para reduzir palavras às suas formas base (stemming e lemmatization).

### Análise Sintática

Análise da estrutura gramatical das sentenças, identificando relações entre palavras através de parsing.

### Análise Semântica

Compreensão do significado das palavras e frases em contexto. Inclui resolução de ambiguidade e identificação de relações semânticas.

## Técnicas Tradicionais de NLP

### Bag of Words (BoW)

Representação de texto como um vetor de contagem de palavras, ignorando ordem e estrutura. Simples mas eficaz para muitas tarefas.

### TF-IDF (Term Frequency-Inverse Document Frequency)

Métrica que avalia a importância de uma palavra em um documento relativo a uma coleção de documentos. Palavras muito comuns recebem peso menor.

### Word Embeddings

Representações vetoriais densas de palavras que capturam relações semânticas e sintáticas. Modelos populares incluem Word2Vec, GloVe e FastText.

**Características**:
- Palavras semanticamente similares têm vetores próximos
- Operações matemáticas podem revelar relações (ex: rei - homem + mulher ≈ rainha)
- Reduz dimensionalidade comparado a representações esparsas

## Deep Learning em NLP

### Redes Neurais Recorrentes (RNNs)

RNNs processam sequências mantendo memória de estados anteriores. Úteis para modelagem de linguagem e tradução.

**Limitações**: Dificuldade em capturar dependências de longo alcance devido ao problema de vanishing gradients.

### LSTMs e GRUs

Long Short-Term Memory (LSTM) e Gated Recurrent Units (GRU) são variantes de RNNs que resolvem problemas de memória de longo prazo através de mecanismos de portão.

### Transformers

Arquitetura revolucionária que usa mecanismos de atenção (attention) para processar sequências de forma paralela, superando limitações de RNNs.

**Componentes principais**:
- **Self-Attention**: Permite que cada posição da sequência acesse informações de todas as outras posições
- **Multi-Head Attention**: Múltiplas representações de atenção em paralelo
- **Feed-Forward Networks**: Processamento não-linear por posição

## Modelos de Linguagem Pré-treinados

### BERT (Bidirectional Encoder Representations from Transformers)

Modelo que pré-treina representações bidirecionais usando máscara de linguagem. Excelente para tarefas de compreensão.

### GPT (Generative Pre-trained Transformer)

Modelo autoregressivo que gera texto sequencialmente. Versões como GPT-3 e GPT-4 demonstraram capacidades impressionantes de geração.

### Outros Modelos Importantes

- **T5**: Text-to-Text Transfer Transformer, trata todas as tarefas como geração de texto
- **RoBERTa**: Versão otimizada do BERT
- **ELECTRA**: Treina discriminadores em vez de geradores

## Tarefas Comuns em NLP

### Classificação de Texto

Categorizar documentos ou sentenças em classes predefinidas. Aplicações incluem análise de sentimento, detecção de spam e categorização de notícias.

### Named Entity Recognition (NER)

Identificar e classificar entidades nomeadas como pessoas, organizações, locais e datas em texto.

### Machine Translation

Tradução automática entre idiomas. Sistemas modernos usam arquiteturas encoder-decoder com atenção.

### Question Answering

Responder perguntas baseadas em contexto. Sistemas podem ser extractivos (extraem resposta do texto) ou generativos (geram resposta).

### Summarization

Criar resumos concisos de documentos longos. Pode ser extractiva (seleciona sentenças) ou abstrativa (gera novo texto).

### Sentiment Analysis

Determinar o sentimento ou opinião expresso em texto (positivo, negativo, neutro).

## Embeddings e Representações

### Word Embeddings Estáticos

Modelos como Word2Vec e GloVe criam representações fixas para palavras, não considerando contexto.

### Contextualized Embeddings

Modelos modernos como ELMo, BERT e GPT geram representações que variam conforme o contexto da palavra na sentença.

**Vantagens**:
- Capturam polissemia (palavras com múltiplos significados)
- Melhor representação de sentido contextual
- Performance superior em tarefas downstream

## Desafios em NLP

### Ambiguidade

Palavras e frases podem ter múltiplos significados dependendo do contexto. Resolver ambiguidade requer compreensão profunda.

### Linguagem Informal

Textos em redes sociais e conversas informais apresentam desafios como gírias, erros ortográficos e abreviações.

### Multilinguismo

Desenvolver sistemas que funcionem bem em múltiplos idiomas requer grandes quantidades de dados e técnicas específicas.

### Viés e Ética

Modelos de NLP podem perpetuar estereótipos e preconceitos presentes nos dados de treinamento. É crucial desenvolver sistemas mais justos e éticos.

## Aplicações Práticas

NLP tem aplicações em:
- Assistentes virtuais (Siri, Alexa, Google Assistant)
- Tradução automática (Google Translate)
- Chatbots e atendimento ao cliente
- Análise de sentimentos em redes sociais
- Busca semântica e recuperação de informação
- Geração automática de conteúdo
- Correção gramatical e ortográfica

## Tendências Futuras

- Modelos maiores e mais eficientes
- Multimodalidade (combinando texto, imagem e áudio)
- Few-shot e zero-shot learning
- Sistemas mais interpretáveis e explicáveis
- Aplicações em domínios específicos (médico, jurídico, etc.)

