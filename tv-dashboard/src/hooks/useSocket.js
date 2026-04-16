import { useEffect, useState, useCallback, useRef } from 'react';
import { io } from 'socket.io-client';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

/**
 * Custom hook for Socket.IO connection to the kramm backend.
 * Manages connection state and provides event listeners.
 */
export function useSocket() {
  const [connected, setConnected] = useState(false);
  const [activeState, setActiveState] = useState('idle'); // idle, quiz, review, visual, summary
  const [quizData, setQuizData] = useState(null);
  const [reviewData, setReviewData] = useState(null);
  const [visualData, setVisualData] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  const [topics, setTopics] = useState([]);
  const [newTopicId, setNewTopicId] = useState(null);
  const socketRef = useRef(null);

  useEffect(() => {
    const socket = io(BACKEND_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: Infinity,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('Connected to kramm backend');
      setConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('📺 Disconnected from backend');
      setConnected(false);
    });

    // --- Topic Events ---
    socket.on('topic_added', (data) => {
      console.log('📡 topic_added:', data);
      setTopics(prev => [data, ...prev]);
      setNewTopicId(data.id);
      // Clear "new" highlight after animation
      setTimeout(() => setNewTopicId(null), 2000);
    });

    socket.on('timeline_refresh', (data) => {
      console.log('📡 timeline_refresh:', data.topics?.length, 'topics');
      setTopics(data.topics || []);
    });

    // --- Quiz Events ---
    socket.on('quiz_start', (data) => {
      console.log('📡 quiz_start:', data);
      setActiveState('quiz');
      setQuizData({
        topic: data.topic,
        totalQuestions: data.totalQuestions,
        currentQuestion: null,
      });
      setReviewData(null);
      setSummaryData(null);
    });

    socket.on('quiz_question', (data) => {
      console.log('📡 quiz_question:', data);
      setActiveState('quiz');
      setQuizData(prev => ({
        ...prev,
        currentQuestion: {
          number: data.questionNumber,
          text: data.question,
          topic: data.topic,
          kidAnswer: data.kidAnswer,
          momExplanation: data.momExplanation
        },
        revealAnswer: false
      }));
      setReviewData(null);
    });

    socket.on('quiz_reveal', (data) => {
      console.log('📡 quiz_reveal:', data);
      setQuizData(prev => ({
        ...prev,
        revealAnswer: true
      }));
    });

    socket.on('quiz_answer_result', (data) => {
      console.log('📡 quiz_answer_result:', data);
      setActiveState('review');
      setReviewData({
        correct: data.correct,
        feedback: data.feedback,
        avatar: data.avatar,
        questionNumber: data.questionNumber,
      });
      // Also update quizData with accumulated results
      setQuizData(prev => ({
        ...prev,
        results: [...(prev?.results || []), {
          correct: data.correct,
          questionNumber: data.questionNumber,
        }],
        revealAnswer: true
      }));
    });

    socket.on('quiz_complete', (data) => {
      console.log('📡 quiz_complete:', data);
      setActiveState('summary');
      setSummaryData({
        score: data.score,
        total: data.total,
        breakdown: data.breakdown || [],
        weakAreas: data.weakAreas || [],
      });
      // Auto-return to idle after 15 seconds
      setTimeout(() => {
        setActiveState('idle');
        setSummaryData(null);
      }, 15000);
    });

    // --- Visual Events ---
    socket.on('show_visual', (data) => {
      console.log('📡 show_visual:', data);
      setActiveState('visual');
      setVisualData({
        topic: data.topic,
        htmlContent: data.htmlContent,
      });
    });

    // --- Idle Event ---
    socket.on('idle', () => {
      console.log('📡 idle');
      setActiveState('idle');
      setQuizData(null);
      setReviewData(null);
      setVisualData(null);
      setSummaryData(null);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  return {
    connected,
    activeState,
    quizData,
    reviewData,
    visualData,
    summaryData,
    topics,
    setTopics,
    newTopicId,
  };
}
