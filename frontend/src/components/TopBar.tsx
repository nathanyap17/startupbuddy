import { Link } from "react-router-dom";
import { ReactNode } from "react";

export default function TopBar({ children }: { children?: ReactNode }) {
  return (
    <header className="topbar">
      <Link to="/" className="logo"><span className="logo-mark">SB</span> StartupBuddy</Link>
      <div className="spacer" />
      {children}
    </header>
  );
}
