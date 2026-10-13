import React from 'react';

export interface SpotlightCardProps {
  as?: React.ElementType;
  from?: string;
  via?: string;
  to?: string;
  size?: number;
  mode?: 'before' | 'after';
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties & Record<string, any>;
  ambient?: boolean;
  spotlightColor?: string;
  intensity?: number;
  spotlightSize?: number;
  borderGlow?: number;
  proximity?: number;
  onClick?: React.MouseEventHandler<any>;
  onMouseEnter?: React.MouseEventHandler<any>;
  onMouseLeave?: React.MouseEventHandler<any>;
  [key: string]: any;
}

declare const SpotlightCard: React.FC<SpotlightCardProps>;
export default SpotlightCard;
