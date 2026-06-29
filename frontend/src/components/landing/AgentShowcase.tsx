'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useGSAP } from '@gsap/react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Hexagon, CheckSquare, Target, Cpu, GitMerge } from 'lucide-react';
import styles from './AgentShowcase.module.css';

gsap.registerPlugin(ScrollTrigger);

interface Agent {
  code: string;
  name: string;
  role: string;
  formula: string;
  desc: string;
  color: string;
  icon: React.ElementType;
}

const AGENTS: Agent[] = [
  {
    code: '01',
    name: 'PRISM',
    role: 'Identity Architect',
    formula: 'Resume → Verified Profile',
    desc: 'You upload your resume and links. This agent reads everything (your PDF, your GitHub, your portfolio) and builds a verified skill profile with proof scores. No fluff, just facts.',
    color: '#d47a43', // Earthy Amber
    icon: Hexagon
  },
  {
    code: '02',
    name: 'LUCID',
    role: 'Truth Validator',
    formula: 'Input → Skill Assessment',
    desc: 'Tests what you actually know. Generates adaptive MCQs and open-ended questions, then mathematically adjusts your skill scores based on your answers.',
    color: '#8c7b65', // Muted Sage
    icon: CheckSquare
  },
  {
    code: '03',
    name: 'RADAR',
    role: 'Market Sweeper',
    formula: 'Profile → Global Targets',
    desc: 'Takes your verified profile and searches across job boards. Finds relevant roles matching your skills, deduplicates results, and prepares a clean job dataset.',
    color: '#c2a886', // Warm Gold
    icon: Target
  },
  {
    code: '04',
    name: 'CIPHER',
    role: 'Deep Analyst',
    formula: 'Syntax → Core Requirements',
    desc: "Reads every job description deeply. Extracts real requirements, detects ghost job postings, and maps each role's needs against your profile.",
    color: '#a85642', // Brick Red
    icon: Cpu
  },
  {
    code: '05',
    name: 'KAIROS',
    role: 'Probability Engine',
    formula: 'Vectors → Success Tiers',
    desc: 'The final scoring engine. Combines skill overlap, experience alignment, and semantic similarity to rank every job into Easy Get, Best Match, or Stretch Goal.',
    color: '#b8a99a', // Warm Sand
    icon: GitMerge
  },
];

// ─── Agent Card ───
function AgentCard({ agent, index }: { agent: Agent; index: number }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const connectionRef = useRef<HTMLDivElement>(null);

  const isEven = index % 2 === 0;

  useGSAP(() => {
    if (!cardRef.current || !contentRef.current || !wrapperRef.current || !connectionRef.current) return;

    // Card Slide-in
    gsap.fromTo(
      wrapperRef.current,
      { x: isEven ? -100 : 100, opacity: 0 },
      {
        x: 0,
        opacity: 1,
        duration: 1.2,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: wrapperRef.current,
          start: 'top 80%',
          toggleActions: 'play none none reverse',
        },
      }
    );

    // Enhancement 2: Connection point flash animation on scroll entry
    const connTl = gsap.timeline({
      scrollTrigger: {
        trigger: wrapperRef.current,
        start: 'top 80%',
        toggleActions: 'play none none reverse',
      },
    });

    connTl
      // Start invisible & tiny
      .fromTo(
        connectionRef.current,
        { scale: 0, opacity: 0 },
        {
          scale: 2.2,
          opacity: 1,
          duration: 0.3,
          ease: 'power2.out',
        }
      )
      // Flash: bright burst
      .to(connectionRef.current, {
        boxShadow: `0 0 40px ${agent.color}, 0 0 80px ${agent.color}`,
        duration: 0.15,
        ease: 'power1.in',
      })
      // Settle to normal state
      .to(connectionRef.current, {
        scale: 1,
        boxShadow: `0 0 20px ${agent.color}`,
        duration: 0.6,
        ease: 'elastic.out(1, 0.5)',
      });

    // Staggered text reveal
    const elements = contentRef.current.children;
    gsap.fromTo(
      elements,
      { y: 30, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.8,
        stagger: 0.1,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: wrapperRef.current,
          start: 'top 75%',
          toggleActions: 'play none none reverse',
        },
      }
    );

    // Subtle 3D Tilt effect on mouse move
    const card = cardRef.current;
    const handleMouseMove = (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -10;
      const rotateY = ((x - centerX) / centerX) * 10;

      gsap.to(card, {
        rotateX,
        rotateY,
        duration: 0.5,
        ease: 'power2.out',
        transformPerspective: 1000,
      });
    };

    const handleMouseLeave = () => {
      gsap.to(card, {
        rotateX: 0,
        rotateY: 0,
        duration: 0.5,
        ease: 'power2.out',
      });
    };

    card.addEventListener('mousemove', handleMouseMove);
    card.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      card.removeEventListener('mousemove', handleMouseMove);
      card.removeEventListener('mouseleave', handleMouseLeave);
    };

  }, { scope: wrapperRef });

  const Icon = agent.icon;

  return (
    <div ref={wrapperRef} className={`${styles.timelineNode} ${isEven ? styles.nodeLeft : styles.nodeRight}`}>
      
      {/* The glowing connection point to the center line */}
      <div
        ref={connectionRef}
        className={styles.connectionPoint}
        style={{ '--agent-color': agent.color } as React.CSSProperties}
      />

      <div ref={cardRef} className={styles.cardWrapper}>
        <div 
          className={styles.glassCard}
          style={{ '--agent-color': agent.color } as React.CSSProperties}
        >
          <div className={styles.agentNumber}>{agent.code}</div>
          
          <div className={styles.iconWrapper}>
            <Icon size={48} color={agent.color} strokeWidth={1.5} />
          </div>

          <div ref={contentRef} className={styles.content}>
            <h3 className={styles.agentName}>{agent.name}</h3>
            <div className={styles.agentRole}>
              {agent.role}
            </div>

            <div className={styles.formula}>
              <span className={styles.formulaPart}>{agent.formula.split('→')[0]}</span>
              <span className={styles.arrow}>→</span>
              <span className={styles.formulaPart}>{agent.formula.split('→')[1]}</span>
            </div>

            <div className={styles.divider} />
            
            <p className={styles.agentDesc}>{agent.desc}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AgentShowcase() {
  const lineRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    if (!lineRef.current || !containerRef.current) return;

    // The central line glowing progressively as you scroll
    gsap.fromTo(
      lineRef.current,
      { scaleY: 0 },
      {
        scaleY: 1,
        ease: 'none',
        scrollTrigger: {
          trigger: containerRef.current,
          start: 'top 50%',
          end: 'bottom 80%',
          scrub: true,
        },
      }
    );
  }, { scope: containerRef });

  return (
    <section className={styles.section} id="agents" ref={containerRef}>
      
      {/* Background ambient light */}
      <div className={styles.ambientGlow} />

      <div className={styles.header}>
        <p className={styles.label}>[ SYSTEM DIRECTIVE ]</p>
        <h2 className={styles.title}>THE AGENTIC DIMENSION</h2>
        <p className={styles.subtitle}>
          Upload your resume and watch SAMAS agents mirror your best potential jobs.
        </p>
      </div>

      <div className={styles.timelineContainer}>
        {/* The central glowing neural link */}
        <div className={styles.centerLineTrack}>
          <div ref={lineRef} className={styles.centerLineFill} />
        </div>

        {AGENTS.map((agent, index) => (
          <AgentCard key={agent.code} agent={agent} index={index} />
        ))}
      </div>
    </section>
  );
}
