import { useState, useEffect } from 'react';
import CurriculumTimeline from './CurriculumTimeline';
import SkillsAnalysis from './SkillsAnalysis';

export default function AnalyticsView() {
  const [activeTab, setActiveTab] = useState('curriculum');
  const [curriculumData, setCurriculumData] = useState(null);
  const [skillsData, setSkillsData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'curriculum' && !curriculumData) {
      setLoading(true);
      fetch('/api/analytics/curriculum-timeline')
        .then(r => r.json())
        .then(d => { setCurriculumData(d); setLoading(false); })
        .catch(() => setLoading(false));
    }
    if (activeTab === 'skills' && !skillsData) {
      setLoading(true);
      fetch('/api/analytics/skill-profile')
        .then(r => r.json())
        .then(d => { setSkillsData(d); setLoading(false); })
        .catch(() => setLoading(false));
    }
  }, [activeTab]);

  return (
    <div className="analytics-view">
      <div className="analytics-tab-bar">
        <button className={`tab-btn ${activeTab === 'curriculum' ? 'active' : ''}`} onClick={() => setActiveTab('curriculum')}>
          📋 Curriculum Timeline
        </button>
        <button className={`tab-btn ${activeTab === 'skills' ? 'active' : ''}`} onClick={() => setActiveTab('skills')}>
          🧠 Skills & Analysis
        </button>
      </div>
      {loading && <div className="analytics-loading">Loading...</div>}
      {!loading && activeTab === 'curriculum' && <CurriculumTimeline data={curriculumData} />}
      {!loading && activeTab === 'skills' && <SkillsAnalysis data={skillsData} />}
    </div>
  );
}
