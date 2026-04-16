/**
 * ActiveArea — right panel state machine.
 * Switches between: idle, quiz, review, visual, summary
 */
import QuizDisplay from './QuizDisplay';
import AvatarReaction from './AvatarReaction';
import VisualExplainer from './VisualExplainer';
import SummaryCard from './SummaryCard';

export default function ActiveArea({ activeState, quizData, reviewData, visualData, summaryData, lastTopic, teachingMessages, teachingEmotion }) {
  
  // Idle state
  if (activeState === 'idle') {
    return (
      <div className="active-area">
        <div className="idle-state">
          <div className="idle-emoji">📚</div>
          <h2 className="idle-title">
            {lastTopic 
              ? `Last topic: ${lastTopic.topic}`
              : 'kramm Ready!'
            }
          </h2>
          <p className="idle-subtitle">
            {lastTopic
              ? 'Choose a quiz or explanation on Telegram'
              : 'Send a homework photo on Telegram to get started'
            }
          </p>
        </div>
      </div>
    );
  }

  // Quiz — showing a question
  if (activeState === 'quiz') {
    return (
      <div className="active-area">
        <QuizDisplay quizData={quizData} teachingMessages={teachingMessages} teachingEmotion={teachingEmotion} />
      </div>
    );
  }

  // Review — showing question eval after answer
  if (activeState === 'review') {
    return (
      <div className="active-area">
        {quizData && <QuizDisplay quizData={quizData} reviewData={reviewData} teachingMessages={teachingMessages} teachingEmotion={teachingEmotion} />}
      </div>
    );
  }

  // Visual — showing AI-generated visual explanation
  if (activeState === 'visual') {
    return (
      <div className="active-area">
        <VisualExplainer visualData={visualData} />
      </div>
    );
  }

  // Summary — post-quiz score card
  if (activeState === 'summary') {
    return (
      <div className="active-area">
        <SummaryCard summaryData={summaryData} />
      </div>
    );
  }

  // Fallback
  return (
    <div className="active-area">
      <div className="idle-state">
        <div className="idle-emoji">⏳</div>
        <h2 className="idle-title">Loading...</h2>
      </div>
    </div>
  );
}
