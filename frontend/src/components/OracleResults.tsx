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
    </div>
  );
}
