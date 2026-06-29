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
import LandingFooter from '@/components/landing/LandingFooter';

type FlowState = 'upload' | 'loading_profile' | 'interview' | 'evaluating' | 'title_select' | 'searching' | 'results' | 'error';

export default function FindPage() {
  // Dynamically resolve the backend URL. Prioritize environment variable for production (Cloudflare/Vercel)
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:8000` : 'http://127.0.0.1:8000');
  
  const [flowState, setFlowState] = useState<FlowState>('upload');
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  
  const [threadId, setThreadId] = useState<string>('');
  const [profile, setProfile] = useState<any>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [, setSuggestedTitles] = useState<string[]>([]);
  const [customTitles, setCustomTitles] = useState<string>('');
  const [searchLocation, setSearchLocation] = useState<string>('Remote');
  const [matchedJobs, setMatchedJobs] = useState<any[]>([]);
  const [droppedJobs, setDroppedJobs] = useState<any[]>([]);
  const [activeAgentId, setActiveAgentId] = useState<string>('profile');
  
  const [prismLogs, setPrismLogs] = useState<LogEntry[]>([]);
  const [lucidLogs, setLucidLogs] = useState<LogEntry[]>([]);
  const [radarLogs, setRadarLogs] = useState<LogEntry[]>([]);
  const [cipherLogs, setCipherLogs] = useState<LogEntry[]>([]);
  const [kairosLogs, setKairosLogs] = useState<LogEntry[]>([]);
  
  const addLog = (agent: string, message: string) => {
    const entry: LogEntry = {
      id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substr(2, 9),
      agent,
      message,
      timestamp: new Date()
    };
    
    if (agent === 'PRISM') setPrismLogs(prev => [...prev, entry]);
    else if (agent === 'LUCID') setLucidLogs(prev => [...prev, entry]);
    else if (agent === 'RADAR') setRadarLogs(prev => [...prev, entry]);
    else if (agent === 'CIPHER') setCipherLogs(prev => [...prev, entry]);
    else if (agent === 'KAIROS') setKairosLogs(prev => [...prev, entry]);
  };

  // BYOK State
  const [apiKey, setApiKey] = useState<string>('');
  const [modelName, setModelName] = useState<string>('qwen/qwen3.7-plus');

  const handleError = (msg: string, err: any) => {
    if (err.name === 'AbortError') {
      console.log('Request aborted by user');
      return;
    }
    console.error(err);
    setErrorMsg(`${msg}: ${err.message || 'Unknown error'}`);
    setFlowState('error');
  };

  const handleStartOver = () => {
    if (abortController) {
      abortController.abort();
    }
    setFlowState('upload');
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

    const controller = new AbortController();
    setAbortController(controller);
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/upload_resume/stream`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
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
                addLog('PRISM', 'Extracting text and structure from resume document...');
              } else if (data.type === 'progress') {
                const node = data.node || '';
                let msg = data.message;
                if (!msg) {
                  if (node === 'extract_resume') msg = "I'm parsing your resume file...";
                  else if (node === 'scrape_urls') msg = "Scraping your GitHub and portfolio links...";
                  else if (node === 'analyze_with_llm') msg = "Running deep AI analysis on your profile (this may take 30-40s)...";
                  else if (node === 'compute_scores') msg = "Computing proof scores for each skill...";
                  else msg = `Finished node: ${node}...`;
                }
                addLog('PRISM', msg);
              } else if (data.type === 'complete') {
                addLog('PRISM', 'Profile extraction complete ✓');
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
    const controller = new AbortController();
    setAbortController(controller);
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/interview/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_profile: userProfile,
          api_key: key,
          model_name: model
        }),
        signal: controller.signal,
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
    setLucidLogs([{ 
      id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substr(2, 9), 
      agent: 'LUCID', 
      message: 'Receiving answer submissions...', 
      timestamp: new Date() 
    }]);
    setFlowState('evaluating');

    const logMessages = [
      "Cross-referencing answers against technical documentation...",
      "Evaluating response structure and completeness...",
      "Running semantic validation on code blocks...",
      "Applying mathematical score adjustments based on confidence vectors...",
      "Finalizing verification profile..."
    ];

    let logIndex = 0;
    const logInterval = setInterval(() => {
      if (logIndex < logMessages.length) {
        setLucidLogs(prev => [...prev, {
          id: `log-${Date.now()}-${logIndex}`,
          agent: 'LUCID',
          message: logMessages[logIndex],
          timestamp: new Date()
        }]);
        logIndex++;
      }
    }, 2500);

    const controller = new AbortController();
    setAbortController(controller);
    
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
        signal: controller.signal,
      });
      if (!res1.ok) throw new Error(await res1.text());
      const evalData = await res1.json();
      setProfile({
        ...evalData.user_profile,
        evaluations: evalData.evaluations,
        questions: evalData.questions,
        answers: evalData.answers
      });
      
      setActiveAgentId('search');
      const res2 = await fetch(`${API_BASE_URL}/api/search/titles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_profile: evalData.user_profile,
          api_key: apiKey,
          model_name: modelName
        }),
        signal: controller.signal,
      });
      if (!res2.ok) throw new Error(await res2.text());
      const titleData = await res2.json();
      
      setThreadId(titleData.thread_id);
      setSuggestedTitles(titleData.suggested_titles);
      setCustomTitles(titleData.suggested_titles.join(', '));
      setFlowState('title_select');
      
    } catch (err) {
      handleError('Failed during evaluation', err);
    } finally {
      clearInterval(logInterval);
    }
  };

  // Phases 3b, 4, 5: Execute full search
  const handleExecuteSearch = async () => {
    setFlowState('searching');
    const controller = new AbortController();
    setAbortController(controller);
    
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
        signal: controller.signal,
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
                let mappedMsg = '';
                
                if (node.includes('search') || node === 'select_titles' || node === 'deduplicate_and_rank') {
                  setActiveAgentId('search');
                  agentName = 'RADAR';
                  if (node === 'job_search' || node === 'select_titles') mappedMsg = "Processing your title selections...";
                  else if (node === 'search_for_title') mappedMsg = "Fetching jobs from search engines...";
                  else if (node === 'deduplicate_and_rank') mappedMsg = "Removing duplicate listings...";
                } else if (node.includes('analyzer')) {
                  setActiveAgentId('analyzer');
                  agentName = 'CIPHER';
                  if (node === 'jd_analyzer_start') {
                    addLog('RADAR', 'Search complete ✓');
                    mappedMsg = "Starting job analysis...";
                  }
                  else if (node === 'analyzer_deep_deduplication') mappedMsg = "Finding similar postings to deduplicate...";
                  else if (node === 'analyzer_keyword_prefilter') mappedMsg = "Running keyword pre-filter on jobs...";
                  else if (node === 'analyzer_batch_jobs') mappedMsg = "Preparing jobs for AI analysis...";
                  else if (node === 'analyzer_extract_requirements') mappedMsg = "Extracting real requirements from job descriptions...";
                  else if (node === 'analyzer_finalize_and_embed') mappedMsg = "Computing ghost job scores & embeddings...";
                } else if (node.includes('matcher') || node.includes('matching')) {
                  setActiveAgentId('matcher');
                  agentName = 'KAIROS';
                  if (node === 'matching_start') {
                    addLog('CIPHER', 'Analysis complete ✓');
                    mappedMsg = "Scoring and ranking all jobs against your profile...";
                  }
                  else if (node === 'matcher_score_jobs') mappedMsg = "Scoring and ranking all jobs against your profile...";
                }

                let finalMsg = mappedMsg || data.message || `Processing step: ${node}...`;
                addLog(agentName, finalMsg);
              } else if (data.type === 'complete') {
                addLog('KAIROS', 'Matching complete ✓');
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
    <>
    <VoidDimension>
      <main className={styles.container}>

      <div className={styles.cornerHUD}>
        <Link href="/" style={{ textDecoration: 'none' }}>
          <p className={styles.hudTopLeft} style={{ cursor: 'pointer', margin: 0 }}>SAMAS</p>
        </Link>
      </div>

      <div className={styles.layoutWrapper}>
        {flowState === 'error' && (
          <div className={styles.errorBox}>
            <span><strong>System Error:</strong> {errorMsg}</span>
            <button onClick={handleStartOver} style={{ padding: '0.5rem 1rem', background: '#F43F5E', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', whiteSpace: 'nowrap' }}>Start Over</button>
          </div>
        )}

        <div className={timelineStyles.timelineContainer}>
          <div className={timelineStyles.centerLineTrack} />
          
          {/* PRISM ROW */}
          <div className={styles.timelineRow}>
            <div className={styles.agentCol}>
              {renderAgentCard('profile', '01', 'PRISM', 'IDENTITY ARCHITECT', 'PDF/DOCX parser → URL scraper → LLM semantic analysis → proof score computation. Extracts skills with evidence-based confidence scoring.', '#d47a43', <><span className={timelineStyles.formulaPart}>Resume</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Verified Profile</span></>)}
            </div>
            <div className={styles.workspaceCol}>
              {flowState === 'upload' && <ResumeUpload onSubmit={handleUpload} isLoading={false} />}
              {flowState !== 'upload' && <TerminalLogger logs={prismLogs} title="PRISM: IDENTITY EXTRACTION" isComplete={flowState !== 'loading_profile'} />}
              {flowState !== 'upload' && flowState !== 'loading_profile' && profile && (
                <div style={{ padding: '2rem', background: 'rgba(10, 10, 15, 0.4)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.1)', marginTop: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                    <div>
                      <h3 style={{ color: '#ffffff', marginBottom: '0.5rem', fontSize: '1.2rem', fontFamily: 'var(--font-display)', letterSpacing: '0.05em' }}>{profile.personal_info?.full_name || 'Verified Profile'}</h3>
                      <p style={{ color: '#d47a43', fontSize: '0.9rem', fontFamily: 'var(--font-mono)' }}>{profile.personal_info?.city ? `${profile.personal_info.city}, ${profile.personal_info.state || ''}` : 'Location Confirmed'}</p>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ color: '#ffffff', fontSize: '1.8rem', fontWeight: '800', fontFamily: 'var(--font-display)' }}>{profile.skills?.length || 0}</div>
                      <div style={{ color: '#a0a0ab', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Verified Skills</div>
                    </div>
                  </div>
                  <p style={{ color: '#d1d1d6', lineHeight: '1.6', fontSize: '0.95rem' }}>
                    {profile.professional_summary}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* LUCID ROW */}
          <div className={styles.timelineRow}>
            <div className={styles.agentCol}>
              {renderAgentCard('interview', '02', 'LUCID', 'TRUTH VALIDATOR', 'Adaptive question generator → HITL interrupt loop → LLM answer evaluation → mathematical score adjustment. Tests verification and assessment.', '#8c7b65', <><span className={timelineStyles.formulaPart}>Profile</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Skill Assessment</span></>)}
            </div>
            <div className={styles.workspaceCol}>
              {flowState !== 'upload' && flowState !== 'loading_profile' && questions.length === 0 && <TerminalLogger logs={lucidLogs.length > 0 ? lucidLogs : [{ id: 'lucid-prep', agent: 'LUCID', message: 'Analyzing your profile and generating adaptive questions...', timestamp: new Date() }]} title="LUCID: PREPARING INTERVIEW" />}
              {flowState !== 'upload' && flowState !== 'loading_profile' && questions.length > 0 && (flowState === 'interview' || flowState === 'evaluating') && <InterviewUI questions={questions} onSubmitAnswers={handleSubmitInterview} isLoading={flowState === 'evaluating'} />}
              {flowState === 'evaluating' && <TerminalLogger logs={lucidLogs} title="LUCID: INTERVIEW ANALYSIS" />}
              {flowState !== 'upload' && flowState !== 'loading_profile' && flowState !== 'interview' && flowState !== 'evaluating' && profile && (
                <OracleResults profile={profile} />
              )}
            </div>
          </div>

          {/* RADAR ROW */}
          <div className={styles.timelineRow}>
            <div className={styles.agentCol}>
              {renderAgentCard('search', '03', 'RADAR', 'MARKET SWEEPER', 'Location fan-out → Cartesian parallel SerpAPI execution → deduplication. Massive scale global search across multiple job boards simultaneously.', '#c2a886', <><span className={timelineStyles.formulaPart}>Profile</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Global Targets</span></>)}
            </div>
            <div className={styles.workspaceCol}>
              {flowState === 'title_select' && (
                <div className={styles.darkCard} style={{ background: 'rgba(10, 10, 15, 0.6)', padding: '2rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <h2 style={{ color: '#ffffff', marginBottom: '1rem', fontSize: '1.5rem', fontFamily: 'var(--font-display)' }}>Set Target Parameters</h2>
                  <p style={{ color: '#a0a0ab', marginBottom: '1.5rem', lineHeight: '1.5' }}>
                    I have analyzed your updated profile. Please confirm your target job titles and location before I deploy the sweepers.
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '2rem' }}>
                    <div>
                      <label style={{ display: 'block', color: '#d1d1d6', marginBottom: '0.5rem', fontSize: '0.9rem', fontFamily: 'var(--font-mono)' }}>Target Job Titles (comma separated)</label>
                      <input 
                        type="text" 
                        style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '6px', fontFamily: 'var(--font-body)' }}
                        value={customTitles}
                        onChange={(e) => setCustomTitles(e.target.value)}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', color: '#d1d1d6', marginBottom: '0.5rem', fontSize: '0.9rem', fontFamily: 'var(--font-mono)' }}>Target Location</label>
                      <input 
                        type="text" 
                        style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '6px', fontFamily: 'var(--font-body)' }}
                        value={searchLocation}
                        onChange={(e) => setSearchLocation(e.target.value)}
                      />
                    </div>
                  </div>
                  <button style={{ width: '100%', padding: '1rem', background: '#ffffff', color: '#1a1a24', fontWeight: 'bold', borderRadius: '6px', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-mono)', letterSpacing: '0.05em' }} onClick={() => { setRadarLogs([]); setCipherLogs([]); setKairosLogs([]); handleExecuteSearch(); }}>
                    [ EXECUTE SWEEP ]
                  </button>
                </div>
              )}
              {(flowState === 'searching' || flowState === 'results') && <TerminalLogger logs={radarLogs} title="RADAR: GLOBAL SWEEP" isComplete={flowState === 'results'} />}
            </div>
          </div>

          {/* CIPHER ROW */}
          <div className={styles.timelineRow}>
            <div className={styles.agentCol}>
              {renderAgentCard('analyzer', '04', 'CIPHER', 'DEEP ANALYST', 'Deep deduplication → keyword pre-filter → batch LLM extraction → ghost job detection → Pinecone embedding. Processes job descriptions at scale.', '#a85642', <><span className={timelineStyles.formulaPart}>JD Batch</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Skill Vectors</span></>)}
            </div>
            <div className={styles.workspaceCol}>
              {(flowState === 'searching' || flowState === 'results') && (cipherLogs.length > 0 || activeAgentId === 'analyzer' || activeAgentId === 'matcher') && <TerminalLogger logs={cipherLogs} title="CIPHER: REQUIREMENT DECODING" isComplete={flowState === 'results'} />}
            </div>
          </div>

          {/* KAIROS ROW */}
          <div className={styles.timelineRow}>
            <div className={styles.agentCol}>
              {renderAgentCard('matcher', '05', 'KAIROS', 'PROBABILITY ENGINE', '35% skill overlap + 20% experience delta + 25% embedding similarity + 20% proof alignment → tier classification. Weighted multi-signal scoring.', '#b8a99a', <><span className={timelineStyles.formulaPart}>Profile Vector</span><span className={timelineStyles.arrow}>→</span><span className={timelineStyles.formulaPart}>Ranked Jobs</span></>)}
            </div>
            <div className={styles.workspaceCol}>
              {(flowState === 'searching' || flowState === 'results') && (kairosLogs.length > 0 || activeAgentId === 'matcher') && <TerminalLogger logs={kairosLogs} title="KAIROS: VECTOR MATCHING" />}
              
              {/* RESULTS DASHBOARD RENDERED INLINE */}
              {flowState === 'results' && (
                <div style={{width: '100%', animation: 'fadeInUp 0.8s ease-out forwards', marginTop: '2rem'}}>
                  <ResultsDashboard jobs={matchedJobs} droppedJobs={droppedJobs} profile={profile} />
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
      </main>
    </VoidDimension>
    <LandingFooter />
    </>
  );
}
