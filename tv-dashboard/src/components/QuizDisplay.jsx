import { useState, useEffect } from 'react';
import TeachingAgent from './TeachingAgent';

/**
 * QuizDisplay — Interactive quiz screen for TV with progress tracker,
 * question counter, topic header, and waiting animation.
 */
export default function QuizDisplay({ quizData, reviewData, teachingMessages, teachingEmotion }) {
  const [showNotice, setShowNotice] = useState(false);
  const total = quizData?.totalQuestions || 7;

  useEffect(() => {
    // Show scope popup if the AI dynamically returned less than 7 questions
    if (quizData && total < 7) {
      setShowNotice(true);
      const timer = setTimeout(() => setShowNotice(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [quizData?.topic, total]);

  if (!quizData?.currentQuestion) {
    return (
      <div className="quiz-display-with-agent">
        <div className="quiz-main-area">
          <div className="quiz-container">
            <div className="quiz-question-card">
              <div className="quiz-question-number">Quiz Starting...</div>
              <div className="quiz-question-text" style={{ fontSize: '24px', color: 'var(--text-secondary)' }}>
                {quizData?.topic || 'Loading quiz...'}
              </div>
              <div className="quiz-waiting">
                Preparing questions <span className="loading-dots"><span></span><span></span><span></span></span>
              </div>
            </div>
          </div>
        </div>
        <TeachingAgent messages={teachingMessages} currentEmotion={teachingEmotion} />
      </div>
    );
  }

  const { number, text, topic, kidAnswer, momExplanation } = quizData.currentQuestion;
  const results = quizData.results || [];
  const isRevealed = quizData.revealAnswer;

  // Build progress dots
  const progressDots = [];
  for (let i = 1; i <= total; i++) {
    let status = 'pending';
    if (i < number) {
      const result = results[i - 1];
      if (result?.correct) status = 'correct';
      else if (result?.skipped) status = 'skipped';
      else status = 'wrong';
    } else if (i === number) {
      status = 'current';
    }
    progressDots.push(status);
  }

  return (
    <div className="quiz-display-with-agent">
      <div className="quiz-main-area">
        <div className="quiz-container">
          {/* Quiz Header Bar */}
          <div className="quiz-header">
            <div className="quiz-header-left">
              <span className="quiz-topic-badge">📝 {topic}</span>
            </div>
            <div className="quiz-header-right">
              <span className="quiz-counter">Question {number} of {total}</span>
            </div>
          </div>

          {/* Scope Analysis Popup */}
          {showNotice && (
            <div className="quiz-scope-popup">
              ℹ️ <b>Topic Analysed:</b> Only {total} questions required for this topic based on exam scope.
            </div>
          )}

          {/* Quiz Body Layout Container */}
          <div className="quiz-body-wrapper">

            {/* Progress Tracker (Now Vertical on Left) */}
            <div className="quiz-progress-track">
              {progressDots.map((status, i) => (
                <div key={i} className="quiz-progress-segment">
                  <div className={`quiz-progress-dot ${status}`}>
                    <div className="quiz-progress-dot-inner">
                      {status === 'correct' && '✓'}
                      {status === 'wrong' && '✗'}
                      {status === 'skipped' && '—'}
                      {status === 'current' && (i + 1)}
                      {status === 'pending' && (i + 1)}
                    </div>
                  </div>
                  {i < total - 1 && <div className={`quiz-progress-line ${status !== 'pending' && status !== 'current' ? 'done' : ''}`} />}
                </div>
              ))}
            </div>

            {/* Main Content Area */}
            <div className="quiz-content-stack">
              {/* Question Card */}
              <div className="quiz-question-card stacked-card">
                <div className="quiz-question-number">Question {number}</div>
                <div className="quiz-question-text">{text}</div>
                {!isRevealed && !reviewData && (
                  <div className="quiz-waiting margin-top-auto">
                    Waiting for answer on Telegram <span className="loading-dots"><span></span><span></span><span></span></span>
                  </div>
                )}
              </div>

              {/* Answer Card */}
              <div className={`quiz-answer-card stacked-card ${(!isRevealed && !reviewData) ? 'blurred-state' : 'revealed-state'}`}>
                {(!isRevealed && !reviewData) && (
                  <div className="lock-overlay">
                    <span>🔒 Answer Locked</span>
                  </div>
                )}

                {/* Permanent Evaluation Section */}
                {reviewData && (
                  <div className={`evaluation-stick ${reviewData.correct ? 'eval-correct' : 'eval-wrong'}`}>
                    <div className="eval-emoji">{reviewData.avatar || (reviewData.correct ? '✅' : '❌')}</div>
                    <div className="eval-text">
                      <span className="eval-status">{reviewData.correct ? 'Correct!' : 'Incorrect'}</span>
                      <p className="eval-feedback">{reviewData.feedback}</p>
                    </div>
                  </div>
                )}

                <div className="answer-section">
                  <h3 className="answer-title">✅ Kid's Answer</h3>
                  <p className="answer-text">{kidAnswer || "..."}</p>
                </div>
                <div className="explainer-section">
                  <h3 className="explainer-title">👩‍🏫 Mom's Explainer</h3>
                  <p className="explainer-text">{momExplanation || "..."}</p>
                </div>
              </div>
            </div>
            {/* End wrappers */}
          </div>
          {/* Score so far */}
          {results.length > 0 && (
            <div className="quiz-live-score">
              <span className="quiz-score-correct">✅ {results.filter(r => r?.correct).length}</span>
              <span className="quiz-score-wrong">❌ {results.filter(r => !r?.correct && !r?.skipped).length}</span>
              {results.some(r => r?.skipped) && (
                <span className="quiz-score-skipped">⏭ {results.filter(r => r?.skipped).length}</span>
              )}
            </div>
          )}
        </div>
      </div>
      <TeachingAgent messages={teachingMessages} currentEmotion={teachingEmotion} />
    </div>
  );
}
