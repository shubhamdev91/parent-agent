export default function ViewToggle({ activeView, onViewChange }) {
  return (
    <div className="view-toggle-container">
      <button
        className={`toggle-btn ${activeView === 'live' ? 'active' : ''}`}
        onClick={() => onViewChange('live')}
      >
        Live Mode
      </button>
      <button
        className={`toggle-btn ${activeView === 'analytics' ? 'active' : ''}`}
        onClick={() => onViewChange('analytics')}
      >
        Analytics
      </button>
    </div>
  );
}
