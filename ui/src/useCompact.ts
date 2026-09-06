import { useEffect, useState } from "react";

export function useCompact() {
  const [compact, setCompact] = useState(
    () => window.matchMedia("(max-width: 599px)").matches,
  );
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 599px)");
    const onChange = () => setCompact(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return compact;
}
