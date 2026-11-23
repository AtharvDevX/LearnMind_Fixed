(() => {
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatQuestion');
  const messages = document.getElementById('chatMessages');
  const sendButton = document.getElementById('chatSendBtn');
  const clearButton = document.getElementById('clearChatBtn');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';

  function addMessage(role, content, animate = false) {
    const wrap = document.createElement('div');
    wrap.className = `chat-message ${role === 'user' ? 'chat-user' : 'chat-assistant'}`;
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.textContent = content;
    if (animate) bubble.classList.add('typing-bubble');
    const meta = document.createElement('small');
    meta.textContent = role === 'user' ? 'You' : 'LearnMind AI';
    wrap.append(bubble, meta);
    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  async function loadHistory() {
    try {
      const response = await fetch('/api/chat/history');
      const data = await response.json();
      messages.replaceChildren();
      if (!data.messages?.length) {
        addMessage('assistant', 'Hello! 👋 I am your LearnMind study assistant. Ask me about your subjects, programming, concepts or exam preparation.');
      } else {
        data.messages.forEach(message => addMessage(message.role, message.content));
      }
    } catch (_error) {
      messages.replaceChildren();
      addMessage('assistant', 'Welcome to LearnMind AI. Send a question to begin.');
    }
  }

  async function sendQuestion(question) {
    if (!question || sendButton.disabled) return;
    addMessage('user', question);
    input.value = '';
    input.style.height = 'auto';
    sendButton.disabled = true;
    sendButton.innerHTML = 'Thinking…';
    const pending = addMessage('assistant', 'Thinking through your question…', true);
    try {
      const response = await fetch('/api/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: JSON.stringify({ question })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'The assistant could not answer.');
      pending.textContent = data.answer;
      pending.classList.remove('typing-bubble');
    } catch (error) {
      pending.textContent = `I couldn't complete that request. ${error.message}`;
      pending.classList.remove('typing-bubble');
      pending.closest('.chat-message')?.classList.add('chat-error');
    } finally {
      sendButton.disabled = false;
      sendButton.innerHTML = 'Send <span>➤</span>';
      input.focus();
      messages.scrollTop = messages.scrollHeight;
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    sendQuestion(input.value.trim());
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
  });
  document.querySelectorAll('.chat-suggestions button').forEach(button => {
    button.addEventListener('click', () => { input.value = button.dataset.prompt || ''; input.focus(); input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 140)}px`; });
  });
  clearButton.addEventListener('click', async () => {
    if (!window.confirm('Clear your saved LearnMind AI conversation?')) return;
    clearButton.disabled = true;
    try {
      const response = await fetch('/api/chat/clear', { method: 'POST', headers: { 'X-CSRF-Token': csrf } });
      if (!response.ok) throw new Error('Unable to clear conversation.');
      await loadHistory();
    } catch (error) { window.alert(error.message); }
    finally { clearButton.disabled = false; }
  });
  loadHistory();
})();
