/**
 * SummaryCard — post-quiz score ring, breakdown, and weak areas.
 */
export default function SummaryCard({ summaryData }) {
  if (!summaryData) return null;

  const { score, total, breakdown, weakAreas } = summaryData;
  const percentage = total > 0 ? (score / total) * 100 : 0;
  
  // SVG ring calculations
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;
  
  // Color based on score
  const scoreColor = percentage >= 80 ? 'var(--green)' : 
                     percentage >= 50 ? 'var(--amber)' : 'var(--red)';

  const emoji = percentage >= 80 ? '🎉' : percentage >= 50 ? '💪' : '📚';

  return (
    <div className="summary-container">
      <div className="summary-card">
        <h2 className="summary-title">{emoji} Quiz Complete!</h2>
        
        {/* Score Ring */}
        <div className="summary-score-ring">
          <svg viewBox="0 0 140 140">
            <circle className="ring-bg" cx="70" cy="70" r={radius} />
            <circle 
              className="ring-progress" 
              cx="70" cy="70" r={radius}
              style={{
                stroke: scoreColor,
                strokeDasharray: circumference,
                strokeDashoffset: offset,
              }}
            />
          </svg>
          <span className="summary-score-text">{score}/{total}</span>
        </div>

        {/* Breakdown */}
        {breakdown.length > 0 && (
          <div className="summary-breakdown">
            {breakdown.map((item, i) => (
              <div key={i} className="summary-breakdown-item">
                <span className="summary-breakdown-icon">
                  {item.correct ? '✅' : item.skipped ? '⏭️' : '❌'}
                </span>
                <span className="summary-breakdown-text">
                  {item.question?.substring(0, 60)}
                  {item.question?.length > 60 ? '...' : ''}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Weak Areas */}
        {weakAreas.length > 0 && (
          <div className="summary-weak-areas">
            <h3 className="summary-weak-title">📌 Focus Areas</h3>
            {weakAreas.map((area, i) => (
              <p key={i} className="summary-weak-item">• {area}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
