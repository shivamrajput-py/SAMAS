import { useEffect, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';

type HoverState = 'none' | 'left' | 'right';

export default function MirrorInstallation() {
  const [hoverState, setHoverState] = useState<HoverState>('none');
  const heroRef = useRef<HTMLDivElement>(null);
  const scrollIndicatorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      if (scrollIndicatorRef.current) {
        const opacity = Math.max(0, 1 - window.scrollY / (window.innerHeight * 0.3));
        scrollIndicatorRef.current.style.opacity = String(opacity);
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const isLeftActive = hoverState === 'left';
  const isRightActive = hoverState === 'right';

  return (
    <section
      ref={heroRef}
      id="hero"
      style={{
        position: 'relative',
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: '#0A0A0F',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Mirror line through center */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '-10%',
          transform: 'translateX(-50%)',
          width: '2px',
          height: '120vh',
          background: 'linear-gradient(to bottom, transparent, rgba(124, 58, 237, 0.4), rgba(6, 182, 212, 0.3), transparent)',
          animation: 'shimmer 3s ease-in-out infinite',
          opacity: isLeftActive || isRightActive ? 0.8 : 0.4,
          transition: 'opacity 0.4s ease',
          zIndex: 5,
          pointerEvents: 'none',
        }}
      />

      {/* Left hover zone */}
      <div
        className="interactive"
        onMouseEnter={() => setHoverState('left')}
        onMouseLeave={() => setHoverState('none')}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: '50%',
          height: '100%',
          zIndex: 10,
          cursor: 'none',
        }}
      />

      {/* Right hover zone */}
      <div
        className="interactive"
        onMouseEnter={() => setHoverState('right')}
        onMouseLeave={() => setHoverState('none')}
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          width: '50%',
          height: '100%',
          zIndex: 10,
          cursor: 'none',
        }}
      />

      {/* Light ray from left */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          width: '50%',
          height: '200px',
          background: 'linear-gradient(to right, rgba(124, 58, 237, 0.15), transparent)',
          opacity: isLeftActive ? 1 : 0,
          transition: 'opacity 0.5s ease',
          zIndex: 2,
          pointerEvents: 'none',
        }}
      />

      {/* Light ray from right */}
      <div
        style={{
          position: 'absolute',
          right: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          width: '50%',
          height: '200px',
          background: 'linear-gradient(to left, rgba(6, 182, 212, 0.15), transparent)',
          opacity: isRightActive ? 1 : 0,
          transition: 'opacity 0.5s ease',
          zIndex: 2,
          pointerEvents: 'none',
        }}
      />

      {/* SA text - left side */}
      <div
        style={{
          position: 'absolute',
          left: 'calc(50% - 25vw)',
          top: '50%',
          transform: isRightActive
            ? 'translateY(-50%) translateX(0) scaleX(-1)'
            : 'translateY(-50%)',
          zIndex: 8,
          fontFamily: "'Outfit', sans-serif",
          fontSize: 'clamp(100px, 18vw, 320px)',
          fontWeight: 900,
          letterSpacing: '0.05em',
          color: isLeftActive || isRightActive
            ? 'rgba(255, 255, 255, 0.9)'
            : 'rgba(255, 255, 255, 0.08)',
          textShadow: isLeftActive
            ? '0 0 40px rgba(124, 58, 237, 0.5)'
            : isRightActive
            ? '0 0 40px rgba(124, 58, 237, 0.5)'
            : 'none',
          opacity: isRightActive ? 1 : isLeftActive ? 1 : 1,
          filter: isRightActive ? 'blur(0)' : 'blur(0)',
          transition: 'all 0.6s cubic-bezier(0.23, 1, 0.32, 1)',
          willChange: 'transform, opacity, filter',
          userSelect: 'none',
          pointerEvents: 'none',
        }}
      >
        SA
      </div>

      {/* M - center mirror */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 9,
          fontFamily: "'Outfit', sans-serif",
          fontSize: 'clamp(100px, 18vw, 320px)',
          fontWeight: 900,
          letterSpacing: '0.05em',
          background: 'linear-gradient(135deg, #7C3AED, #06B6D4)',
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          animation: 'pulse-glow 3s ease-in-out infinite',
          userSelect: 'none',
          pointerEvents: 'none',
        }}
      >
        M
      </div>

      {/* AS text - right side */}
      <div
        style={{
          position: 'absolute',
          right: 'calc(50% - 25vw)',
          top: '50%',
          transform: isLeftActive
            ? 'translateY(-50%) translateX(0) scaleX(-1)'
            : 'translateY(-50%)',
          zIndex: 8,
          fontFamily: "'Outfit', sans-serif",
          fontSize: 'clamp(100px, 18vw, 320px)',
          fontWeight: 900,
          letterSpacing: '0.05em',
          color: isLeftActive || isRightActive
            ? 'rgba(255, 255, 255, 0.9)'
            : 'rgba(255, 255, 255, 0.08)',
          textShadow: isLeftActive
            ? '0 0 40px rgba(124, 58, 237, 0.5)'
            : isRightActive
            ? '0 0 40px rgba(124, 58, 237, 0.5)'
            : 'none',
          opacity: isLeftActive ? 1 : isRightActive ? 1 : 1,
          filter: isLeftActive ? 'blur(0)' : 'blur(0)',
          transition: 'all 0.6s cubic-bezier(0.23, 1, 0.32, 1)',
          willChange: 'transform, opacity, filter',
          userSelect: 'none',
          pointerEvents: 'none',
        }}
      >
        AS
      </div>

      {/* Tagline */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: 'calc(50% + clamp(60px, 10vw, 160px))',
          transform: 'translateX(-50%)',
          zIndex: 8,
          textAlign: 'center',
          pointerEvents: 'none',
        }}
      >
        <p
          className="font-inter"
          style={{
            fontSize: 'clamp(14px, 1.5vw, 20px)',
            fontWeight: 300,
            color: '#A1A1AA',
            whiteSpace: 'nowrap',
          }}
        >
          Where AI mirrors your potential.
        </p>
        {/* Mirrored reflection of tagline */}
        <p
          className="font-inter"
          style={{
            fontSize: 'clamp(14px, 1.5vw, 20px)',
            fontWeight: 300,
            color: '#A1A1AA',
            opacity: 0.12,
            transform: 'scaleY(-1)',
            maskImage: 'linear-gradient(to bottom, rgba(0,0,0,0.4), transparent)',
            WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,0.4), transparent)',
            marginTop: '2px',
            whiteSpace: 'nowrap',
          }}
        >
          Where AI mirrors your potential.
        </p>
      </div>

      {/* Scroll indicator */}
      <div
        ref={scrollIndicatorRef}
        style={{
          position: 'absolute',
          bottom: '40px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px',
          animation: 'scroll-pulse 2s ease-in-out infinite',
          pointerEvents: 'none',
        }}
      >
        <span
          className="font-mono"
          style={{
            fontSize: '10px',
            letterSpacing: '0.2em',
            color: '#A1A1AA',
            textTransform: 'uppercase',
          }}
        >
          Scroll to enter
        </span>
        <ChevronDown size={16} color="#A1A1AA" />
      </div>
    </section>
  );
}
