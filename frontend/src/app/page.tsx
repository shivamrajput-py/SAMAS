'use client';

import SamasHero from '@/components/landing/SamasHero';
import TransitionPortal from '@/components/landing/TransitionPortal';
import AgentShowcase from '@/components/landing/AgentShowcase';
import VoidDimension from '@/components/landing/VoidDimension';
import LandingFooter from '@/components/landing/LandingFooter';

export default function LandingPage() {
  return (
    <>
      {/* Real World (Light) */}
      <SamasHero />

      <VoidDimension>
        {/* The Mirror Surface — transition from light to dark via GSAP */}
        <TransitionPortal />

        {/* Mirror Dimension (Dark) */}
        <AgentShowcase />
      </VoidDimension>

      {/* Footer (returns to light) */}
      <LandingFooter />
    </>
  );
}
