import { useState } from 'react';

function getNodeClass(status) {
  return { tested_in_quiz: 'tested', covered_in_class: 'covered', not_started: 'not-started', in_progress: 'in-progress' }[status] || 'not-started';
}

function ChapterNode({ chapter, onSelect }) {
  return (
    <div className="chapter-node" onClick={() => onSelect(chapter)}>
      <div className={`node-circle ${getNodeClass(chapter.status)}`}>
        {chapter.chapter_number}
      </div>
      <div className="chapter-label">{chapter.name.split(':')[0]}</div>
    </div>
  );
}

function ChapterDetailPanel({ chapter, onClose }) {
  return (
    <div className="detail-panel">
      <div className="detail-header">
        <h2>{chapter.name}</h2>
        <button onClick={onClose}>✕</button>
      </div>
      <section className="topics-section">
        <h3>Topics Covered</h3>
        {chapter.topics_covered.length === 0 && <p style={{color:'#6B7280'}}>None yet</p>}
        {chapter.topics_covered.map((t, i) => (
          <div key={i} className="topic-item">
            <span>{t.name}</span>
            <span className="topic-date">{t.date}</span>
          </div>
        ))}
      </section>
      <section className="quizzes-section">
        <h3>Quizzes Taken</h3>
        {chapter.quizzes.length === 0 && <p style={{color:'#6B7280'}}>None yet</p>}
        {chapter.quizzes.map((q, i) => (
          <div key={i} className="quiz-button">
            <span className="quiz-date">{q.date}</span>
            <span className="quiz-score">{q.score}</span>
          </div>
        ))}
      </section>
    </div>
  );
}

export default function CurriculumTimeline({ data }) {
  const [expanded, setExpanded] = useState(null);
  if (!data) return <div className="analytics-loading">Loading curriculum data...</div>;
  return (
    <div className="curriculum-timeline">
      <div className="timeline-track math-track">
        <div className="track-label">📐 Math</div>
        {(data.math || []).map(ch => (
          <ChapterNode key={ch.chapter_number} chapter={ch} onSelect={setExpanded} />
        ))}
      </div>
      <div className="timeline-track science-track">
        <div className="track-label">🔬 Science</div>
        {(data.science || []).map(ch => (
          <ChapterNode key={ch.chapter_number} chapter={ch} onSelect={setExpanded} />
        ))}
      </div>
      {expanded && <ChapterDetailPanel chapter={expanded} onClose={() => setExpanded(null)} />}
    </div>
  );
}
