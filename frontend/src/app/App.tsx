import { useEffect } from "react";
import { SiteShell } from "../components/layout/SiteShell";
import { getCurrentRoute } from "./routes";

export function App() {
  const route = getCurrentRoute();
  const PageComponent = route.component;

  useEffect(() => {
    document.title = route.title;
    const targetId = window.location.hash.slice(1);
    if (!targetId) return;

    const frame = window.requestAnimationFrame(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: "instant" });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [route.fileName, route.title]);

  return (
    <SiteShell variant={route.variant}>
      <PageComponent />
    </SiteShell>
  );
}
