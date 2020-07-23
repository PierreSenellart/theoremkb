import React from "react";
import { useRouteMatch } from "react-router-dom";
export function Header() {
  let match = useRouteMatch<{ id: string; }>("/paper/:id");

  let title = "TheoremKB";
  if (match) {
    title += " - " + match.params.id;
  }
  return (
    <header className="App-header">
      <h2>{title}</h2>
    </header>
  );
}
