import React, { Suspense } from "react";
import { Switch, Route } from "react-router-dom";

import "./App.css";
import { ListPapers } from "./index/ListPapers";
import { Header } from "./index/Header";
import { Paper } from "./index/Paper";

function App() {
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
      <Switch>
        <Route path="/paper/:id">
          <Header />
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
