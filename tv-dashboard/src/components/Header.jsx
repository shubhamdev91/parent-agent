/**
 * Header component — kramm brand prominently displayed, student info secondary.
 */
export default function Header({ student, connected }) {
  return (
    <header className="header">
      <div className="header-brand">
        <svg
          className="header-kramm-logo"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ width: '30px', height: '30px', color: '#ffffff' }}
        >
          <path d="M12 2 L2 7 l10 5 10 -5 -10 -5 Z" />
          <path d="M2 17 l10 5 10 -5" />
          <path d="M2 12 l10 5 10 -5" />
        </svg>
        <span className="header-kramm-name">kramm</span>
        <span className="header-tagline">Mom's Teaching Partner</span>
      </div>
      <div className="header-student">
        <div className="header-student-details">
          <span className="header-student-name">{student?.name || 'Student'}</span>
          <span className="header-student-info">
            {student?.class} • {student?.board} • {student?.school}
          </span>
        </div>
        <div className={`connection-dot ${connected ? '' : 'disconnected'}`} 
             title={connected ? 'Connected' : 'Disconnected'} />
      </div>
    </header>
  );
}
