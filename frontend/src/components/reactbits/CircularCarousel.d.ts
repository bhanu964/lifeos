import React from 'react';

export interface CircularCarouselItem {
  src: string;
  alt?: string;
  title?: string;
  subtitle?: string;
  [key: string]: any;
}

export interface CircularCarouselProps {
  items?: CircularCarouselItem[];
  preset?: string;
  intro?: string;
  cardWidth?: number;
  aspectRatio?: number;
  gap?: number;
  curve?: any;
  tilt?: any;
  perspective?: any;
  speed?: number;
  captions?: boolean;
  autoplay?: string;
  onChange?: (index: number) => void;
  onItemClick?: (item: CircularCarouselItem, index: number) => void;
  style?: React.CSSProperties;
  className?: string;
  [key: string]: any;
}

declare const CircularCarousel: React.FC<CircularCarouselProps>;
export default CircularCarousel;
