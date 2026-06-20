'use client';

import { useRef, useEffect, useState } from 'react';
import { useGSAP } from '@gsap/react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import styles from './TransitionPortal.module.css';

gsap.registerPlugin(ScrollTrigger);

// ==========================================
// SCRAMBLER TEXT COMPONENT
// ==========================================
const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*!<>{}[]';

function ScramblerText({ text, progress, className }: { text: string; progress: number; className?: string }) {
  const [displayText, setDisplayText] = useState(text);

  useEffect(() => {
    if (progress <= 0) {
      setDisplayText('');
      return;
    }
    
    if (progress >= 1) {
      setDisplayText(text);
      return;
    }

    // Scramble logic
    const resolvedLength = Math.floor(text.length * progress);
    let scrambled = '';
    
    for (let i = 0; i < text.length; i++) {
      if (text[i] === ' ') {
        scrambled += ' ';
      } else if (i < resolvedLength) {
        scrambled += text[i];
      } else {
        scrambled += CHARS[Math.floor(Math.random() * CHARS.length)];
      }
    }
    
    setDisplayText(scrambled);
  }, [text, progress]);

  return <div className={className}>{displayText}</div>;
}

// ==========================================
// MAIN PORTAL COMPONENT
// ==========================================
export default function TransitionPortal() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const circleRef = useRef<HTMLDivElement>(null);
  const crackRef = useRef<HTMLDivElement>(null);

  // State for text scrambling progress
  const [prog1, setProg1] = useState(0);
  const [prog2, setProg2] = useState(0);
  const [prog3, setProg3] = useState(0);

  useGSAP(() => {
    if (!sectionRef.current || !circleRef.current) return;

    const mElement = document.getElementById('hero-m');

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top top',
        end: '+=180%',     // Slightly longer scroll for smoother pacing
        scrub: 1.5,
        pin: true,
        anticipatePin: 1,
      },
    });

    // 0.0 - 0.1: M letter shrinks and fades
    if (mElement) {
      tl.to(mElement, {
        scale: 0.2,
        opacity: 0,
        duration: 0.1,
        ease: 'power2.in',
      }, 0);
    }

    // 0.03 - 0.5: Expand the hole in the light overlay to reveal the void dimension
    tl.fromTo(circleRef.current,
      { '--hole-size': '0%' },
      { '--hole-size': '150%', duration: 0.47, ease: 'power2.inOut' },
      0.03
    );

    // 0.1: Optical shatter flare
    if (crackRef.current) {
      tl.fromTo(crackRef.current,
        { scaleX: 0, opacity: 0, height: '2px' },
        { scaleX: 1.5, opacity: 1, height: '8px', duration: 0.1, ease: 'power4.out' },
        0.1
      );
      tl.to(crackRef.current,
        { opacity: 0, height: '0px', duration: 0.15 },
        0.25
      );
    }

    // Text 1: SYSTEM DIRECTIVE
    tl.to({ val: 0 }, {
      val: 1,
      duration: 0.15,
      ease: 'none',
      onUpdate: function() { setProg1(this.targets()[0].val); }
    }, 0.2);
    tl.to({ val: 1 }, {
      val: -0.1,
      duration: 0.1,
      ease: 'none',
      onUpdate: function() { setProg1(this.targets()[0].val); }
    }, 0.4);

    // Text 2: ENTERING THE VOID
    tl.to({ val: 0 }, {
      val: 1,
      duration: 0.15,
      ease: 'none',
      onUpdate: function() { setProg2(this.targets()[0].val); }
    }, 0.45);
    tl.to({ val: 1 }, {
      val: -0.1,
      duration: 0.1,
      ease: 'none',
      onUpdate: function() { setProg2(this.targets()[0].val); }
    }, 0.65);

    // Text 3: AGENTS ONLINE
    tl.to({ val: 0 }, {
      val: 1,
      duration: 0.15,
      ease: 'none',
      onUpdate: function() { setProg3(this.targets()[0].val); }
    }, 0.7);
    tl.to({ val: 1 }, {
      val: -0.1,
      duration: 0.1,
      ease: 'none',
      onUpdate: function() { setProg3(this.targets()[0].val); }
    }, 0.9);

  }, { scope: sectionRef });

  return (
    <section ref={sectionRef} className={styles.section}>
      {/* The light overlay with an expanding hole that reveals the void canvas behind it */}
      <div ref={circleRef} className={styles.solidOverlay} />
      
      {/* Dynamic mirror fracture */}
      <div ref={crackRef} className={styles.mirrorCrack} />

      {/* Scrambling Narrative Texts */}
      <ScramblerText 
        text="[ INITIALIZING ]" 
        progress={prog1} 
        className={`${styles.text} ${styles.text1} ${prog1 > 0 && prog1 < 1 ? styles.textActive : ''}`} 
      />
      <ScramblerText 
        text="[ DEPLOYING AGENTS ]" 
        progress={prog2} 
        className={`${styles.text} ${styles.text2} ${prog2 > 0 && prog2 < 1 ? styles.textActive : ''}`} 
      />
      <ScramblerText 
        text="[ DIMENSION ACTIVE ]" 
        progress={prog3} 
        className={`${styles.text} ${styles.text3} ${prog3 > 0 && prog3 < 1 ? styles.textActive : ''}`} 
      />
    </section>
  );
}
