import React, { Suspense } from "react";
import { useRouteMatch, Link } from "react-router-dom";
import { useResource } from "rest-hooks";
import { PaperResource } from "../resources";

function HeaderPaper(props: { id: string }) {
  let paperInfo = useResource(PaperResource.detailShape(), { id: props.id });

  let title = "TheoremKB - " + (paperInfo.title.length > 0 ? paperInfo.title :  props.id);

  return (
    <Link to="/" style={{ textDecoration: "none", color: "white" }}>
      <h3>{title}</h3>
    </Link>
  );
}

export function Header(props: {children?: React.ReactChild}) {
  let match = useRouteMatch<{ id: string }>("/paper/:id");

  if (match) {
    return (
      <header className="App-header">
        <Suspense fallback={<h3>TheoremKB - {match.params.id}</h3>}>
          <HeaderPaper id={match.params.id} />
        </Suspense>
        {props.children}
      </header>
    );
  } else {
    return (
      <header className="App-header" style={{display: "flex", flexDirection: "row", alignItems: "center"}}>
        <h3 style={{flex: 0, marginRight: 30}}>TheoremKB</h3>
        <div style={{flex: 1}}>
        {props.children}
        </div>
      </header>
    );
  }
}
