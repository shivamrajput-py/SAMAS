import { useEffect, useRef } from 'react';
import * as THREE from 'three';

const vertexShader = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position, 1.0);
}
`;

const fragmentShader = `
precision highp float;
varying vec2 vUv;

uniform float u_time;
uniform vec2 u_resolution;
uniform float u_particleCount;
uniform vec2 u_mouse;
uniform float u_mirrorLine;
uniform vec3 u_accentColor;

float hash(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float particleGlow(vec2 uv, vec2 center, float radius, float intensity) {
  float dist = length(uv - center);
  float glow = exp(-dist * dist / (radius * radius));
  return glow * intensity;
}

vec2 mirrorUV(vec2 uv, float line) {
  float distToLine = uv.x - line;
  return vec2(line - distToLine, uv.y);
}

void main() {
  vec2 uv = vUv * u_resolution;
  vec2 mirrorCenter = vec2(u_mirrorLine * u_resolution.x, u_resolution.y * 0.5);

  vec2 mirroredUV = mirrorUV(uv, u_mirrorLine * u_resolution.x);

  float t = u_time * 0.3;

  vec3 color = vec3(0.02, 0.02, 0.03);

  // Ambient mirrored particles
  for (float i = 0.0; i < 8.0; i++) {
    if (i >= u_particleCount) break;
    float fi = float(i);
    float angle = fi * 0.785 + t * 0.1;
    float radius = 0.15 + 0.1 * sin(fi * 1.17);
    float px = mirrorCenter.x + cos(angle) * radius * u_resolution.x + noise(uv * 0.01 + t * 0.1 + fi) * 100.0;
    float py = mirrorCenter.y + sin(angle * 1.3) * radius * u_resolution.y * 0.5 + noise(uv * 0.01 - t * 0.15 + fi + 10.0) * 80.0;
    vec2 particlePos = vec2(px, py);
    float glow = particleGlow(uv, particlePos, 25.0 + 10.0 * sin(fi * 2.3 + t), 0.15);
    color += u_accentColor * glow * (0.5 + 0.5 * sin(fi * 3.14 + t));
  }

  // Mouse-reactive glow
  if (u_mouse.x > 0.0) {
    vec2 mousePos = u_mouse * u_resolution;
    float mouseGlow = particleGlow(uv, mousePos, 60.0, 0.4);
    vec2 mirroredMousePos = mirrorUV(mousePos, u_mirrorLine * u_resolution.x);
    float mirroredMouseGlow = particleGlow(uv, mirroredMousePos, 60.0, 0.25);
    color += vec3(0.024, 0.714, 0.831) * (mouseGlow + mirroredMouseGlow);
  }

  // Mirror line glow
  float lineDist = abs(uv.x - u_mirrorLine * u_resolution.x);
  float lineGlow = exp(-lineDist * lineDist / 8.0) * 0.3;
  color += u_accentColor * lineGlow;

  // Vignette
  float vignette = 1.0 - length(vUv - 0.5) * 0.8;
  color *= vignette;

  // Film grain
  color += (hash(vUv * u_resolution + u_time) - 0.5) * 0.02;

  gl_FragColor = vec4(color, 1.0);
}
`;

interface ParticleMirrorCanvasProps {
  visible: boolean;
  accentColor?: [number, number, number];
}

export default function ParticleMirrorCanvas({ visible, accentColor = [0.486, 0.227, 0.929] }: ParticleMirrorCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const materialRef = useRef<THREE.ShaderMaterial | null>(null);
  const rafRef = useRef<number>(0);
  const mouseRef = useRef({ x: -1, y: -1 });
  const accentRef = useRef(new THREE.Vector3(...accentColor));
  const targetAccentRef = useRef(new THREE.Vector3(...accentColor));

  // Update target accent color when prop changes
  useEffect(() => {
    targetAccentRef.current.set(...accentColor);
  }, [accentColor]);

  useEffect(() => {
    if (!visible || !containerRef.current) return;

    const container = containerRef.current;
    const isMobile = navigator.hardwareConcurrency < 4;
    const particleCount = isMobile ? 4.0 : 8.0;

    // Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.display = 'block';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Shader material
    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        u_time: { value: 0.0 },
        u_resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
        u_particleCount: { value: particleCount },
        u_mouse: { value: new THREE.Vector2(-1.0, -1.0) },
        u_mirrorLine: { value: 0.5 },
        u_accentColor: { value: accentRef.current },
      },
    });
    materialRef.current = material;

    const geometry = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // Clock
    const clock = new THREE.Clock();

    // Mouse tracking
    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.x = e.clientX / window.innerWidth;
      mouseRef.current.y = 1.0 - e.clientY / window.innerHeight;
    };

    const handleMouseLeave = () => {
      mouseRef.current.x = -1;
      mouseRef.current.y = -1;
    };

    window.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);

    // Resize
    const handleResize = () => {
      renderer.setSize(window.innerWidth, window.innerHeight);
      material.uniforms.u_resolution.value.set(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    // Animation loop
    const animate = () => {
      material.uniforms.u_time.value = clock.getElapsedTime();
      material.uniforms.u_mouse.value.set(mouseRef.current.x, mouseRef.current.y);

      // Smooth accent color interpolation
      accentRef.current.lerp(targetAccentRef.current, 0.02);

      renderer.render(scene, camera);
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [visible]);

  if (!visible) return null;

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0,
        pointerEvents: 'none',
      }}
    />
  );
}
