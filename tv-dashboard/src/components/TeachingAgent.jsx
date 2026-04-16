import { useRef, useEffect } from 'react';

const AVATAR_MAP = {
  neutral: "🧑‍🏫", thinking: "🤔", happy: "😊",
  celebrating: "🎉", encouraging: "💪", concerned: "😟",
  teaching: "📚", hint: "💡", proud: "🌟", supportive: "🤗"
};

export default function TeachingAgent({ messages = [], currentEmotion = "neutral" }) {
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="teaching-agent-panel">
      <div className="agent-avatar-section">
        <div className="avatar-emoji" key={currentEmotion}>
          {AVATAR_MAP[currentEmotion] || "🧑‍🏫"}
        </div>
        <div className="agent-name">Kramm</div>
      </div>
      <div className="agent-chat-window">
        {messages.length === 0 && (
          <div className="chat-bubble agent">
            <span className="bubble-emoji">🧑‍🏫</span>
            <p className="bubble-text">Hey Ridham! Ready to learn? Let's go!</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className="chat-bubble agent">
            <span className="bubble-emoji">{AVATAR_MAP[msg.emotion] || "🧑‍🏫"}</span>
            <p className="bubble-text">{msg.text}</p>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
    </div>
  );
}
