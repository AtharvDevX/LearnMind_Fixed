(() => {
  const subjectSelect = document.getElementById('quizSubject');
  const loadButton = document.getElementById('loadQuizBtn');
  const resetButton = document.getElementById('resetQuizBtn');
  const retryButton = document.getElementById('retryQuizBtn');
  const form = document.getElementById('quizForm');
  const panel = document.getElementById('quizPanel');
  const result = document.getElementById('quizResult');
  const questionList = document.getElementById('questionList');
  const notice = document.getElementById('quizNotice');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  let activeQuestions = [];

  function showNotice(message, warning = false) {
    notice.textContent = message;
    notice.classList.remove('hidden', 'notice-warning');
    if (warning) notice.classList.add('notice-warning');
  }
  function clearNotice() { notice.textContent = ''; notice.classList.add('hidden'); }

  async function loadQuiz() {
    const subject = subjectSelect.value;
    if (!subject) { showNotice('Choose a supported subject first.', true); return; }
    loadButton.disabled = true;
    loadButton.textContent = 'Loading…';
    clearNotice();
    try {
      const response = await fetch(`/api/quiz/questions?subject=${encodeURIComponent(subject)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not load this quiz.');
      activeQuestions = data.questions;
      document.getElementById('quizTitle').textContent = `${data.subject} · Practice Quiz`;
      document.getElementById('questionCount').textContent = `${activeQuestions.length} questions`;
      renderQuestions();
      panel.classList.remove('hidden');
      result.classList.add('hidden');
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
      showNotice(error.message, true);
    } finally {
      loadButton.disabled = false;
      loadButton.textContent = 'Load quiz →';
    }
  }

  function renderQuestions() {
    questionList.replaceChildren();
    activeQuestions.forEach((question, index) => {
      const article = document.createElement('article');
      article.className = 'quiz-question';
      const title = document.createElement('h3');
      title.textContent = `${index + 1}. ${question.question}`;
      article.appendChild(title);
      const topic = document.createElement('div');
      topic.className = 'question-topic';
      topic.textContent = question.topic;
      article.appendChild(topic);
      const options = document.createElement('div');
      options.className = 'quiz-options';
      question.options.forEach((option, optionIndex) => {
        const label = document.createElement('label');
        label.className = 'quiz-option';
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = `question-${index}`;
        radio.value = String(optionIndex);
        radio.required = true;
        const text = document.createElement('span');
        text.textContent = option;
        label.append(radio, text);
        options.appendChild(label);
      });
      article.append(topic, options);
      questionList.appendChild(article);
    });
  }

  function resetQuiz() {
    form.reset();
    result.classList.add('hidden');
    questionList.querySelectorAll('.quiz-option').forEach(option => option.classList.remove('selected'));
  }

  questionList.addEventListener('change', event => {
    if (event.target.matches('input[type="radio"]')) {
      const group = event.target.name;
      questionList.querySelectorAll(`input[name="${group}"]`).forEach(input => input.closest('.quiz-option')?.classList.toggle('selected', input.checked));
    }
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const answers = activeQuestions.map((_, index) => form.querySelector(`input[name="question-${index}"]:checked`)?.value);
    if (answers.some(answer => answer === undefined)) {
      showNotice('Please answer all questions before submitting.', true);
      return;
    }
    const submitButton = document.getElementById('submitQuizBtn');
    submitButton.disabled = true;
    submitButton.textContent = 'Checking answers…';
    clearNotice();
    try {
      const response = await fetch('/api/quiz/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: JSON.stringify({ subject: subjectSelect.value, answers })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not submit your assessment.');
      renderResult(data);
    } catch (error) {
      showNotice(error.message, true);
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = 'Submit assessment →';
    }
  });

  function renderResult(data) {
    document.getElementById('resultScore').textContent = `${data.score}/${data.total}`;
    document.getElementById('resultPercent').textContent = `${data.percentage}%`;
    document.getElementById('resultMessage').textContent = data.message;
    const review = document.getElementById('resultReview');
    review.replaceChildren();
    data.details.forEach((detail, index) => {
      const row = document.createElement('article');
      row.className = `review-item ${detail.correct ? 'review-correct' : 'review-incorrect'}`;
      const heading = document.createElement('b');
      heading.textContent = `${index + 1}. ${detail.topic} — ${detail.correct ? 'Correct' : 'Review this topic'}`;
      const answer = document.createElement('p');
      answer.textContent = detail.correct ? `Your answer: ${detail.selected}` : `Your answer: ${detail.selected} · Correct answer: ${detail.correct_answer}`;
      const explanation = document.createElement('small');
      explanation.textContent = detail.explanation;
      row.append(heading, answer, explanation);
      review.appendChild(row);
    });
    panel.classList.add('hidden');
    result.classList.remove('hidden');
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  loadButton.addEventListener('click', loadQuiz);
  subjectSelect.addEventListener('change', () => { panel.classList.add('hidden'); result.classList.add('hidden'); clearNotice(); });
  resetButton.addEventListener('click', resetQuiz);
  retryButton.addEventListener('click', () => { resetQuiz(); panel.classList.remove('hidden'); panel.scrollIntoView({ behavior: 'smooth' }); });
  if (subjectSelect.options.length) loadQuiz();
})();
