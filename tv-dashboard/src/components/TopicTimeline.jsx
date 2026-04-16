/**
 * TopicTimeline — left panel showing scrollable topic history
 * plus a chapter overview showing NCERT syllabus progress.
 * Color-coded by subject (purple = Math, green = Science).
 */
export default function TopicTimeline({ topics, newTopicId, progress }) {
  // Sort by date descending
  const sortedTopics = [...topics].sort((a, b) => 
    new Date(b.date) - new Date(a.date)
  );

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[d.getMonth()]} ${d.getDate()}`;
  };

  const isMath = (subject) => subject?.toLowerCase() === 'mathematics';

  // Build chapter overview from progress data
  const mathChapters = progress?.Mathematics?.chapters || [];
  const scienceChapters = progress?.Science?.chapters || [];

  // Find active chapters (in_progress or covered)
  const getChapterStatus = (chapters) => {
    const active = chapters.filter(ch => ch.status === 'in_progress');
    const covered = chapters.filter(ch => ch.status === 'covered');
    const next = chapters.find(ch => ch.status === 'not_started');
    return { active, covered, next, total: chapters.length };
  };

  const mathStatus = getChapterStatus(mathChapters);
  const scienceStatus = getChapterStatus(scienceChapters);

  return (
    <aside className="timeline-panel">
      {/* Topic Timeline Section — grouped by chapter */}
      <h2 className="timeline-title">📅 Recent Topics</h2>
      
      {sortedTopics.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
          No topics yet. Send a homework photo on Telegram!
        </p>
      )}

      {(() => {
        // Group topics by chapter
        const grouped = {};
        sortedTopics.forEach(topic => {
          const key = topic.chapter || 'Other';
          if (!grouped[key]) {
            grouped[key] = { chapter: topic.chapter, subject: topic.subject, topics: [] };
          }
          grouped[key].topics.push(topic);
        });

        return Object.values(grouped).map((group, gIndex) => (
          <div key={group.chapter || gIndex} className="timeline-chapter-group">
            <div className={`timeline-chapter-header ${isMath(group.subject) ? '' : 'science'}`}>
              <div className={`timeline-dot ${!isMath(group.subject) ? 'science' : ''}`} />
              <span className="timeline-chapter-name">{group.chapter}</span>
              <span className="timeline-chapter-count">{group.topics.length}</span>
            </div>
            {group.topics.map((topic, tIndex) => (
              <div 
                key={topic.id || tIndex} 
                className={`timeline-subtopic ${topic.id === newTopicId ? 'new' : ''}`}
              >
                <span className="timeline-date">{formatDate(topic.date)}</span>
                <div className="timeline-topic">{topic.topic}</div>
                {topic.exercises && (
                  <div className="timeline-exercises">{topic.exercises}</div>
                )}
              </div>
            ))}
          </div>
        ));
      })()}

      {/* Divider */}
      <div className="timeline-divider" />

      {/* Chapter Overview Section */}
      <div className="chapter-overview">
        <h2 className="timeline-title">📖 NCERT Syllabus</h2>
        
        {/* Math Overview */}
        {mathChapters.length > 0 && (
          <div className="chapter-subject-block">
            <div className="chapter-subject-header math">
              <span className="chapter-subject-icon">📐</span>
              <span className="chapter-subject-name">Mathematics</span>
              <span className="chapter-subject-count">
                {mathStatus.covered.length + mathStatus.active.length}/{mathStatus.total}
              </span>
            </div>
            <div className="chapter-list">
              {mathChapters.map((ch) => (
                <div 
                  key={ch.number} 
                  className={`chapter-item ${ch.status}`}
                  title={`Ch ${ch.number}: ${ch.name}`}
                >
                  <span className={`chapter-dot ${ch.status}`} />
                  <span className="chapter-number">Ch {ch.number}</span>
                  <span className="chapter-name">{ch.name}</span>
                  {ch.status === 'in_progress' && <span className="chapter-badge">NOW</span>}
                  {ch.status === 'covered' && <span className="chapter-check">✓</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Science Overview */}
        {scienceChapters.length > 0 && (
          <div className="chapter-subject-block">
            <div className="chapter-subject-header science">
              <span className="chapter-subject-icon">🔬</span>
              <span className="chapter-subject-name">Science</span>
              <span className="chapter-subject-count">
                {scienceStatus.covered.length + scienceStatus.active.length}/{scienceStatus.total}
              </span>
            </div>
            <div className="chapter-list">
              {scienceChapters.map((ch) => (
                <div 
                  key={ch.number} 
                  className={`chapter-item ${ch.status}`}
                  title={`Ch ${ch.number}: ${ch.name}`}
                >
                  <span className={`chapter-dot ${ch.status}`} />
                  <span className="chapter-number">Ch {ch.number}</span>
                  <span className="chapter-name">{ch.name}</span>
                  {ch.status === 'in_progress' && <span className="chapter-badge">NOW</span>}
                  {ch.status === 'covered' && <span className="chapter-check">✓</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
