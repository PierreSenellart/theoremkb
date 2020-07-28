import React, { useState, Suspense } from "react";
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

  let [displayLayer, setDisplayLayer] = useState<{[k: string]: boolean}>({});

  return (
    <div style={{ height: "100%" }}>
      <div style={{ display: "flex", height: "100%" }}>
        <PaperRenderer
          id={id}
          enableAddBoxLayer={enableAddBoxLayer} 
          displayLayer={displayLayer}
        />
        <Suspense fallback="Loading.">
          <AnnotationMenu 
            id={id} 
            onAnnotationSelected={setEnableAddBoxLayer}
            onDisplayChange={(name, value) => setDisplayLayer({...displayLayer, [name]: value})} />
        </Suspense>
      </div>
    </div>
  );
}
