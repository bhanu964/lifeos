import React from 'react';

export interface BorderGlowProps {
  children?: React.ReactNode;
  className?: string;
  borderGradient?: string;
  glowColor?: string;
  borderWidth?: number;
  borderRadius?: number;
  glowIntensity?: number;
  glowRadius?: number;
  fillOpacity?: number;
  animationSpeed?: number;
  animated?: boolean;
  colors?: string[];
  backgroundColor?: string;
  edgeSensitivity?: number;
  style?: React.CSSProperties & Record<string, any>;
  onClick?: React.MouseEventHandler<any>;
  [key: string]: any;
}

declare const BorderGlow: React.FC<BorderGlowProps>;
export default BorderGlow;
