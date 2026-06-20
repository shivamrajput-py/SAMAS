'use client';

import React from 'react';
import NeuralCanvas from './NeuralCanvas';
import styles from './VoidDimension.module.css';

export default function VoidDimension({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.wrapper}>
      {/* The single continuous neural canvas that spans both sections */}
      <NeuralCanvas className={styles.canvas} />
      
      {/* The sections (TransitionPortal & AgentShowcase) sit on top */}
      <div className={styles.content}>
        {children}
      </div>
    </div>
  );
}
