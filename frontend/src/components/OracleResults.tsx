import React from 'react';
import styles from './OracleResults.module.css';

interface Props {
  profile: any;
}

export default function OracleResults({ profile }: Props) {
  if (!profile || !profile.score_adjustments || profile.score_adjustments.length === 0) return null;
  
  const adjustments = profile.score_adjustments;

  return (
    <div className={`glass-panel ${styles.container}`}>
      <div className={styles.header}>
        <div className={styles.agentTag}>ORACLE NODE</div>
        <h2 className={styles.title}>Interview Verification Results</h2>
      </div>
      
      <div className={styles.adjustmentsList}>
        {adjustments.map((adj: any, idx: number) => {
          const isPositive = adj.adjustment >= 0;
          return (
            <div key={idx} className={styles.adjustmentCard}>
              <div className={styles.skillName}>{adj.skill_name}</div>
              <div className={styles.details}>
                <div className={styles.reasoning}>{adj.reasoning}</div>
                <div className={`${styles.badge} ${isPositive ? styles.positive : styles.negative}`}>
                  {isPositive ? '+' : ''}{(adj.adjustment * 100).toFixed(0)}% Confidence
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className={styles.analysisSection}>
        <h3 className={styles.sectionTitle}>Detailed Analysis</h3>
        <div className={styles.qaList}>
          {profile.questions && profile.questions.map((q: any, idx: number) => {
            const evaluation = profile.evaluations?.find((e: any) => e.question_id === q.question_id);
            const answer = profile.answers?.find((a: any) => a.question_id === q.question_id);
            
            return (
              <div key={idx} className={styles.qaCard}>
                <div className={styles.qHeader}>
                  <span className={styles.qNumber}>Q{idx + 1}</span>
                  <span className={styles.qText}>{q.question_text}</span>
                </div>
                
                <div className={styles.aSection}>
                  <div className={styles.aLabel}>Your Answer:</div>
                  <div className={styles.aText}>{answer?.answer || "No answer provided"}</div>
                </div>
                
                {evaluation && (
                  <div className={styles.evalSection}>
                    <div className={styles.evalHeader}>
                      <span className={styles.evalLabel}>ORACLE Feedback</span>
                      <span className={`${styles.evalScore} ${evaluation.answer_quality >= 0.7 ? styles.goodScore : evaluation.answer_quality >= 0.4 ? styles.okScore : styles.badScore}`}>
                        Score: {(evaluation.answer_quality * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className={styles.evalFeedback}>{evaluation.feedback}</div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
