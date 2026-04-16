/**
 * AvatarReaction — animated emoji responses for quiz answers.
 * Shows for ~3 seconds then fades away.
 */
import { useEffect, useState } from 'react';

export default function AvatarReaction({ reviewData }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(true);
    const timer = setTimeout(() => setVisible(false), 4000);
    return () => clearTimeout(timer);
  }, [reviewData]);

  if (!reviewData || !visible) return null;

  const { correct, feedback, avatar } = reviewData;

  // Determine animation class
  let animClass = 'wrong';
  if (correct) animClass = 'correct';
  else if (reviewData.partial) animClass = 'partial';

  return (
    <div className="avatar-container">
      <span className={`avatar-emoji ${animClass}`}>{avatar || '🤔'}</span>
      <p className="avatar-feedback">{feedback}</p>
    </div>
  );
}
