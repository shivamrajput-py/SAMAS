'use client';
/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useState } from 'react';
import styles from './page.module.css';
import timelineStyles from '@/components/AgentTimeline.module.css';
import ResumeUpload from '@/components/ResumeUpload';
import InterviewUI, { Question } from '@/components/InterviewUI';
import ResultsDashboard from '@/components/ResultsDashboard';
import PrismResults from '@/components/PrismResults';
import OracleResults from '@/components/OracleResults';
import Link from 'next/link';

type FlowState = 'upload' | 'loading_profile' | 'interview' | 'evaluating' | 'title_select' | 'searching' | 'results' | 'error';

export default function FindPage() {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  
  const [flowState, setFlowState] = useState<FlowState>('upload');
  const [errorMsg, setErrorMsg] = useState<string>('');
  
  const [threadId, setThreadId] = useState<string>('');
  const [profile, setProfile] = useState<any>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [, setSuggestedTitles] = useState<string[]>([]);
  const [customTitles, setCustomTitles] = useState<string>('');
  const [matchedJobs, setMatchedJobs] = useState<any[]>([]);
  const [droppedJobs, setDroppedJobs] = useState<any[]>([]);
  const [activeAgentId, setActiveAgentId] = useState<string>('profile');

  // BYOK State
  const [apiKey, setApiKey] = useState<string>('');
  const [modelName, setModelName] = useState<string>('qwen/qwen3.7-plus');

  const handleError = (msg: string, err: any) => {
    console.error(err);
    setErrorMsg(`${msg}: ${err.message || 'Unknown error'}`);
    setFlowState('error');
  };

  // Phase 1: Upload Resume
  const handleUpload = async (file: File, urls: string[], key: string, model: string) => {
    setApiKey(key);
    setModelName(model);
    setFlowState('loading_profile');
    setActiveAgentId('profile');
    setErrorMsg('');
    
    const formData = new FormData();
    formData.append('file', file);
    if (urls.length > 0) formData.append('urls', JSON.stringify(urls));
    if (key) formData.append('api_key', key);
    if (model) formData.append('model_name', model);

    try {
      const res = await fetch(`${API_BASE_URL}/api/upload_resume/stream`, {
        method: 'POST',
        body: formData,
      });
      
      if (!res.ok) throw new Error(await res.text());
      if (!res.body) throw new Error("No response body");
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      
      let finalProfile = null;
      let finalThreadId = null;
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              if (data.type === 'error') {
                throw new Error(data.message);
              } else if (data.type === 'complete') {
                finalProfile = data.user_profile;
                finalThreadId = data.thread_id;
                setProfile(data.user_profile);
              }
            } catch (e: any) {
              if (e.message !== "Unexpected end of JSON input" && !e.message.includes("JSON") && !e.message.includes("parse")) {
                throw e;
              }
            }
          }
        }
      }
      
      if (!finalProfile) throw new Error("Stream ended without profile");
      
      setThreadId(finalThreadId || '');
      await fetchQuestions(finalProfile, key, model);
    } catch (err) {
      handleError('Failed to parse resume', err);
    }
  };

  // Phase 2a: Get Questions
  const fetchQuestions = async (userProfile: any, key: string, model: string) => {
    setActiveAgentId('interview');
    try {
      const res = await fetch(`${API_BASE_URL}/api/interview/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_profile: userProfile,
          api_key: key,
          model_name: model
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      
      setThreadId(data.thread_id);
      setQuestions(data.questions);
      setFlowState('interview');
    } catch (err) {
      handleError('Failed to generate interview questions', err);
    }
  };

  // Phase 2b: Submit Answers & Phase 3a: Get Titles
  const handleSubmitInterview = async (answers: string[]) => {
    setFlowState('evaluating');
    try {
      const formattedAnswers = answers.map((ans, idx) => ({
        question_id: questions[idx].question_id,
        answer: ans
      }));

      const res1 = await fetch(`${API_BASE_URL}/api/interview/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          thread_id: threadId, 
          answers: formattedAnswers,
          api_key: apiKey,
          model_name: modelName
        }),
      });
      if (!res1.ok) throw new Error(await res1.text());
      const evalData = await res1.json();
      setProfile(evalData.user_profile);
      
      setActiveAgentId('search');
      const res2 = await fetch(`${API_BASE_URL}/api/search/titles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_profile: evalData.user_profile,
          api_key: apiKey,
          model_name: modelName
        }),
      });
      if (!res2.ok) throw new Error(await res2.text());
      const titleData = await res2.json();
      
      setThreadId(titleData.thread_id);
      setSuggestedTitles(titleData.suggested_titles);
      setCustomTitles(titleData.suggested_titles.join(', '));
      setFlowState('title_select');
      
    } catch (err) {
      handleError('Failed during evaluation', err);
    }
  };

  // Phases 3b, 4, 5: Execute full search
  const handleExecuteSearch = async () => {
    setFlowState('searching');
    try {
      const titles = customTitles.split(',').map(t => t.trim()).filter(t => t);
      setActiveAgentId('search');
      
      const res = await fetch(`${API_BASE_URL}/api/search/execute/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          thread_id: threadId, 
          selected_titles: titles,
          user_profile: profile,
          api_key: apiKey,
          model_name: modelName
        }),
      });
      
      if (!res.ok) throw new Error(await res.text());
      if (!res.body) throw new Error("No response body");
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      
      let finalMatchedJobs = null;
      let finalDroppedJobs = null;
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              if (data.type === 'error') {
                throw new Error(data.message);
              } else if (data.type === 'progress') {
                if (data.node.includes('search')) setActiveAgentId('search');
                if (data.node.includes('analyzer')) setActiveAgentId('analyzer');
                if (data.node.includes('matcher')) setActiveAgentId('matcher');
              } else if (data.type === 'complete') {
                finalMatchedJobs = data.matched_jobs;
                finalDroppedJobs = data.dropped_jobs;
              }
            } catch (e: any) {
              if (e.message !== "Unexpected end of JSON input" && !e.message.includes("JSON") && !e.message.includes("parse")) {
                throw e;
              }
            }
          }
        }
      }

      if (finalMatchedJobs) setMatchedJobs(finalMatchedJobs);
      if (finalDroppedJobs) setDroppedJobs(finalDroppedJobs);
      setFlowState('results');
    } catch (err) {
      handleError('Search failed', err);
    }
  };

  const getAgentState = (agentId: string) => {
    const order = ['profile', 'interview', 'search', 'analyzer', 'matcher'];
    const currentIndex = order.indexOf(activeAgentId);
    const agentIndex = order.indexOf(agentId);
    
    if (currentIndex > agentIndex) return 'past';
    if (currentIndex === agentIndex) return 'active';
    return 'future';
  };

  const renderAgentCard = (
    id: string,
    number: string,
    name: string,
    role: string,
    desc: string,
    color: string,
    formula: React.ReactNode
  ) => {
    const state = getAgentState(id);
    return (
      <div className={`${timelineStyles.cardWrapper} ${timelineStyles[state]}`} style={{ '--agent-color': color } as React.CSSProperties}>
        <div className={`${timelineStyles.connectionPoint} ${timelineStyles[state]}`} />
        <div className={timelineStyles.glassCard}>
          <div className={timelineStyles.agentNumber}>{number}</div>
          <div className={timelineStyles.content}>
            <div className={timelineStyles.agentRole}>{role}</div>
            <h3 className={timelineStyles.agentName}>{name}</h3>
            <div className={timelineStyles.formula}>{formula}</div>
            <div className={timelineStyles.divider} />
            <p className={timelineStyles.agentDesc}>{desc}</p>
          </div>
        </div>
      </div>
    );
  };

  const renderLoadingIndicator = (text: string) => (
    <div className={styles.inlineLoading}>
      <div className={styles.spinner} />
      <span>{text}</span>
    </div>
  );

  return (
    <main className={styles.container}>
      <div className={styles.ambientGlow} />

      <div className={styles.cornerHUD}>
        <p className={styles.hudTopLeft}>SAMAS</p>
        <p className={styles.hudTopRight}>IS A MULTI-AGENT JOB INTELLIGENCE SYSTEM</p>
      </div>

      <Link href="/" className={styles.backLink}>← BACK TO HOME</Link>

      <div className={styles.layoutWrapper}>
        {flowState === 'error' && (
          <div className={styles.errorBox}>
            <strong>System Error:</strong> {errorMsg}
            <button onClick={() => setFlowState('upload')} className="btn-primary" style={{marginTop: '1rem'}}>Start Over</button>
          </div>
        )}

        {flowState !== 'results' ? (
          <div className={timelineStyles.timelineContainer}>
            <div className={timelineStyles.centerLineTrack} />
            
            {/* PRISM ROW */}
            <div className={styles.timelineRow}>
              <div className={styles.agentCol}>
                {renderAgentCard('profile', '01', 'PRISM', 'IDENTITY ARCHITECT', 'Extracting your true achievements and rebuilding your resume into a verified proof map.', '#d47a43', <><span className={timelineStyles.formulaPart}>Resume</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Verified Profile</span></>)}
              </div>
              <div className={styles.workspaceCol}>
                {flowState === 'upload' && <ResumeUpload onSubmit={handleUpload} isLoading={false} />}
                {flowState === 'loading_profile' && renderLoadingIndicator("Extracting profile text and computing initial proof scores...")}
                {flowState !== 'upload' && flowState !== 'loading_profile' && profile && (
                  <PrismResults profile={profile} condensed={true} />
                )}
              </div>
            </div>

            {/* ORACLE ROW */}
            <div className={styles.timelineRow}>
              <div className={styles.agentCol}>
                {renderAgentCard('interview', '02', 'ORACLE', 'INTERROGATOR', 'Adaptive interview engine testing your claimed skills and finding knowledge gaps.', '#8c7b65', <><span className={timelineStyles.formulaPart}>Profile</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Skill Assessment</span></>)}
              </div>
              <div className={styles.workspaceCol}>
                {flowState === 'interview' && <InterviewUI questions={questions} onSubmitAnswers={handleSubmitInterview} isLoading={false} />}
                {flowState === 'evaluating' && renderLoadingIndicator("Evaluating answers and applying mathematical score penalties...")}
                {flowState !== 'upload' && flowState !== 'loading_profile' && flowState !== 'interview' && flowState !== 'evaluating' && profile && profile.score_adjustments && (
                  <OracleResults profile={profile} />
                )}
              </div>
            </div>

            {/* RADAR ROW */}
            <div className={styles.timelineRow}>
              <div className={styles.agentCol}>
                {renderAgentCard('search', '03', 'RADAR', 'MARKET SWEEPER', 'Scanning the global job market to surface the highest-impact opportunities.', '#4f6b5b', <><span className={timelineStyles.formulaPart}>Profile</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Global Targets</span></>)}
              </div>
              <div className={styles.workspaceCol}>
                {flowState === 'title_select' && (
                  <div className={styles.darkCard}>
                    <h2 className={styles.cardTitle}>Job Title Selection</h2>
                    <p style={{ color: '#4a4a55', marginBottom: '1.5rem' }}>
                      Based on your verified profile, we suggest the following titles. You can edit them before we begin the massive parallel search.
                    </p>
                    <input 
                      type="text" 
                      className={styles.titleInput}
                      value={customTitles}
                      onChange={(e) => setCustomTitles(e.target.value)}
                    />
                    <button className={styles.executeBtn} onClick={handleExecuteSearch}>
                      Execute Massive Search
                    </button>
                  </div>
                )}
                {flowState === 'searching' && activeAgentId === 'search' && renderLoadingIndicator("Fetching jobs via SerpAPI and running deep deduplication...")}
              </div>
            </div>

            {/* CORTEX ROW */}
            <div className={styles.timelineRow}>
              <div className={styles.agentCol}>
                {renderAgentCard('analyzer', '04', 'CORTEX', 'REQUIREMENT DECODER', 'Breaking down job descriptions into explicit and implicit requirements.', '#3b5a6c', <><span className={timelineStyles.formulaPart}>JD Batch</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Skill Vectors</span></>)}
              </div>
              <div className={styles.workspaceCol}>
                {flowState === 'searching' && activeAgentId === 'analyzer' && renderLoadingIndicator("LLM extracting explicit and implicit requirements from JD batches...")}
              </div>
            </div>

            {/* NEXUS ROW */}
            <div className={styles.timelineRow}>
              <div className={styles.agentCol}>
                {renderAgentCard('matcher', '05', 'NEXUS', 'VECTOR MATCHER', 'Mathematically matching your profile vector against job requirement vectors.', '#5a4661', <><span className={timelineStyles.formulaPart}>Profile Vector</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Ranked Jobs</span></>)}
              </div>
              <div className={styles.workspaceCol}>
                {flowState === 'searching' && activeAgentId === 'matcher' && renderLoadingIndicator("Computing Pinecone vectors and mathematically ranking final jobs...")}
              </div>
            </div>

          </div>
        ) : (
          <div style={{width: '100%', animation: 'fadeInUp 0.5s ease-out forwards'}}>
            <ResultsDashboard jobs={matchedJobs} droppedJobs={droppedJobs} profile={profile} />
          </div>
        )}
      </div>
    </main>
  );
}
