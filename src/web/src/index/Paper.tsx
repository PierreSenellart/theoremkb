import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { useResource } from "rest-hooks";
import { AnnotationResource } from "../resources";
import { PaperRenderer } from "./Paper/PaperRenderer";
import { AnnotationMenu } from "./Paper/AnnotationMenu";
export function Paper() {
  let { id } = useParams();

  let [enableAddBoxLayer, setEnableAddBoxLayer] = useState<
    [string, string] | undefined
  >(undefined);

  return (
    <div style={{ height: "100%" }}>
      <div style={{ display: "flex", height: "100%" }}>
        <PaperRenderer
          id={id}
          enableAddBoxLayer={enableAddBoxLayer} />
        <AnnotationMenu id={id} onAnnotationSelected={setEnableAddBoxLayer} />
      </div>
    </div>
  );
}
