// Clued front end. No build step: fetch + the browser's own speech APIs,
// marked/DOMPurify for Markdown, KaTeX for LaTeX.

// --------------------------------------------------------------------
// Elements
// --------------------------------------------------------------------

const initialScreen = document.getElementById('initial-name-screen');
const mainInterface = document.getElementById('main-interface');
const nameSubmitBtn = document.getElementById('name-submit-btn');
const usernameInput = document.getElementById('username');
const greetingText = document.getElementById('greeting-text');
const sidebarName = document.getElementById('sidebar-user-name');
const avatarText = document.getElementById('user-avatar-text');
const recentsList = document.getElementById('recents-list');

const chatThread = document.getElementById('chat-thread');
const greetingBlock = document.getElementById('greeting-block');
const chatTextarea = document.getElementById('chat-textarea');
const submitBtn = document.getElementById('submit-btn');
const arrowWrapper = submitBtn.querySelector('.id-arrow-wrapper');
const suggestionPills = document.querySelectorAll('.suggestion-pill');
const newChatBtn = document.getElementById('new-chat-btn');

const modelBtn = document.getElementById('model-dropdown-btn');
const modelMenu = document.getElementById('model-menu');
const currentModelText = document.getElementById('current-model');
const modelOpts = document.querySelectorAll('.model-opt');
const modeBanner = document.getElementById('mode-banner');
const modeTaglineText = document.getElementById('mode-tagline-text');

const settingsBtn = document.getElementById('settings-btn');
const settingsPanel = document.getElementById('settings-panel');
const lengthToggle = document.getElementById('length-toggle');

const attachBtn = document.getElementById('attach-btn');
const imageInput = document.getElementById('image-input');
const imagePreviewRow = document.getElementById('image-preview-row');
const imagineBtn = document.getElementById('imagine-btn');
const micBtn = document.getElementById('mic-btn');

const MODE_TAGLINES = {
  webetron: 'All-round research — fans out to every relevant source',
  open: 'Medical & health lookups — PubMed Central, ClinicalTrials.gov, OpenFDA',
  atlas: 'General chat, memory, image understanding & generation',
};

let currentModel = 'webetron';
let answerLength = 'concise'; // concise | detailed
let pendingImage = null;      // { dataUrl, mime }
let imagineActive = false;
let atlasSessionId = localStorage.getItem('clued_atlas_session') || null;
let hasStartedChat = false;

// --------------------------------------------------------------------
// Name gate
// --------------------------------------------------------------------

function initApp() {
  lucide.createIcons();
  const storedName = localStorage.getItem('clued_username');
  if (storedName) {
    initialScreen.classList.add('hidden');
    mainInterface.classList.remove('hidden');
    updateUIForUser(storedName);
  } else {
    initialScreen.classList.remove('hidden');
    mainInterface.classList.add('hidden');
    usernameInput.focus();
  }
  applyModelUI();
}

function handleUserNameSubmit() {
  const name = usernameInput.value.trim();
  if (name.length === 0) {
    usernameInput.style.border = '2px solid #ff6b6b';
    return;
  }
  usernameInput.style.border = 'none';
  localStorage.setItem('clued_username', name);
  initialScreen.classList.add('hidden');
  mainInterface.classList.remove('hidden');
  updateUIForUser(name);
}

nameSubmitBtn.addEventListener('click', handleUserNameSubmit);
usernameInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') handleUserNameSubmit();
});

function updateUIForUser(name) {
  greetingText.textContent = `What's new, ${name}?`;
  sidebarName.textContent = name;
  const initials = name.split(' ').map((n) => n[0]).join('').substring(0, 2).toUpperCase();
  avatarText.textContent = initials || 'U';
}

// --------------------------------------------------------------------
// Textarea growth + submit-button state
// --------------------------------------------------------------------

chatTextarea.addEventListener('input', () => {
  chatTextarea.style.height = 'auto';
  chatTextarea.style.height = `${chatTextarea.scrollHeight}px`;
  evaluateInputState();
});

function evaluateInputState() {
  const hasText = chatTextarea.value.trim().length > 0;
  const canSend = hasText || pendingImage;
  submitBtn.disabled = !canSend;
  if (canSend) {
    submitBtn.classList.remove('bg-clued-hover', 'cursor-not-allowed', 'border-clued-border/40');
    submitBtn.classList.add('bg-clued-accent', 'cursor-pointer', 'hover:bg-clued-accentHover', 'active:scale-95', 'border-transparent');
    arrowWrapper.classList.remove('bg-clued-text/5', 'text-clued-text/40');
    arrowWrapper.classList.add('bg-white', 'text-clued-accent', 'shadow-sm');
  } else {
    submitBtn.classList.add('bg-clued-hover', 'cursor-not-allowed', 'border-clued-border/40');
    submitBtn.classList.remove('bg-clued-accent', 'cursor-pointer', 'hover:bg-clued-accentHover', 'active:scale-95', 'border-transparent');
    arrowWrapper.classList.add('bg-clued-text/5', 'text-clued-text/40');
    arrowWrapper.classList.remove('bg-white', 'text-clued-accent', 'shadow-sm');
  }
}

suggestionPills.forEach((pill) => {
  pill.addEventListener('click', () => {
    chatTextarea.value = pill.getAttribute('data-prompt');
    chatTextarea.focus();
    chatTextarea.dispatchEvent(new Event('input'));
  });
});

// --------------------------------------------------------------------
// Model dropdown
// --------------------------------------------------------------------

modelBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  modelMenu.classList.toggle('hidden');
});

modelOpts.forEach((opt) => {
  opt.addEventListener('click', (e) => {
    e.stopPropagation();
    currentModel = opt.getAttribute('data-model');
    currentModelText.textContent = opt.querySelector('span').textContent;

    modelOpts.forEach((o) => {
      const check = o.querySelector('[data-lucide="check"]');
      if (check) check.classList.add('hidden');
    });
    const activeCheck = opt.querySelector('[data-lucide="check"]');
    if (activeCheck) activeCheck.classList.remove('hidden');

    modelMenu.classList.add('hidden');
    applyModelUI();
  });
});

window.addEventListener('click', () => {
  modelMenu.classList.add('hidden');
  settingsPanel.classList.add('hidden');
});

function applyModelUI() {
  modeBanner.textContent = MODE_TAGLINES[currentModel] || '';
  modeTaglineText.textContent = MODE_TAGLINES[currentModel] || '';
  const isAtlas = currentModel === 'atlas';
  imagineBtn.classList.toggle('hidden', !isAtlas);
  imagineBtn.classList.toggle('flex', isAtlas);
  attachBtn.title = isAtlas
    ? 'Attach an image to ask about it'
    : 'Image upload is available in Atlas mode';
  if (!isAtlas) {
    imagineActive = false;
    imagineBtn.classList.remove('bg-clued-accentMuted', 'text-clued-accent', 'border-clued-accent/40');
  }
}

// --------------------------------------------------------------------
// Settings popover (answer length)
// --------------------------------------------------------------------

settingsBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  settingsPanel.classList.toggle('hidden');
});
settingsPanel.addEventListener('click', (e) => e.stopPropagation());

lengthToggle.addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  answerLength = btn.dataset.length;
  [...lengthToggle.children].forEach((c) => c.classList.toggle('active', c === btn));
});

// --------------------------------------------------------------------
// Image attach (Atlas: ask questions about an image)
// --------------------------------------------------------------------

attachBtn.addEventListener('click', () => {
  if (currentModel !== 'atlas') {
    applyModelUI();
    modeBanner.textContent = 'Switch to Atlas mode to attach an image.';
    return;
  }
  imageInput.click();
});

imageInput.addEventListener('change', () => {
  const file = imageInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    pendingImage = { dataUrl: reader.result, mime: file.type || 'image/png' };
    renderImagePreview();
    evaluateInputState();
  };
  reader.readAsDataURL(file);
});

function renderImagePreview() {
  imagePreviewRow.innerHTML = '';
  if (!pendingImage) return;
  const chip = document.createElement('div');
  chip.className = 'image-preview-chip';
  chip.innerHTML = `<img src="${pendingImage.dataUrl}" alt="attached"><span>Image attached</span>`;
  const removeBtn = document.createElement('button');
  removeBtn.innerHTML = '&times;';
  removeBtn.addEventListener('click', () => {
    pendingImage = null;
    imageInput.value = '';
    renderImagePreview();
    evaluateInputState();
  });
  chip.appendChild(removeBtn);
  imagePreviewRow.appendChild(chip);
}

// --------------------------------------------------------------------
// Imagine (Atlas: generate images via Perchance)
// --------------------------------------------------------------------

imagineBtn.addEventListener('click', () => {
  imagineActive = !imagineActive;
  imagineBtn.classList.toggle('bg-clued-accentMuted', imagineActive);
  imagineBtn.classList.toggle('text-clued-accent', imagineActive);
  imagineBtn.classList.toggle('border-clued-accent/40', imagineActive);
  chatTextarea.placeholder = imagineActive
    ? 'Describe the image you want (via Perchance)…'
    : 'How can I help you today?';
});

// --------------------------------------------------------------------
// Voice input (native SpeechRecognition)
// --------------------------------------------------------------------

const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognizer = null;
if (SpeechRecognitionCtor) {
  recognizer = new SpeechRecognitionCtor();
  recognizer.continuous = false;
  recognizer.interimResults = false;
  recognizer.lang = 'en-US';
  recognizer.onresult = (event) => {
    chatTextarea.value = event.results[0][0].transcript;
    chatTextarea.dispatchEvent(new Event('input'));
  };
  recognizer.onend = () => micBtn.classList.remove('listening');
  recognizer.onerror = () => micBtn.classList.remove('listening');
} else {
  micBtn.disabled = true;
  micBtn.title = "Voice input isn't supported in this browser";
}

micBtn.addEventListener('click', () => {
  if (!recognizer) return;
  if (micBtn.classList.contains('listening')) {
    recognizer.stop();
    return;
  }
  micBtn.classList.add('listening');
  recognizer.start();
});

// --------------------------------------------------------------------
// Text-to-speech: VoiPi with a native speechSynthesis fallback
// --------------------------------------------------------------------

let ttsEngine = null;
let ttsMode = 'native';
let ttsController = null;
let speakingBtn = null;

async function initTTS() {
  try {
    const mod = await import('https://esm.sh/voipi@0.0.12/browser');
    ttsEngine = new mod.BrowserTTS();
    ttsMode = 'voipi';
  } catch (err) {
    ttsMode = 'native';
  }
}
initTTS();

async function toggleSpeak(text, btn) {
  if (!text) return;
  if (btn.classList.contains('speaking')) {
    stopSpeak();
    return;
  }
  stopSpeak();
  btn.classList.add('speaking');
  speakingBtn = btn;

  if (ttsMode === 'voipi' && ttsEngine) {
    ttsController = new AbortController();
    try {
      await ttsEngine.speak(text, { signal: ttsController.signal });
    } catch (err) { /* aborted or provider failed */ }
  } else if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    await new Promise((resolve) => {
      utterance.onend = resolve;
      utterance.onerror = resolve;
      window.speechSynthesis.speak(utterance);
    });
  }
  btn.classList.remove('speaking');
  ttsController = null;
  speakingBtn = null;
}

function stopSpeak() {
  if (ttsController) ttsController.abort();
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  if (speakingBtn) speakingBtn.classList.remove('speaking');
  speakingBtn = null;
}

// --------------------------------------------------------------------
// New chat
// --------------------------------------------------------------------

newChatBtn.addEventListener('click', () => {
  stopSpeak();
  chatThread.innerHTML = '';
  chatThread.classList.add('hidden');
  greetingBlock.classList.remove('hidden');
  chatTextarea.value = '';
  chatTextarea.style.height = 'auto';
  pendingImage = null;
  renderImagePreview();
  imagineActive = false;
  hasStartedChat = false;
  atlasSessionId = null;
  localStorage.removeItem('clued_atlas_session');
  evaluateInputState();
});

// --------------------------------------------------------------------
// Sending a message
// --------------------------------------------------------------------

submitBtn.addEventListener('click', () => submitMessage());
chatTextarea.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitMessage();
  }
});

function showChatView() {
  if (hasStartedChat) return;
  hasStartedChat = true;
  greetingBlock.classList.add('hidden');
  chatThread.classList.remove('hidden');
}

async function submitMessage() {
  const text = chatTextarea.value.trim();
  if (!text && !pendingImage) return;
  showChatView();

  const imageForRequest = pendingImage;
  addUserMessage(text, imageForRequest);

  chatTextarea.value = '';
  chatTextarea.style.height = 'auto';
  pendingImage = null;
  renderImagePreview();
  evaluateInputState();

  const thinkingEl = addThinkingBubble();

  try {
    if (currentModel === 'atlas' && imagineActive) {
      const data = await callImageGen(text);
      thinkingEl.remove();
      addImageGenMessage(data);
    } else if (currentModel === 'atlas') {
      const data = await callChat(text, imageForRequest);
      thinkingEl.remove();
      addAssistantMessage(data.answer, { backend: data.backend });
    } else {
      const data = await callResearch(text, currentModel);
      thinkingEl.remove();
      addAssistantMessage(applyLengthPreference(data.answer), {
        backend: data.answer_backend,
        sources: data.sources,
        warnings: data.warnings,
        domains: data.domains,
      });
    }
  } catch (err) {
    thinkingEl.remove();
    addAssistantMessage(`Something went wrong: ${err.message}. Is the Clued API running?`, { backend: 'error' });
  }
}

function applyLengthPreference(fullText) {
  if (answerLength !== 'concise') return fullText;
  const sentences = fullText.split(/(?<=[.!?])\s+/);
  return sentences.slice(0, 4).join(' ');
}

// --------------------------------------------------------------------
// API calls
// --------------------------------------------------------------------

async function callResearch(query, mode) {
  const resp = await fetch('/api/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, mode }),
  });
  if (!resp.ok) throw new Error(`request failed (${resp.status})`);
  return resp.json();
}

async function callChat(message, image) {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: atlasSessionId,
      image_data_url: image ? image.dataUrl : null,
    }),
  });
  if (!resp.ok) throw new Error(`request failed (${resp.status})`);
  const data = await resp.json();
  atlasSessionId = data.session_id;
  localStorage.setItem('clued_atlas_session', atlasSessionId);
  return data;
}

async function callImageGen(prompt) {
  const resp = await fetch('/api/imagegen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  if (!resp.ok) throw new Error(`request failed (${resp.status})`);
  return resp.json();
}

// --------------------------------------------------------------------
// Rendering the chat thread
// --------------------------------------------------------------------

const PROVIDER_ICONS = {
  web: '🌐', encyclopedia: '📖', academic: '🎓', health: '⚕️', finance: '📊', geospatial: '📍',
};
const BACKEND_LABELS = {
  openai: 'AI answer', 't5-small': 'AI answer (t5-small)', extractive: 'Extractive summary',
  identity: 'Clued', 'extractive+atlas-fallback': 'Research fallback (no OPENAI_API_KEY set)',
};

function addUserMessage(text, image) {
  const row = document.createElement('div');
  row.className = 'msg-row user';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  if (image) {
    const img = document.createElement('img');
    img.src = image.dataUrl;
    img.style.cssText = 'max-width:220px;border-radius:12px;margin-bottom:8px;display:block;';
    bubble.appendChild(img);
  }
  if (text) {
    const p = document.createElement('div');
    p.textContent = text;
    bubble.appendChild(p);
  }
  row.appendChild(bubble);
  chatThread.appendChild(row);
  scrollToBottom();
}

function addThinkingBubble() {
  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  row.innerHTML = `
    <div class="msg-avatar">C</div>
    <div class="msg-bubble"><div class="thinking-dots"><span></span><span></span><span></span></div></div>
  `;
  chatThread.appendChild(row);
  scrollToBottom();
  return row;
}

function addAssistantMessage(text, meta = {}) {
  const row = document.createElement('div');
  row.className = 'msg-row assistant';

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = 'C';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = renderMarkdown(text);

  const actions = document.createElement('div');
  actions.className = 'msg-actions';
  const speakBtn = document.createElement('button');
  speakBtn.innerHTML = '🔊 Listen';
  speakBtn.addEventListener('click', () => toggleSpeak(text, speakBtn));
  actions.appendChild(speakBtn);
  bubble.appendChild(actions);

  if (meta.warnings && meta.warnings.length) {
    meta.warnings.forEach((w) => {
      const note = document.createElement('div');
      note.className = 'warning-note';
      note.textContent = `💡 ${w}`;
      bubble.appendChild(note);
    });
  }

  if (meta.sources && meta.sources.length) {
    const cardWrap = document.createElement('div');
    cardWrap.className = 'source-cards';
    meta.sources.forEach((s) => {
      const a = document.createElement('a');
      a.className = 'source-card';
      a.href = s.url || '#';
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.innerHTML = `
        <div class="source-provider">${PROVIDER_ICONS[s.source_type] || '🔎'} ${escapeHtml(s.provider)}</div>
        <div class="source-title">${escapeHtml(s.title)}</div>
      `;
      cardWrap.appendChild(a);
    });
    bubble.appendChild(cardWrap);
  }

  const metaLine = document.createElement('div');
  metaLine.className = 'msg-meta';
  metaLine.textContent = BACKEND_LABELS[meta.backend] || meta.backend || '';
  bubble.appendChild(metaLine);

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatThread.appendChild(row);

  renderMathIn(bubble);
  scrollToBottom();
}

function addImageGenMessage(data) {
  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = 'C';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';

  if (data.ok && data.images && data.images.length) {
    const grid = document.createElement('div');
    grid.className = 'gen-image-grid';
    data.images.forEach((img) => {
      const el = document.createElement('img');
      el.src = img.url;
      el.alt = 'Generated image';
      grid.appendChild(el);
    });
    bubble.appendChild(grid);
    const caption = document.createElement('div');
    caption.className = 'gen-image-caption';
    caption.textContent = `Generated via ${data.provider}`;
    bubble.appendChild(caption);
  } else {
    bubble.textContent = data.error || 'Image generation failed.';
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatThread.appendChild(row);
  scrollToBottom();
}

function renderMarkdown(text) {
  if (window.marked && window.DOMPurify) {
    const html = marked.parse(text || '', { breaks: true, gfm: true });
    return DOMPurify.sanitize(html);
  }
  return escapeHtml(text);
}

function renderMathIn(el) {
  if (window.renderMathInElement) {
    try {
      renderMathInElement(el, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true },
        ],
        throwOnError: false,
      });
    } catch (err) { /* ignore malformed LaTeX */ }
  }
}

function scrollToBottom() {
  chatThread.scrollTop = chatThread.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

initApp();
