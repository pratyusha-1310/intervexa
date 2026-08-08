/**
 * INTERVEXA - Isolated Mock Data Layer
 * 
 * NOTE FOR BACKEND INTEGRATION:
 * This file contains temporary sample data used exclusively for frontend UI demo & development.
 * The real candidate data, interview questions, and feedback evaluations will be provided
 * by the backend HTTP API post-hackathon.
 */

export const MOCK_COHORT_TOPICS = [
  'Retrieval-Augmented Generation (RAG)',
  'Vector Databases',
  'Prompt Engineering',
  'Agentic AI',
  'Model Context Protocol (MCP)',
  'AI Deployment',
  'Production AI Systems'
];

export const MOCK_CANDIDATES = [
  {
    id: 'cand-01',
    name: 'Alex Chen',
    track: 'RAG & Agentic AI Specialist',
    completedTopics: [
      'Retrieval-Augmented Generation (RAG)',
      'Vector Databases',
      'Agentic AI',
      'Prompt Engineering'
    ],
    skippedTopics: ['Model Context Protocol (MCP)'],
    learningSignals: [
      'Strong grasp of hybrid BM25 + dense vector retrieval',
      'Needs probing on chunking strategy trade-offs under high document variance',
      'Successfully implemented multi-agent loop with tool calls'
    ],
    demoScenario: {
      initialTopic: 'RAG',
      initialQuestion: `Welcome Alex. Let's begin by discussing your work with Retrieval-Augmented Generation. 

When designing a production RAG pipeline for dense technical documentation, how do you evaluate chunking strategies—specifically semantic chunking vs. fixed-size token sliding windows—and what impact does this choice have on downstream context retrieval accuracy?`,
      demoAnswer1: `In enterprise technical search, fixed-size sliding windows often split critical code blocks or API parameter tables across chunks. I prefer semantic chunking based on document AST or header boundaries. 

For dense documentation, we implemented a parent-child retriever pattern: small 256-token child chunks are indexed for high-precision vector cosine matching, but the parent 1024-token section is passed into the prompt context window to preserve full technical clarity.`,
      followUp1: `That parent-child retriever design directly addresses the context fragmentation problem. 

Following up on that: how did you handle vector store index latency when re-ranking retrieved candidates? Specifically, what trade-offs did you encounter when placing a Cross-Encoder re-ranker before LLM context injection?`,
      demoAnswer2: `Adding a Cross-Encoder like bge-reranker-large added around 120ms of latency per query, which was too slow for interactive chat. 

We optimized this by first fetching Top-50 results via HNSW vector index + Reciprocal Rank Fusion (RRF), then pruning to Top-15 before running a lightweight bi-encoder or flash Cross-Encoder. This brought re-ranking latency under 35ms while keeping Precision@5 above 92%.`,
      finalQuestion: `Impressive latency tuning. To close our discussion on production AI systems: how do you monitor and handle hallucination risks when your vector retriever returns low-confidence semantic matches (e.g., cosine similarity < 0.65)?`,
      demoAnswer3: `We enforce a strict confidence threshold at the retriever boundary. If the top cosine score is below 0.65, we bypass vector injection and trigger a fallback flow with explicit system prompt instructions: 'State clearly that context is unavailable in the database.' We also stream output through an automated LLM self-critique guardrail to detect ungrounded claims.`,
      feedback: {
        assessment: 'Strong',
        summary: 'Alex demonstrated deep architectural understanding of production RAG systems, showing exceptional maturity in vector index optimization, parent-child chunking, and latency-budgeted re-ranking.',
        competencies: {
          technicalUnderstanding: 94,
          depthOfReasoning: 92,
          communicationClarity: 95,
          systemDesign: 88
        },
        strengths: [
          'Articulated clear trade-offs between fixed sliding window vs. semantic parent-child chunking.',
          'Quantified latency budgets for Cross-Encoder re-rankers (reduced from 120ms to 35ms using RRF).',
          'Proactively implemented retriever confidence thresholds (0.65 similarity cut-off) to mitigate hallucination.'
        ],
        growthAreas: [
          'Could further explore Model Context Protocol (MCP) for standardizing external tool access.',
          'Consider evaluating speculative decoding or caching strategies for LLM guardrail verification.'
        ],
        revisitTopics: ['Model Context Protocol (MCP)', 'Production AI Systems']
      }
    }
  },
  {
    id: 'cand-02',
    name: 'Maya Lin',
    track: 'MCP & Enterprise Deployment Specialist',
    completedTopics: [
      'Model Context Protocol (MCP)',
      'AI Deployment',
      'Production AI Systems',
      'Vector Databases'
    ],
    skippedTopics: ['Prompt Engineering'],
    learningSignals: [
      'Demonstrated clean MCP client/server tool orchestration',
      'Built Dockerized vLLM deployment with auto-scaling',
      'Needs probing on context window saturation under concurrent agent calls'
    ],
    demoScenario: {
      initialTopic: 'MCP',
      initialQuestion: `Hello Maya. Let's focus on Model Context Protocol (MCP) and AI Deployment.

When building an enterprise AI assistant that interfaces with internal DBs via MCP servers, how do you handle state management and connection pooling across stateless LLM inference requests?`,
      demoAnswer1: `MCP decouples tool execution from LLM prompt construction. In our architecture, the MCP server runs as a sidecar microservice with a persistent PostgreSQL connection pool (pgbouncer). 

When the LLM generates a tool call request, our API gateway routes the structured JSON-RPC payload to the MCP server. Connection state is retained in Redis, avoiding DB connection exhaustion under high concurrency.`,
      followUp1: `Solid microservice separation. How do you prevent context window blowup when an MCP tool returns large payload objects (e.g. 5,000 JSON rows)?`,
      demoAnswer2: `We implement payload truncation and pagination at the MCP server boundary. Rather than dumping raw JSON into the LLM context, the MCP server computes a compact summary dataframe and stores the full result in temporary S3 storage, returning a reference ID. The LLM can then issue targeted follow-up queries if needed.`,
      finalQuestion: `Excellent handling of context constraints. Lastly, what monitoring metrics do you prioritize when deploying LLM endpoints with vLLM in production?`,
      demoAnswer3: `We monitor Time to First Token (TTFT), Inter-Token Latency (ITL), and KV Cache memory utilization percentage. If KV Cache usage exceeds 85%, our auto-scaler triggers additional model replicas to prevent requests from queueing in memory.`,
      feedback: {
        assessment: 'Solid',
        summary: 'Maya demonstrated excellent practical experience with Model Context Protocol microservices, payload pagination, and enterprise vLLM deployment metrics.',
        competencies: {
          technicalUnderstanding: 88,
          depthOfReasoning: 86,
          communicationClarity: 90,
          systemDesign: 92
        },
        strengths: [
          'Built clean MCP sidecar architecture with Redis connection pooling.',
          'Prevented LLM context window bloat via server-side payload summaries and reference IDs.',
          'Monitored key inference metrics (TTFT, ITL, KV Cache utilization) for auto-scaling.'
        ],
        growthAreas: [
          'Revisit advanced Prompt Engineering techniques for structured output validation.',
          'Explore hybrid vector search strategies alongside relational MCP database lookups.'
        ],
        revisitTopics: ['Prompt Engineering', 'Vector Databases']
      }
    }
  },
  {
    id: 'cand-03',
    name: 'David Kim',
    track: 'Vector DB & Agentic AI Specialist',
    completedTopics: [
      'Vector Databases',
      'Agentic AI',
      'Prompt Engineering',
      'Retrieval-Augmented Generation (RAG)'
    ],
    skippedTopics: ['AI Deployment'],
    learningSignals: [
      'Implemented HNSW index tuning for 10M+ embeddings',
      'Built multi-agent reflection loop for code generation',
      'Needs evaluation on error-handling when agent loops enter infinite recursion'
    ],
    demoScenario: {
      initialTopic: 'Vector DBs',
      initialQuestion: `Welcome David. Let's discuss your work with Vector Databases and Agentic AI.

When scaling a Qdrant or Milvus vector database past 10 million embedding vectors, how do you tune HNSW indexing parameters (`M` and `efConstruction`) to balance index build time vs. recall accuracy?`,
      demoAnswer1: `For 10M+ 1536-dimensional vectors, we set M=16 and efConstruction=200 during index build time. This ensures high recall (around 96%) while keeping index creation memory usage within server limits. During query execution, we dynamically adjust `efSearch` based on SLA: `efSearch=64` for realtime search, and `efSearch=128` for batch workloads.`,
      followUp1: `Clear understanding of HNSW index trade-offs. Moving to Agentic AI: how do you prevent autonomous agents from getting stuck in infinite reflection loops when tool execution repeatedly fails?`,
      demoAnswer2: `We implement a multi-layered guardrail: 1) A hard max_turns counter (capped at 5 loops), 2) A dynamic loop detector that hashes previous tool arguments and aborts if identical inputs recur, and 3) A fallback supervisor prompt that rewrites the sub-goal if progress stalls.`,
      finalQuestion: `Good defensive programming. Finally, how do you handle schema drifts or embedding model version upgrades without causing index downtime?`,
      demoAnswer3: `We use a blue-green index migration strategy. We spin up a new vector collection with the updated embedding model (e.g. text-embedding-3-large), backfill vectors in the background, and perform a dual-write during transition before swapping the API collection alias.`,
      feedback: {
        assessment: 'Strong',
        summary: 'David displayed high technical competency in large-scale vector indexing, HNSW parameter tuning, blue-green index migrations, and robust agent execution guardrails.',
        competencies: {
          technicalUnderstanding: 92,
          depthOfReasoning: 90,
          communicationClarity: 91,
          systemDesign: 89
        },
        strengths: [
          'Detailed knowledge of HNSW parameters (M, efConstruction, efSearch) for 10M+ vector datasets.',
          'Implemented multi-layered agent recursion prevention (hash-based duplicate detection + supervisor fallbacks).',
          'Designed zero-downtime blue-green vector collection migrations.'
        ],
        growthAreas: [
          'Strengthen knowledge of AI Deployment infra (vLLM, Triton Server containerization).',
          'Explore Model Context Protocol (MCP) for standardizing multi-agent tool integrations.'
        ],
        revisitTopics: ['AI Deployment', 'Model Context Protocol (MCP)']
      }
    }
  }
];
