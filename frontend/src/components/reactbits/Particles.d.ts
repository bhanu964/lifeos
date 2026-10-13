import React from 'react';

export interface ParticlesProps {
  particleColors?: string[];
  particleCount?: number;
  particleSpread?: number;
  speed?: number;
  particleBaseSize?: number;
  moveParticlesOnHover?: boolean;
  alphaParticles?: boolean;
  disableRotation?: boolean;
  pixelRatio?: number;
  sizeRandomness?: number;
  cameraDistance?: number;
  resetOnResize?: boolean;
  style?: React.CSSProperties;
  className?: string;
  [key: string]: any;
}

declare const Particles: React.FC<ParticlesProps>;
export default Particles;
