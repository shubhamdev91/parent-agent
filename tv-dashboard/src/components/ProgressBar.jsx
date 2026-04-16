/**
 * ProgressBar — bottom bar showing chapter completion for Math and Science.
 */
export default function ProgressBar({ progress }) {
  const math = progress?.Mathematics || { covered: 0, total: 14 };
  const science = progress?.Science || { covered: 0, total: 13 };

  const mathPercent = (math.covered / math.total) * 100;
  const sciencePercent = (science.covered / science.total) * 100;

  return (
    <footer className="progress-bar-container">
      <div className="progress-subject">
        <span className="progress-label">📐 Math</span>
        <div className="progress-track">
          <div 
            className="progress-fill math" 
            style={{ width: `${mathPercent}%` }}
          />
        </div>
        <span className="progress-count">{math.covered}/{math.total}</span>
      </div>
      
      <div className="progress-subject">
        <span className="progress-label">🔬 Science</span>
        <div className="progress-track">
          <div 
            className="progress-fill science" 
            style={{ width: `${sciencePercent}%` }}
          />
        </div>
        <span className="progress-count">{science.covered}/{science.total}</span>
      </div>
    </footer>
  );
}
