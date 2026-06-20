import { useEffect, useRef } from 'react';
import AgentCard from '../components/AgentCard';
import { PrismIcon, OracleIcon, RadarIcon, CortexIcon, NexusIcon } from '../components/AgentIcons';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const agents = [
  {
    number: '01',
    name: 'PRISM',
    role: 'Profile Decoder',
    formula: 'Resume → proof map',
    description: 'Reads your resume and external links, extracts granular skills, then turns every claim into a proof score so SAMAS knows what is real.',
    icon: <PrismIcon color="#7C3AED" size={48} />,
    glowClass: 'agent-glow-prism',
    accentColor: '#7C3AED',
    rgb: [0.486, 0.227, 0.929] as [number, number, number],
  },
  {
    number: '02',
    name: 'ORACLE',
    role: 'Skill Verifier',
    formula: 'Answers → verified scores',
    description: 'Runs a focused technical interview. Strong answers boost hidden skills; weak answers expose gaps before the job market does.',
    icon: <OracleIcon color="#06B6D4" size={48} />,
    glowClass: 'agent-glow-oracle',
    accentColor: '#06B6D4',
    rgb: [0.024, 0.714, 0.831] as [number, number, number],
  },
  {
    number: '03',
    name: 'RADAR',
    role: 'Job Hunter',
    formula: 'Titles → jobs',
    description: 'Converts the verified profile into search titles, fans out across job results, and deduplicates the noise into a clean opportunity field.',
    icon: <RadarIcon color="#EC4899" size={48} />,
    glowClass: 'agent-glow-radar',
    accentColor: '#EC4899',
    rgb: [0.925, 0.286, 0.6] as [number, number, number],
  },
  {
    number: '04',
    name: 'CORTEX',
    role: 'JD Analyst',
    formula: 'JD text → requirements',
    description: 'Parses each job description, extracts required skills, flags suspicious listings, and builds the semantic vectors used for matching.',
    icon: <CortexIcon color="#10B981" size={48} />,
    glowClass: 'agent-glow-cortex',
    accentColor: '#10B981',
    rgb: [0.063, 0.725, 0.506] as [number, number, number],
  },
  {
    number: '05',
    name: 'NEXUS',
    role: 'Match Engine',
    formula: 'Profile x JD → tier',
    description: 'Scores every role against your proof map and separates easy wins, best matches, and stretch goals with clear learning gaps.',
    icon: <NexusIcon color="#F59E0B" size={48} />,
    glowClass: 'agent-glow-nexus',
    accentColor: '#F59E0B',
    rgb: [0.961, 0.62, 0.043] as [number, number, number],
  },
];

interface AgentSectionProps {
  onAgentChange?: (rgb: [number, number, number]) => void;
}

export default function AgentSection({ onAgentChange }: AgentSectionProps) {
  const sectionRef = useRef<HTMLDivElement>(null);
  const triggersRef = useRef<ScrollTrigger[]>([]);

  useEffect(() => {
    if (!sectionRef.current) return;

    // Create ScrollTrigger for each agent to detect which is in view
    const cards = sectionRef.current.querySelectorAll('[data-agent-index]');

    cards.forEach((card, index) => {
      const trigger = ScrollTrigger.create({
        trigger: card,
        start: 'top center',
        end: 'bottom center',
        onEnter: () => onAgentChange?.(agents[index].rgb),
        onEnterBack: () => onAgentChange?.(agents[index].rgb),
      });
      triggersRef.current.push(trigger);
    });

    return () => {
      triggersRef.current.forEach(t => t.kill());
      triggersRef.current = [];
    };
  }, [onAgentChange]);

  return (
    <section
      ref={sectionRef}
      id="agents"
      style={{
        position: 'relative',
        width: '100%',
        zIndex: 4,
        background: 'transparent',
      }}
    >
      {/* Section header */}
      <div
        style={{
          textAlign: 'center',
          paddingTop: 'clamp(60px, 10vh, 120px)',
          paddingBottom: '40px',
        }}
      >
        <p
          className="font-mono"
          style={{
            fontSize: 'clamp(12px, 1vw, 14px)',
            letterSpacing: '0.3em',
            color: '#7C3AED',
            textTransform: 'uppercase',
            marginBottom: '16px',
          }}
        >
          AGENT PROTOCOL
        </p>
        <p
          className="font-inter"
          style={{
            fontSize: 'clamp(16px, 1.5vw, 22px)',
            fontWeight: 300,
            color: '#A1A1AA',
            maxWidth: '600px',
            margin: '0 auto',
            padding: '0 24px',
          }}
        >
          Five agents turn a resume into a verified job map.
        </p>
      </div>

      {/* Agent cards */}
      {agents.map((agent, index) => (
        <div key={agent.number} data-agent-index={index}>
          <AgentCard
            number={agent.number}
            name={agent.name}
            role={agent.role}
            formula={agent.formula}
            description={agent.description}
            icon={agent.icon}
            glowClass={agent.glowClass}
            accentColor={agent.accentColor}
          />
        </div>
      ))}
    </section>
  );
}
