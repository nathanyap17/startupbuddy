import { Link } from "react-router-dom";
import { ReactNode } from "react";

export default function TopBar({ children }: { children?: ReactNode }) {
  return (
    <header className="topbar">
      <Link to="/" className="logo"><img src="/logo.png" alt="" /> <span className="logo-text">StartupBuddy</span></Link>
      <div className="spacer" />
      {children}
    </header>
  );
}
