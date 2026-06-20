'use client';
import React, { useState } from 'react';
import styles from './InterviewUI.module.css';

export interface Question {
  question_id: number;
  question_text: string;
  question_type: 'mcq' | 'written';
  difficulty: string;
  target_skills: string[];
  options: string[] | null;
}

interface Props {
  questions: Question[];
  onSubmitAnswers: (answers: string[]) => void;
  isLoading: boolean;
}

export default function InterviewUI({ questions, onSubmitAnswers, isLoading }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<string[]>(Array(questions.length).fill(''));
  
  const question = questions[currentIndex];
  
  const handleAnswerChange = (val: string) => {
    const newAnswers = [...answers];
    newAnswers[currentIndex] = val;
    setAnswers(newAnswers);
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(prev => prev + 1);
    } else {
      onSubmitAnswers(answers);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) setCurrentIndex(prev => prev - 1);
  };

  if (!question) return null;

  const isLast = currentIndex === questions.length - 1;
  const currentAnswer = answers[currentIndex];
  const hasAnswered = currentAnswer.trim() !== '';

  return (
    <div className={`glass-panel ${styles.interviewCard}`}>
      <div className={styles.progressHeader}>
        <div className={styles.stepIndicator}>
          Question {currentIndex + 1} of {questions.length}
        </div>
        <div className={styles.progressBar}>
          <div 
            className={styles.progressFill} 
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          ></div>
        </div>
      </div>

      <div className={styles.questionMeta}>
        <span className={styles.badge}>{question.difficulty.toUpperCase()}</span>
        <div className={styles.skills}>
          {question.target_skills.map(skill => (
            <span key={skill} className={styles.skillTag}>{skill}</span>
          ))}
        </div>
      </div>

      <h3 className={styles.questionText}>{question.question_text}</h3>

      <div className={styles.answerArea}>
        {question.question_type === 'mcq' && question.options ? (
          <div className={styles.optionsList}>
            {question.options.map((opt, i) => {
              const letter = String.fromCharCode(97 + i); // a, b, c, d
              const isSelected = currentAnswer.toLowerCase() === letter;
              return (
                <button
                  key={i}
                  className={`${styles.optionBtn} ${isSelected ? styles.selectedOption : ''}`}
                  onClick={() => handleAnswerChange(letter)}
                >
                  <span className={styles.optionLetter}>{letter.toUpperCase()}</span>
                  <span className={styles.optionText}>{opt.replace(/^[A-D]\)\s*/, '')}</span>
                </button>
              );
            })}
          </div>
        ) : (
          <textarea
            className={`input-glass ${styles.textArea}`}
            placeholder="Type your detailed answer here..."
            value={currentAnswer}
            onChange={(e) => handleAnswerChange(e.target.value)}
            rows={6}
          />
        )}
      </div>

      <div className={styles.actions}>
        <button 
          className="btn-secondary" 
          onClick={handlePrev} 
          disabled={currentIndex === 0 || isLoading}
        >
          Previous
        </button>
        <button 
          className="btn-primary" 
          onClick={handleNext} 
          disabled={!hasAnswered || isLoading}
        >
          {isLoading ? 'Evaluating...' : isLast ? 'Submit Interview' : 'Next Question'}
        </button>
      </div>
    </div>
  );
}
