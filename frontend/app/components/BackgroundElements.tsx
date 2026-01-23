'use client';

import { useEffect, useRef } from 'react';

export function BackgroundElements() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      if (!containerRef.current) return;
      const scrolled = window.scrollY;
      const shapes = containerRef.current.querySelectorAll('.floating-shape');
      
      shapes.forEach((shape, index) => {
        const element = shape as HTMLElement;
        // Parallax effect: shapes move slower than content
        // Use CSS custom property to avoid overriding CSS animations
        const speed = 0.2 + (index % 3) * 0.05;
        const yPos = scrolled * speed;
        element.style.setProperty('--parallax-y', `${yPos}px`);
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Initial call
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div 
      ref={containerRef}
      className="fixed inset-0 overflow-hidden pointer-events-none -z-10"
    >
      {/* Large floating circles */}
      <div 
        className="absolute floating-shape w-96 h-96 rounded-full gradient-overlay"
        style={{
          top: '10%',
          left: '-10%',
          background: 'radial-gradient(circle, rgba(var(--primary-rgb), 0.1) 0%, transparent 70%)',
        }}
      />
      
      <div 
        className="absolute floating-shape w-80 h-80 rounded-full"
        style={{
          top: '60%',
          right: '-5%',
          background: 'radial-gradient(circle, rgba(var(--primary-rgb), 0.08) 0%, transparent 70%)',
          animationDelay: '5s',
        }}
      />

      {/* Medium shapes */}
      <div 
        className="absolute floating-shape w-64 h-64 rounded-full"
        style={{
          top: '30%',
          right: '15%',
          background: 'radial-gradient(circle, rgba(var(--primary-rgb), 0.06) 0%, transparent 60%)',
          animationDelay: '10s',
        }}
      />

      <div 
        className="absolute floating-shape w-72 h-72 rounded-full"
        style={{
          bottom: '20%',
          left: '10%',
          background: 'radial-gradient(circle, rgba(var(--primary-rgb), 0.07) 0%, transparent 65%)',
          animationDelay: '15s',
        }}
      />

      {/* Small accent shapes */}
      <div 
        className="absolute floating-shape w-32 h-32 rounded-full"
        style={{
          top: '15%',
          left: '50%',
          background: 'radial-gradient(circle, rgba(var(--primary-rgb), 0.1) 0%, transparent 50%)',
          animationDelay: '2s',
        }}
      />

      <div 
        className="absolute floating-shape w-40 h-40 rounded-full"
        style={{
          bottom: '10%',
          right: '30%',
          background: 'radial-gradient(circle, rgba(var(--primary-rgb), 0.08) 0%, transparent 55%)',
          animationDelay: '8s',
        }}
      />

      {/* Organic blob shapes */}
      <div 
        className="absolute floating-shape"
        style={{
          top: '45%',
          left: '25%',
          width: '200px',
          height: '200px',
          borderRadius: '40% 60% 70% 30% / 40% 50% 60% 50%',
          background: 'radial-gradient(ellipse, rgba(var(--primary-rgb), 0.05) 0%, transparent 70%)',
          animationDelay: '12s',
        }}
      />

      <div 
        className="absolute floating-shape"
        style={{
          bottom: '30%',
          right: '20%',
          width: '180px',
          height: '180px',
          borderRadius: '60% 40% 30% 70% / 50% 40% 50% 60%',
          background: 'radial-gradient(ellipse, rgba(var(--primary-rgb), 0.06) 0%, transparent 65%)',
          animationDelay: '18s',
        }}
      />
    </div>
  );
}

export default BackgroundElements;
