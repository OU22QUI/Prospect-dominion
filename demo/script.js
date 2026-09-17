document.addEventListener('DOMContentLoaded', () => {
  const demoSection = document.getElementById('demo');
  const dialog = document.getElementById('demoDialog');
  const requestDemo = document.getElementById('requestDemo');
  const viewWorkflow = document.getElementById('viewWorkflow');
  const dialogWorkflow = document.getElementById('dialogWorkflow');
  const closeDialog = document.getElementById('closeDialog');
  const accountListEl = document.getElementById('accountList');
  const detailCompanyEl = document.getElementById('detailCompany');
  const detailScoreEl = document.getElementById('detailScore');
  const detailIntentEl = document.getElementById('detailIntent');
  const detailStageEl = document.getElementById('detailStage');
  const detailSignalEl = document.getElementById('detailSignal');
  const detailPathEl = document.getElementById('detailPath');
  const relationshipMapEl = document.getElementById('relationshipMap');
  const activityFeedEl = document.getElementById('activityFeed');
  const timelineStatusEl = document.getElementById('timelineStatus');
  const runActionBtn = document.getElementById('runAction');
  const refreshQueueBtn = document.getElementById('refreshQueue');
  const resetDemoBtn = document.getElementById('resetDemo');
  const shareDemoBtn = document.getElementById('shareDemo');
  const accountSearchEl = document.getElementById('accountSearch');
  const stageFilterEl = document.getElementById('stageFilter');
  const intentFilterEl = document.getElementById('intentFilter');
  const compareLabelEl = document.getElementById('compareLabel');
  const clearCompareBtn = document.getElementById('clearCompare');
  const scoreExplanationEl = document.getElementById('scoreExplanation');
  const guideStepEl = document.getElementById('guideStep');
  const guideTitleEl = document.getElementById('guideTitle');
  const guideCopyEl = document.getElementById('guideCopy');
  const guideNextBtn = document.getElementById('guideNext');
  const finalBookDemoBtn = document.getElementById('finalBookDemo');
  const scenarioChips = document.querySelectorAll('.scenario-chip');
  const actionFeedbackEl = document.getElementById('actionFeedback');
  const walkthroughForm = document.getElementById('walkthroughForm');
  const formStatusEl = document.getElementById('formStatus');
  const summaryEls = {
    trustScore: document.getElementById('trustScore'),
    qualifiedAccounts: document.getElementById('qualifiedAccounts'),
    workflowRuns: document.getElementById('workflowRuns'),
    operatingLeverage: document.getElementById('operatingLeverage'),
    qualificationSpeed: document.getElementById('qualificationSpeed'),
    warmPaths: document.getElementById('warmPaths'),
    heroTrustScore: document.getElementById('heroTrustScore'),
    heroQualifiedAccounts: document.getElementById('heroQualifiedAccounts'),
    heroWarmPaths: document.getElementById('heroWarmPaths')
  };

  const fallbackAccounts = [
    {
      company: 'Nexa Labs',
      intent: 'Expansion',
      stage: 'Proposal',
      score: 94,
      signal: 'AI platform expansion',
      path: 'VP Revenue + CTO',
      relationships: ['Sarah Lin', 'David Wu', 'Maya Patel'],
      activities: [
        ['09:18', 'Intent signal detected from expansion brief'],
        ['09:33', 'AI ranked account as high-priority opportunity'],
        ['09:51', 'Warm intro path identified to VP Revenue'],
      ],
      health: 'Healthy'
    },
    {
      company: 'Harbor Works',
      intent: 'Renewal',
      stage: 'Qualification',
      score: 89,
      signal: 'Renewal risk + budget review',
      path: 'Head of Ops + CFO',
      relationships: ['Lena Ortiz', 'Omar Bell', 'Ari Cole'],
      activities: [
        ['08:42', 'Renewal risk model triggered on procurement activity'],
        ['09:12', 'Related org update surfaced in expansion review'],
        ['09:44', 'Follow-up sequence queued for finance stakeholders'],
      ],
      health: 'Review'
    },
    {
      company: 'Northstar One',
      intent: 'New logo',
      stage: 'Discovery',
      score: 86,
      signal: 'Multi-region rollout requirement',
      path: 'VP Sales + RevOps',
      relationships: ['Jules Price', 'Nina Shah', 'Leo Grant'],
      activities: [
        ['08:18', 'Recent buying signals mapped to rollout initiative'],
        ['08:55', 'Account prioritized for outbound orchestration'],
        ['09:28', 'Partner contact added to outreach board'],
      ],
      health: 'Healthy'
    },
    {
      company: 'Lattice Grid',
      intent: 'Cross-sell',
      stage: 'Engaged',
      score: 91,
      signal: 'Cross-sell expansion in AI ops',
      path: 'VP of Growth + Product',
      relationships: ['Chris Wade', 'Priya Menon', 'Maddie Ross'],
      activities: [
        ['07:52', 'Cross-sell opportunity validated by product team'],
        ['08:37', 'Sequence generated for multi-threaded engagement'],
        ['09:10', 'Warm intro list updated by relationship graph'],
      ],
      health: 'Healthy'
    }
  ];

  const fallbackSummary = {
    brand: 'Prospect Dominion',
    signalCoverage: 31,
    qualificationSpeed: 2.4,
    activePaths: 8,
    healthScore: 96.4,
    qualifiedAccounts: 148,
    workflowRuns: 237,
    operatingLeverage: '3.2x',
  };

  let accounts = [...fallbackAccounts];
  let summary = { ...fallbackSummary };
  let selectedIndex = 0;
  let compareIndex = null;
  let guideStep = 0;
  const storageKey = 'prospect-dominion-demo-state-v1';
  const baseConfig = window.PD_DEMO_CONFIG || {};

  const track = (eventName, details = {}) => {
    const event = { eventName, details, timestamp: new Date().toISOString() };
    try {
      const events = JSON.parse(sessionStorage.getItem('pd-demo-events') || '[]');
      events.push(event);
      sessionStorage.setItem('pd-demo-events', JSON.stringify(events.slice(-50)));
    } catch (error) {
      // Analytics must never block the demo.
    }
    if (baseConfig.analyticsEndpoint) {
      fetch(baseConfig.analyticsEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event),
        keepalive: true,
      }).catch(() => {});
    }
  };

  const saveState = () => {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ accounts, summary }));
    } catch (error) {
      // Persistence is optional in restricted browser contexts.
    }
  };

  const resetState = () => {
    accounts = fallbackAccounts.map((account) => ({ ...account, relationships: [...account.relationships], activities: account.activities.map((activity) => [...activity]) }));
    summary = { ...fallbackSummary };
    selectedIndex = 0;
    compareIndex = null;
    guideStep = 0;
    localStorage.removeItem(storageKey);
    track('demo_reset');
    hydrateSummary();
    populateFilters();
    loadSharedScenario();
    renderAccountDetail();
    updateGuide();
  };

  const loadSharedScenario = () => {
    const scenario = Number(new URLSearchParams(window.location.search).get('scenario'));
    if (Number.isInteger(scenario) && scenario >= 0 && scenario < accounts.length) {
      selectedIndex = scenario;
      track('shared_scenario_open', { scenario });
    }
  };

  const restoreState = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
      if (saved?.accounts?.length) {
        accounts = saved.accounts;
        summary = { ...fallbackSummary, ...(saved.summary || {}) };
      }
    } catch (error) {
      localStorage.removeItem(storageKey);
    }
  };

  const filteredAccounts = () => {
    const query = (accountSearchEl?.value || '').trim().toLowerCase();
    const stage = stageFilterEl?.value || 'all';
    const intent = intentFilterEl?.value || 'all';
    return accounts
      .map((account, index) => ({ account, index }))
      .filter(({ account }) => {
        const haystack = `${account.company} ${account.signal} ${account.intent}`.toLowerCase();
        return (!query || haystack.includes(query)) && (stage === 'all' || account.stage === stage) && (intent === 'all' || account.intent === intent);
      });
  };

  const populateFilters = () => {
    if (!stageFilterEl || !intentFilterEl) return;
    const stages = [...new Set(accounts.map((account) => account.stage))].sort();
    const intents = [...new Set(accounts.map((account) => account.intent))].sort();
    stageFilterEl.innerHTML = '<option value="all">All stages</option>' + stages.map((value) => `<option value="${value}">${value}</option>`).join('');
    intentFilterEl.innerHTML = '<option value="all">All intents</option>' + intents.map((value) => `<option value="${value}">${value}</option>`).join('');
  };

  const updateGuide = () => {
    const steps = [
      ['01', 'Choose an account', 'Start with the highest-priority account in the queue.'],
      ['02', 'Understand the signal', 'Review the buying context and explainable score.'],
      ['03', 'Take a governed action', 'Run a signal scan, queue an intro, or approve outreach.'],
    ];
    const [number, title, copy] = steps[guideStep];
    guideStepEl.textContent = number;
    guideTitleEl.textContent = title;
    guideCopyEl.textContent = copy;
    guideNextBtn.textContent = guideStep === steps.length - 1 ? 'Restart guide' : 'Next step';
  };

  const hydrateSummary = () => {
    if (!summaryEls.trustScore) return;

    const trustScore = Number(summary.healthScore ?? summary.trustScore ?? 96.4).toFixed(1);
    const qualifiedAccounts = Number(summary.qualifiedAccounts ?? 148);
    const workflowRuns = Number(summary.workflowRuns ?? 237);
    const operatingLeverage = summary.operatingLeverage ?? '3.2x';
    const qualificationSpeed = summary.qualificationSpeed ?? 2.4;
    const warmPaths = Number(summary.activePaths ?? 8);

    summaryEls.trustScore.textContent = trustScore;
    summaryEls.qualifiedAccounts.textContent = qualifiedAccounts;
    summaryEls.workflowRuns.textContent = workflowRuns;
    summaryEls.operatingLeverage.textContent = operatingLeverage;
    summaryEls.qualificationSpeed.textContent = `${qualificationSpeed.toFixed(1)}x`;
    summaryEls.warmPaths.textContent = `${warmPaths} active`;
    summaryEls.heroTrustScore.textContent = trustScore;
    summaryEls.heroQualifiedAccounts.textContent = qualifiedAccounts;
    summaryEls.heroWarmPaths.textContent = `${warmPaths} ready`;
  };

  const applyDemoState = (payload) => {
    const nextSummary = payload?.summary ?? {};
    const nextAccounts = Array.isArray(payload?.accounts) && payload.accounts.length ? payload.accounts : fallbackAccounts;

    summary = { ...fallbackSummary, ...nextSummary };
    accounts = nextAccounts.map((account) => ({
      ...account,
      activities: Array.isArray(account.activities) ? account.activities : [[ '09:00', `${account.company || 'Account'} is ready for review` ]],
      relationships: Array.isArray(account.relationships) ? account.relationships : [],
      health: account.health || 'Healthy',
    }));

    if (!accounts.length) {
      accounts = [...fallbackAccounts];
    }

    restoreState();
    loadSharedScenario();
    hydrateSummary();
    populateFilters();
    renderAccountDetail();
    updateGuide();
  };

  async function loadDemoState() {
    const candidates = ['./demo-data.json', './demo/demo-data.json'];

    for (const path of candidates) {
      try {
        const response = await fetch(path, { cache: 'no-store' });
        if (!response.ok) continue;

        const payload = await response.json();
        if (payload && (Array.isArray(payload.accounts) || payload.summary)) {
          applyDemoState(payload);
          return;
        }
      } catch (error) {
        // Fall back to the curated static demo state.
      }
    }

    hydrateSummary();
    populateFilters();
    renderAccountDetail();
    updateGuide();
  }

  const scrollToWorkflow = () => {
    if (demoSection) {
      demoSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const renderAccounts = () => {
    if (!accountListEl) return;

    const visibleAccounts = filteredAccounts();
    accountListEl.innerHTML = visibleAccounts
      .map(({ account, index }) => {
        const isActive = index === selectedIndex;
        return `
          <div class="account-card ${isActive ? 'active' : ''}" role="button" tabindex="0" data-index="${index}">
            <div class="account-card-header">
              <h5>${account.company}</h5>
              <span class="score-pill">${account.score}</span>
            </div>
            <p>${account.intent} · ${account.stage}</p>
            <div class="card-meta">
              <span>${account.signal}</span>
              <span>${account.health} · <button class="compare-button" type="button" data-compare="${index}">${compareIndex === index ? 'Comparing' : 'Compare'}</button></span>
            </div>
          </div>
        `;
      })
      .join('');

    accountListEl.querySelectorAll('.account-card').forEach((card) => {
      card.addEventListener('click', () => {
        selectedIndex = Number(card.dataset.index);
        track('account_select', { company: accounts[selectedIndex]?.company });
        renderAccountDetail();
      });
      card.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          card.click();
        }
      });
    });
    accountListEl.querySelectorAll('.compare-button').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        compareIndex = Number(button.dataset.compare);
        track('account_compare', { selected: accounts[selectedIndex]?.company, compared: accounts[compareIndex]?.company });
        renderAccountDetail();
      });
    });
  };

  const renderAccountDetail = () => {
    if (!accounts.length) return;

    const account = accounts[selectedIndex] ?? accounts[0];
    if (!account) return;

    detailCompanyEl.textContent = account.company;
    detailScoreEl.textContent = account.score;
    detailIntentEl.textContent = account.intent;
    detailStageEl.textContent = account.stage;
    detailSignalEl.textContent = account.signal;
    detailPathEl.textContent = account.path;
    timelineStatusEl.textContent = account.health;

    const signalWeight = account.intent === 'Expansion' || account.intent === 'Cross-sell' ? 'High commercial urgency' : 'Active buying motion';
    const relationshipWeight = account.relationships?.length >= 3 ? 'Three relevant paths identified' : 'Relationship path developing';
    const scoreReason = `Score ${account.score} · ${signalWeight} · ${relationshipWeight}.`;
    scoreExplanationEl.textContent = scoreReason;

    if (compareIndex !== null && accounts[compareIndex] && compareIndex !== selectedIndex) {
      const compared = accounts[compareIndex];
      compareLabelEl.textContent = `${account.company} (${account.score}) vs ${compared.company} (${compared.score}) · ${account.score >= compared.score ? account.company : compared.company} is currently prioritized.`;
    } else {
      compareLabelEl.textContent = 'Select another account to compare.';
    }

    scenarioChips.forEach((chip) => {
      const isSelected = Number(chip.dataset.scenario) === selectedIndex;
      chip.classList.toggle('active', isSelected);
      chip.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
    });

    relationshipMapEl.innerHTML = (account.relationships || [])
      .map((person, idx) => `
        <div class="relationship-node">
          <span>${idx + 1}. ${person}</span>
          <strong>${['Strong', 'Warm', 'Ready'][idx % 3]}</strong>
        </div>
      `)
      .join('');

    activityFeedEl.innerHTML = (account.activities || [])
      .map(([time, text]) => `
        <div class="activity-item">
          <span class="time">${time}</span>
          <span class="bullet"></span>
          <span>${text}</span>
        </div>
      `)
      .join('');

    renderAccounts();
  };

  const performAction = (type) => {
    const account = accounts[selectedIndex] ?? accounts[0];
    const actions = {
      scan: {
        label: 'Signal scan refreshed',
        stage: 'Signals updated',
        score: account.score + 2,
        signal: 'new buying signal surfaced'
      },
      intro: {
        label: 'Warm intro queued',
        stage: 'Intro sequence queued',
        score: account.score + 3,
        signal: 'warm-intro opportunity activated'
      },
      approve: {
        label: 'Outreach approved',
        stage: 'Approved for outreach',
        score: account.score + 4,
        signal: 'outreach approved by governance layer'
      }
    };

    const action = actions[type];
    const now = new Date();
    const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    account.activities.unshift([time, `${action.label} for ${account.company}`]);
    account.stage = action.stage;
    account.score = Math.min(99, action.score);
    account.signal = action.signal;
    account.health = 'Healthy';
    summary.workflowRuns = Number(summary.workflowRuns ?? 237) + 1;
    hydrateSummary();
    if (actionFeedbackEl) {
      actionFeedbackEl.textContent = `${action.label}. ${account.company} is now marked ${account.stage.toLowerCase()}.`;
    }

    saveState();
    track('workflow_action', { action: type, company: account.company, stage: account.stage });
    renderAccountDetail();
  };

  viewWorkflow?.addEventListener('click', scrollToWorkflow);
  guideNextBtn?.addEventListener('click', () => {
    guideStep = (guideStep + 1) % 3;
    updateGuide();
    track('guide_step', { step: guideStep + 1 });
    if (guideStep === 1) renderAccountDetail();
    if (guideStep === 2) document.getElementById('runAction')?.focus();
  });
  dialogWorkflow?.addEventListener('click', () => {
    dialog?.close();
    scrollToWorkflow();
  });
  closeDialog?.addEventListener('click', () => dialog?.close());
  requestDemo?.addEventListener('click', () => {
    if (dialog?.showModal) {
      dialog.showModal();
    } else {
      scrollToWorkflow();
    }
  });

  document.querySelectorAll('.action-button').forEach((button) => {
    button.addEventListener('click', () => performAction(button.dataset.action));
  });

  runActionBtn?.addEventListener('click', () => {
    const actionTypes = ['scan', 'intro', 'approve'];
    const next = actionTypes[Math.floor(Math.random() * actionTypes.length)];
    performAction(next);
  });

  refreshQueueBtn?.addEventListener('click', () => {
    accounts.forEach((account) => {
      account.score = Math.max(80, Math.min(99, account.score + 1));
    });
    summary.qualifiedAccounts = Math.max(120, Number(summary.qualifiedAccounts ?? 148) + 1);
    summary.workflowRuns = Number(summary.workflowRuns ?? 237) + 1;
    hydrateSummary();
    if (actionFeedbackEl) {
      actionFeedbackEl.textContent = 'Queue refreshed. Account scores have been re-ranked for this session.';
    }
    saveState();
    track('queue_refresh');
    renderAccountDetail();
  });

  resetDemoBtn?.addEventListener('click', resetState);
  shareDemoBtn?.addEventListener('click', async () => {
    const shareUrl = `${window.location.origin}${window.location.pathname}?scenario=${selectedIndex}`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      if (actionFeedbackEl) actionFeedbackEl.textContent = 'Scenario link copied. Share this account command-center view.';
    } catch (error) {
      if (actionFeedbackEl) actionFeedbackEl.textContent = shareUrl;
    }
    track('scenario_share', { scenario: selectedIndex });
  });
  clearCompareBtn?.addEventListener('click', () => {
    compareIndex = null;
    renderAccountDetail();
  });
  accountSearchEl?.addEventListener('input', () => {
    track('account_search', { query: accountSearchEl.value });
    renderAccounts();
  });
  stageFilterEl?.addEventListener('change', renderAccounts);
  intentFilterEl?.addEventListener('change', renderAccounts);

  scenarioChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      selectedIndex = Number(chip.dataset.scenario);
      renderAccountDetail();
    });
  });

  walkthroughForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    const formData = new FormData(walkthroughForm);
    const name = String(formData.get('name') || '').trim();
    const email = String(formData.get('email') || '').trim();

    if (!name || !email) {
      if (formStatusEl) formStatusEl.textContent = 'Add your name and work email to continue.';
      return;
    }

    if (formStatusEl) {
      formStatusEl.textContent = `Thanks, ${name}. Your request is captured in this demo session for ${email}.`;
    }
    track('walkthrough_request', { role: formData.get('role') || 'unknown' });
    if (baseConfig.requestEndpoint) {
      fetch(baseConfig.requestEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(formData.entries())),
      }).catch(() => {
        if (formStatusEl) formStatusEl.textContent = 'Your request is saved locally. We could not reach the configured follow-up service.';
      });
    }
    walkthroughForm.reset();
  });

  finalBookDemoBtn?.addEventListener('click', () => {
    if (dialog?.showModal) {
      dialog.showModal();
    } else {
      scrollToWorkflow();
    }
  });

  dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });

  loadDemoState();
});
