import { Component, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { Environment, Lightformer, OrbitControls } from '@react-three/drei';
import { ArrowsOut, Cube, Minus, Plus } from '@phosphor-icons/react';
import {
  Box3,
  BufferGeometry,
  EdgesGeometry,
  Float32BufferAttribute,
  OrthographicCamera,
  PCFShadowMap,
  Vector3,
} from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { toCreasedNormals } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export type PreviewMesh = { vertices: number[]; triangles: number[] };
export type PreviewPart = { id: string; name: string; mesh?: PreviewMesh };
export type PreviewMaterial = 'pla' | 'petg' | 'abs' | 'asa' | 'tpu' | 'nylon';
const noParts: PreviewPart[] = [];

// Visual finish presets only, not measured material properties or a print simulation.
const finishes: Record<PreviewMaterial, { roughness: number; clearcoat: number }> = {
  pla: { roughness: 0.5, clearcoat: 0.08 },
  petg: { roughness: 0.32, clearcoat: 0.16 },
  abs: { roughness: 0.46, clearcoat: 0.05 },
  asa: { roughness: 0.6, clearcoat: 0.02 },
  tpu: { roughness: 0.72, clearcoat: 0 },
  nylon: { roughness: 0.65, clearcoat: 0 },
};

// 'raking' lights the part from about 15 degrees above the horizon with little fill, so
// shallow relief casts readable shading. Lighting only; geometry is unchanged.
export type ViewerLighting = 'studio' | 'raking';

type ModelViewerProps = {
  mesh: PreviewMesh | null;
  lighting?: ViewerLighting;
  resetKey: number;
  loading: boolean;
  color?: string;
  material?: PreviewMaterial;
  parts?: PreviewPart[];
};

type View = 'iso' | 'top' | 'front';
type ViewRequest = { view: View; sequence: number };
type ViewerActions = {
  zoom: (factor: number) => void;
  rotate: (horizontal: number, vertical: number) => void;
};

const buttonStyle = {
  width: 34,
  height: 34,
  padding: 0,
  display: 'inline-flex',
  justifyContent: 'center',
  alignItems: 'center',
  background: '#252d34',
  color: '#dce4e9',
  border: '1px solid #46515b',
  borderRadius: 5,
  cursor: 'pointer',
} as const;

function Unavailable({ retry }: { retry?: () => void }) {
  return (
    <div
      role="status"
      style={{
        padding: 32,
        maxWidth: 380,
        margin: 'auto',
        textAlign: 'center',
        color: '#b8c4cc',
        lineHeight: 1.6,
      }}
    >
      <Cube size={36} aria-hidden="true" />
      <p style={{ color: '#eef2f4', fontWeight: 600 }}>3D preview is unavailable</p>
      <p>
        Enable WebGL or try another browser. Your outline, dimensions, and CAD downloads remain
        available.
      </p>
      {retry && (
        <button
          type="button"
          onClick={retry}
          style={{ ...buttonStyle, width: 'auto', padding: '0 16px' }}
        >
          Retry preview
        </button>
      )}
    </div>
  );
}

function CanvasContextListener({ onLost }: { onLost: () => void }) {
  const { gl } = useThree();
  useEffect(() => {
    const canvas = gl.domElement;
    const handleLoss = (event: Event) => {
      event.preventDefault();
      // A renderer intentionally loses its old context after unmounting. That
      // delayed event must never mark a replacement canvas as unavailable.
      if (canvas.isConnected) onLost();
    };
    canvas.addEventListener('webglcontextlost', handleLoss);
    return () => canvas.removeEventListener('webglcontextlost', handleLoss);
  }, [gl, onLost]);
  return null;
}

class ViewerBoundary extends Component<
  { children: ReactNode; onRetry: () => void; onFailure: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onFailure();
  }
  render() {
    if (this.state.failed) return <Unavailable retry={this.props.onRetry} />;
    return this.props.children;
  }
}

function prepareMesh(mesh: PreviewMesh) {
  if (
    !mesh.vertices.length ||
    mesh.vertices.length % 3 ||
    !mesh.triangles.length ||
    mesh.triangles.length % 3
  ) {
    throw new Error('The model does not contain a complete triangle mesh.');
  }
  const vertexCount = mesh.vertices.length / 3;
  if (
    mesh.vertices.some((n) => !Number.isFinite(n)) ||
    mesh.triangles.some((i) => !Number.isInteger(i) || i < 0 || i >= vertexCount)
  ) {
    throw new Error('The model contains invalid mesh coordinates.');
  }
  const indexed = new BufferGeometry();
  indexed.setAttribute('position', new Float32BufferAttribute(mesh.vertices, 3));
  indexed.setIndex(mesh.triangles);
  // Preserve the top/side crease while smoothing the polygonal outline walls.
  const geometry = toCreasedNormals(indexed, Math.PI / 4);
  indexed.dispose();
  geometry.computeBoundingBox();
  const bounds = geometry.boundingBox as Box3;
  const center = bounds.getCenter(new Vector3());
  const dimensions = bounds.getSize(new Vector3());
  const span = Math.max(dimensions.x, dimensions.y, dimensions.z, 1);
  return { geometry, edges: new EdgesGeometry(geometry, 24), bounds, center, dimensions, span };
}

function CadScene({
  mesh,
  resetKey,
  request,
  actions,
  color,
  material,
  parts,
  separated,
  lighting = 'studio',
}: {
  mesh: PreviewMesh;
  lighting?: ViewerLighting;
  resetKey: number;
  request: ViewRequest;
  actions: React.RefObject<ViewerActions | null>;
  color: string;
  material: PreviewMaterial;
  parts: PreviewPart[];
  separated: boolean;
}) {
  const controls = useRef<OrbitControlsImpl>(null);
  const { camera, size, invalidate, gl } = useThree();
  const finish = finishes[material];

  useEffect(() => invalidate(), [color, material, invalidate]);

  const model = useMemo(() => prepareMesh(mesh), [mesh]);
  const partModels = useMemo(
    () =>
      parts
        .filter((part) => part.mesh)
        .map((part) => ({ ...prepareMesh(part.mesh!), id: part.id })),
    [parts],
  );
  const layout = useMemo(() => {
    if (!separated || partModels.length < 2)
      return [{ ...model, id: 'assembled', offset: new Vector3() }];
    // Space the actual cut solids for inspection only. These offsets never reach exports.
    const columns = Math.ceil(Math.sqrt(partModels.length));
    const rows = Math.ceil(partModels.length / columns);
    const gap = model.span * 0.12;
    const cellWidth = Math.max(...partModels.map((part) => part.dimensions.x)) + gap;
    const cellHeight = Math.max(...partModels.map((part) => part.dimensions.y)) + gap;
    return partModels.map((part, index) => ({
      ...part,
      offset: new Vector3(
        model.center.x + ((index % columns) - (columns - 1) / 2) * cellWidth - part.center.x,
        model.center.y +
          ((rows - 1) / 2 - Math.floor(index / columns)) * cellHeight -
          part.center.y,
        0,
      ),
    }));
  }, [model, partModels, separated]);
  const display = useMemo(() => {
    const bounds = new Box3();
    for (const part of layout) bounds.union(part.bounds.clone().translate(part.offset));
    const dimensions = bounds.getSize(new Vector3());
    return {
      bounds,
      center: bounds.getCenter(new Vector3()),
      span: Math.max(dimensions.x, dimensions.y, dimensions.z, 1),
    };
  }, [layout]);
  const lastFit = useRef<{ mesh: PreviewMesh; resetKey: number; sequence: number } | null>(null);

  useEffect(
    () => () => {
      model.geometry.dispose();
      model.edges.dispose();
    },
    [model],
  );
  useEffect(
    () => () => {
      for (const part of partModels) {
        part.geometry.dispose();
        part.edges.dispose();
      }
    },
    [partModels],
  );

  useEffect(() => {
    if (!(camera instanceof OrthographicCamera)) return;
    const { center, span, bounds } = display;
    const keepDirection =
      lastFit.current?.mesh === mesh &&
      lastFit.current.resetKey === resetKey &&
      lastFit.current.sequence === request.sequence;
    const direction = keepDirection
      ? camera.position.clone().sub(controls.current?.target ?? model.center)
      : request.view === 'top'
        ? new Vector3(0, -0.0001, 1)
        : request.view === 'front'
          ? new Vector3(0, -1, 0)
          : new Vector3(1, -1, 1.3);
    lastFit.current = { mesh, resetKey, sequence: request.sequence };
    camera.up.set(0, 0, 1);
    camera.position.copy(center).add(direction.normalize().multiplyScalar(span * 4));
    camera.near = Math.max(span / 1000, 0.001);
    camera.far = span * 30;
    camera.lookAt(center);
    camera.updateMatrixWorld();
    const right = new Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
    const up = new Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
    const widths: number[] = [];
    const heights: number[] = [];
    for (const x of [bounds.min.x, bounds.max.x]) {
      for (const y of [bounds.min.y, bounds.max.y]) {
        for (const z of [bounds.min.z, bounds.max.z]) {
          const point = new Vector3(x, y, z).sub(center);
          widths.push(point.dot(right));
          heights.push(point.dot(up));
        }
      }
    }
    const projectedWidth = Math.max(...widths) - Math.min(...widths);
    const projectedHeight = Math.max(...heights) - Math.min(...heights);
    camera.zoom = Math.min(
      size.width / Math.max(projectedWidth * 1.1, span * 0.25),
      size.height / Math.max(projectedHeight * 1.2, span * 0.25),
    );
    camera.updateProjectionMatrix();
    controls.current?.target.copy(center);
    if (controls.current) {
      controls.current.minZoom = camera.zoom / 5;
      controls.current.maxZoom = camera.zoom * 10;
      controls.current.update();
      controls.current.saveState();
    }
    invalidate();
  }, [camera, display, mesh, model, resetKey, request, size.width, size.height, invalidate]);

  useEffect(() => {
    actions.current = {
      zoom: (factor) => {
        if (!(camera instanceof OrthographicCamera)) return;
        const min = controls.current?.minZoom ?? 0.01;
        const max = controls.current?.maxZoom ?? 1000;
        camera.zoom = Math.min(max, Math.max(min, camera.zoom * factor));
        camera.updateProjectionMatrix();
        controls.current?.update();
        invalidate();
      },
      rotate: (horizontal, vertical) => {
        const target = controls.current?.target ?? display.center;
        const offset = camera.position.clone().sub(target);
        const azimuth = Math.atan2(offset.y, offset.x) + horizontal;
        const polar = Math.max(
          0.03,
          Math.min(Math.PI - 0.03, Math.acos(offset.z / offset.length()) + vertical),
        );
        const length = offset.length();
        camera.position.set(
          target.x + length * Math.sin(polar) * Math.cos(azimuth),
          target.y + length * Math.sin(polar) * Math.sin(azimuth),
          target.z + length * Math.cos(polar),
        );
        camera.lookAt(target);
        controls.current?.update();
        invalidate();
      },
    };
    return () => {
      actions.current = null;
    };
  }, [actions, camera, invalidate, display]);

  const span = display.span;
  const raking = lighting === 'raking';
  const fill = raking ? 0.3 : 1;
  return (
    <>
      <color attach="background" args={['#1b2025']} />
      <ambientLight intensity={0.25 * fill} />
      <hemisphereLight args={['#edf0f3', '#525a62', 0.9 * fill]} />
      <directionalLight
        position={
          raking ? [-span * 1.6, span * 0.5, span * 0.45] : [-span * 0.8, -span * 0.6, span * 2]
        }
        intensity={raking ? 3.2 : 2.0}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-span}
        shadow-camera-right={span}
        shadow-camera-top={span}
        shadow-camera-bottom={-span}
        shadow-camera-near={span * 0.1}
        shadow-camera-far={span * 5}
        shadow-bias={-0.0002}
        shadow-normalBias={span * 0.0005}
      />
      <directionalLight position={[span, span, span]} intensity={0.9 * fill} color="#dde3e8" />
      <Environment resolution={128} frames={1}>
        <Lightformer
          form="rect"
          intensity={3 * fill}
          color="#ffffff"
          position={[-5, -3, 6]}
          scale={[7, 5, 1]}
        />
        <Lightformer
          form="rect"
          intensity={1.6 * fill}
          color="#e5e9ed"
          position={[5, 3, 7]}
          scale={[5, 9, 1]}
        />
        <Lightformer
          form="rect"
          intensity={0.8 * fill}
          color="#ffffff"
          position={[0, -7, 1]}
          scale={[12, 2, 1]}
        />
      </Environment>
      {layout.map((part) => (
        <group key={part.id} position={part.offset}>
          <mesh
            geometry={part.geometry}
            castShadow
            receiveShadow
            onAfterRender={() => {
              gl.domElement.dataset.modelReady = 'true';
              gl.domElement.dataset.inspectionView = separated ? 'separated' : 'assembled';
            }}
          >
            <meshPhysicalMaterial
              color={color}
              metalness={0}
              roughness={finish.roughness}
              envMapIntensity={0.7}
              clearcoat={finish.clearcoat}
              clearcoatRoughness={0.5}
            />
          </mesh>
          <lineSegments geometry={part.edges}>
            <lineBasicMaterial color="#c0c9ce" transparent opacity={0.22} />
          </lineSegments>
        </group>
      ))}
      <mesh position={[0, 0, display.bounds.min.z - span * 0.012]}>
        <planeGeometry args={[span * 14, span * 14]} />
        <meshBasicMaterial color="#1b2025" toneMapped={false} />
      </mesh>
      <gridHelper
        args={[span * 8, 64, '#343c43', '#30383f']}
        rotation={[Math.PI / 2, 0, 0]}
        position={[0, 0, display.bounds.min.z - span * 0.011]}
        material-transparent
        material-opacity={0.55}
      />
      <mesh position={[0, 0, display.bounds.min.z - span * 0.01]} receiveShadow>
        <planeGeometry args={[span * 14, span * 14]} />
        <shadowMaterial transparent opacity={0.4} />
      </mesh>
      <OrbitControls
        ref={controls}
        makeDefault
        enableDamping={false}
        maxPolarAngle={Math.PI - 0.015}
        minPolarAngle={0.01}
        zoomSpeed={0.7}
        rotateSpeed={0.65}
        screenSpacePanning
      />
    </>
  );
}

export default function ModelViewer({
  mesh,
  resetKey,
  loading,
  color = '#c4c7ca',
  material = 'pla',
  parts = noParts,
  lighting = 'studio',
}: ModelViewerProps) {
  const [request, setRequest] = useState<ViewRequest>({ view: 'iso', sequence: 0 });
  const [attempt, setAttempt] = useState(0);
  const [contextLost, setContextLost] = useState(false);
  const [failed, setFailed] = useState(false);
  const [separated, setSeparated] = useState(false);
  const canSeparate = parts.length > 1 && parts.every((part) => part.mesh);
  const showSeparated = separated && canSeparate;
  const actions = useRef<ViewerActions | null>(null);
  const previewColor = /^#[\da-f]{6}$/i.test(color) ? color : '#c4c7ca';
  const previewMaterial = Object.hasOwn(finishes, material) ? material : 'pla';
  const setView = (view: View) =>
    setRequest((previous) => ({ view, sequence: previous.sequence + 1 }));
  const retry = () => {
    setFailed(false);
    setContextLost(false);
    setAttempt((n) => n + 1);
  };

  useEffect(() => {
    setRequest((previous) => ({ view: 'iso', sequence: previous.sequence + 1 }));
  }, [resetKey]);

  return (
    <div
      className="model-viewer"
      role="region"
      aria-label={`Interactive CAD model with approximate ${previewMaterial.toUpperCase()} appearance in ${previewColor}. Drag to orbit, scroll to zoom. Focus this area and use arrow keys to rotate, plus or minus to zoom, or zero to reset.`}
      data-preview-color={previewColor}
      data-preview-material={previewMaterial}
      data-inspection-view={showSeparated ? 'separated' : 'assembled'}
      tabIndex={mesh ? 0 : -1}
      onKeyDown={(event) => {
        // Buttons keep their own normal keyboard behavior.
        if (event.target !== event.currentTarget) return;
        const keys: Record<string, () => void> = {
          ArrowLeft: () => actions.current?.rotate(-0.12, 0),
          ArrowRight: () => actions.current?.rotate(0.12, 0),
          ArrowUp: () => actions.current?.rotate(0, -0.12),
          ArrowDown: () => actions.current?.rotate(0, 0.12),
          '+': () => actions.current?.zoom(1.2),
          '=': () => actions.current?.zoom(1.2),
          '-': () => actions.current?.zoom(1 / 1.2),
          '0': () => setView('iso'),
        };
        if (keys[event.key]) {
          event.preventDefault();
          keys[event.key]();
        }
      }}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 280,
        background: '#1d2329',
        display: 'flex',
        alignItems: 'stretch',
      }}
    >
      {mesh ? (
        <ViewerBoundary key={attempt} onRetry={retry} onFailure={() => setFailed(true)}>
          {contextLost ? (
            <Unavailable retry={retry} />
          ) : (
            <Canvas
              key={attempt}
              orthographic
              frameloop="demand"
              dpr={[1, 2]}
              shadows={{ type: PCFShadowMap }}
              camera={{
                position: [100, -120, 120],
                up: [0, 0, 1],
                near: 0.01,
                far: 100000,
                zoom: 8,
              }}
              gl={{ antialias: true, alpha: false, powerPreference: 'low-power' }}
              fallback={<Unavailable />}
              onCreated={({ gl }) => {
                gl.domElement.setAttribute('aria-label', 'CAD solid preview');
              }}
              style={{ width: '100%', height: '100%', position: 'absolute', inset: 0 }}
            >
              <CanvasContextListener onLost={() => setContextLost(true)} />
              <Suspense fallback={null}>
                <CadScene
                  mesh={mesh}
                  resetKey={resetKey}
                  request={request}
                  actions={actions}
                  color={previewColor}
                  material={previewMaterial}
                  parts={parts}
                  separated={showSeparated}
                  lighting={lighting}
                />
              </Suspense>
            </Canvas>
          )}
        </ViewerBoundary>
      ) : (
        <div
          role="status"
          style={{
            margin: 'auto',
            padding: 32,
            textAlign: 'center',
            color: '#aebdc7',
            lineHeight: 1.7,
          }}
        >
          <Cube size={40} weight="light" aria-hidden="true" />
          <p style={{ color: '#e1e7eb', fontWeight: 600, marginBottom: 4 }}>
            {loading ? 'Building your CAD solid…' : 'Your CAD model will appear here'}
          </p>
          {!loading && (
            <p style={{ marginTop: 0 }}>Trace a photo and set its dimensions to begin.</p>
          )}
        </div>
      )}
      {mesh && !contextLost && !failed && (
        <>
          {canSeparate && (
            <div
              aria-label="Piece inspection"
              role="group"
              style={{ position: 'absolute', top: 58, left: 16, display: 'flex', gap: 5 }}
            >
              {([false, true] as const).map((value) => (
                <button
                  type="button"
                  key={String(value)}
                  aria-pressed={showSeparated === value}
                  onClick={() => setSeparated(value)}
                  style={{
                    ...buttonStyle,
                    width: 'auto',
                    padding: '0 10px',
                    fontFamily: 'inherit',
                    fontSize: 12,
                    borderColor: showSeparated === value ? '#7bd1ef' : '#46515b',
                    color: showSeparated === value ? '#bdefff' : '#dce4e9',
                  }}
                >
                  {value ? 'Separate pieces' : 'Assembled'}
                </button>
              ))}
            </div>
          )}
          <div
            aria-label="Model views"
            role="group"
            style={{ position: 'absolute', top: 16, right: 16, display: 'flex', gap: 5 }}
          >
            {(['iso', 'top', 'front'] as const).map((view) => (
              <button
                type="button"
                key={view}
                onClick={() => setView(view)}
                aria-label={`${view === 'iso' ? 'Isometric' : view === 'top' ? 'Top' : 'Front'} view`}
                style={{
                  ...buttonStyle,
                  width: 'auto',
                  padding: '0 10px',
                  fontSize: 12,
                  fontFamily: 'inherit',
                }}
              >
                {view === 'iso' ? 'Iso' : view === 'top' ? 'Top' : 'Front'}
              </button>
            ))}
          </div>
          <div
            aria-label="Preview zoom"
            role="group"
            style={{ position: 'absolute', bottom: 18, right: 16, display: 'flex', gap: 5 }}
          >
            <button
              type="button"
              onClick={() => actions.current?.zoom(1.2)}
              title="Zoom in"
              aria-label="Zoom in"
              style={buttonStyle}
            >
              <Plus size={17} />
            </button>
            <button
              type="button"
              onClick={() => actions.current?.zoom(1 / 1.2)}
              title="Zoom out"
              aria-label="Zoom out"
              style={buttonStyle}
            >
              <Minus size={17} />
            </button>
            <button
              type="button"
              onClick={() => setView('iso')}
              title="Fit model"
              aria-label="Fit model"
              style={buttonStyle}
            >
              <ArrowsOut size={17} />
            </button>
          </div>
          <span
            style={{
              pointerEvents: 'none',
              position: 'absolute',
              left: 18,
              bottom: 22,
              color: '#a7b5bf',
              fontSize: 11,
              fontFamily: 'inherit',
              maxWidth: 'calc(100% - 154px)',
              lineHeight: 1.45,
            }}
          >
            {showSeparated && <span style={{ display: 'block' }}>Separated for inspection</span>}
            Drag to orbit · Scroll to zoom
          </span>
        </>
      )}
    </div>
  );
}
