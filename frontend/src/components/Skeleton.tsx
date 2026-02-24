import React from 'react';
import './Skeleton.css';

interface SkeletonProps {
  variant?: 'text' | 'rect' | 'circle';
  width?: string | number;
  height?: string | number;
  className?: string;
}

const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  className,
}) => {
  const defaultHeight = variant === 'text' ? '1em' : undefined;

  return (
    <div
      className={`skeleton${variant === 'circle' ? ' skeleton--circle' : ''}${className ? ` ${className}` : ''}`}
      style={{
        width: width ?? '100%',
        height: height ?? defaultHeight,
      }}
      role="status"
      aria-label="Loading"
    />
  );
};

export default Skeleton;
