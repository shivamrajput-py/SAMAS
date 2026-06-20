import { Github, Twitter, Linkedin } from 'lucide-react';

const links = ['About', 'Agents', 'Careers', 'Contact'];

export default function FooterSection() {
  return (
    <footer
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '300px',
        background: '#0A0A0F',
        borderTop: '1px solid rgba(124, 58, 237, 0.1)',
        padding: '80px 0 40px',
        zIndex: 5,
      }}
    >
      <div
        style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: '0 clamp(24px, 4vw, 60px)',
        }}
      >
        {/* Top row */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '40px',
            alignItems: 'start',
          }}
        >
          {/* Left column - Wordmark + tagline */}
          <div>
            <div
              className="font-outfit"
              style={{
                fontSize: '14px',
                fontWeight: 700,
                letterSpacing: '0.3em',
                color: '#FFFFFF',
                marginBottom: '12px',
              }}
            >
              SAMAS
            </div>
            <p
              className="font-inter"
              style={{
                fontSize: '14px',
                fontWeight: 300,
                color: '#A1A1AA',
              }}
            >
              Where AI mirrors your potential.
            </p>
          </div>

          {/* Center column - Links */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              gap: '32px',
              flexWrap: 'wrap',
            }}
          >
            {links.map((link) => (
              <a
                key={link}
                href={`#${link.toLowerCase()}`}
                className="interactive font-inter"
                style={{
                  fontSize: '14px',
                  fontWeight: 400,
                  color: '#A1A1AA',
                  textDecoration: 'none',
                  transition: 'color 0.2s ease',
                  position: 'relative',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#FFFFFF';
                  const underline = e.currentTarget.querySelector('.underline') as HTMLElement;
                  if (underline) underline.style.width = '100%';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#A1A1AA';
                  const underline = e.currentTarget.querySelector('.underline') as HTMLElement;
                  if (underline) underline.style.width = '0%';
                }}
              >
                {link}
                <span
                  className="underline"
                  style={{
                    position: 'absolute',
                    bottom: '-2px',
                    left: 0,
                    width: '0%',
                    height: '1px',
                    background: '#7C3AED',
                    transition: 'width 0.3s ease',
                  }}
                />
              </a>
            ))}
          </div>

          {/* Right column - Social icons */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '20px',
            }}
          >
            {[
              { Icon: Github, label: 'GitHub' },
              { Icon: Twitter, label: 'Twitter' },
              { Icon: Linkedin, label: 'LinkedIn' },
            ].map(({ Icon, label }) => (
              <a
                key={label}
                href="#"
                aria-label={label}
                className="interactive"
                style={{
                  color: '#A1A1AA',
                  transition: 'color 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#7C3AED';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#A1A1AA';
                }}
              >
                <Icon size={20} />
              </a>
            ))}
          </div>
        </div>

        {/* Bottom row - Copyright */}
        <div
          style={{
            textAlign: 'center',
            marginTop: '60px',
            paddingTop: '24px',
            borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          }}
        >
          <p
            className="font-inter"
            style={{
              fontSize: '12px',
              fontWeight: 300,
              color: 'rgba(161, 161, 170, 0.5)',
            }}
          >
            &copy; 2025 SAMAS. All rights reserved.
          </p>
        </div>
      </div>

      {/* Ambient floating particles */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          overflow: 'hidden',
          pointerEvents: 'none',
          zIndex: -1,
        }}
      >
        {Array.from({ length: 15 }).map((_, i) => (
          <div
            key={i}
            style={{
              position: 'absolute',
              width: `${2 + Math.random() * 3}px`,
              height: `${2 + Math.random() * 3}px`,
              borderRadius: '50%',
              background: 'rgba(124, 58, 237, 0.3)',
              left: `${Math.random() * 100}%`,
              bottom: 0,
              animation: `float-up ${8 + Math.random() * 12}s linear infinite`,
              animationDelay: `${Math.random() * 10}s`,
            }}
          />
        ))}
      </div>

      <style>{`
        @keyframes float-up {
          0% {
            transform: translateY(0) translateX(0);
            opacity: 0;
          }
          10% {
            opacity: 0.6;
          }
          90% {
            opacity: 0.3;
          }
          100% {
            transform: translateY(-300px) translateX(${Math.random() > 0.5 ? '' : '-'}${20 + Math.random() * 40}px);
            opacity: 0;
          }
        }
      `}</style>
    </footer>
  );
}
