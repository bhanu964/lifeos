import React from 'react';

export interface AuroraProps {
  colorStops?: string[];
  amplitude?: number;
  blend?: number;
  height?: number;
  speed?: number;
  scale?: number;
  glow?: number;
  brightness?: number;
  layers?: number;
  direction?: 'top' | 'bottom';
  mouseInteraction?: boolean;
  intro?: boolean;
  opacity?: number;
  lightMode?: boolean;
  time?: number;
  paused?: boolean;
  dpr?: number;
  style?: React.CSSProperties;
  className?: string;
  [key: string]: any;
}

declare const Aurora: React.FC<AuroraProps>;
export default Aurora;
