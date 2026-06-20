'use client';

import { useRef } from 'react';
import { useGSAP } from '@gsap/react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import styles from './TransitionPortal.module.css';

gsap.registerPlugin(ScrollTrigger);

export default function TransitionPortal() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const circleRef = useRef<HTMLDivElement>(null);
  const text1Ref = useRef<HTMLDivElement>(null);
  const text2Ref = useRef<HTMLDivElement>(null);
  const text3Ref = useRef<HTMLDivElement>(null);
  const crackRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    if (!sectionRef.current || !circleRef.current) return;

    // We target the #hero-m from the SamasHero component
    const mElement = document.getElementById('hero-m');

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top top',
        end: '+=200%',     // Long scroll distance for pinned section
        scrub: 1.5,        // Slower scrub for more control
        pin: true,          // PIN the section!
        anticipatePin: 1,
      },
    });

    // 0.0 - 0.15: M letter shrinks and fades
    if (mElement) {
      tl.to(mElement, {
        scale: 0.4,
        opacity: 0,
        duration: 0.15,
        ease: 'power2.in',
      }, 0);
    }

    // 0.05 - 0.5: Void circle expands slowly
    tl.fromTo(circleRef.current,
      { clipPath: 'circle(0% at 50% 50%)' },
      { clipPath: 'circle(160% at 50% 50%)', duration: 0.5, ease: 'power2.inOut' },
      0.05
    );

    // 0.1: Horizontal crack/light streak flashes
    if (crackRef.current) {
      tl.fromTo(crackRef.current,
        { scaleX: 0, opacity: 0 },
        { scaleX: 1, opacity: 1, duration: 0.1, ease: 'power4.out' },
        0.1
      );
      tl.to(crackRef.current,
        { opacity: 0, duration: 0.15 },
        0.25
      );
    }

    // Sequential narrative text
    // Text 1: "[ SYSTEM DIRECTIVE ]" — 0.15 to 0.35
    if (text1Ref.current) {
      tl.fromTo(text1Ref.current,
        { opacity: 0, y: 20, scale: 0.95 },
        { opacity: 1, y: 0, scale: 1, duration: 0.1, ease: 'power2.out' },
        0.15
      );
      tl.to(text1Ref.current,
        { opacity: 0, y: -15, duration: 0.1 },
        0.3
      );
    }

    // Text 2: "[ ENTERING THE VOID ]" — 0.35 to 0.55
    if (text2Ref.current) {
      tl.fromTo(text2Ref.current,
        { opacity: 0, y: 20, scale: 0.95 },
        { opacity: 1, y: 0, scale: 1, duration: 0.1, ease: 'power2.out' },
        0.38
      );
      tl.to(text2Ref.current,
        { opacity: 0, y: -15, duration: 0.1 },
        0.55
      );
    }

    // Text 3: "[ AGENTS ONLINE ]" — 0.6 to 0.85
    if (text3Ref.current) {
      tl.fromTo(text3Ref.current,
        { opacity: 0, y: 20, scale: 0.95 },
        { opacity: 1, y: 0, scale: 1, duration: 0.1, ease: 'power2.out' },
        0.62
      );
      tl.to(text3Ref.current,
        { opacity: 0, y: -15, duration: 0.15 },
        0.8
      );
    }

  }, { scope: sectionRef });

  return (
    <section ref={sectionRef} className={styles.section}>
      <div ref={circleRef} className={styles.circleBg} />
      
      {/* Horizontal mirror crack / light streak */}
      <div ref={crackRef} className={styles.mirrorCrack} />

      {/* Sequential narrative texts */}
      <div ref={text1Ref} className={`${styles.text} ${styles.text1}`}>
        [ SYSTEM DIRECTIVE ]
      </div>
      <div ref={text2Ref} className={`${styles.text} ${styles.text2}`}>
        [ ENTERING THE VOID ]
      </div>
      <div ref={text3Ref} className={`${styles.text} ${styles.text3}`}>
        [ AGENTS ONLINE ]
      </div>
    </section>
  );
}
