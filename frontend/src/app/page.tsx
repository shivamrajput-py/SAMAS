'use client';

import SamasHero from '@/components/landing/SamasHero';
import TransitionPortal from '@/components/landing/TransitionPortal';
import AgentShowcase from '@/components/landing/AgentShowcase';
import LandingFooter from '@/components/landing/LandingFooter';

export default function LandingPage() {
  return (
    <>
      {/* Real World (Light) */}
      <SamasHero />

      {/* The Mirror Surface — transition from light to dark via GSAP */}
      <TransitionPortal />

      {/* Mirror Dimension (Dark) */}
      <AgentShowcase />

      {/* Footer (returns to light) */}
      <LandingFooter />
    </>
  );
}
