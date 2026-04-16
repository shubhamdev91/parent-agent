import { useEffect, useState } from 'react';
import './index.css';
import { useSocket } from './hooks/useSocket';
import Header from './components/Header';
import TopicTimeline from './components/TopicTimeline';
import ActiveArea from './components/ActiveArea';
import ProgressBar from './components/ProgressBar';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

function App() {
  const {
    connected,
    activeState,
    quizData,
    reviewData,
    visualData,
    summaryData,
    topics,
    setTopics,
    newTopicId,
    teachingMessages,
    teachingEmotion,
  } = useSocket();

  const [student, setStudent] = useState(null);
  const [progress, setProgress] = useState(null);

  // Fetch initial profile data on mount
  useEffect(() => {
    fetch(`${BACKEND_URL}/api/profile`)
      .then(res => res.json())
      .then(data => {
        setStudent(data.student);
        setTopics(data.topics || []);
        setProgress(data.progress || null);
      })
      .catch(err => {
        console.error('Failed to fetch profile:', err);
        // Use fallback data
        setStudent({
          name: 'Ridham Aggarwal',
          class: 'X-B',
          board: 'CBSE',
          school: 'Ahlcon International School'
        });
      });
  }, []);

  // Get last topic for idle state display
  const sortedTopics = [...topics].sort((a, b) => 
    new Date(b.date) - new Date(a.date)
  );
  const lastTopic = sortedTopics[0] || null;

  return (
    <div className="app-container">
      <Header student={student} connected={connected} />
      
      <div className="main-content">
        <TopicTimeline topics={topics} newTopicId={newTopicId} progress={progress} />
        <ActiveArea
          activeState={activeState}
          quizData={quizData}
          reviewData={reviewData}
          visualData={visualData}
          summaryData={summaryData}
          lastTopic={lastTopic}
          teachingMessages={teachingMessages}
          teachingEmotion={teachingEmotion}
        />
      </div>

      <ProgressBar progress={progress} />
    </div>
  );
}

export default App;
