import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';

const SKILL_LABELS = {
  quantitative: 'Quantitative', analytical: 'Analytical', logical_reasoning: 'Logical Reasoning',
  conceptual_understanding: 'Conceptual', scientific_reasoning: 'Scientific',
  procedural_fluency: 'Procedural', problem_solving: 'Problem Solving'
};

export default function SkillsAnalysis({ data }) {
  if (!data) return <div className="analytics-loading">Loading skills data...</div>;
  const scores = data.current_scores || {};
  const radarData = Object.entries(scores).map(([k, v]) => ({ subject: SKILL_LABELS[k] || k, score: v }));
  const summary = data.strength_summary || { strong: [], needs_work: [] };
  const topics = data.topic_mastery || [];
  const recs = data.revision_recommendations || [];

  return (
    <div className="skills-analysis-container">
      <div className="skills-left-panel">
        <h3 style={{textAlign:'center',color:'#fff',marginBottom:'16px'}}>Cognitive Skills</h3>
        <ResponsiveContainer width="100%" height={340}>
          <RadarChart data={radarData}>
            <PolarGrid stroke="rgba(147,51,234,0.3)" />
            <PolarAngleAxis dataKey="subject" stroke="#D1D5DB" tick={{fontSize:11}} />
            <PolarRadiusAxis angle={90} domain={[0,100]} stroke="#9CA3AF" tick={{fontSize:10}} />
            <Radar name="Score" dataKey="score" stroke="#9333ea" fill="#9333ea" fillOpacity={0.3} />
          </RadarChart>
        </ResponsiveContainer>
        <div className="skill-legend">
          {Object.entries(scores).map(([k,v]) => (
            <div key={k} className="skill-item">
              <span className="skill-name">{SKILL_LABELS[k]}</span>
              <span className="skill-score">{v}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="skills-right-panel">
        <div className="strength-summary-banner">
          <div className="summary-section">
            <h4>💪 Strong Areas</h4>
            {summary.strong.map(s => <span key={s} className="skill-badge strong">{SKILL_LABELS[s] || s}</span>)}
            {summary.strong.length === 0 && <span style={{color:'#9CA3AF',fontSize:'14px'}}>Keep practicing!</span>}
          </div>
          <div className="summary-section">
            <h4>📈 Needs Work</h4>
            {summary.needs_work.map(s => <span key={s} className="skill-badge needs-work">{SKILL_LABELS[s] || s}</span>)}
            {summary.needs_work.length === 0 && <span style={{color:'#9CA3AF',fontSize:'14px'}}>Great shape!</span>}
          </div>
        </div>
        {topics.length > 0 && (
          <div className="topic-strength-grid">
            <h3>Topic Mastery</h3>
            <div className="topics-grid">
              {topics.slice(0,12).map((t,i) => (
                <div key={i} className={`topic-card strength-${t.current_mastery_score >= 70 ? 'high' : t.current_mastery_score >= 40 ? 'medium' : 'low'}`}>
                  <div className="topic-header">
                    <span className="topic-name">{t.topic_name}</span>
                    <span className={`trend-arrow ${t.trend}`}>{t.trend === 'improving' ? '↗' : t.trend === 'declining' ? '↘' : '→'}</span>
                  </div>
                  <div className="topic-score">{t.current_mastery_score}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
        {recs.length > 0 && (
          <div className="revision-recommendations">
            <h3>📚 Recommended Revisions</h3>
            {recs.map((r,i) => (
              <div key={i} className="revision-card">
                <div className="revision-header">
                  <span className="revision-topic">{r.topic || r.concept}</span>
                </div>
                <p className="revision-reason">{r.reason}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
