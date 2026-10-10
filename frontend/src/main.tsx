import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "@xyflow/react/dist/style.css";
import "./styles.css";
import Landing from "./pages/Landing";
import Sessions from "./pages/Sessions";
import Workspace from "./pages/Workspace";
import Report from "./pages/Report";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<Sessions />} />
        <Route path="/app/s/:id" element={<Workspace />} />
        <Route path="/app/s/:id/report" element={<Report />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
