import React from "react";
import ReactDOM from "react-dom/client";
import { Root } from "./Root";
import { warmBackend } from "./backendConnection";
import "./styles.css";

// Começa a acordar a API enquanto a pessoa navega pelo site.
void warmBackend().catch(() => { /* a próxima ação pode tentar novamente */ });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
