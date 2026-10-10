import { Link } from "react-router-dom";
import { ReactNode, useEffect, useState } from "react";

/** `glass`: transparent at the top of the page, frosted glass once scrolled (landing page). */
export default function TopBar({ children, glass = false }: { children?: ReactNode; glass?: boolean }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    if (!glass) return;
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [glass]);
  return (
    <header className={`topbar ${glass ? "glass-bar" : ""} ${scrolled ? "scrolled" : ""}`}>
      <Link to="/" className="logo"><img src="/logo.png" alt="" /> <span className="logo-text">StartupBuddy</span></Link>
      <div className="spacer" />
      {children}
    </header>
  );
}
