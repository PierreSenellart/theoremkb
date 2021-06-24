import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useStatefulResource } from "@rest-hooks/legacy";
import { AutoSizer } from "react-virtualized";
import { PaperResource } from "../resources";
import { PaperListView } from "./ListPapers/PaperListView";
import { PaperSearch } from "./ListPapers/PaperSearch";
import { Header } from "./Header";
import _ from "lodash";

export function ListPapers(): React.ReactElement {
  const [query, setQuery] = useState({});

  const papersList = useStatefulResource(PaperResource.listShape(), {
    q: JSON.stringify({ ...query, limit: 0 }),
  });

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <Header>
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "baseline",
          }}
        >
          <Link to="/layers" style={{ paddingRight: 30 }}>
            &gt; layers and extractors
          </Link>
          <PaperSearch onQueryChange={setQuery} />
          <div style={{ fontStyle: "italic", padding: 10, fontSize: "0.8em" }}>
            {papersList.data?.count ?? 0} papers.
          </div>
        </div>
      </Header>
      <div style={{ flex: 1 }}>
        <AutoSizer>
          {({ width, height }) => (
            <PaperListView width={width} height={height} query={query} />
          )}
        </AutoSizer>
      </div>
    </div>
  );
}
