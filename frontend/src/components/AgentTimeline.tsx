import React, { useRef, useEffect } from 'react';
import styles from './AgentTimeline.module.css';
import { Hexagon, CheckSquare, Target, Cpu, GitMerge } from 'lucide-react';
import gsap from 'gsap';

export type AgentStep = 'profile' | 'interview' | 'search' | 'analyzer' | 'matcher';

interface Props {
  activeAgentId: string;
}

const AGENTS = [
  {
    id: 'profile',
    code: '01',
    name: 'PRISM',
    role: 'Identity Architect',
    formula: 'Resume → Verified Profile',
    desc: 'Extracting your true achievements and rebuilding your resume into a verified proof map.',
    color: '#d47a43', // Earthy Amber
    icon: Hexagon
  },
  {
    id: 'interview',
    code: '02',
    name: 'ORACLE',
    role: 'Truth Validator',
    formula: 'Input → Skill Assessment',
    desc: 'Adaptive interview engine testing your claimed skills and finding knowledge gaps.',
    color: '#8c7b65', // Muted Sage
    icon: CheckSquare
  },
  {
    id: 'search',
    code: '03',
    name: 'RADAR',
    role: 'Market Sweeper',
    formula: 'Profile → Global Targets',
    desc: 'Scanning the global job market to surface the highest-impact opportunities.',
    color: '#c2a886', // Warm Gold
    icon: Target
  },
  {
    id: 'analyzer',
    code: '04',
    name: 'CORTEX',
    role: 'Deep Analyst',
    formula: 'Syntax → Core Requirements',
    desc: 'Dissecting job descriptions to strip away marketing fluff and map core requirements.',
    color: '#a85642', // Brick Red
    icon: Cpu
  },
  {
    id: 'matcher',
    code: '05',
    name: 'NEXUS',
    role: 'Probability Engine',
    formula: 'Vectors → Success Tiers',
    desc: 'Calculating your exact chances of landing the role via mathematical vectors.',
    color: '#b8a99a', // Warm Sand
    icon: GitMerge
  }
];

export default function AgentTimeline({ activeAgentId }: Props) {
  const activeIndex = AGENTS.findIndex(a => a.id === activeAgentId);
  const safeActiveIndex = activeIndex === -1 ? 0 : activeIndex;
  
  // Calculate percentage for the glowing line fill
  const progressPercent = ((safeActiveIndex) / (AGENTS.length - 1)) * 100;

  return (
    <div className={styles.timelineContainer}>
      <h3 className={styles.timelineHeader}>SYSTEM STATUS</h3>
      
      <div className={styles.centerLineTrack}>
        <div 
          className={styles.centerLineFill} 
          style={{ height: `${progressPercent}%` }}
        />
      </div>

      {AGENTS.map((agent, index) => {
        const isPast = index < safeActiveIndex;
        const isActive = index === safeActiveIndex;
        const isFuture = index > safeActiveIndex;
        
        let stateClass = '';
        if (isPast) stateClass = styles.past;
        if (isActive) stateClass = styles.active;
        if (isFuture) stateClass = styles.future;

        const Icon = agent.icon;

        return (
          <div key={agent.id} className={styles.timelineNode}>
            
            <div 
              className={`${styles.connectionPoint} ${stateClass}`} 
              style={{ '--agent-color': agent.color } as React.CSSProperties} 
            />

            <div className={`${styles.cardWrapper} ${stateClass}`}>
              <div 
                className={styles.glassCard}
                style={{ '--agent-color': agent.color } as React.CSSProperties}
              >
                <div className={styles.agentNumber}>{agent.code}</div>
                
                <div className={styles.iconWrapper}>
                  <Icon size={40} color={agent.color} strokeWidth={1.5} />
                </div>

                <div className={styles.content}>
                  <h3 className={styles.agentName}>{agent.name}</h3>
                  <div className={styles.agentRole}>{agent.role}</div>

                  <div className={styles.formula}>
                    <span className={styles.formulaPart}>{agent.formula.split('→')[0]}</span>
                    <span className={styles.arrow}>→</span>
                    <span className={styles.formulaPart}>{agent.formula.split('→')[1]}</span>
                  </div>

                  <div className={styles.divider} />
                  
                  <p className={styles.agentDesc}>{agent.desc}</p>

                  {isActive && (
                    <div className={styles.processingStatus}>
                      <div className={styles.pulse} />
                      <span>Processing...</span>
                    </div>
                  )}
                  {isPast && (
                    <div className={styles.processingStatus} style={{ color: 'var(--silver)' }}>
                      <span>✓ Completed</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
