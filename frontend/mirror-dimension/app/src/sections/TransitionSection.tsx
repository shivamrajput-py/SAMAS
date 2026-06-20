import { useRef } from 'react';
import { useGSAP } from '@gsap/react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface TransitionSectionProps {
  onTransitionProgress?: (progress: number) => void;
}

export default function TransitionSection({ onTransitionProgress }: TransitionSectionProps) {
  const sectionRef = useRef<HTMLDivElement>(null);
  const circleRef = useRef<HTMLDivElement>(null);
  const mRef = useRef<HTMLDivElement>(null);
  const flashRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    if (!sectionRef.current || !circleRef.current || !mRef.current || !flashRef.current || !textRef.current) return;

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top bottom',
        end: 'bottom top',
        scrub: 1,
        onUpdate: (self) => {
          onTransitionProgress?.(self.progress);
        },
      },
    });

    // M letter shrinks and fades
    tl.to(mRef.current, {
      scale: 0.6,
      opacity: 0,
      duration: 0.8,
      ease: 'power2.in',
    }, 0);

    // Clip-path circle expands
    tl.fromTo(circleRef.current,
      { clipPath: 'circle(0% at 50% 50%)' },
      { clipPath: 'circle(150% at 50% 50%)', duration: 1, ease: 'power2.inOut' },
      0.1
    );

    // Flash effect at midpoint
    tl.fromTo(flashRef.current,
      { opacity: 0 },
      { opacity: 0.8, duration: 0.15 },
      0.45
    );
    tl.to(flashRef.current,
      { opacity: 0, duration: 0.15 },
      0.6
    );

    // Transition text fades in then out
    tl.fromTo(textRef.current,
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.25 },
      0.2
    );
    tl.to(textRef.current,
      { opacity: 0, y: -20, duration: 0.25 },
      0.55
    );
  }, { scope: sectionRef });

  return (
    <section
      ref={sectionRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '50vh',
        overflow: 'hidden',
        zIndex: 3,
      }}
    >
      {/* Circle that expands to reveal mirror dimension */}
      <div
        ref={circleRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: '#050508',
          clipPath: 'circle(0% at 50% 50%)',
        }}
      />

      {/* M letter that shrinks */}
      <div
        ref={mRef}
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 5,
          fontFamily: "'Outfit', sans-serif",
          fontSize: 'clamp(200px, 35vw, 500px)',
          fontWeight: 900,
          background: 'linear-gradient(135deg, #7C3AED, #06B6D4)',
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          userSelect: 'none',
          pointerEvents: 'none',
        }}
      >
        M
      </div>

      {/* Flash overlay */}
      <div
        ref={flashRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'linear-gradient(135deg, rgba(255,255,255,0.9), rgba(124,58,237,0.6))',
          opacity: 0,
          zIndex: 6,
          pointerEvents: 'none',
        }}
      />

      {/* Transition text */}
      <div
        ref={textRef}
        className="font-mono"
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 7,
          fontSize: 'clamp(10px, 1vw, 13px)',
          letterSpacing: '0.2em',
          color: '#7C3AED',
          textTransform: 'uppercase',
          whiteSpace: 'nowrap',
          opacity: 0,
          textAlign: 'center',
        }}
      >
        ENTERING MIRROR DIMENSION...
      </div>
    </section>
  );
}
