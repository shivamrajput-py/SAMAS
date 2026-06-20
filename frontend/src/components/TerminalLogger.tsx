'use client';
import React, { useEffect, useRef } from 'react';
import styles from './TerminalLogger.module.css';

export interface LogEntry {
  id: string;
  agent: string;
  message: string;
  timestamp: Date;
}

interface Props {
  logs: LogEntry[];
  title?: string;
}

export default function TerminalLogger({ logs, title = "SYSTEM TERMINAL" }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className={styles.terminalContainer}>
      <div className={styles.header}>
        <div className={styles.spinner}></div>
        <h3 className={styles.title}>{title}</h3>
      </div>
      <div className={styles.logsArea} ref={scrollRef}>
        {logs.map((log, index) => {
          const isActive = index === logs.length - 1;
          return (
            <div key={log.id} className={`${styles.logLine} ${isActive ? styles.activeLog : ''}`}>
              <span className={styles.logPrefix}>&gt;</span>
              <span className={styles.logMessage}>
                <span className={styles.agentTag}>[{log.agent}]</span> {log.message}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
