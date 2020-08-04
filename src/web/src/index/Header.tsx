import React, { Suspense } from "react";
import { useRouteMatch, Link } from "react-router-dom";
import { useResource } from "rest-hooks";
import { PaperResource } from "../resources";

function HeaderPaper(props: { id: string }) {
  let paper_info = useResource(PaperResource.detailShape(), { id: props.id });

  let title = "TheoremKB - " + (paper_info.title.length > 0 ? paper_info.title :  props.id);

  return (
    <Link to="/" style={{ textDecoration: "none", color: "white" }}>
      <h2>{title}</h2>
    </Link>
  );
}

export function Header() {
  let match = useRouteMatch<{ id: string }>("/paper/:id");

  if (match) {
    return (
      <header className="App-header">
        <Suspense fallback={<h2>TheoremKB - {match.params.id}</h2>}>
          <HeaderPaper id={match.params.id} />
        </Suspense>
      </header>
    );
  } else {
    return (
      <header className="App-header">
        <h2>TheoremKB</h2>
      </header>
    );
  }
}
