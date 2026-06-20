'use client';
import React from 'react';
import styles from './ArchitectureLoader.module.css';

interface Agent {
  id: string;
  name: string;
  icon: string;
  description: string;
}

const agents: Agent[] = [
  { id: 'profile', name: 'Profile Builder', icon: '01', description: 'Extracting skills and computing proof scores' },
  { id: 'interview', name: 'Interview Agent', icon: '02', description: 'Generating and evaluating skill questions' },
  { id: 'search', name: 'Job Search Agent', icon: '03', description: 'Running parallel search via SerpAPI' },
  { id: 'analyzer', name: 'JD Analyzer', icon: '04', description: 'Extracting requirements and ghost signals' },
  { id: 'matcher', name: 'Matching Engine', icon: '05', description: 'Scoring fit with vectors and gap analysis' },
];

interface Props {
  activeAgentId: string;
  statusMessage?: string;
}

export default function ArchitectureLoader({ activeAgentId, statusMessage }: Props) {
  const activeIndex = agents.findIndex((agent) => agent.id === activeAgentId);

  return (
    <div className={`glass-panel ${styles.loaderContainer}`}>
      <div className={styles.header}>
        <div className={styles.spinner}></div>
        <h3 className={styles.title}>SAMAS Agents Processing</h3>
      </div>

      {statusMessage && <p className={styles.statusMsg}>{statusMessage}</p>}

      <div className={styles.agentList}>
        {agents.map((agent, index) => {
          const isActive = index === activeIndex;
          const isDone = index < activeIndex;

          let stateClass = styles.pending;
          if (isActive) stateClass = styles.active;
          if (isDone) stateClass = styles.done;

          return (
            <div key={agent.id} className={`${styles.agentItem} ${stateClass}`}>
              <div className={styles.iconWrapper}>
                <span className={styles.icon}>{agent.icon}</span>
                {isDone && <div className={styles.checkmark}>OK</div>}
              </div>
              <div className={styles.details}>
                <h4 className={styles.agentName}>{agent.name}</h4>
                <p className={styles.agentDesc}>{agent.description}</p>
              </div>

              {index < agents.length - 1 && (
                <div className={`${styles.connector} ${isDone ? styles.connectorDone : ''}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
