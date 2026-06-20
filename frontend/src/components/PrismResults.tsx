import React, { useState } from 'react';
import styles from './PrismResults.module.css';

interface Props {
  profile: any;
  condensed?: boolean;
}

export default function PrismResults({ profile, condensed = false }: Props) {
  const [showModal, setShowModal] = useState(false);

  if (!profile) return null;
  
  const skills = profile.skills || [];
  const displaySkills = condensed ? skills.slice(0, 3) : skills;
  
  return (
    <>
      <div className={`glass-panel ${styles.container}`}>
        <div className={styles.header}>
          <div className={styles.agentTag}>PRISM NODE</div>
          <h2 className={styles.title}>Verified Profile Data</h2>
        </div>
        
        <div className={styles.summaryBox}>
          <p>{profile.personal_info?.professional_summary || "No summary generated."}</p>
        </div>

        <h3 className={styles.skillsTitle}>Extracted Skills</h3>
        <div className={styles.skillsGrid}>
          {displaySkills.map((skill: any, idx: number) => {
            const proofScore = skill.proof_score || 0;
            let colorClass = styles.low;
            if (proofScore >= 0.7) colorClass = styles.high;
            else if (proofScore >= 0.4) colorClass = styles.medium;
            
            return (
              <div key={idx} className={`${styles.skillCard} ${colorClass}`}>
                <div className={styles.skillHeader}>
                  <span className={styles.skillName}>{skill.name}</span>
                  <span className={styles.skillScore}>{(proofScore * 100).toFixed(0)}% Confidence</span>
                </div>
                <div className={styles.progressBar}>
                  <div 
                    className={styles.progressFill} 
                    style={{ width: `${Math.min(100, proofScore * 100)}%` }}
                  ></div>
                </div>
                {skill.proofs && skill.proofs.length > 0 && (
                  <div className={styles.proofs}>
                    <small>Proof: {skill.proofs[0].source} - {skill.proofs[0].context}</small>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        
        {condensed && skills.length > 3 && (
          <button 
            className={styles.seeMoreBtn}
            onClick={() => setShowModal(true)}
          >
            See More ({skills.length - 3} additional skills)
          </button>
        )}
      </div>

      {showModal && (
        <div className={styles.modalOverlay} onClick={() => setShowModal(false)}>
          <div className={styles.modalContent} onClick={e => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2 className={styles.title}>All Extracted Skills</h2>
              <button className={styles.closeBtn} onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className={styles.skillsGrid}>
              {skills.map((skill: any, idx: number) => {
                const proofScore = skill.proof_score || 0;
                let colorClass = styles.low;
                if (proofScore >= 0.7) colorClass = styles.high;
                else if (proofScore >= 0.4) colorClass = styles.medium;
                
                return (
                  <div key={idx} className={`${styles.skillCard} ${colorClass}`}>
                    <div className={styles.skillHeader}>
                      <span className={styles.skillName}>{skill.name}</span>
                      <span className={styles.skillScore}>{(proofScore * 100).toFixed(0)}% Confidence</span>
                    </div>
                    <div className={styles.progressBar}>
                      <div 
                        className={styles.progressFill} 
                        style={{ width: `${Math.min(100, proofScore * 100)}%` }}
                      ></div>
                    </div>
                    {skill.proofs && skill.proofs.length > 0 && (
                      <div className={styles.proofs}>
                        <small>Proof: {skill.proofs[0].source} - {skill.proofs[0].context}</small>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
