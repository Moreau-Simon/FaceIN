import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import type { RefObject } from "react";
import * as THREE from "three";

const NODE_COUNT = 4;
const ORBIT_NODES: readonly [number, number, number][] = [
  [-1.1, 0.16, 0.22],
  [0.82, 0.88, -0.18],
  [1.1, -0.4, 0.15],
  [-0.1, -1.25, -0.13],
];

function createShieldGeometry() {
  const shape = new THREE.Shape();
  shape.moveTo(0, 1.13);
  shape.quadraticCurveTo(0.26, 1.02, 0.75, 0.82);
  shape.quadraticCurveTo(0.78, 0.8, 0.78, 0.73);
  shape.lineTo(0.72, 0.06);
  shape.quadraticCurveTo(0.67, -0.59, 0, -1.06);
  shape.quadraticCurveTo(-0.67, -0.59, -0.72, 0.06);
  shape.lineTo(-0.78, 0.73);
  shape.quadraticCurveTo(-0.78, 0.8, -0.75, 0.82);
  shape.quadraticCurveTo(-0.26, 1.02, 0, 1.13);
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: 0.16,
    bevelEnabled: true,
    bevelSegments: 3,
    bevelSize: 0.045,
    bevelThickness: 0.045,
    curveSegments: 12,
  });
  geometry.center();
  return geometry;
}

function OrbitingNodes() {
  const nodesRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  useLayoutEffect(() => {
    const mesh = nodesRef.current;
    if (!mesh) return;
    ORBIT_NODES.forEach((position, index) => {
      dummy.position.set(...position);
      dummy.scale.setScalar(index === 1 ? 1.18 : 1);
      dummy.updateMatrix();
      mesh.setMatrixAt(index, dummy.matrix);
    });
    mesh.instanceMatrix.needsUpdate = true;
  }, [dummy]);

  return (
    <instancedMesh ref={nodesRef} args={[undefined, undefined, NODE_COUNT]}>
      <sphereGeometry args={[0.075, 20, 16]} />
      <meshStandardMaterial color="#a697ff" emissive="#7357ed" emissiveIntensity={1.1} roughness={0.25} />
    </instancedMesh>
  );
}

function IdentitySeal() {
  const shieldGeometry = useMemo(createShieldGeometry, []);

  useEffect(
    () => () => {
      shieldGeometry.dispose();
    },
    [shieldGeometry],
  );

  return (
    <group>
      <mesh geometry={shieldGeometry} dispose={null}>
        <meshPhysicalMaterial
          color="#c9c4fa"
          emissive="#5847d2"
          emissiveIntensity={0.16}
          metalness={0.2}
          roughness={0.24}
          clearcoat={0.9}
          clearcoatRoughness={0.18}
        />
      </mesh>
      <mesh geometry={shieldGeometry} position={[0, 0, 0.13]} scale={[0.82, 0.82, 0.4]} dispose={null}>
        <meshPhysicalMaterial color="#f7f5ff" metalness={0.08} roughness={0.3} clearcoat={0.75} />
      </mesh>
    </group>
  );
}

function OrbitalFrame({ rotationRef }: { rotationRef: RefObject<THREE.Group | null> }) {
  const { width } = useThree((state) => state.size);
  const orbitScale = width < 480 ? 0.82 : width < 560 ? 0.9 : 1;

  return (
    <group ref={rotationRef}>
      <group position={[0, 0, 0.18]} scale={orbitScale}>
        <mesh rotation={[0.34, 0.1, 0.18]}>
          <torusGeometry args={[1.38, 0.012, 8, 128]} />
          <meshBasicMaterial color="#8471f2" transparent opacity={0.88} />
        </mesh>
        <mesh rotation={[0.45, 0.68, -0.45]}>
          <torusGeometry args={[1.5, 0.01, 8, 128]} />
          <meshBasicMaterial color="#83b8ee" transparent opacity={0.82} />
        </mesh>
        <mesh rotation={[0.62, -0.48, 0.78]}>
          <torusGeometry args={[1.62, 0.009, 8, 128]} />
          <meshBasicMaterial color="#f4a27e" transparent opacity={0.78} />
        </mesh>
      </group>
      <group position={[0, 0, 0.75]} scale={0.86}>
        <OrbitingNodes />
      </group>
    </group>
  );
}

export function IdentityModel({ reducedMotion }: { reducedMotion: boolean }) {
  const modelRef = useRef<THREE.Group>(null);
  const orbitRef = useRef<THREE.Group>(null);
  const pointer = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const onPointerMove = (event: PointerEvent) => {
      pointer.current.x = (event.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (event.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    return () => window.removeEventListener("pointermove", onPointerMove);
  }, []);

  useFrame((state, delta) => {
    const model = modelRef.current;
    if (!model) return;
    if (reducedMotion) {
      model.scale.setScalar(1);
      return;
    }

    const time = state.clock.elapsedTime;
    const progress = THREE.MathUtils.clamp(time / 1.05, 0, 1);
    const eased = 1 - (1 - progress) ** 3;
    model.scale.setScalar(0.9 + eased * 0.1 + Math.sin(time * 0.6) * 0.006);
    model.position.y = Math.sin(time * 0.45) * 0.025;
    model.rotation.y = THREE.MathUtils.damp(
      model.rotation.y,
      pointer.current.x * 0.18 + Math.sin(time * 0.28) * 0.045,
      2.1,
      delta,
    );
    model.rotation.x = THREE.MathUtils.damp(
      model.rotation.x,
      -pointer.current.y * 0.13 + Math.sin(time * 0.21) * 0.024,
      2.1,
      delta,
    );
    if (orbitRef.current) {
      orbitRef.current.rotation.z = time * 0.075;
      orbitRef.current.rotation.x = Math.sin(time * 0.17) * 0.055;
    }
  });

  return (
    <group ref={modelRef}>
      <OrbitalFrame rotationRef={orbitRef} />
      <IdentitySeal />
    </group>
  );
}
