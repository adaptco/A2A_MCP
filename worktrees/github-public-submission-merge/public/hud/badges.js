(function () {
  'use strict';

  const API_PROOF_URL = '/qbit/proof.latest.v1';
  const CANONICAL_DEFAULT = '/governance/authority_map.v1.canonical.json';
  const REFRESH_INTERVAL_MS = 12000;
  const warnedMessages = new Set();
  const state = {
    timer: null,
    lastProof: null,
    lastLocalHash: null
  };

  function warnOnce(message) {
    const key = String(message);
    if (warnedMessages.has(key)) {
      return;
    }
    warnedMessages.add(key);
    console.warn('[HUD]', key);
  }

  function injectStyles() {
    const styleId = 'hud-badge-styles';
    if (document.getElementById(styleId)) {
      return;
    }
    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      #hud-badge-root { font-family: 'Inter', 'Segoe UI', sans-serif; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 8px 0; }
      #hud-badge-root .hud-badge { padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; letter-spacing: 0.02em; background: #e5e7eb; color: #1f2937; display: inline-flex; align-items: center; gap: 6px; }
      #hud-badge-root .hud-badge.match { background: #16a34a; color: #f9fafb; }
      #hud-badge-root .hud-badge.mismatch { background: #dc2626; color: #f9fafb; }
      #hud-badge-root .hud-badge.info { background: #c7d2fe; color: #1e1b4b; }
      #hud-badge-root .hud-badge.offline { background: #9ca3af; color: #111827; }
      #hud-badge-root .hud-controls { display: inline-flex; gap: 6px; margin-left: 8px; }
      #hud-badge-root .hud-btn { border: 1px solid #d1d5db; background: #ffffff; border-radius: 6px; padding: 5px 10px; font-size: 12px; cursor: pointer; }
      #hud-badge-root .hud-btn:active { transform: translateY(1px); }
    `;
    document.head.appendChild(style);
  }

  function ensureRoot() {
    injectStyles();
    let root = document.getElementById('hud-badge-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'hud-badge-root';
      document.body.appendChild(root);
    }
    return root;
  }

  function createBadge(label) {
    const badge = document.createElement('span');
    badge.className = 'hud-badge info';
    badge.dataset.label = label;
    badge.textContent = `${label}: —`;
    return badge;
  }

  function setBadge(badge, status, text) {
    badge.className = `hud-badge ${status}`;
    badge.textContent = `${badge.dataset.label}: ${text}`;
  }

  function createControls(onRefresh, onRehash) {
    const wrapper = document.createElement('div');
    wrapper.className = 'hud-controls';

    const refreshBtn = document.createElement('button');
    refreshBtn.className = 'hud-btn';
    refreshBtn.type = 'button';
    refreshBtn.textContent = 'Refresh';
    refreshBtn.addEventListener('click', () => {
      onRefresh();
    });

    const rehashBtn = document.createElement('button');
    rehashBtn.className = 'hud-btn';
    rehashBtn.type = 'button';
    rehashBtn.textContent = 'Rehash';
    rehashBtn.addEventListener('click', () => {
      onRehash();
    });

    wrapper.appendChild(refreshBtn);
    wrapper.appendChild(rehashBtn);
    return wrapper;
  }

  async function fetchJson(url) {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Request failed for ${url} (status ${response.status})`);
    }
    return response.json();
  }

  async function computeLocalHash(canonicalUrl) {
    const response = await fetch(canonicalUrl, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Canonical fetch failed (status ${response.status})`);
    }
    const canonicalText = await response.text();
    const data = new TextEncoder().encode(canonicalText);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
    return { hash: hashHex, canonical: canonicalText };
  }

  function scheduleNextRefresh(fn) {
    if (state.timer) {
      clearTimeout(state.timer);
    }
    state.timer = setTimeout(() => {
      fn().catch((err) => warnOnce(err.message));
    }, REFRESH_INTERVAL_MS);
  }

  function describeHash(proof, localInfo) {
    if (!proof) {
      return { status: 'offline', text: 'Offline' };
    }
    const serverMatch = proof.hash_matches === undefined ? null : Boolean(proof.hash_matches);
    if (localInfo && typeof localInfo.matches === 'boolean') {
      return {
        status: localInfo.matches ? 'match' : 'mismatch',
        text: localInfo.matches ? 'MATCH (local)' : 'MISMATCH (local)'
      };
    }
    if (serverMatch === null) {
      return { status: 'info', text: 'Unknown' };
    }
    return {
      status: serverMatch ? 'match' : 'mismatch',
      text: serverMatch ? 'MATCH' : 'MISMATCH'
    };
  }

  function describeDuo(proof) {
    if (!proof || !proof.duo) {
      return { status: 'offline', text: 'Offline' };
    }
    const duoOk = Boolean(proof.duo.ok && proof.duo.maker && proof.duo.checker);
    return {
      status: duoOk ? 'match' : 'mismatch',
      text: duoOk ? 'MATCH' : 'MISMATCH'
    };
  }

  function describeShimmer(proof) {
    if (!proof || !proof.scrollstream) {
      return { status: 'offline', text: 'Offline' };
    }
    const shimmer = proof.scrollstream.shimmer;
    if (shimmer === 'engaged') {
      return { status: 'match', text: 'Shimmer ON' };
    }
    if (shimmer === 'idle') {
      return { status: 'info', text: 'Shimmer idle' };
    }
    return { status: 'info', text: shimmer || 'Unknown' };
  }

  function describeReplay(proof) {
    if (!proof || !proof.scrollstream) {
      return { status: 'offline', text: 'Offline' };
    }
    const replay = proof.scrollstream.replay_glyph;
    if (replay === 'pulse') {
      return { status: 'match', text: 'Replay pulse' };
    }
    if (replay === 'idle') {
      return { status: 'info', text: 'Replay idle' };
    }
    return { status: 'info', text: replay || 'Unknown' };
  }

  function updateBadges(badges, proof, localInfo) {
    const hashBadgeState = describeHash(proof, localInfo);
    setBadge(badges.hash, hashBadgeState.status, hashBadgeState.text);

    const duoBadgeState = describeDuo(proof);
    setBadge(badges.duo, duoBadgeState.status, duoBadgeState.text);

    const policyText = proof && proof.policy_tag ? proof.policy_tag : 'n/a';
    setBadge(badges.policy, 'info', policyText);

    const shimmerState = describeShimmer(proof);
    setBadge(badges.scrollstream, shimmerState.status, shimmerState.text);

    const replayState = describeReplay(proof);
    setBadge(badges.replay, replayState.status, replayState.text);

    if (!proof) {
      setBadge(badges.status, 'offline', 'Offline');
    } else {
      const updatedAt = proof.generated_at || new Date().toISOString();
      setBadge(badges.status, 'info', `Updated ${updatedAt}`);
    }
  }

  async function refreshBadges(options = {}) {
    const root = ensureRoot();
    if (!state.badges) {
      state.badges = {
        hash: createBadge('Hash'),
        duo: createBadge('Duo'),
        policy: createBadge('Policy'),
        scrollstream: createBadge('Shimmer'),
        replay: createBadge('Replay'),
        status: createBadge('Status')
      };
      root.appendChild(state.badges.hash);
      root.appendChild(state.badges.duo);
      root.appendChild(state.badges.policy);
      root.appendChild(state.badges.scrollstream);
      root.appendChild(state.badges.replay);
      root.appendChild(state.badges.status);
      root.appendChild(createControls(() => refreshBadges({ force: true }), () => refreshBadges({ force: true, rehash: true })));
    }

    const force = Boolean(options.force);
    const rehash = Boolean(options.rehash);
    const querySuffix = force ? (API_PROOF_URL.includes('?') ? '&force=true' : '?force=true') : '';

    try {
      const proof = await fetchJson(`${API_PROOF_URL}${querySuffix}`);
      state.lastProof = proof;
      let localInfo = null;
      if (rehash) {
        try {
          const canonicalUrl = proof.canonical_endpoint || CANONICAL_DEFAULT;
          const local = await computeLocalHash(canonicalUrl);
          localInfo = {
            hash: local.hash,
            matches: local.hash === proof.manifest_hash
          };
          state.lastLocalHash = localInfo;
        } catch (err) {
          warnOnce(err.message);
          localInfo = { hash: null, matches: false };
        }
      } else {
        localInfo = state.lastLocalHash;
      }
      updateBadges(state.badges, proof, localInfo);
    } catch (err) {
      warnOnce(err.message);
      state.lastProof = null;
      updateBadges(state.badges, null, null);
    }

    scheduleNextRefresh(() => refreshBadges({ force: false, rehash: false }));
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      refreshBadges({});
    }
  });

  window.addEventListener('load', () => {
    refreshBadges({}).catch((err) => warnOnce(err.message));
  });
})();
