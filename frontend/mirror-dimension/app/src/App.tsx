import { useState, useCallback } from 'react';
import CustomCursor from './components/CustomCursor';
import Navigation from './components/Navigation';
import ParticleMirrorCanvas from './components/ParticleMirrorCanvas';
import MirrorInstallation from './sections/MirrorInstallation';
import TransitionSection from './sections/TransitionSection';
import AgentSection from './sections/AgentSection';
import FooterSection from './sections/FooterSection';

const DEFAULT_ACCENT: [number, number, number] = [0.486, 0.227, 0.929];

export default function App() {
  const [transitionProgress, setTransitionProgress] = useState(0);
  const [accentColor, setAccentColor] = useState<[number, number, number]>(DEFAULT_ACCENT);

  // Show particle canvas once transition starts (progress > 0.1)
  const showParticles = transitionProgress > 0.1;

  const handleTransitionProgress = useCallback((progress: number) => {
    setTransitionProgress(progress);
  }, []);

  const handleAgentChange = useCallback((rgb: [number, number, number]) => {
    setAccentColor(rgb);
  }, []);

  return (
    <div
      style={{
        position: 'relative',
        minHeight: '100vh',
        background: '#0A0A0F',
        overflow: 'hidden',
      }}
    >
      {/* Custom cursor */}
      <CustomCursor />

      {/* Navigation */}
      <Navigation />

      {/* Particle mirror background (visible during/after transition) */}
      <ParticleMirrorCanvas visible={showParticles} accentColor={accentColor} />

      {/* Hero Section - The Mirror */}
      <MirrorInstallation />

      {/* Transition Section - Enter Mirror Dimension */}
      <TransitionSection onTransitionProgress={handleTransitionProgress} />

      {/* Agent Protocol Section */}
      <AgentSection onAgentChange={handleAgentChange} />

      {/* Footer */}
      <FooterSection />
    </div>
  );
}
