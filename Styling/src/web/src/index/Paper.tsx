import React, { useState, Suspense } from "react";
import { useParams } from "react-router-dom";
import { PaperRenderer } from "./Paper/PaperRenderer";
import { AnnotationMenu } from "./Paper/AnnotationMenu";
import { AnnotationClassFilter } from "../resources";

export interface Tag {
  parents: AnnotationClassFilter[];
  layer: string;
  label: string;
}

export const Infobox = React.createContext({
  infobox: "",
});

export const InfoboxSetter = React.createContext({
  setInfobox: (_: any) => {},
});

Infobox.displayName = "Infobox";

export function Paper() {
  let { id } = useParams<{id: string}>();

  let [infobox, setInfobox] = useState<any>();

  let [addTag, setAddTag] = useState<Tag | undefined>(undefined);

  let [displayLayer, setDisplayLayer] = useState<{ [k: string]: boolean }>({});

  return (
    <Infobox.Provider value={{ infobox }}>
      <InfoboxSetter.Provider value={{ setInfobox }}>
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          <div
            style={{
              flex: 1,
              height: "100%",
            }}
          >
            <Suspense fallback="Loading.">
              <PaperRenderer
                id={id}
                addTag={addTag}
                displayLayer={displayLayer}
              />
            </Suspense>
          </div>
          <div
            style={{
              backgroundColor: "#ddd",
              minHeight: "30px",
              padding: 10,
              flex: 0.4,
              overflowY: "scroll",
            }}
          >
            <Suspense fallback="Loading.">
              <AnnotationMenu
                id={id}
                onAddTag={setAddTag}
                display={displayLayer}
                onDisplayChange={(name, value) =>
                  setDisplayLayer((displayLayer) => ({
                    ...displayLayer,
                    [name]: value,
                  }))
                }
              />
            </Suspense>
          </div>
        </div>
      </InfoboxSetter.Provider>
    </Infobox.Provider>
  );
}
