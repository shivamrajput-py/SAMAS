'use client';
import React, { useState } from 'react';
import styles from './OracleResults.module.css';

interface Props {
  profile: any;
}

export default function OracleResults({ profile }: Props) {
  const [currentSlide, setCurrentSlide] = useState(0);

  if (!profile || !profile.evaluations || profile.evaluations.length === 0) return null;
  
  const totalQuestions = profile.questions?.length || 0;
  const correctMCQs = profile.questions?.filter((q: any) => {
    if (q.question_type !== 'mcq') return false;
    const answer = profile.answers?.find((a: any) => a.question_id === q.question_id);
    return answer && answer.answer === q.options[q.correct_option_index];
  }).length || 0;

  const writtenQuestions = profile.questions?.filter((q: any) => q.question_type === 'written') || [];
  let avgWrittenScore = 0;
  if (writtenQuestions.length > 0) {
    const totalScore = writtenQuestions.reduce((sum: number, q: any) => {
      const evalObj = profile.evaluations?.find((e: any) => e.question_id === q.question_id);
      return sum + (evalObj?.answer_quality || 0);
    }, 0);
    avgWrittenScore = (totalScore / writtenQuestions.length) * 100;
  }

  return (
    <div className={`glass-panel ${styles.container}`}>
      <div className={styles.header} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '1.5rem', marginBottom: '1.5rem' }}>
        <div>
          <div className={styles.agentTag}>LUCID NODE</div>
          <h2 className={styles.title} style={{ margin: '0.5rem 0 0 0', fontSize: '1.25rem' }}>Interview Verification Results</h2>
        </div>
        
        <div style={{ display: 'flex', gap: '1.5rem', background: 'rgba(255,255,255,0.03)', padding: '0.5rem 1rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <div style={{ color: '#a0a0ab', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>MCQ Accuracy</div>
            <div style={{ color: '#10B981', fontSize: '1.1rem', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>{correctMCQs}/{profile.questions?.filter((q:any) => q.question_type === 'mcq').length}</div>
          </div>
          <div style={{ width: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <div style={{ color: '#a0a0ab', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Avg Written</div>
            <div style={{ color: '#EAB308', fontSize: '1.1rem', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>{avgWrittenScore.toFixed(0)}%</div>
          </div>
        </div>
      </div>

      <div className={styles.analysisSection}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h3 className={styles.sectionTitle} style={{ margin: 0 }}>Detailed Analysis</h3>
          {totalQuestions > 1 && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                onClick={() => setCurrentSlide(p => Math.max(0, p - 1))}
                disabled={currentSlide === 0}
                style={{ padding: '0.25rem 0.75rem', background: currentSlide === 0 ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.1)', color: currentSlide === 0 ? '#666' : '#fff', border: 'none', borderRadius: '4px', cursor: currentSlide === 0 ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}
              >
                &larr; Prev
              </button>
              <span style={{ color: '#a0a0ab', fontSize: '0.85rem', display: 'flex', alignItems: 'center', padding: '0 0.5rem', fontFamily: 'var(--font-mono)' }}>
                {currentSlide + 1} / {totalQuestions}
              </span>
              <button 
                onClick={() => setCurrentSlide(p => Math.min(totalQuestions - 1, p + 1))}
                disabled={currentSlide === totalQuestions - 1}
                style={{ padding: '0.25rem 0.75rem', background: currentSlide === totalQuestions - 1 ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.1)', color: currentSlide === totalQuestions - 1 ? '#666' : '#fff', border: 'none', borderRadius: '4px', cursor: currentSlide === totalQuestions - 1 ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}
              >
                Next &rarr;
              </button>
            </div>
          )}
        </div>
        <div className={styles.qaList}>
          {profile.questions && profile.questions.map((q: any, idx: number) => {
            const evaluation = profile.evaluations?.find((e: any) => e.question_id === q.question_id);
            const answer = profile.answers?.find((a: any) => a.question_id === q.question_id);
            
            const isMCQ = q.question_type === 'mcq';
            const isCorrectMCQ = isMCQ && answer?.answer === q.options[q.correct_option_index];
            const answerColor = isMCQ ? (isCorrectMCQ ? '#10B981' : '#F43F5E') : '#d1d1d6';
            
            return (
              <div key={idx} className={styles.qaCard} style={{ borderLeft: `3px solid ${answerColor}`, display: currentSlide === idx ? 'block' : 'none' }}>
                <div className={styles.qHeader}>
                  <span className={styles.qNumber}>Q{idx + 1}</span>
                  <span className={styles.qText}>{q.question_text}</span>
                </div>
                
                <div className={styles.aSection}>
                  {isMCQ ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                      {q.options?.map((opt: string, i: number) => {
                        const letter = String.fromCharCode(97 + i); // a, b, c, d
                        const isSelected = answer?.answer?.toLowerCase() === letter;
                        const isCorrect = q.options[q.correct_option_index] === opt;
                        
                        let bgColor = 'rgba(255, 255, 255, 0.05)';
                        let borderColor = 'rgba(255, 255, 255, 0.1)';
                        let textColor = '#d1d1d6';
                        
                        if (isCorrect) {
                          bgColor = 'rgba(16, 185, 129, 0.1)';
                          borderColor = '#10B981';
                          textColor = '#10B981';
                        } else if (isSelected && !isCorrect) {
                          bgColor = 'rgba(244, 63, 94, 0.1)';
                          borderColor = '#F43F5E';
                          textColor = '#F43F5E';
                        }

                        return (
                          <div key={i} style={{ 
                            padding: '0.5rem 0.75rem', 
                            borderRadius: '6px', 
                            background: bgColor, 
                            border: `1px solid ${borderColor}`,
                            color: textColor,
                            display: 'flex',
                            gap: '1rem',
                            alignItems: 'center',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.9rem'
                          }}>
                            <span style={{ fontWeight: 'bold' }}>{letter.toUpperCase()}</span>
                            <span>{opt.replace(/^[A-D]\)\s*/, '')}</span>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <>
                      <div className={styles.aLabel}>Your Answer:</div>
                      <div className={styles.aText} style={{ color: answerColor }}>
                        {answer?.answer || "No answer provided"}
                      </div>
                    </>
                  )}
                </div>
                
                {evaluation && !isMCQ && (
                  <div className={styles.evalSection}>
                    <div className={styles.evalHeader}>
                      <span className={styles.evalLabel}>LUCID Feedback</span>
                      <span className={`${styles.evalScore} ${evaluation.answer_quality >= 0.7 ? styles.goodScore : evaluation.answer_quality >= 0.4 ? styles.okScore : styles.badScore}`}>
                        Quality: {(evaluation.answer_quality * 100).toFixed(0)}%
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
