/**
 * INTERVEXA - Main UI Router & Controller
 * 
 * Manages screen navigation, Candidate Setup UI, and the dynamic
 * Interview Experience (F2) via the `interviewService` boundary.
 */

import { interviewService } from './services/interviewService.js';

class IntervexaApp {
  constructor() {
    this.activeScreen = 'landing';
    this.selectedCandidateId = null;
    this.isSubmitting = false;
    this.elements = {};
  }

  /**
   * Initialize DOM references and attach event listeners
   */
  init() {
    this._cacheElements();
    this._attachEventListeners();
    this.navigate('landing');
  }

  _cacheElements() {
    this.elements.screens = {
      landing: document.getElementById('screen-landing'),
      candidateSelect: document.getElementById('screen-candidate-select'),
      interviewChat: document.getElementById('screen-chat'),
      interviewFeedback: document.getElementById('screen-feedback')
    };

    this.elements.brandHomeBtn = document.getElementById('brand-home-btn');
    this.elements.startSelectionBtn = document.getElementById('start-selection-btn');
    this.elements.backToLandingBtn = document.getElementById('back-to-landing-btn');

    // Candidate Selection elements (F1B)
    this.elements.candidateListContainer = document.getElementById('candidate-list-container');
    this.elements.journeyPanel = document.getElementById('journey-panel');
    this.elements.startInterviewBtn = document.getElementById('start-interview-btn');
    this.elements.selectionErrorBanner = document.getElementById('selection-error-banner');
    this.elements.selectionLoadingState = document.getElementById('selection-loading-state');
    this.elements.selectionEmptyState = document.getElementById('selection-empty-state');
    this.elements.selectionMainLayout = document.getElementById('selection-main-layout');

    // Interview Workspace elements (F2)
    this.elements.chatCandidateAvatar = document.getElementById('chat-candidate-avatar');
    this.elements.chatCandidateName = document.getElementById('chat-candidate-name');
    this.elements.chatCandidateRole = document.getElementById('chat-candidate-role');
    this.elements.chatInterviewerStatus = document.getElementById('chat-interviewer-status');
    this.elements.chatInterviewerStatusText = document.getElementById('chat-interviewer-status-text');
    this.elements.chatTurnCounter = document.getElementById('chat-turn-counter');
    this.elements.chatFeed = document.getElementById('chat-feed');
    this.elements.chatTextarea = document.getElementById('chat-textarea');
    this.elements.submitAnswerBtn = document.getElementById('submit-answer-btn');
    this.elements.requestClarificationBtn = document.getElementById('request-clarification-btn');
    this.elements.endInterviewBtn = document.getElementById('end-interview-btn');
    
    // F2 QA Completion Banner elements
    this.elements.sessionCompletedBanner = document.getElementById('session-completed-banner');
    this.elements.viewFeedbackBtn = document.getElementById('view-feedback-btn');
    this.elements.inputActionsBar = document.getElementById('input-actions-bar');
    this.elements.inputFormWrapper = document.getElementById('input-form-wrapper');

    // Feedback Screen elements
    this.elements.feedbackCandName = document.getElementById('feedback-cand-name');
    this.elements.feedbackCandTrack = document.getElementById('feedback-cand-track');
    this.elements.evaluateAnotherBtn = document.getElementById('evaluate-another-btn');
    this.elements.returnHomeBtn = document.getElementById('return-home-btn');
  }

  _attachEventListeners() {
    // Brand Header Home Click
    if (this.elements.brandHomeBtn) {
      this.elements.brandHomeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.navigate('landing');
      });
    }

    // Screen 1 Landing CTA -> Screen 2 Candidate Selection
    const startBtn = this.elements.startSelectionBtn || document.getElementById('start-selection-btn');
    if (startBtn) {
      startBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.navigate('candidate-select');
      });
    }

    // Screen 2 Begin Interview Button -> Initialize Interview Workspace (F2)
    const beginBtn = this.elements.startInterviewBtn || document.getElementById('start-interview-btn');
    if (beginBtn) {
      beginBtn.addEventListener('click', async () => {
        if (!this.selectedCandidateId) return;
        await this._handleStartInterview();
      });
    }

    // Screen 3: Submit Answer Action
    if (this.elements.submitAnswerBtn) {
      this.elements.submitAnswerBtn.addEventListener('click', async () => {
        await this._handleSubmitAnswer();
      });
    }

    // Screen 3: Request Clarification Action
    if (this.elements.requestClarificationBtn) {
      this.elements.requestClarificationBtn.addEventListener('click', async () => {
        await this._handleRequestClarification();
      });
    }

    // Screen 3: Textarea Enter Key handling (Enter = Submit, Shift+Enter = Newline)
    if (this.elements.chatTextarea) {
      this.elements.chatTextarea.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          await this._handleSubmitAnswer();
        }
      });
    }

    // Screen 3: End Interview CTA
    if (this.elements.endInterviewBtn) {
      this.elements.endInterviewBtn.addEventListener('click', async () => {
        await this._handleEndInterview();
      });
    }

    // Screen 3: View Feedback CTA (Session Completed Banner)
    if (this.elements.viewFeedbackBtn) {
      this.elements.viewFeedbackBtn.addEventListener('click', async () => {
        await this._handleEndInterview();
      });
    }

    // Screen 4 Action Buttons
    if (this.elements.evaluateAnotherBtn) {
      this.elements.evaluateAnotherBtn.addEventListener('click', () => {
        this.navigate('candidate-select');
      });
    }
    if (this.elements.returnHomeBtn) {
      this.elements.returnHomeBtn.addEventListener('click', () => {
        this.navigate('landing');
      });
    }

    // Global Event Delegation fallback for navigation buttons
    document.addEventListener('click', (e) => {
      const targetStart = e.target.closest('#start-selection-btn');
      if (targetStart) {
        e.preventDefault();
        this.navigate('candidate-select');
      }

      const targetBack = e.target.closest('#back-to-landing-btn');
      if (targetBack) {
        e.preventDefault();
        this.navigate('landing');
      }

      const targetViewFb = e.target.closest('#view-feedback-btn');
      if (targetViewFb) {
        e.preventDefault();
        this._handleEndInterview();
      }
    });
  }

  /**
   * Router: Switch active screen view
   * @param {string} screenName 
   */
  navigate(screenName) {
    this.activeScreen = screenName;

    const allScreens = document.querySelectorAll('.screen-view');
    allScreens.forEach(el => el.classList.remove('active'));

    const screenIdMap = {
      'landing': 'screen-landing',
      'candidate-select': 'screen-candidate-select',
      'interview-chat': 'screen-chat',
      'interview-feedback': 'screen-feedback'
    };

    const targetId = screenIdMap[screenName] || 'screen-' + screenName;
    const targetEl = document.getElementById(targetId);

    if (targetEl) {
      targetEl.classList.add('active');
    }

    window.scrollTo(0, 0);

    if (screenName === 'candidate-select') {
      this._loadCandidatesView();
    } else if (screenName === 'interview-chat') {
      const info = interviewService.getSessionInfo();
      if (info && !info.isCompleted && this.elements.chatTextarea) {
        this.elements.chatTextarea.focus();
      }
    }
  }

  /* ------------------------------------------------------------------------
     Screen 2: Candidate Setup Controller (F1B)
     ------------------------------------------------------------------------ */
  async _loadCandidatesView() {
    const listContainer = this.elements.candidateListContainer || document.getElementById('candidate-list-container');
    const loadingState = this.elements.selectionLoadingState || document.getElementById('selection-loading-state');
    const emptyState = this.elements.selectionEmptyState || document.getElementById('selection-empty-state');
    const errorBanner = this.elements.selectionErrorBanner || document.getElementById('selection-error-banner');
    const mainLayout = this.elements.selectionMainLayout || document.getElementById('selection-main-layout');
    const startBtn = this.elements.startInterviewBtn || document.getElementById('start-interview-btn');

    if (errorBanner) errorBanner.style.display = 'none';
    if (emptyState) emptyState.style.display = 'none';
    if (startBtn) startBtn.disabled = true;
    this.selectedCandidateId = null;

    if (loadingState) loadingState.style.display = 'flex';
    if (mainLayout) mainLayout.style.display = 'none';

    try {
      const candidates = await interviewService.getCandidates();

      if (loadingState) loadingState.style.display = 'none';

      if (!candidates || candidates.length === 0) {
        if (emptyState) emptyState.style.display = 'flex';
        return;
      }

      if (mainLayout) mainLayout.style.display = 'grid';
      if (!listContainer) return;

      listContainer.innerHTML = '';

      candidates.forEach((cand) => {
        const member = cand.member || {};
        const card = document.createElement('div');
        card.className = 'candidate-card';
        card.setAttribute('data-id', member.id);
        card.tabIndex = 0;
        card.role = 'radio';
        card.ariaChecked = 'false';

        card.innerHTML = `
          <div class="card-meta-top">
            <h3 class="candidate-name">${member.name || 'Unnamed Candidate'}</h3>
            <span class="badge ${member.status === 'Active' ? 'badge-success' : 'badge-neutral'}">${member.status || 'Active'}</span>
          </div>
          <div class="candidate-role">${member.jobRole || 'Engineer'}</div>
          <div class="candidate-meta-details">
            <span class="meta-item">${member.yearsExperience || 0} Yrs Exp</span>
            <span class="meta-divider">•</span>
            <span class="meta-item">${member.education || 'N/A'}</span>
          </div>
        `;

        card.addEventListener('click', () => this._selectCandidate(member.id));
        card.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this._selectCandidate(member.id);
          }
        });

        listContainer.appendChild(card);
      });

    } catch (err) {
      if (loadingState) loadingState.style.display = 'none';
      if (errorBanner) {
        errorBanner.style.display = 'block';
        errorBanner.textContent = `Unable to load candidate records: ${err.message}`;
      }
    }
  }

  async _selectCandidate(candidateId) {
    this.selectedCandidateId = candidateId;

    const listContainer = this.elements.candidateListContainer || document.getElementById('candidate-list-container');
    const journeyPanel = this.elements.journeyPanel || document.getElementById('journey-panel');
    const startBtn = this.elements.startInterviewBtn || document.getElementById('start-interview-btn');

    if (listContainer) {
      const cards = listContainer.querySelectorAll('.candidate-card');
      cards.forEach(c => {
        if (c.getAttribute('data-id') === candidateId) {
          c.classList.add('selected');
          c.ariaChecked = 'true';
        } else {
          c.classList.remove('selected');
          c.ariaChecked = 'false';
        }
      });
    }

    if (startBtn) {
      startBtn.disabled = false;
    }

    try {
      const candidate = await interviewService.getCandidateById(candidateId);
      interviewService.setSelectedCandidate(candidate);

      const { member, missions, signals } = candidate;

      const missionsMarkup = (missions || []).map(m => {
        let statusBadge = '';
        if (m.passed) {
          statusBadge = `<span class="badge badge-success">✓ Passed (Attempt ${m.attempts})</span>`;
        } else if (m.attempts > 0) {
          statusBadge = `<span class="badge badge-danger">✗ Failed (${m.attempts} attempts)</span>`;
        } else {
          statusBadge = `<span class="badge badge-warning">- Skipped</span>`;
        }

        return `
          <div class="mission-item">
            <div class="mission-info">
              <span class="mission-day">Day ${m.day}</span>
              <span class="mission-title">${m.title}</span>
            </div>
            ${statusBadge}
          </div>
        `;
      }).join('');

      if (journeyPanel) {
        journeyPanel.innerHTML = `
          <div class="journey-header">
            <div class="candidate-summary">
              <h3 class="journey-candidate-name">${member.name}</h3>
              <p class="journey-candidate-role">${member.jobRole} • ${member.yearsExperience} Yrs Exp • ${member.education}</p>
            </div>
          </div>

          <div class="signals-grid">
            <div class="signal-card">
              <span class="signal-value">${signals.missionsCompleted}</span>
              <span class="signal-label">Missions Completed</span>
            </div>
            <div class="signal-card">
              <span class="signal-value">${signals.missionsFirstTry}</span>
              <span class="signal-label">First-Try Missions</span>
            </div>
            <div class="signal-card">
              <span class="signal-value">${signals.commitDays}</span>
              <span class="signal-label">Commit Days</span>
            </div>
          </div>

          <div class="missions-section">
            <h4 class="missions-heading">Relevant Mission Topics & Status</h4>
            <div class="missions-list">
              ${missionsMarkup}
            </div>
          </div>
        `;
      }
    } catch (err) {
      if (journeyPanel) {
        journeyPanel.innerHTML = `<div class="alert-banner alert-error">Error displaying candidate details: ${err.message}</div>`;
      }
    }
  }

  /* ------------------------------------------------------------------------
     Screen 3: Interview Workspace Controller (F2 QA FIX)
     ------------------------------------------------------------------------ */

  async _handleStartInterview() {
    try {
      const { sessionInfo, initialTurn } = await interviewService.startInterview(this.selectedCandidateId);

      // Populate Session Header
      if (this.elements.chatCandidateName) this.elements.chatCandidateName.textContent = sessionInfo.candidateName;
      if (this.elements.chatCandidateRole) this.elements.chatCandidateRole.textContent = sessionInfo.jobRole;
      if (this.elements.chatCandidateAvatar) this.elements.chatCandidateAvatar.textContent = sessionInfo.candidateName.charAt(0);
      if (this.elements.chatTurnCounter) this.elements.chatTurnCounter.textContent = `Turn ${sessionInfo.currentTurnIndex} of ${sessionInfo.maxTurns}`;
      this._updateInterviewerStatus('Listening', 'status-listening');

      // Reset Completion Banner & Form controls
      if (this.elements.sessionCompletedBanner) this.elements.sessionCompletedBanner.style.display = 'none';
      if (this.elements.inputActionsBar) this.elements.inputActionsBar.style.display = 'flex';
      if (this.elements.inputFormWrapper) this.elements.inputFormWrapper.style.display = 'flex';

      this._setFormDisabled(false);
      if (this.elements.chatTextarea) {
        this.elements.chatTextarea.placeholder = 'Type your technical response here... Describe architectural decisions, trade-offs, and reasoning.';
        this.elements.chatTextarea.value = '';
      }

      // Clear feed and append initial question
      if (this.elements.chatFeed) {
        this.elements.chatFeed.innerHTML = '';
        this._renderTurnToFeed(initialTurn);
      }

      this.navigate('interview-chat');
    } catch (err) {
      alert(`Unable to initialize interview session: ${err.message}`);
    }
  }

  async _handleSubmitAnswer() {
    const session = interviewService.getSessionInfo();
    if (!session || !session.isActive || session.isCompleted || this.isSubmitting) {
      return;
    }

    const textarea = this.elements.chatTextarea || document.getElementById('chat-textarea');
    const answerText = textarea ? textarea.value.trim() : '';

    if (!answerText) return;

    this.isSubmitting = true;
    this._setFormDisabled(true);

    if (textarea) textarea.value = '';

    try {
      // 1. Instantly append candidate answer to feed
      const currentTurnNumber = Math.min(session.currentTurnIndex, 3);
      const userTurn = {
        turnNumber: currentTurnNumber,
        sender: 'user',
        text: answerText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      this._renderTurnToFeed(userTurn);

      // 2. Display AI Thinking loading state
      this._updateInterviewerStatus('Thinking...', 'status-thinking');
      this._showThinkingIndicator();

      // 3. Service API processing
      const result = await interviewService.submitAnswer(answerText);

      // 4. Hide thinking indicator and append AI response
      this._hideThinkingIndicator();
      this._renderTurnToFeed(result.aiTurn);

      // 5. Check if session completed
      if (result.isConcluded) {
        this._transitionToCompletedState();
      } else {
        this._updateInterviewerStatus('Listening', 'status-listening');
        if (this.elements.chatTurnCounter) {
          this.elements.chatTurnCounter.textContent = `Turn ${result.turnNumber} of 3`;
        }
        this._setFormDisabled(false);
        if (textarea) textarea.focus();
      }

    } catch (err) {
      this._hideThinkingIndicator();
      this._updateInterviewerStatus('Listening', 'status-listening');
      this._setFormDisabled(false);
      console.warn(`Submission prevented: ${err.message}`);
    } finally {
      this.isSubmitting = false;
    }
  }

  async _handleRequestClarification() {
    const session = interviewService.getSessionInfo();
    if (!session || !session.isActive || session.isCompleted || this.isSubmitting) {
      return;
    }

    this.isSubmitting = true;
    this._setFormDisabled(true);

    try {
      this._updateInterviewerStatus('Thinking...', 'status-thinking');
      this._showThinkingIndicator();

      const result = await interviewService.requestClarification();

      this._hideThinkingIndicator();
      this._updateInterviewerStatus('Listening', 'status-listening');

      this._renderTurnToFeed(result.userTurn);
      this._renderTurnToFeed(result.aiTurn);

    } catch (err) {
      this._hideThinkingIndicator();
      this._updateInterviewerStatus('Listening', 'status-listening');
      console.warn(`Clarification prevented: ${err.message}`);
    } finally {
      this.isSubmitting = false;
      this._setFormDisabled(false);
    }
  }

  _transitionToCompletedState() {
  this._updateInterviewerStatus('Completed', 'status-completed');

  if (this.elements.chatTurnCounter) {
    this.elements.chatTurnCounter.textContent = 'Turn 3 of 3 (Completed)';
  }

  // Permanently disable interview inputs
  this._setFormDisabled(true);

  if (this.elements.chatTextarea) {
    this.elements.chatTextarea.value = '';
    this.elements.chatTextarea.placeholder =
      'Interview session completed. Preparing your feedback report...';
  }

  // Show completion banner
  const banner =
    this.elements.sessionCompletedBanner ||
    document.getElementById('session-completed-banner');

  if (banner) {
    banner.style.display = 'flex';
  }

  // Give the completion state a moment to be visible,
  // then move to the feedback report.
  setTimeout(() => {
    if (interviewService.getSessionInfo()?.isCompleted) {
      this._handleEndInterview();
    }
  }, 1200);
}

  async _handleEndInterview() {
    try {
      const summary = await interviewService.endInterview();
      
      // Populate feedback screen summary
      if (this.elements.feedbackCandName) {
        this.elements.feedbackCandName.textContent = summary.candidateName;
      }
      if (this.elements.feedbackCandTrack) {
        this.elements.feedbackCandTrack.textContent = `${summary.jobRole} • All ${summary.completedTurns} Turns Evaluated`;
      }

      this.navigate('interview-feedback');
    } catch (err) {
      alert(`Error ending interview: ${err.message}`);
    }
  }

  _renderTurnToFeed(turn) {
    if (!this.elements.chatFeed) return;

    const isAi = turn.sender === 'ai';
    const turnEl = document.createElement('div');
    turnEl.className = `chat-message-card ${isAi ? 'message-ai' : 'message-user'}`;

    const formattedText = this._formatMessageText(turn.text);

    turnEl.innerHTML = `
      <div class="message-meta-header">
        <div class="message-sender-info">
          <div class="message-avatar ${isAi ? 'avatar-ai' : 'avatar-user'}">
            ${isAi ? 'IX' : 'YOU'}
          </div>
          <span class="message-sender-name">${isAi ? 'AI Interviewer' : 'Candidate Response'}</span>
          ${isAi && turn.intentTag ? `<span class="badge ${turn.intentTag === 'Session Complete' ? 'badge-success' : 'badge-info'}">${turn.intentTag}</span>` : ''}
        </div>
        <span class="message-timestamp">${turn.timestamp || ''}</span>
      </div>
      <div class="message-body">${formattedText}</div>
    `;

    this.elements.chatFeed.appendChild(turnEl);
    this.elements.chatFeed.scrollTop = this.elements.chatFeed.scrollHeight;
  }

  _formatMessageText(text) {
    if (!text) return '';
    
    // Convert code blocks ```code``` to <pre><code> for monospace rendering
    let html = text.replace(/```([\s\S]*?)```/g, (match, codeContent) => {
      return `<pre class="code-block"><code>${this._escapeHtml(codeContent.trim())}</code></pre>`;
    });

    // Convert inline `code` to <code>
    html = html.replace(/`([^`]+)`/g, (match, codeInline) => {
      return `<code class="inline-code">${this._escapeHtml(codeInline)}</code>`;
    });

    if (!html.includes('<pre')) {
      html = html.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
    }

    return html;
  }

  _escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  _showThinkingIndicator() {
    if (!this.elements.chatFeed) return;

    const indicator = document.createElement('div');
    indicator.id = 'ai-thinking-indicator';
    indicator.className = 'thinking-state-card';
    indicator.innerHTML = `
      <div class="thinking-dots">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
      <span class="thinking-text">AI Interviewer is analyzing response reasoning & trade-offs...</span>
    `;

    this.elements.chatFeed.appendChild(indicator);
    this.elements.chatFeed.scrollTop = this.elements.chatFeed.scrollHeight;
  }

  _hideThinkingIndicator() {
    const indicator = document.getElementById('ai-thinking-indicator');
    if (indicator) indicator.remove();
  }

  _updateInterviewerStatus(text, statusClass) {
    const txt = this.elements.chatInterviewerStatusText || document.getElementById('chat-interviewer-status-text');
    const badge = this.elements.chatInterviewerStatus || document.getElementById('chat-interviewer-status');

    if (txt) txt.textContent = text;
    if (badge) {
      badge.className = `interviewer-status-badge ${statusClass}`;
    }
  }

  _setFormDisabled(disabled) {
    const textarea = this.elements.chatTextarea || document.getElementById('chat-textarea');
    const submitBtn = this.elements.submitAnswerBtn || document.getElementById('submit-answer-btn');
    const clarifyBtn = this.elements.requestClarificationBtn || document.getElementById('request-clarification-btn');

    if (textarea) textarea.disabled = disabled;
    if (submitBtn) submitBtn.disabled = disabled;
    if (clarifyBtn) clarifyBtn.disabled = disabled;
  }
}

// Bootstrap application reliably
const startApp = () => {
  const app = new IntervexaApp();
  app.init();
  window.intervexaApp = app;
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startApp);
} else {
  startApp();
}
