'use client';

import { useEffect, useRef, useState } from 'react';
import styles from './SamasHero.module.css';
import Link from 'next/link';

interface Point3D {
  x: number;
  z: number;
  baseY: number;
  mouseOffset: number;
  waveOffset: number;
  waveId: number;
}

type HoverState = 'none' | 'left-bg' | 'left-text' | 'right-bg' | 'right-text';

const BOTTOM_PHRASES_LEFT = [
  '[ BEYOND THE TRADITIONAL SEARCH ]',
  '[ WHERE PROOF REPLACES PROMISES ]',
  '[ YOUR TRUTH, ALGORITHMICALLY VERIFIED ]',
];

const BOTTOM_PHRASES_RIGHT = [
  '[ INTO ALGORITHMIC TRUTH ]',
  '[ FIVE AGENTS. ONE DIMENSION. ]',
  '[ THE MIRROR SEES WHAT YOU CANNOT ]',
];

export default function SamasHero() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoverState, setHoverState] = useState<HoverState>('none');
  const [booted, setBooted] = useState(false);
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [phraseFading, setPhraseFading] = useState(false);
  
  // Refs for animation loop without triggering React renders
  const stateRef = useRef<HoverState>('none');
  const pointsRef = useRef<Point3D[]>([]);
  const waveRef = useRef<{ id: number; startX: number; direction: 1 | -1; startTime: number } | null>(null);
  const waveIdCounter = useRef(0);
  const mouseRef = useRef({ x: -1000, y: -1000, active: false });

  // Boot sequence
  useEffect(() => {
    const timer = setTimeout(() => setBooted(true), 300);
    return () => clearTimeout(timer);
  }, []);

  // Cycling bottom text
  useEffect(() => {
    const interval = setInterval(() => {
      setPhraseFading(true);
      setTimeout(() => {
        setPhraseIndex(prev => (prev + 1) % BOTTOM_PHRASES_LEFT.length);
        setPhraseFading(false);
      }, 600);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Only update wave when hovering specifically over the TEXT hitboxes
    const oldState = stateRef.current;
    const isNowLeftText = hoverState === 'left-text';
    const wasLeftText = oldState === 'left-text';
    const isNowRightText = hoverState === 'right-text';
    const wasRightText = oldState === 'right-text';

    if (canvasRef.current) {
      if (isNowLeftText && !wasLeftText) {
        waveIdCounter.current++;
        waveRef.current = { id: waveIdCounter.current, startX: 0, direction: 1, startTime: performance.now() };
      } 
      else if (isNowRightText && !wasRightText) {
        waveIdCounter.current++;
        waveRef.current = { id: waveIdCounter.current, startX: 0, direction: -1, startTime: performance.now() };
      } 
      else if (hoverState !== 'left-text' && hoverState !== 'right-text') {
        waveRef.current = null;
      }
    }
    
    stateRef.current = hoverState;
  }, [hoverState]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    let ctx = canvas.getContext('2d', { alpha: false }); // Optimize
    let W = 0;
    let H = 0;
    
    // 3D Engine Constants
    const FOV = 400;
    const SPACING_X = 60; // Spread out more to cover the same width with fewer points
    const SPACING_Z = 60; 
    const GRID_SIZE_X = 60; // Reduced from 100
    const GRID_SIZE_Z = 40; // Reduced from 60
    const CAMERA_Y = -150;
    
    const WAVE_DURATION = 1200;
    const WAVE_THICKNESS = 600;

    const easeOutCubic = (x: number): number => {
      return 1 - Math.pow(1 - x, 3);
    };

    function init() {
      const dpr = window.devicePixelRatio || 1;
      const rect = container!.getBoundingClientRect();
      W = rect.width;
      H = rect.height;
      canvas!.width = W * dpr;
      canvas!.height = H * dpr;
      ctx!.scale(dpr, dpr);
      canvas!.style.width = `${W}px`;
      canvas!.style.height = `${H}px`;

      pointsRef.current = [];
      const startX = -(GRID_SIZE_X * SPACING_X) / 2;
      const startZ = 100;
      
      for (let zIndex = GRID_SIZE_Z - 1; zIndex >= 0; zIndex--) {
        for (let xIndex = 0; xIndex < GRID_SIZE_X; xIndex++) {
          pointsRef.current.push({
            x: startX + xIndex * SPACING_X,
            z: startZ + zIndex * SPACING_Z,
            baseY: 0,
            mouseOffset: 0,
            waveOffset: 0,
            waveId: 0,
          });
        }
      }
    }

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas!.getBoundingClientRect();
      mouseRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        active: true
      };
    };

    const handleMouseLeave = () => {
      mouseRef.current.active = false;
    };

    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseleave', handleMouseLeave);

    let animationFrame: number;

    function draw() {
      const now = performance.now();
      const time = now * 0.001;
      
      ctx!.fillStyle = '#e6e4df';
      ctx!.fillRect(0, 0, W, H);
      
      const grad = ctx!.createRadialGradient(W/2, H/2, 0, W/2, H/2, W);
      grad.addColorStop(0, '#eeebe5');
      grad.addColorStop(1, '#e6e4df');
      ctx!.fillStyle = grad;
      ctx!.fillRect(0, 0, W, H);

      const cx = W / 2;
      const cy = H * 0.6;

      const wave = waveRef.current;
      let waveX = 0;
      if (wave) {
        const progress = Math.min((now - wave.startTime) / WAVE_DURATION, 1);
        const easedProgress = easeOutCubic(progress);
        const travelDist = (GRID_SIZE_X * SPACING_X) / 2;
        waveX = wave.direction === 1 ? easedProgress * travelDist : -easedProgress * travelDist;
      }

      const mouse = mouseRef.current;

      for (const p of pointsRef.current) {
        const freqX = 0.002;
        const freqZ = 0.003;
        const amplitude = 100;
        p.baseY = Math.sin(p.x * freqX + time) * Math.cos(p.z * freqZ + time * 0.8) * amplitude;

        const scale = FOV / (FOV + p.z);
        const projX = p.x * scale + cx;
        
        const projYBase = (p.baseY - CAMERA_Y) * scale + cy;

        p.mouseOffset *= 0.80;
        if (mouse.active) {
          const dx = projX - mouse.x;
          const dy = projYBase - mouse.y;
          const distSq = dx * dx + dy * dy;
          if (distSq < 40000) {
            const dist = Math.sqrt(distSq);
            const force = (200 - dist) / 200;
            p.mouseOffset -= force * 40;
          }
        }

        p.waveOffset *= 0.85;
        if (wave) {
          const distToWave = Math.abs(p.x - waveX);
          if (distToWave < WAVE_THICKNESS) {
             const progressToCenter = 1 - (distToWave / WAVE_THICKNESS);
             const waveForce = progressToCenter * progressToCenter;
             p.waveOffset -= waveForce * 35;
          }
        }

        const finalY = p.baseY + p.mouseOffset + p.waveOffset;
        const projY = (finalY - CAMERA_Y) * scale + cy;

        if (p.z < -FOV + 10) continue;
        if (projY > H + 50 || projY < -50 || projX < -50 || projX > W + 50) continue;

        const totalOffset = Math.abs(p.mouseOffset) + Math.abs(p.waveOffset);
        let baseSize = 2.5 * scale;
        
        if (totalOffset > 15) {
           baseSize = 5 * scale;
           ctx!.fillStyle = wave && wave.direction === 1 
              ? `rgba(212, 122, 67, ${0.9 * scale})`
              : `rgba(140, 123, 101, ${0.9 * scale})`;
        } else {
           ctx!.fillStyle = `rgba(58, 56, 53, ${0.7 * scale})`; 
        }

        ctx!.beginPath();
        ctx!.arc(projX, projY, Math.max(0.5, baseSize), 0, Math.PI * 2);
        ctx!.fill();
      }

      animationFrame = requestAnimationFrame(draw);
    }

    init();
    draw();

    window.addEventListener('resize', init);
    return () => {
      window.removeEventListener('resize', init);
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseleave', handleMouseLeave);
      cancelAnimationFrame(animationFrame);
    };
  }, []);

  const isLeftBg = hoverState === 'left-bg';
  const isLeftText = hoverState === 'left-text';
  const isRightBg = hoverState === 'right-bg';
  const isRightText = hoverState === 'right-text';

  const saVisible = isLeftBg || isLeftText || isRightText;
  const saTranslate = (isRightBg || hoverState === 'none') ? 'translateX(100%)' : 'translateX(0)';

  const asVisible = isRightBg || isRightText || isLeftText;
  const asTranslate = (isLeftBg || hoverState === 'none') ? 'translateX(-100%)' : 'translateX(0)';

  return (
    <section ref={containerRef} className={`${styles.hero} ${booted ? styles.booted : ''}`}>
      <canvas ref={canvasRef} className={styles.canvas} />

      {/* Boot overlay — fades out after boot */}
      <div className={styles.bootOverlay} />

      {/* Background Hover Zones */}
      <div className={styles.hoverZones}>
        <div 
          className={styles.zoneLeft} 
          onMouseEnter={() => setHoverState(s => s === 'left-text' ? s : 'left-bg')}
          onMouseLeave={() => setHoverState('none')}
        />
        <div 
          className={styles.zoneRight} 
          onMouseEnter={() => setHoverState(s => s === 'right-text' ? s : 'right-bg')}
          onMouseLeave={() => setHoverState('none')}
        />
      </div>

      {/* Corner HUD Typography — types in on boot */}
      <div className={`${styles.cornerHUD} ${booted ? styles.hudVisible : ''}`}>
        <div className={styles.hudTop}>
          <p className={styles.hudTopLeft}>SAMAS</p>
          <p className={styles.hudTopRight}>IS A MULTI-AGENT JOB INTELLIGENCE SYSTEM</p>
        </div>
        <div className={styles.hudBottom}>
          <p className={`${styles.hudBottomLeft} ${phraseFading ? styles.phraseFading : ''}`}>
            {BOTTOM_PHRASES_LEFT[phraseIndex]}
          </p>
          <p className={`${styles.hudBottomRight} ${phraseFading ? styles.phraseFading : ''}`}>
            {BOTTOM_PHRASES_RIGHT[phraseIndex]}
          </p>
        </div>
      </div>

      <div className={styles.overlay}>
        <div className={styles.textContainer}>
          
          <div className={styles.textTrack}>
            {/* SA */}
            <div 
              className={styles.saHitbox}
              onMouseEnter={() => setHoverState('left-text')}
              onMouseLeave={() => setHoverState('left-bg')}
            >
              <h1 
                className={styles.saText}
                style={{
                  opacity: saVisible ? 1 : 0,
                  transform: saTranslate,
                  filter: saVisible ? 'blur(0)' : 'blur(10px)',
                }}
              >
                SA
              </h1>
            </div>

            {/* M - Center Sticky — Creative Treatment */}
            <div id="hero-m">
              <div 
                className={`${styles.centerM} ${booted ? styles.mBooted : ''}`}
              >
                <h1 className={styles.mText}>M</h1>
                {/* Ambient glow ring that breathes */}
                <div className={styles.mGlowRing} />
                {/* Subtle orbital particle */}
                <div className={styles.mOrbital} />
              </div>
            </div>

            {/* AS */}
            <div 
              className={styles.asHitbox}
              onMouseEnter={() => setHoverState('right-text')}
              onMouseLeave={() => setHoverState('right-bg')}
            >
              <h1 
                className={styles.asText}
                style={{
                  opacity: asVisible ? 1 : 0,
                  transform: asTranslate,
                  filter: asVisible ? 'blur(0)' : 'blur(10px)',
                }}
              >
                AS
              </h1>
            </div>
          </div>

        </div>

        <div className={styles.taglineContainer}>
          <p className={styles.tagline}>Where AI mirrors your potential.</p>
          <div className={styles.mirrorLine} />
          <p className={styles.taglineMirror}>Where AI mirrors your potential.</p>
          
          <div className={styles.actionWrap}>
            <Link href="/find" className={styles.enterBtn}>
              ENTER THE SYSTEM <span className={styles.arrow}>→</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Scroll Indicator */}
      <div className={styles.scrollIndicator}>
        <span className={styles.scrollText}>SCROLL TO ENTER</span>
        <div className={styles.scrollChevron} />
      </div>
    </section>
  );
}
