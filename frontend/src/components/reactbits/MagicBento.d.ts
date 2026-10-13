import React from 'react';

export interface MagicBentoItem {
  title?: string;
  description?: string;
  label?: string;
  icon?: any;
  image?: string;
  visual?: React.ReactNode | string;
  content?: React.ReactNode;
  href?: string;
  onClick?: () => void;
  colSpan?: number;
  rowSpan?: number;
  [key: string]: any;
}

export interface MagicBentoProps {
  items?: MagicBentoItem[];
  columns?: number;
  rowHeight?: number;
  gap?: number;
  radius?: number;
  enableBorderGlow?: boolean;
  enableSpotlight?: boolean;
  spotlightRadius?: number;
  clickEffect?: boolean;
  glowColor?: string;
  onItemClick?: (item: MagicBentoItem, index: number) => void;
  style?: React.CSSProperties;
  className?: string;
  [key: string]: any;
}

declare const MagicBento: React.FC<MagicBentoProps>;
export default MagicBento;
