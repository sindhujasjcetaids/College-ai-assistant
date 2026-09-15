// Campus Desk — chat frontend logic

const messagesEl = document.getElementById('messages');
const composerEl = document.getElementById('composer');
const inputEl = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const resetBtn = document.getElementById('reset-btn');
const statusPill = document.getElementById('status-pill');

const CATEGORY_CLASS = {
  'Regulations': 'regulations',
  'Syllabus': 'syllabus',
  'FAQ': 'faq',
  'Notice': 'notice',
};

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderUserMessage(text) {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-user';
  wrap.innerHTML = `
    <div class="msg-avatar">You</div>
    <div class="msg-body">${escapeHtml(text)}</div>
  `;
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

function renderTypingIndicator() {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-assistant';
  wrap.id = 'typing-indicator';
  wrap.innerHTML = `
    <div class="msg-avatar">CD</div>
    <div class="msg-body">
      <div class="typing"><span></span><span></span><span></span></div>
    </div>
  `;
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function toolLabel(toolUsed) {
  const labels = {
    gpa_calculator: 'GPA Calculator',
    attendance_calculator: 'Attendance Calculator',
    date_tool: 'Date Lookup',
    rag: 'Knowledge Base',
  };
  return labels[toolUsed] || null;
}

function renderAssistantMessage(payload) {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-assistant';

  const label = toolLabel(payload.tool_used);
  const tagHtml = label ? `<span class="msg-tool-tag">${escapeHtml(label)}</span><br/>` : '';

  let sourcesHtml = '';
  if (payload.sources && payload.sources.length) {
    const items = payload.sources.map(s => {
      const cls = CATEGORY_CLASS[s.category] || 'faq';
      return `<div class="source-item">
                <span class="source-cat ${cls}">${escapeHtml(s.category)}</span>
                <span>${escapeHtml(s.snippet)}</span>
              </div>`;
    }).join('');
    sourcesHtml = `<div class="sources">${items}</div>`;
  }

  wrap.innerHTML = `
    <div class="msg-avatar">CD</div>
    <div class="msg-body">
      ${tagHtml}
      <p>${escapeHtml(payload.answer).replace(/\n/g, '<br/>')}</p>
      ${sourcesHtml}
    </div>
  `;
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

async function sendMessage(text) {
  if (!text.trim()) return;

  renderUserMessage(text);
  inputEl.value = '';
  autoResize();
  sendBtn.disabled = true;
  renderTypingIndicator();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    removeTypingIndicator();

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      renderAssistantMessage({ answer: err.error || 'Something went wrong. Please try again.', sources: [] });
      setStatus(false);
      return;
    }

    const data = await res.json();
    renderAssistantMessage(data);
    setStatus(true);
  } catch (e) {
    removeTypingIndicator();
    renderAssistantMessage({ answer: 'I couldn\'t reach the server. Please check your connection and try again.', sources: [] });
    setStatus(false);
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

function setStatus(ok) {
  if (ok) {
    statusPill.textContent = '● Knowledge base ready';
    statusPill.classList.remove('error');
  } else {
    statusPill.textContent = '● Connection issue';
    statusPill.classList.add('error');
  }
}

function autoResize() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
}

composerEl.addEventListener('submit', (e) => {
  e.preventDefault();
  sendMessage(inputEl.value);
});

inputEl.addEventListener('input', autoResize);

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(inputEl.value);
  }
});

document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const prompt = chip.getAttribute('data-prompt');
    sendMessage(prompt);
  });
});

resetBtn.addEventListener('click', async () => {
  await fetch('/api/reset', { method: 'POST' });
  messagesEl.innerHTML = `
    <div class="msg msg-assistant">
      <div class="msg-avatar">CD</div>
      <div class="msg-body">
        <p>Conversation cleared. What would you like to know?</p>
      </div>
    </div>
  `;
});

// health check on load
fetch('/api/health').then(r => r.json()).then(d => {
  if (d.status === 'ok') setStatus(true);
}).catch(() => setStatus(false));
