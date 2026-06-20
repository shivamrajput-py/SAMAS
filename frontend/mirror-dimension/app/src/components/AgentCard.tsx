import { useRef } from 'react';
import { useGSAP } from '@gsap/react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface AgentCardProps {
  number: string;
  name: string;
  role: string;
  formula: string;
  description: string;
  icon: React.ReactNode;
  glowClass: string;
  accentColor: string;
}

export default function AgentCard({
  number,
  name,
  role,
  formula,
  description,
  icon,
  glowClass,
}: AgentCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    if (!cardRef.current || !contentRef.current) return;

    const elements = contentRef.current.children;

    gsap.fromTo(
      elements,
      { y: 60, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.8,
        stagger: 0.1,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: cardRef.current,
          start: 'top 80%',
          toggleActions: 'play none none reverse',
        },
      }
    );
  }, { scope: cardRef });

  return (
    <div
      ref={cardRef}
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
      }}
    >
      <div
        className={`glass-card ${glowClass}`}
        style={{
          maxWidth: '900px',
          width: '90vw',
          padding: 'clamp(32px, 4vw, 48px)',
          position: 'relative',
          transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
        }}
      >
        {/* Agent number */}
        <div
          className="font-outfit"
          style={{
            position: 'absolute',
            top: 'clamp(16px, 2vw, 24px)',
            left: 'clamp(16px, 2vw, 24px)',
            fontSize: 'clamp(48px, 6vw, 80px)',
            fontWeight: 900,
            color: 'rgba(124, 58, 237, 0.2)',
            lineHeight: 1,
            userSelect: 'none',
          }}
        >
          {number}
        </div>

        {/* Icon */}
        <div
          style={{
            position: 'absolute',
            top: 'clamp(16px, 2vw, 24px)',
            right: 'clamp(16px, 2vw, 24px)',
          }}
        >
          {icon}
        </div>

        <div ref={contentRef}>
          {/* Agent name */}
          <h3
            className="font-outfit"
            style={{
              fontSize: 'clamp(28px, 3.5vw, 48px)',
              fontWeight: 700,
              color: '#FFFFFF',
              letterSpacing: '0.05em',
              marginTop: 'clamp(40px, 5vw, 60px)',
              marginBottom: '8px',
            }}
          >
            {name}
          </h3>

          {/* Agent role */}
          <p
            className="font-mono"
            style={{
              fontSize: 'clamp(11px, 0.9vw, 13px)',
              color: '#06B6D4',
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              marginBottom: '12px',
            }}
          >
            {role}
          </p>

          {/* Conversion formula */}
          <p
            className="font-mono"
            style={{
              fontSize: 'clamp(12px, 1vw, 14px)',
              color: '#A1A1AA',
              marginBottom: '24px',
            }}
          >
            {formula.split('->')[0]}
            <span style={{ color: '#EC4899', margin: '0 8px' }}>&rarr;</span>
            {formula.split('->')[1] || formula.split('→')[1]}
          </p>

          {/* Divider */}
          <div
            style={{
              width: '100%',
              height: '1px',
              background: 'linear-gradient(to right, transparent, rgba(124, 58, 237, 0.3), transparent)',
              margin: '24px 0',
            }}
          />

          {/* Description */}
          <p
            className="font-inter"
            style={{
              fontSize: 'clamp(14px, 1.2vw, 18px)',
              fontWeight: 300,
              color: '#A1A1AA',
              lineHeight: 1.7,
            }}
          >
            {description}
          </p>
        </div>
      </div>
    </div>
  );
}
