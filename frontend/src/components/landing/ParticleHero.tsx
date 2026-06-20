'use client';
/* eslint-disable react-hooks/immutability */

import { useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import styles from './ParticleHero.module.css';

/* constants */
const DOT_BASE_RADIUS = 1.4;
const DOT_MAX_RADIUS = 3.2;
const INFLUENCE_RADIUS = 120;
const RETURN_SPEED = 0.06; // lerp factor for glow fade-out
const DIM_COLOR: [number, number, number] = [26, 26, 46]; // #1a1a2e
const GLOW_COLOR: [number, number, number] = [0, 240, 255]; // --accent-cyan

interface Dot {
  x: number;
  y: number;
  /** 0 = fully dim, 1 = fully glowing */
  intensity: number;
}

export default function ParticleHero() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef<{ x: number; y: number; active: boolean }>({
    x: -9999,
    y: -9999,
    active: false,
  });
  const dotsRef = useRef<Dot[]>([]);
  const rafRef = useRef<number>(0);
  const spacingRef = useRef(20);

  /* build the dot grid */
  const buildGrid = useCallback((width: number, height: number) => {
    const isMobile = width < 640;
    const spacing = isMobile ? 30 : 20;
    spacingRef.current = spacing;

    const cols = Math.ceil(width / spacing) + 1;
    const rows = Math.ceil(height / spacing) + 1;
    const dots: Dot[] = [];

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        dots.push({ x: c * spacing, y: r * spacing, intensity: 0 });
      }
    }
    dotsRef.current = dots;
  }, []);

  /* main animation loop */
  const animate = useCallback(
    (ctx: CanvasRenderingContext2D, width: number, height: number) => {
      ctx.clearRect(0, 0, width, height);

      const { x: mx, y: my, active } = mouseRef.current;
      const dots = dotsRef.current;
      const invRadius = 1 / INFLUENCE_RADIUS;

      for (let i = 0; i < dots.length; i++) {
        const dot = dots[i];

        /* compute target intensity based on distance to cursor */
        let target = 0;
        if (active) {
          const dx = dot.x - mx;
          const dy = dot.y - my;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < INFLUENCE_RADIUS) {
            target = 1 - dist * invRadius;
          }
        }

        /* lerp toward target for smooth transitions */
        dot.intensity += (target - dot.intensity) * RETURN_SPEED;
        if (dot.intensity < 0.003) dot.intensity = 0;

        const t = dot.intensity;

        /* interpolate colour */
        const r = DIM_COLOR[0] + (GLOW_COLOR[0] - DIM_COLOR[0]) * t;
        const g = DIM_COLOR[1] + (GLOW_COLOR[1] - DIM_COLOR[1]) * t;
        const b = DIM_COLOR[2] + (GLOW_COLOR[2] - DIM_COLOR[2]) * t;

        /* interpolate radius */
        const radius = DOT_BASE_RADIUS + (DOT_MAX_RADIUS - DOT_BASE_RADIUS) * t;

        ctx.beginPath();
        ctx.arc(dot.x, dot.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgb(${r | 0},${g | 0},${b | 0})`;
        ctx.fill();

        /* glow halo for bright dots */
        if (t > 0.25) {
          ctx.beginPath();
          ctx.arc(dot.x, dot.y, radius + 4 * t, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(0,240,255,${0.12 * t})`;
          ctx.fill();
        }
      }

      rafRef.current = requestAnimationFrame(() => animate(ctx, width, height));
    },
    [],
  );

  /* setup and teardown */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      buildGrid(w, h);
    };

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        active: true,
      };
    };

    const handleMouseLeave = () => {
      mouseRef.current = { ...mouseRef.current, active: false };
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 0) return;
      const touch = e.touches[0];
      const rect = canvas.getBoundingClientRect();
      mouseRef.current = {
        x: touch.clientX - rect.left,
        y: touch.clientY - rect.top,
        active: true,
      };
    };

    const handleTouchEnd = () => {
      mouseRef.current = { ...mouseRef.current, active: false };
    };

    resize();
    rafRef.current = requestAnimationFrame(() =>
      animate(ctx, canvas.clientWidth, canvas.clientHeight),
    );

    window.addEventListener('resize', resize);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseleave', handleMouseLeave);
    canvas.addEventListener('touchmove', handleTouchMove, { passive: true });
    canvas.addEventListener('touchend', handleTouchEnd);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mouseleave', handleMouseLeave);
      canvas.removeEventListener('touchmove', handleTouchMove);
      canvas.removeEventListener('touchend', handleTouchEnd);
    };
  }, [animate, buildGrid]);

  return (
    <section className={styles.hero} aria-label="SAMAS hero section">
      <canvas ref={canvasRef} className={styles.canvas} aria-hidden="true" />

      <div className={styles.overlay}>
        <h1 className={styles.title}>SAMAS</h1>

        <p className={styles.tagline}>
          5 AI Agents. One Mission. Your Perfect Job.
        </p>

        <Link
          href="/find"
          className={styles.cta}
          aria-label="Initialize job search"
        >
          [ INITIALIZE SEARCH ]
        </Link>
      </div>

      <div className={styles.terminal} aria-hidden="true">
        <span>
          {'> system.agents.loaded: 5 | status: READY | protocol: AGENTIC'}
        </span>
        <span className={styles.cursor} />
      </div>
    </section>
  );
}
