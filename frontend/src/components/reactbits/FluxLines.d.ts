import React from 'react';

export interface FluxLinesProps {
  colors?: string[];
  speed?: number;
  scale?: number;
  turbulence?: number;
  fluidity?: number;
  rimWidth?: number;
  sharpness?: number;
  shimmer?: number;
  glow?: number;
  lineWidth?: number;
  flowDirection?: string;
  mouseInteraction?: boolean;
  clickSwirl?: boolean;
  backgroundColor?: string;
  dpr?: number;
  mixBlendMode?: string;
  style?: React.CSSProperties;
  className?: string;
  [key: string]: any;
}

declare const FluxLines: React.FC<FluxLinesProps>;
export default FluxLines;
