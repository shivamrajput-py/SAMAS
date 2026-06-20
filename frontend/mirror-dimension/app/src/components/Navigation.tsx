import { useEffect, useRef, useState } from 'react';
import { Menu } from 'lucide-react';

export default function Navigation() {
  const [scrolled, setScrolled] = useState(false);
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const vh = window.innerHeight;
      setScrolled(scrollY > vh * 0.5);

      // Progress line
      if (progressRef.current) {
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = Math.min(scrollY / docHeight, 1);
        progressRef.current.style.width = `${progress * 100}%`;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '72px',
        zIndex: 100,
        background: 'rgba(10, 10, 15, 0.8)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(124, 58, 237, 0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 clamp(24px, 4vw, 60px)',
        transition: 'opacity 0.3s',
        opacity: scrolled ? 1 : 0.7,
      }}
    >
      {/* Wordmark */}
      <div
        className="font-outfit"
        style={{
          fontSize: '14px',
          fontWeight: 700,
          letterSpacing: '0.3em',
          color: '#FFFFFF',
        }}
      >
        SAMAS
      </div>

      {/* Menu icon */}
      <button
        className="interactive"
        style={{
          background: 'none',
          border: 'none',
          cursor: 'none',
          padding: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'box-shadow 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.boxShadow = '0 0 10px rgba(124, 58, 237, 0.5)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        <Menu size={20} color="#A1A1AA" />
      </button>

      {/* Scroll progress line */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          width: '100%',
          height: '1px',
          background: 'rgba(124, 58, 237, 0.1)',
        }}
      >
        <div
          ref={progressRef}
          style={{
            height: '100%',
            width: '0%',
            background: 'linear-gradient(to right, #7C3AED, #06B6D4)',
            transition: 'width 0.1s linear',
          }}
        />
      </div>
    </nav>
  );
}
