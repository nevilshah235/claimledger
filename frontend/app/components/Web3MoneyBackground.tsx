'use client';

import { useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  opacity: number;
  pulsePhase: number;
  isCoin: boolean;
}

export function Web3MoneyBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();
  const particlesRef = useRef<Particle[]>([]);
  const timeRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    // Get primary RGB values from CSS variable
    const getPrimaryRgb = (): [number, number, number] => {
      const root = document.documentElement;
      const rgbString = getComputedStyle(root).getPropertyValue('--primary-rgb').trim();
      if (rgbString) {
        const parts = rgbString.split(',').map((s) => parseInt(s.trim(), 10));
        if (parts.length === 3) {
          return [parts[0], parts[1], parts[2]];
        }
      }
      // Fallback to default primary color: 30, 142, 90
      return [30, 142, 90];
    };

    const primaryRgb = getPrimaryRgb();
    const rgba = (r: number, g: number, b: number, a: number) => 
      `rgba(${r}, ${g}, ${b}, ${a})`;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const particleCount = prefersReducedMotion ? 80 : 220;

    // Initialize particles (coin-like discs)
    const initParticles = () => {
      particlesRef.current = [];
      for (let i = 0; i < particleCount; i++) {
        particlesRef.current.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          vx: (Math.random() - 0.5) * 0.3,
          vy: (Math.random() - 0.5) * 0.3,
          radius: 3 + Math.random() * 4,
          opacity: 0.28 + Math.random() * 0.35,
          pulsePhase: Math.random() * Math.PI * 2,
          isCoin: Math.random() > 0.3, // 70% are "coins" with highlight
        });
      }
    };
    initParticles();

    const drawParticle = (p: Particle, t: number, primaryRgb: [number, number, number], rgba: (r: number, g: number, b: number, a: number) => string) => {
      const pulse = Math.sin(t * 0.001 + p.pulsePhase) * 0.1 + 1;
      const currentOpacity = p.opacity * (0.8 + pulse * 0.2);

      ctx.save();
      ctx.globalAlpha = currentOpacity;

      if (p.isCoin) {
        // Draw coin with radial gradient (specular highlight)
        const gradient = ctx.createRadialGradient(
          p.x - p.radius * 0.3,
          p.y - p.radius * 0.3,
          0,
          p.x,
          p.y,
          p.radius * pulse
        );
        gradient.addColorStop(0, rgba(primaryRgb[0], primaryRgb[1], primaryRgb[2], 0.65));
        gradient.addColorStop(0.4, rgba(primaryRgb[0], primaryRgb[1], primaryRgb[2], 0.35));
        gradient.addColorStop(1, rgba(primaryRgb[0], primaryRgb[1], primaryRgb[2], 0.12));

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius * pulse, 0, Math.PI * 2);
        ctx.fill();

        // Optional: subtle ring for some coins
        if (Math.random() > 0.7) {
          ctx.strokeStyle = rgba(primaryRgb[0], primaryRgb[1], primaryRgb[2], currentOpacity * 0.3);
          ctx.lineWidth = 0.5;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius * pulse * 1.1, 0, Math.PI * 2);
          ctx.stroke();
        }
      } else {
        // Simple disc for non-coin particles
        ctx.fillStyle = rgba(primaryRgb[0], primaryRgb[1], primaryRgb[2], currentOpacity);
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius * pulse, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.restore();
    };

    const drawConnection = (p1: Particle, p2: Particle, primaryRgb: [number, number, number], rgba: (r: number, g: number, b: number, a: number) => string) => {
      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const maxDist = 120;

      if (dist < maxDist) {
        const opacity = (1 - dist / maxDist) * 0.18;
        ctx.strokeStyle = rgba(primaryRgb[0], primaryRgb[1], primaryRgb[2], opacity);
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }
    };

    const animate = (t: number) => {
      timeRef.current = t;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const particles = particlesRef.current;

      // Update and draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Simple noise-based movement (simulated dynamics)
        p.vx += (Math.random() - 0.5) * 0.02;
        p.vy += (Math.random() - 0.5) * 0.02;
        p.vx *= 0.98; // Friction
        p.vy *= 0.98;

        p.x += p.vx;
        p.y += p.vy;

        // Wrap around edges
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        drawParticle(p, t, primaryRgb, rgba);
      }

      // Draw connections between nearby particles
      if (!prefersReducedMotion) {
        for (let i = 0; i < particles.length; i++) {
          for (let j = i + 1; j < particles.length; j++) {
            drawConnection(particles[i], particles[j], primaryRgb, rgba);
          }
        }
      }

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', resize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none -z-10"
      style={{ background: 'transparent' }}
      aria-hidden="true"
    />
  );
}

export default Web3MoneyBackground;
