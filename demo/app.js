/* ============================================================
   Prospect Dominion — Application Logic
   Navigation, data rendering, interactions, approval workflow
   ============================================================ */

(function () {
  'use strict';

  let appData = null;
  let currentPage = 'home';
  let selectedAccount = null;
  let signalFilter = 'All';
  let oppFilter = 'All';
  let actionFilter = 'All';

  const avatarColors = ['blue', 'indigo', 'violet', 'teal', 'amber', 'pink'];

  // --- Icons (inline SVG) ---
  const icons = {
    home: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1"/></svg>',
    signal: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>',
    opportunities: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>',
    actions: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
    approvals: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>',
    accounts: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>',
    contacts: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>',
    reports: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2"/></svg>',
    settings: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>',
    bell: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg>',
    close: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M6 18L18 6M6 6l12 12"/></svg>',
    menu: '<svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>',
    check: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path d="M5 13l4 4L19 7"/></svg>',
    x: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path d="M6 18L18 6M6 6l12 12"/></svg>',
    kpiSignal: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>',
    kpiPrioritised: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12"/></svg>',
    kpiApproval: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
    kpiAction: '<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>',
  };

  function getAvatarColor(index) {
    return avatarColors[index % avatarColors.length];
  }

  function getBadgeClass(value) {
    const map = {
      'High': 'badge-high', 'Medium': 'badge-medium', 'Low': 'badge-low',
      'Awaiting Approval': 'badge-awaiting', 'Ready': 'badge-ready',
      'In Progress': 'badge-progress', 'Approved': 'badge-approved',
      'Queued': 'badge-queued', 'Completed': 'badge-completed',
      'Pending': 'badge-pending', 'Not Required': 'badge-reviewed',
      'New': 'badge-new', 'Prioritised': 'badge-prioritised', 'Reviewed': 'badge-reviewed',
    };
    return map[value] || 'badge-low';
  }

  function getActivityIconClass(type) {
    return type || 'signal';
  }

  function getActivityIconSymbol(type) {
    const map = {
      signal: '⚡', prioritised: '↑', approved: '✓', status: '↻', action: '▶',
    };
    return map[type] || '•';
  }

  // --- Data Loading ---
  async function loadData() {
    const paths = ['../app-data.json', './app-data.json', '../demo-data.json'];
    for (const path of paths) {
      try {
        const res = await fetch(path, { cache: 'no-store' });
        if (res.ok) {
          const data = await res.json();
          if (data && data.accounts) return data;
        }
      } catch (e) { /* continue */ }
    }
    return null;
  }

  // --- Navigation ---
  function navigate(page) {
    currentPage = page;

    // Update sidebar
    document.querySelectorAll('.sidebar-link').forEach(link => {
      link.classList.toggle('active', link.dataset.page === page);
    });

    // Update page views
    document.querySelectorAll('.page-view').forEach(view => {
      view.classList.toggle('active', view.id === 'page-' + page);
    });

    // Update topbar title
    const titles = {
      home: 'Dashboard', signals: 'Signals', opportunities: 'Opportunities',
      actions: 'Actions', approvals: 'Approvals', accounts: 'Accounts',
      contacts: 'Contacts', reports: 'Reports', settings: 'Settings',
    };
    const topTitle = document.getElementById('topbar-title');
    if (topTitle) topTitle.textContent = titles[page] || 'Dashboard';

    // Close mobile menu
    closeMobileMenu();

    // Render page content
    renderPage(page);
  }

  function renderPage(page) {
    if (!appData) return;
    switch (page) {
      case 'home': renderDashboard(); break;
      case 'signals': renderSignals(); break;
      case 'opportunities': renderOpportunities(); break;
      case 'actions': renderActions(); break;
      case 'approvals': renderApprovals(); break;
      case 'accounts': renderAccountsList(); break;
      case 'contacts': renderContacts(); break;
      case 'reports': renderReports(); break;
      case 'settings': renderSettings(); break;
    }
  }

  // --- Dashboard ---
  function renderDashboard() {
    renderKPIs();
    renderOppTable('dashboard-opp-table', appData.accounts);
    renderSignalSources();
    renderActivityFeed('dashboard-activity', appData.recentActivity.slice(0, 6));
  }

  function renderKPIs() {
    const grid = document.getElementById('kpi-grid');
    if (!grid) return;
    const kpis = appData.kpis;
    const kpiConfigs = [
      { key: 'signalsDetected', icon: icons.kpiSignal, color: 'blue' },
      { key: 'prioritised', icon: icons.kpiPrioritised, color: 'indigo' },
      { key: 'awaitingApproval', icon: icons.kpiApproval, color: 'amber' },
      { key: 'actionsInProgress', icon: icons.kpiAction, color: 'teal' },
    ];

    grid.innerHTML = kpiConfigs.map(cfg => {
      const kpi = kpis[cfg.key];
      const trend = kpi.trend === 'up' ? 'up' : kpi.trend === 'down' ? 'down' : 'neutral';
      return `
        <div class="kpi-card">
          <div class="kpi-header">
            <div class="kpi-icon ${cfg.color}">${cfg.icon}</div>
            <span class="kpi-change ${trend}">${kpi.change}</span>
          </div>
          <div class="kpi-value">${kpi.value}</div>
          <div class="kpi-label">${kpi.label}</div>
        </div>`;
    }).join('');
  }

  function renderOppTable(containerId, accounts) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <table class="opp-table">
        <thead>
          <tr>
            <th>Account / Opportunity</th>
            <th>Signal</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Owner</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${accounts.map((acc, i) => `
            <tr data-account-id="${acc.id}" onclick="window.pdApp.openDetail('${acc.id}')">
              <td>
                <div class="opp-company">
                  <div class="opp-avatar ${getAvatarColor(i)}">${acc.avatar}</div>
                  <div>
                    <div class="opp-name">${acc.company}</div>
                    <div class="opp-signal-text truncate">${acc.signal}</div>
                  </div>
                </div>
              </td>
              <td><span class="badge ${getBadgeClass(acc.signalType === 'Company Changes' ? 'Prioritised' : 'New')}">${acc.signalType}</span></td>
              <td><span class="badge ${getBadgeClass(acc.priority)}">${acc.priority}</span></td>
              <td><span class="badge ${getBadgeClass(acc.status)}">${acc.status}</span></td>
              <td>
                <div class="owner-badge">
                  <div class="owner-avatar">${acc.owner.initials}</div>
                  <span class="owner-name">${acc.owner.name}</span>
                </div>
              </td>
              <td>
                <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); window.pdApp.openDetail('${acc.id}')">${acc.status === 'Awaiting Approval' ? 'Review' : 'View'}</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  function renderSignalSources() {
    const container = document.getElementById('signal-sources');
    if (!container || !appData.signalSources) return;

    container.innerHTML = appData.signalSources.map(src => `
      <div class="source-item">
        <div class="source-dot" style="background: ${src.color}"></div>
        <span class="source-label">${src.name}</span>
        <span class="source-count">${src.count}</span>
      </div>
    `).join('');
  }

  function renderActivityFeed(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = items.map(item => `
      <div class="activity-item">
        <div class="activity-icon ${getActivityIconClass(item.type)}">${getActivityIconSymbol(item.type)}</div>
        <div class="activity-content">
          <div class="activity-text">${item.text} — <strong>${item.account}</strong></div>
          <div class="activity-meta">${item.time}</div>
        </div>
      </div>
    `).join('');
  }

  // --- Signals Page ---
  function renderSignals() {
    const container = document.getElementById('signals-table-body');
    if (!container) return;

    let filtered = appData.signals;
    if (signalFilter !== 'All') {
      filtered = filtered.filter(s => s.status === signalFilter);
    }

    const search = document.getElementById('signals-search');
    if (search && search.value.trim()) {
      const q = search.value.trim().toLowerCase();
      filtered = filtered.filter(s =>
        s.account.toLowerCase().includes(q) || s.text.toLowerCase().includes(q) || s.type.toLowerCase().includes(q)
      );
    }

    container.innerHTML = filtered.map(sig => `
      <tr>
        <td>${sig.type}</td>
        <td><strong>${sig.account}</strong></td>
        <td>${sig.text}</td>
        <td>${sig.time}</td>
        <td><span class="badge ${getBadgeClass(sig.importance)}">${sig.importance}</span></td>
        <td><span class="badge ${getBadgeClass(sig.status)}">${sig.status}</span></td>
        <td>${sig.action}</td>
      </tr>
    `).join('');
  }

  // --- Opportunities Page ---
  function renderOpportunities() {
    const container = document.getElementById('opportunities-table');
    if (!container) return;

    let filtered = appData.accounts;
    if (oppFilter !== 'All') {
      filtered = filtered.filter(a => a.status === oppFilter);
    }

    const search = document.getElementById('opp-search');
    if (search && search.value.trim()) {
      const q = search.value.trim().toLowerCase();
      filtered = filtered.filter(a =>
        a.company.toLowerCase().includes(q) || a.signal.toLowerCase().includes(q)
      );
    }

    renderOppTable('opportunities-table', filtered);
  }

  // --- Actions Page ---
  function renderActions() {
    const container = document.getElementById('actions-table-body');
    if (!container) return;

    let filtered = appData.actions;
    if (actionFilter !== 'All') {
      filtered = filtered.filter(a => a.status === actionFilter);
    }

    container.innerHTML = filtered.map(act => `
      <tr>
        <td><strong>${act.type}</strong></td>
        <td>${act.account}</td>
        <td>${act.owner}</td>
        <td><span class="badge ${getBadgeClass(act.approval)}">${act.approval}</span></td>
        <td>${act.created}</td>
        <td><span class="badge ${getBadgeClass(act.status)}">${act.status}</span></td>
      </tr>
    `).join('');
  }

  // --- Approvals Page ---
  function renderApprovals() {
    const container = document.getElementById('approvals-list');
    if (!container) return;

    const pending = appData.accounts.filter(a => a.status === 'Awaiting Approval');

    container.innerHTML = pending.length ? pending.map((acc, i) => `
      <div class="approval-card" data-id="${acc.id}">
        <div class="approval-card-header">
          <div class="opp-avatar ${getAvatarColor(i)}">${acc.avatar}</div>
          <div>
            <div class="approval-card-company">${acc.company}</div>
            <span class="badge ${getBadgeClass(acc.priority)}" style="margin-top:4px">${acc.priority} priority</span>
          </div>
        </div>
        <div class="approval-card-signal">${acc.signal}</div>
        <div class="approval-card-action">
          <strong>Recommended:</strong> ${acc.recommendedAction}
        </div>
        <div class="approval-card-meta">
          <div class="approval-card-owner">
            <div class="owner-avatar">${acc.owner.initials}</div>
            <span>${acc.owner.name}</span>
          </div>
          <span class="approval-card-time">${acc.activities[0]?.time || ''}</span>
        </div>
        <div class="approval-card-buttons">
          <button class="btn btn-success" onclick="window.pdApp.approveAccount('${acc.id}')">
            ${icons.check} Approve
          </button>
          <button class="btn btn-danger" onclick="window.pdApp.rejectAccount('${acc.id}')">
            ${icons.x} Send Back
          </button>
          <button class="btn btn-outline" onclick="window.pdApp.openDetail('${acc.id}')">Review</button>
        </div>
      </div>
    `).join('') : '<div style="text-align:center;padding:40px;color:var(--text-muted)">No items awaiting approval.</div>';
  }

  // --- Accounts List ---
  function renderAccountsList() {
    const container = document.getElementById('accounts-list-table');
    if (!container) return;

    container.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Company</th>
            <th>Stage</th>
            <th>Intent</th>
            <th>Score</th>
            <th>Signals</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${appData.accounts.map((acc, i) => `
            <tr onclick="window.pdApp.openDetail('${acc.id}')" style="cursor:pointer">
              <td>
                <div class="opp-company">
                  <div class="opp-avatar ${getAvatarColor(i)}">${acc.avatar}</div>
                  <div class="opp-name">${acc.company}</div>
                </div>
              </td>
              <td>${acc.stage}</td>
              <td>${acc.intent}</td>
              <td><strong>${acc.score}</strong></td>
              <td>${acc.activities.length}</td>
              <td><span class="badge ${getBadgeClass(acc.status)}">${acc.status}</span></td>
              <td><button class="btn btn-sm btn-outline" onclick="event.stopPropagation(); window.pdApp.openDetail('${acc.id}')">View</button></td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  // --- Contacts ---
  function renderContacts() {
    const container = document.getElementById('contacts-list');
    if (!container) return;

    const contacts = [];
    appData.accounts.forEach((acc, i) => {
      (acc.contacts || []).forEach(name => {
        contacts.push({ name, company: acc.company, color: getAvatarColor(i), initials: name.split(' ').map(w => w[0]).join('') });
      });
    });

    container.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Name</th><th>Company</th></tr></thead>
        <tbody>
          ${contacts.map(c => `
            <tr>
              <td>
                <div class="opp-company">
                  <div class="owner-avatar">${c.initials}</div>
                  <span>${c.name}</span>
                </div>
              </td>
              <td>${c.company}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  // --- Reports ---
  function renderReports() {
    // Mini bar chart
    const bars = document.getElementById('report-bars');
    if (bars) {
      const heights = [35, 55, 42, 68, 75, 60, 85];
      bars.innerHTML = heights.map(h => `<div class="mini-bar" style="height:${h}%"></div>`).join('');
    }
  }

  // --- Settings ---
  function renderSettings() { /* static content in HTML */ }

  // --- Detail Panel ---
  function openDetail(accountId) {
    const acc = appData.accounts.find(a => a.id === accountId);
    if (!acc) return;
    selectedAccount = acc;

    const overlay = document.getElementById('detail-overlay');
    const panel = document.getElementById('detail-content');
    if (!overlay || !panel) return;

    const i = appData.accounts.indexOf(acc);
    const isAwaitingApproval = acc.status === 'Awaiting Approval';
    const isApproved = acc.status === 'Approved';

    panel.innerHTML = `
      <div class="detail-header">
        <div class="detail-company-header">
          <div class="detail-avatar opp-avatar ${getAvatarColor(i)}">${acc.avatar}</div>
          <div>
            <div class="detail-company-name">${acc.company}</div>
            <div class="detail-company-meta">
              <span class="badge ${getBadgeClass(acc.priority)}">${acc.priority}</span>
              <span class="badge ${getBadgeClass(acc.status)}">${acc.status}</span>
            </div>
          </div>
        </div>
        <button class="detail-close" onclick="window.pdApp.closeDetail()">${icons.close}</button>
      </div>

      <div class="detail-body">
        <div class="detail-section">
          <div class="detail-section-title">Signal & Context</div>
          <div class="detail-context">${acc.context}</div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Account Details</div>
          <div class="detail-info-grid">
            <div class="detail-info-item">
              <div class="detail-info-label">Stage</div>
              <div class="detail-info-value">${acc.stage}</div>
            </div>
            <div class="detail-info-item">
              <div class="detail-info-label">Intent</div>
              <div class="detail-info-value">${acc.intent}</div>
            </div>
            <div class="detail-info-item">
              <div class="detail-info-label">Decision Path</div>
              <div class="detail-info-value">${acc.path}</div>
            </div>
            <div class="detail-info-item">
              <div class="detail-info-label">Owner</div>
              <div class="detail-info-value">${acc.owner.name}</div>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Contacts</div>
          <div class="detail-contacts">
            ${(acc.contacts || []).map(c => `
              <div class="detail-contact-chip">
                <div class="detail-contact-avatar">${c.split(' ').map(w => w[0]).join('')}</div>
                ${c}
              </div>
            `).join('')}
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Recommended Action</div>
          ${isAwaitingApproval ? `
            <div class="approval-box">
              <div class="approval-title">Awaiting Approval</div>
              <div class="approval-desc">${acc.recommendedAction}</div>
              <div class="approval-actions">
                <button class="btn btn-success" onclick="window.pdApp.approveAccount('${acc.id}')">${icons.check} Approve</button>
                <button class="btn btn-danger" onclick="window.pdApp.rejectAccount('${acc.id}')">${icons.x} Send Back</button>
              </div>
            </div>
          ` : isApproved ? `
            <div class="approval-box approved">
              <div class="approval-title">Approved</div>
              <div class="approval-desc">${acc.recommendedAction}</div>
            </div>
          ` : `
            <div class="detail-context"><strong>${acc.recommendedAction}</strong></div>
          `}
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Activity History</div>
          <div class="detail-activity-list">
            ${(acc.activities || []).map(act => `
              <div class="detail-activity-item">
                <div class="detail-activity-dot ${act.type}"></div>
                <div>
                  <div class="detail-activity-text">${act.text}</div>
                  <div class="detail-activity-time">${act.time}</div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;

    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeDetail() {
    const overlay = document.getElementById('detail-overlay');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  // --- Approval Actions ---
  function approveAccount(accountId) {
    const acc = appData.accounts.find(a => a.id === accountId);
    if (!acc) return;
    acc.status = 'Approved';
    acc.activities.unshift({
      type: 'approved',
      text: `Action approved for ${acc.company}`,
      time: 'Just now',
      account: acc.company,
    });

    // Update KPIs
    appData.kpis.awaitingApproval.value = Math.max(0, appData.kpis.awaitingApproval.value - 1);
    appData.kpis.actionsInProgress.value += 1;

    // Update actions
    const action = appData.actions.find(a => a.account === acc.company && a.status === 'Awaiting Approval');
    if (action) {
      action.status = 'In Progress';
      action.approval = 'Approved';
    }

    // Add to recent activity
    appData.recentActivity.unshift({
      type: 'approved',
      text: `Action approved — ${acc.recommendedAction}`,
      account: acc.company,
      time: 'Just now',
    });

    // Re-render current view
    renderPage(currentPage);

    // Update detail if open
    if (selectedAccount && selectedAccount.id === accountId) {
      openDetail(accountId);
    }
  }

  function rejectAccount(accountId) {
    const acc = appData.accounts.find(a => a.id === accountId);
    if (!acc) return;
    acc.status = 'Ready';
    acc.activities.unshift({
      type: 'status',
      text: `Action sent back for review — ${acc.company}`,
      time: 'Just now',
      account: acc.company,
    });

    appData.kpis.awaitingApproval.value = Math.max(0, appData.kpis.awaitingApproval.value - 1);

    appData.recentActivity.unshift({
      type: 'status',
      text: 'Action sent back for review',
      account: acc.company,
      time: 'Just now',
    });

    renderPage(currentPage);
    if (selectedAccount && selectedAccount.id === accountId) {
      openDetail(accountId);
    }
  }

  // --- Mobile Menu ---
  function openMobileMenu() {
    document.querySelector('.sidebar')?.classList.add('open');
    document.querySelector('.sidebar-backdrop')?.classList.add('open');
  }

  function closeMobileMenu() {
    document.querySelector('.sidebar')?.classList.remove('open');
    document.querySelector('.sidebar-backdrop')?.classList.remove('open');
  }

  // --- Initialization ---
  async function init() {
    appData = await loadData();
    if (!appData) {
      console.warn('Prospect Dominion: Could not load app data.');
      return;
    }

    // Sidebar nav
    document.querySelectorAll('.sidebar-link').forEach(link => {
      link.addEventListener('click', () => navigate(link.dataset.page));
    });

    // Mobile menu
    document.getElementById('mobile-menu-btn')?.addEventListener('click', openMobileMenu);
    document.querySelector('.sidebar-backdrop')?.addEventListener('click', closeMobileMenu);

    // Detail overlay close
    document.getElementById('detail-overlay')?.addEventListener('click', (e) => {
      if (e.target.id === 'detail-overlay') closeDetail();
    });

    // Signal filter tabs
    document.querySelectorAll('[data-signal-filter]').forEach(tab => {
      tab.addEventListener('click', () => {
        signalFilter = tab.dataset.signalFilter;
        document.querySelectorAll('[data-signal-filter]').forEach(t => t.classList.toggle('active', t === tab));
        renderSignals();
      });
    });

    // Opp filter
    document.getElementById('opp-status-filter')?.addEventListener('change', (e) => {
      oppFilter = e.target.value;
      renderOpportunities();
    });
    document.getElementById('opp-search')?.addEventListener('input', () => renderOpportunities());

    // Action filter
    document.getElementById('action-status-filter')?.addEventListener('change', (e) => {
      actionFilter = e.target.value;
      renderActions();
    });

    // Signals search
    document.getElementById('signals-search')?.addEventListener('input', () => renderSignals());

    // Global search
    document.getElementById('global-search')?.addEventListener('input', (e) => {
      const q = e.target.value.trim().toLowerCase();
      if (q.length >= 2) {
        // Navigate to opportunities and filter
        navigate('opportunities');
        const oppSearch = document.getElementById('opp-search');
        if (oppSearch) { oppSearch.value = q; renderOpportunities(); }
      }
    });

    // Render initial page
    navigate('home');
  }

  // Expose public API
  window.pdApp = { openDetail, closeDetail, approveAccount, rejectAccount, navigate };

  // Start
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
