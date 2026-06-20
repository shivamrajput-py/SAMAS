'use client';
/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useState } from 'react';
import styles from './page.module.css';
import timelineStyles from '@/components/AgentTimeline.module.css';
import ResumeUpload from '@/components/ResumeUpload';
import InterviewUI, { Question } from '@/components/InterviewUI';
import ResultsDashboard from '@/components/ResultsDashboard';
import OracleResults from '@/components/OracleResults';
import Link from 'next/link';
import VoidDimension from '@/components/landing/VoidDimension';
import TerminalLogger, { LogEntry } from '@/components/TerminalLogger';

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
  const [searchLocation, setSearchLocation] = useState<string>('Remote');
  const [matchedJobs, setMatchedJobs] = useState<any[]>([]);
  const [droppedJobs, setDroppedJobs] = useState<any[]>([]);
  const [activeAgentId, setActiveAgentId] = useState<string>('profile');
  
  const [terminalLogs, setTerminalLogs] = useState<LogEntry[]>([]);
  
  const addLog = (agent: string, message: string) => {
    setTerminalLogs(prev => [...prev, {
      id: Math.random().toString(36).substr(2, 9),
      agent,
      message,
      timestamp: new Date()
    }]);
  };

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
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the last incomplete line in the buffer
        
        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmedLine.substring(6));
              if (data.type === 'error') {
                throw new Error(data.message);
              } else if (data.type === 'start') {
                addLog('PRISM', 'Initializing identity extraction protocol...');
              } else if (data.type === 'progress') {
                const node = data.node || '';
                let msg = data.message;
                if (!msg) {
                  if (node === 'parser') msg = 'Parsing raw document arrays...';
                  else if (node === 'skill_extractor') msg = 'Extracting latent capabilities and skills...';
                  else if (node === 'proof_analyzer') msg = 'Cross-referencing claims and generating proof scores...';
                  else if (node === 'formatter') msg = 'Compiling unified semantic profile...';
                  else msg = `Processing node: ${node}...`;
                }
                addLog('PRISM', msg);
              } else if (data.type === 'complete') {
                addLog('PRISM', 'Identity extraction complete.');
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
    setFlowState('interview');
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
          location: searchLocation,
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
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the last incomplete line
        
        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmedLine.substring(6));
              if (data.type === 'error') {
                throw new Error(data.message);
              } else if (data.type === 'progress') {
                const node = data.node || '';
                
                let agentName = 'SYSTEM';
                if (node.includes('search')) {
                  setActiveAgentId('search');
                  agentName = 'RADAR';
                } else if (node.includes('analyzer')) {
                  setActiveAgentId('analyzer');
                  agentName = 'CORTEX';
                } else if (node.includes('matcher') || node.includes('ranking')) {
                  setActiveAgentId('matcher');
                  agentName = 'NEXUS';
                }

                let msg = data.message;
                if (!msg) {
                  msg = `Processing step: ${node}...`;
                }
                
                addLog(agentName, msg);
              } else if (data.type === 'complete') {
                addLog('NEXUS', 'Match vectors finalized.');
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
    <VoidDimension>
      <main className={styles.container}>

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
                {flowState === 'loading_profile' && <TerminalLogger logs={terminalLogs} title="PRISM: IDENTITY EXTRACTION" />}
                {flowState !== 'upload' && flowState !== 'loading_profile' && profile && (
                  <div style={{ padding: '2rem', background: 'rgba(10, 10, 15, 0.4)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <h3 style={{ color: '#ffffff', marginBottom: '1rem' }}>Identity Extracted</h3>
                    <p style={{ color: '#d1d1d6', lineHeight: '1.6' }}>
                      {profile.professional_summary}
                    </p>
                  </div>
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
                  <div className={styles.darkCard} style={{ background: 'rgba(10, 10, 15, 0.6)', padding: '2rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
                    <h2 style={{ color: '#ffffff', marginBottom: '1rem', fontSize: '1.5rem' }}>Set Target Parameters</h2>
                    <p style={{ color: '#a0a0ab', marginBottom: '1.5rem', lineHeight: '1.5' }}>
                      I have analyzed your updated profile. Please confirm your target job titles and location before I deploy the sweepers.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '2rem' }}>
                      <div>
                        <label style={{ display: 'block', color: '#d1d1d6', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Target Job Titles (comma separated)</label>
                        <input 
                          type="text" 
                          style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '6px' }}
                          value={customTitles}
                          onChange={(e) => setCustomTitles(e.target.value)}
                        />
                      </div>
                      <div>
                        <label style={{ display: 'block', color: '#d1d1d6', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Target Location</label>
                        <input 
                          type="text" 
                          style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '6px' }}
                          value={searchLocation}
                          onChange={(e) => setSearchLocation(e.target.value)}
                        />
                      </div>
                    </div>
                    <button style={{ width: '100%', padding: '1rem', background: '#ffffff', color: '#1a1a24', fontWeight: 'bold', borderRadius: '6px', border: 'none', cursor: 'pointer' }} onClick={() => {
                      setTerminalLogs([]);
                      handleExecuteSearch();
                    }}>
                      EXECUTE SWEEP
                    </button>
                  </div>
                )}
                {flowState === 'searching' && activeAgentId === 'search' && <TerminalLogger logs={terminalLogs} title="RADAR: GLOBAL SWEEP" />}
              </div>
            </div>

            {/* CORTEX ROW */}
            <div className={styles.timelineRow}>
              <div className={styles.agentCol}>
                {renderAgentCard('analyzer', '04', 'CORTEX', 'REQUIREMENT DECODER', 'Breaking down job descriptions into explicit and implicit requirements.', '#3b5a6c', <><span className={timelineStyles.formulaPart}>JD Batch</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Skill Vectors</span></>)}
              </div>
              <div className={styles.workspaceCol}>
                {flowState === 'searching' && activeAgentId === 'analyzer' && <TerminalLogger logs={terminalLogs} title="CORTEX: REQUIREMENT DECODING" />}
              </div>
            </div>

            {/* NEXUS ROW */}
            <div className={styles.timelineRow}>
              <div className={styles.agentCol}>
                {renderAgentCard('matcher', '05', 'NEXUS', 'VECTOR MATCHER', 'Mathematically matching your profile vector against job requirement vectors.', '#5a4661', <><span className={timelineStyles.formulaPart}>Profile Vector</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Ranked Jobs</span></>)}
              </div>
              <div className={styles.workspaceCol}>
                {flowState === 'searching' && activeAgentId === 'matcher' && <TerminalLogger logs={terminalLogs} title="NEXUS: VECTOR MATCHING" />}
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
    </VoidDimension>
  );
}
