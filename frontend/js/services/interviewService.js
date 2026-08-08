/**
 * INTERVEXA - Frontend Data & Service Boundary
 * 
 * ARCHITECTURE DESIGN:
 * This service abstracts candidate dataset retrieval and interview turn management.
 * 
 * TURN STATE MACHINE (F2 QA FIX):
 * - Enforces a strict 3-turn interview limit.
 * - Turn counter is strictly clamped between Turn 1 of 3 and Turn 3 of 3.
 * - Single conclusion turn generated upon Turn 3 submission.
 * - Prevents submitAnswer() and requestClarification() processing once completed.
 */

class InterviewService {
  constructor() {
    this.cachedCandidates = null;
    this.selectedCandidate = null;
    this.activeSession = null;
    this.simulatedLatencyMs = 600;
  }

  async _delay(ms = this.simulatedLatencyMs) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async getCandidates() {
    try {
      const response = await fetch('./candidates.json');
      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}: Unable to fetch candidates.json`);
      }
      const data = await response.json();
      if (!data || !Array.isArray(data.candidates)) {
        throw new Error("Malformed JSON: 'candidates' array expected in data payload.");
      }
      this.cachedCandidates = data.candidates;
      return data.candidates;
    } catch (err) {
      console.error('InterviewService: Failed to fetch candidate data:', err);
      throw err;
    }
  }

  async getCandidateById(candidateId) {
    if (!this.cachedCandidates) {
      await this.getCandidates();
    }
    const found = this.cachedCandidates.find(
      c => c.member && c.member.id === candidateId
    );
    if (!found) {
      throw new Error(`Candidate with ID "${candidateId}" not found.`);
    }
    return found;
  }

  setSelectedCandidate(candidate) {
    this.selectedCandidate = candidate;
  }

  getSelectedCandidate() {
    return this.selectedCandidate;
  }

  /* ------------------------------------------------------------------------
     INTERVIEW SESSION STATE MACHINE (F2 QA FIX)
     ------------------------------------------------------------------------ */

  async startInterview(candidateId) {
    await this._delay(300);
    const candidate = await this.getCandidateById(candidateId);
    this.selectedCandidate = candidate;

    const scenarios = this._getScenarioForCandidate(candidate);

    const initialTurn = {
      turnNumber: 1,
      sender: 'ai',
      text: scenarios.initialQuestion,
      intentTag: 'Technical Scenario',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    this.activeSession = {
      candidateId: candidate.member.id,
      candidateName: candidate.member.name,
      jobRole: candidate.member.jobRole,
      currentTurnIndex: 1,
      maxTurns: 3,
      isActive: true,
      isCompleted: false,
      transcript: [initialTurn],
      scenarios: scenarios
    };

    return {
      sessionInfo: this.getSessionInfo(),
      initialTurn: initialTurn
    };
  }

  async submitAnswer(responseText) {
    if (!this.activeSession || !this.activeSession.isActive) {
      throw new Error('No active interview session found.');
    }

    if (this.activeSession.isCompleted) {
      throw new Error('Interview session has already been completed.');
    }

    if (!responseText || !responseText.trim()) {
      throw new Error('Response text cannot be empty.');
    }

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const turnNumber = Math.min(this.activeSession.currentTurnIndex, 3);

    // 1. Record candidate answer turn
    const userTurn = {
      turnNumber: turnNumber,
      sender: 'user',
      text: responseText.trim(),
      timestamp: timestamp
    };
    this.activeSession.transcript.push(userTurn);

    // 2. Simulate AI thinking / reasoning latency
    await this._delay(700);

    const sc = this.activeSession.scenarios;
    let aiTurn = null;

    if (turnNumber === 1) {
      this.activeSession.currentTurnIndex = 2;
      aiTurn = {
        turnNumber: 2,
        sender: 'ai',
        text: sc.followUpQuestion,
        intentTag: 'Probing Reasoning',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
    } else if (turnNumber === 2) {
      this.activeSession.currentTurnIndex = 3;
      aiTurn = {
        turnNumber: 3,
        sender: 'ai',
        text: sc.finalQuestion,
        intentTag: 'Production Resilience',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
    } else {
      // Turn 3 completed -> Conclude session strictly
      this.activeSession.isCompleted = true;
      this.activeSession.isActive = false;

      aiTurn = {
        turnNumber: 3,
        sender: 'ai',
        text: `Thank you, ${this.activeSession.candidateName}. You have completed all 3 technical evaluation turns. We have gathered sufficient signals to generate your comprehensive feedback report.`,
        intentTag: 'Session Complete',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isConcluded: true
      };
    }

    this.activeSession.transcript.push(aiTurn);

    return {
      turnNumber: Math.min(this.activeSession.currentTurnIndex, 3),
      userTurn: userTurn,
      aiTurn: aiTurn,
      isConcluded: this.activeSession.isCompleted
    };
  }

  async requestClarification() {
    if (!this.activeSession || !this.activeSession.isActive || this.activeSession.isCompleted) {
      throw new Error('Cannot request clarification: interview session is inactive or completed.');
    }

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const turnNumber = Math.min(this.activeSession.currentTurnIndex, 3);

    const userTurn = {
      turnNumber: turnNumber,
      sender: 'user',
      text: 'Could you please clarify what specific architecture aspect or constraints I should focus on for this scenario?',
      timestamp: timestamp,
      isClarificationRequest: true
    };
    this.activeSession.transcript.push(userTurn);

    await this._delay(500);

    const sc = this.activeSession.scenarios;
    const aiTurn = {
      turnNumber: turnNumber,
      sender: 'ai',
      text: sc.clarificationPrompt,
      intentTag: 'Clarification',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    this.activeSession.transcript.push(aiTurn);

    return {
      userTurn: userTurn,
      aiTurn: aiTurn
    };
  }

  async endInterview() {
    if (!this.activeSession) {
      throw new Error('No session active to conclude.');
    }

    await this._delay(300);
    this.activeSession.isActive = false;
    this.activeSession.isCompleted = true;

    return {
      candidateName: this.activeSession.candidateName,
      jobRole: this.activeSession.jobRole,
      completedTurns: Math.min(this.activeSession.currentTurnIndex, 3),
      transcript: this.activeSession.transcript
    };
  }

  getSessionInfo() {
    if (!this.activeSession) return null;
    return {
      candidateId: this.activeSession.candidateId,
      candidateName: this.activeSession.candidateName,
      jobRole: this.activeSession.jobRole,
      currentTurnIndex: Math.min(this.activeSession.currentTurnIndex, 3),
      maxTurns: 3,
      isActive: this.activeSession.isActive,
      isCompleted: this.activeSession.isCompleted || false
    };
  }

  getCurrentTranscript() {
    return this.activeSession ? this.activeSession.transcript : [];
  }

  _getScenarioForCandidate(candidate) {
    const name = candidate.member ? candidate.member.name : '';
    const id = candidate.member ? candidate.member.id : '';

    if (id === 'cand-01' || name.includes('Alex')) {
      return {
        initialQuestion: `Welcome Alex. Based on your work with Retrieval-Augmented Generation (RAG), let's discuss chunking strategies for technical documentation. When designing a production RAG pipeline, how do you evaluate semantic chunking versus fixed-size sliding windows, and what impact does this choice have on downstream context retrieval accuracy?`,
        followUpQuestion: `That's a solid explanation of parent-child retriever chunking. Following up on vector retrieval: how do you manage latency budgets when adding a Cross-Encoder re-ranker stage before injecting retrieved context into the LLM prompt?`,
        finalQuestion: `Great latency tuning strategy with Reciprocal Rank Fusion. To wrap up our technical session: how do you detect and handle hallucination risks when vector cosine similarity scores drop below your confidence threshold (e.g. similarity < 0.65)?`,
        clarificationPrompt: `To clarify: focus on how you balance precision vs latency when indexing dense documents, specifically whether you index small child chunks for vector matching while preserving parent sections for full prompt context.`
      };
    } else if (id === 'cand-02' || name.includes('Maya')) {
      return {
        initialQuestion: `Welcome Maya. Looking at your experience with Model Context Protocol (MCP) and Dockerized deployment: when building an enterprise AI assistant that interfaces with internal DBs via MCP servers, how do you handle connection pooling and state management across stateless LLM inference requests?`,
        followUpQuestion: `Excellent microservice separation using Redis and pgbouncer sidecars. How do you prevent context window saturation when an MCP tool returns large payload objects (such as 5,000 JSON database rows)?`,
        finalQuestion: `Solid payload truncation strategy. Finally, how do you manage auto-scaling for Dockerized vLLM instances during sudden traffic spikes while preserving active session state?`,
        clarificationPrompt: `To clarify: focus on how MCP decouples tool execution from prompt construction, and how state is preserved between the gateway and underlying persistent databases.`
      };
    } else if (id === 'cand-03' || name.includes('Marcus')) {
      return {
        initialQuestion: `Welcome Marcus. Let's discuss your work with Prompt Engineering and Vector Embeddings. When embedding domain-specific technical queries into a vector database, how do you select and evaluate distance metrics (e.g. Cosine Similarity vs. Euclidean Distance), and how do you handle out-of-vocabulary technical terms?`,
        followUpQuestion: `Good insight on embedding space normalization. When your RAG system encounters failed retrieval attempts, what diagnostic steps do you take to identify whether the issue is chunking fragmentation or embedding misalignment?`,
        finalQuestion: `Solid diagnostic approach. To complete our interview: how do you benchmark quantization performance (e.g., INT8 vs. FP16) when deploying models on resource-constrained infrastructure?`,
        clarificationPrompt: `To clarify: consider how vector space geometry changes under normalization and how cosine similarity behaves with unit-length normalized vectors.`
      };
    }

    return {
      initialQuestion: `Welcome. Let's begin by discussing the technical systems you've built during your cohort journey. Can you describe the core architectural trade-offs you made in your primary enterprise AI project?`,
      followUpQuestion: `Thank you for that overview. Following up: how did you validate system reliability and handle edge cases when model output confidence was low?`,
      finalQuestion: `Great technical explanation. Lastly: how would you optimize this system if query volume increased by 10x?`,
      clarificationPrompt: `To clarify: please focus on performance bottlenecks, latency budgets, and engineering trade-offs.`
    };
  }
}

export const interviewService = new InterviewService();
