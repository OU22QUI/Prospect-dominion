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

  const accounts = [
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

  let selectedIndex = 0;

  const scrollToWorkflow = () => {
    if (demoSection) {
      demoSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const renderAccounts = () => {
    if (!accountListEl) return;

    accountListEl.innerHTML = accounts
      .map((account, index) => {
        const isActive = index === selectedIndex;
        return `
          <button class="account-card ${isActive ? 'active' : ''}" type="button" data-index="${index}">
            <div class="account-card-header">
              <h5>${account.company}</h5>
              <span class="score-pill">${account.score}</span>
            </div>
            <p>${account.intent} · ${account.stage}</p>
            <div class="card-meta">
              <span>${account.signal}</span>
              <span>${account.health}</span>
            </div>
          </button>
        `;
      })
      .join('');

    accountListEl.querySelectorAll('.account-card').forEach((button) => {
      button.addEventListener('click', () => {
        selectedIndex = Number(button.dataset.index);
        renderAccountDetail();
      });
    });
  };

  const renderAccountDetail = () => {
    const account = accounts[selectedIndex];
    detailCompanyEl.textContent = account.company;
    detailScoreEl.textContent = account.score;
    detailIntentEl.textContent = account.intent;
    detailStageEl.textContent = account.stage;
    detailSignalEl.textContent = account.signal;
    detailPathEl.textContent = account.path;
    timelineStatusEl.textContent = account.health;

    relationshipMapEl.innerHTML = account.relationships
      .map((person, idx) => `
        <div class="relationship-node">
          <span>${idx + 1}. ${person}</span>
          <strong>${['Strong', 'Warm', 'Ready'][idx % 3]}</strong>
        </div>
      `)
      .join('');

    activityFeedEl.innerHTML = account.activities
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
    const account = accounts[selectedIndex];
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

    renderAccountDetail();
  };

  viewWorkflow?.addEventListener('click', scrollToWorkflow);
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
    renderAccountDetail();
  });

  dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });

  renderAccountDetail();
});
