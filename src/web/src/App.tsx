import React, { Suspense } from "react";
import { Switch, Route, useParams } from "react-router-dom";

import "./App.css";
import { ListPapers } from "./index/ListPapers";
import { Header } from "./index/Header";
import { Paper } from "./index/Paper";

function App() {
  let { id } = useParams();

  return (
    <div
      className="App"
      style={{
        height: "100vh",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Header />
      <Switch>
        <Route path="/paper/:id">
          <Paper />
        </Route>
        <Route path="/">
          <Suspense fallback="Loading..">
            <ListPapers />
          </Suspense>
        </Route>
      </Switch>
    </div>
  );
}

export default App;
