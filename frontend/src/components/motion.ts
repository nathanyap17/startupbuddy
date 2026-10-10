import { RefObject, useEffect, useRef } from "react";

export const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Run `play` once when the element first scrolls into view (one-time effects: count-ups, line drawing). */
export function useReveal<T extends HTMLElement>(play: (el: T) => void | (() => void), threshold = 0.2) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || reducedMotion()) return;
    let cleanup: void | (() => void);
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        io.disconnect();
        cleanup = play(el);
      }
    }, { threshold });
    io.observe(el);
    return () => { io.disconnect(); if (typeof cleanup === "function") cleanup(); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return ref;
}

/**
 * Reversible scroll reveal for every `.rv` element inside `root`:
 * appears when it enters from below (scrolling down), hides again when it leaves
 * through the bottom (scrolling up). Elements scrolled past upward stay visible.
 */
export function useScrollReveal(root: RefObject<HTMLElement>) {
  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const items = Array.from(el.querySelectorAll<HTMLElement>(".rv"));
    if (reducedMotion()) { items.forEach((i) => i.classList.add("in")); return; }
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        const t = e.target as HTMLElement;
        if (e.isIntersecting) t.classList.add("in");
        else if (e.boundingClientRect.top > 0) t.classList.remove("in"); // left through the bottom: user scrolled up
      }
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    items.forEach((i) => io.observe(i));
    return () => io.disconnect();
  }, [root]);
}
