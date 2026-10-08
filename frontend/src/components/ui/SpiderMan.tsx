"use client";
import { useEffect, useRef } from "react";

export default function SpiderWebBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const parent = canvas.parentElement;
    if (!parent) return;

    let dots: { x: number; y: number; size: number; color: string }[] = [];
    const color = "white";

    const setCanvasSize = () => {
      canvas.width = parent.offsetWidth;
      canvas.height = parent.offsetHeight;
    };

    const initDots = () => {
      dots = [];
      for (let i = 0; i < 50; i++) {
        dots.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          size: Math.random() * 2+1,
          color,
        });
      }
    };

    const drawDots = () => {
      dots.forEach((dot) => {
        ctx.fillStyle = dot.color;
        ctx.beginPath();
        ctx.arc(dot.x, dot.y, dot.size, 0, Math.PI * 2);
        ctx.fill();
      });
    };

    const handleMouseMove = (e: MouseEvent) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      drawDots();

      const rect = parent.getBoundingClientRect();
      const mouse = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };

      dots.forEach((dot) => {
        const distance = Math.hypot(mouse.x - dot.x, mouse.y - dot.y);
        if (distance < 300) {
          ctx.strokeStyle = dot.color;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(dot.x, dot.y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.stroke();
        }
      });
    };

    const handleMouseOut = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      drawDots();
    };

    const handleResize = () => {
      setCanvasSize();
      initDots();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      drawDots();
    };

    // Init
    setCanvasSize();
    initDots();
    drawDots();

    // Events
    parent.addEventListener("mousemove", handleMouseMove);
    parent.addEventListener("mouseout", handleMouseOut);
    window.addEventListener("resize", handleResize);

    return () => {
      parent.removeEventListener("mousemove", handleMouseMove);
      parent.removeEventListener("mouseout", handleMouseOut);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
    />
  );
}
