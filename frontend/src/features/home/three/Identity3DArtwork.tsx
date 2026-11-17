import { Component, Suspense, lazy, useMemo, type ReactNode } from "react";
import { hasWebGL2, useMaxDeviceDpr, usePrefersReducedMotion } from "./perf";

const IdentityScene = lazy(() => import("./IdentityScene"));

type BoundaryProps = { fallback: ReactNode; children: ReactNode };

class SceneErrorBoundary extends Component<BoundaryProps, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

const MODEL_LABEL = "Bouclier 3D FaceIN à surface centrale vide, entouré d’orbites et de nœuds lumineux";

function UnavailableMessage({ children }: { children: string }) {
  return <p className="identity-3d__message" role="status">{children}</p>;
}

export function Identity3DArtwork({ className = "" }: { className?: string }) {
  const webglAvailable = useMemo(() => hasWebGL2(), []);
  const reducedMotion = usePrefersReducedMotion();
  const maxDpr = useMaxDeviceDpr();

  return (
    <div className={`identity-3d ${className}`}>
      {webglAvailable ? (
        <SceneErrorBoundary fallback={<UnavailableMessage>La scène 3D n’a pas pu être chargée.</UnavailableMessage>}>
          <Suspense fallback={null}>
            <IdentityScene maxDpr={maxDpr} reducedMotion={reducedMotion} />
          </Suspense>
        </SceneErrorBoundary>
      ) : (
        <UnavailableMessage>La scène 3D nécessite un navigateur compatible WebGL.</UnavailableMessage>
      )}
      {webglAvailable && <span className="sr-only" role="img">{MODEL_LABEL}</span>}
    </div>
  );
}
