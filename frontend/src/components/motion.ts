import { useEffect, useRef } from "react";

export const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Run `play` once when the element first scrolls into view. Content stays visible if motion is reduced. */
export function useReveal<T extends HTMLElement>(play: (el: T) => void | (() => void), threshold = 0.2) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (reducedMotion()) { el.classList.add("revealed"); return; }
    el.classList.add("will-reveal");
    let cleanup: void | (() => void);
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        io.disconnect();
        el.classList.add("revealed");
        cleanup = play(el);
      }
    }, { threshold });
    io.observe(el);
    return () => { io.disconnect(); if (typeof cleanup === "function") cleanup(); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return ref;
}
