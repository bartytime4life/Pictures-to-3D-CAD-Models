import { useEffect, useRef } from 'react';
import { shapePath, SHAPE_LABELS } from './shapes';
import type { DesignShape } from './shapes';
import { useStudioActive } from './StudioActivity';

export default function ShapeCanvas({
  shapes,
  selected,
  snap,
  onSelect,
  onMove,
  onMoveStart,
  onMoveEnd,
}: {
  shapes: DesignShape[];
  selected: string;
  snap: boolean;
  onSelect: (id: string) => void;
  onMove: (id: string, x: number, y: number) => void;
  onMoveStart: () => void;
  onMoveEnd: () => void;
}) {
  const active = useStudioActive();
  const canvas = useRef<HTMLCanvasElement>(null);
  const transform = useRef({ scale: 1, x: 0, y: 0 });
  const drag = useRef<{ id: string; dx: number; dy: number; pointerId: number } | null>(null);
  const moveEnd = useRef(onMoveEnd);
  moveEnd.current = onMoveEnd;
  const latest = useRef(shapes);
  latest.current = shapes;
  function finishGesture() {
    const gesture = drag.current;
    if (!gesture) return;
    drag.current = null;
    moveEnd.current();
    if (canvas.current?.hasPointerCapture(gesture.pointerId))
      canvas.current.releasePointerCapture(gesture.pointerId);
  }
  useEffect(() => {
    if (!active) finishGesture();
    return finishGesture;
  }, [active]);
  useEffect(() => {
    if (!active || !canvas.current) return;
    const target = canvas.current;
    function draw() {
      const ctx = target.getContext('2d');
      if (!ctx) return;
      const { width, height } = target.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      target.width = Math.round(width * ratio);
      target.height = Math.round(height * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, width, height);
      const finite = shapes.filter(
        (shape) =>
          [shape.x_mm, shape.y_mm, shape.width_mm, shape.height_mm, shape.rotation_deg].every(
            Number.isFinite,
          ) &&
          shape.width_mm > 0 &&
          shape.height_mm > 0 &&
          shape.corner_mm >= 0,
      );
      // Keep the view fixed during a drag so the part follows the pointer predictably.
      if (!drag.current) {
        const bounds = finite.map((shape) => {
          const r = (shape.rotation_deg * Math.PI) / 180,
            h = shape.kind === 'circle' ? shape.width_mm : shape.height_mm;
          return {
            x: shape.x_mm,
            y: shape.y_mm,
            w: Math.abs(shape.width_mm * Math.cos(r)) + Math.abs(h * Math.sin(r)),
            h: Math.abs(shape.width_mm * Math.sin(r)) + Math.abs(h * Math.cos(r)),
          };
        });
        const left = Math.min(-20, ...bounds.map((b) => b.x - b.w / 2));
        const right = Math.max(20, ...bounds.map((b) => b.x + b.w / 2));
        const top = Math.min(-20, ...bounds.map((b) => b.y - b.h / 2));
        const bottom = Math.max(20, ...bounds.map((b) => b.y + b.h / 2));
        const scale = Math.min((width - 60) / (right - left), (height - 60) / (bottom - top));
        transform.current = {
          scale,
          x: width / 2 - ((left + right) / 2) * scale,
          y: height / 2 - ((top + bottom) / 2) * scale,
        };
      }
      const t = transform.current;
      ctx.translate(t.x, t.y);
      ctx.scale(t.scale, t.scale);
      ctx.strokeStyle = '#284153';
      ctx.lineWidth = 1 / t.scale;
      // Bound the grid even for very large designs.
      const step = Math.max(10, 10 ** Math.floor(Math.log10(35 / t.scale)));
      for (
        let x = Math.floor(-t.x / t.scale / step) * step;
        x <= (width - t.x) / t.scale;
        x += step
      ) {
        ctx.beginPath();
        ctx.moveTo(x, -t.y / t.scale);
        ctx.lineTo(x, (height - t.y) / t.scale);
        ctx.stroke();
      }
      for (
        let y = Math.floor(-t.y / t.scale / step) * step;
        y <= (height - t.y) / t.scale;
        y += step
      ) {
        ctx.beginPath();
        ctx.moveTo(-t.x / t.scale, y);
        ctx.lineTo((width - t.x) / t.scale, y);
        ctx.stroke();
      }
      // Draw the composition on an offscreen layer so cutouts don't erase the grid.
      const layer = document.createElement('canvas');
      layer.width = target.width;
      layer.height = target.height;
      const material = layer.getContext('2d');
      if (!material) return;
      material.setTransform(ratio * t.scale, 0, 0, ratio * t.scale, ratio * t.x, ratio * t.y);
      for (const operation of ['add', 'cut'])
        for (const shape of finite.filter((item) => item.operation === operation)) {
          material.save();
          material.translate(shape.x_mm, shape.y_mm);
          material.rotate((shape.rotation_deg * Math.PI) / 180);
          material.globalCompositeOperation =
            operation === 'cut' ? 'destination-out' : 'source-over';
          material.fillStyle = '#3e9eaf';
          shapePath(material, shape);
          material.fill();
          material.restore();
        }
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(layer, 0, 0);
      ctx.restore();
      const chosen = finite.find((shape) => shape.id === selected);
      if (chosen) {
        ctx.save();
        ctx.translate(chosen.x_mm, chosen.y_mm);
        ctx.rotate((chosen.rotation_deg * Math.PI) / 180);
        ctx.strokeStyle = chosen.operation === 'cut' ? '#ffc799' : '#a3f7ff';
        ctx.lineWidth = 2 / t.scale;
        ctx.setLineDash([5 / t.scale, 4 / t.scale]);
        shapePath(ctx, chosen);
        ctx.stroke();
        ctx.restore();
      }
    }
    const observer = new ResizeObserver(draw);
    observer.observe(target);
    draw();
    return () => observer.disconnect();
  }, [shapes, selected, active]);
  function position(event: React.PointerEvent<HTMLCanvasElement>) {
    const bounds = event.currentTarget.getBoundingClientRect(),
      t = transform.current;
    return {
      x: (event.clientX - bounds.left - t.x) / t.scale,
      y: (event.clientY - bounds.top - t.y) / t.scale,
    };
  }
  return (
    <canvas
      ref={canvas}
      className="shape-canvas"
      aria-label="2D shape design. Drag shapes to move; use the shape list and dimension fields for keyboard editing."
      role="img"
      onPointerDown={(event) => {
        if (!active || event.button !== 0 || !event.isPrimary || drag.current) return;
        const ctx = event.currentTarget.getContext('2d');
        if (!ctx) return;
        const point = position(event);
        for (const shape of [...latest.current].reverse()) {
          if (!(shape.width_mm > 0 && shape.height_mm > 0 && shape.corner_mm >= 0)) continue;
          const r = (-shape.rotation_deg * Math.PI) / 180,
            dx = point.x - shape.x_mm,
            dy = point.y - shape.y_mm;
          ctx.save();
          ctx.resetTransform();
          shapePath(ctx, shape);
          const hit = ctx.isPointInPath(
            dx * Math.cos(r) - dy * Math.sin(r),
            dx * Math.sin(r) + dy * Math.cos(r),
          );
          ctx.restore();
          if (hit) {
            onSelect(shape.id);
            onMoveStart();
            drag.current = {
              id: shape.id,
              dx: point.x - shape.x_mm,
              dy: point.y - shape.y_mm,
              pointerId: event.pointerId,
            };
            event.currentTarget.setPointerCapture(event.pointerId);
            break;
          }
        }
      }}
      onPointerMove={(event) => {
        if (!active || !drag.current || event.pointerId !== drag.current.pointerId) return;
        const point = position(event),
          step = snap ? 1 : 0.1;
        onMove(
          drag.current.id,
          Math.round((point.x - drag.current.dx) / step) * step,
          Math.round((point.y - drag.current.dy) / step) * step,
        );
      }}
      onPointerUp={finishGesture}
      onPointerCancel={finishGesture}
      onLostPointerCapture={finishGesture}
    >
      <span>
        {shapes.map((shape) => `${SHAPE_LABELS[shape.kind]} ${shape.operation}`).join(', ')}
      </span>
    </canvas>
  );
}
