import React, { Suspense, useState, useEffect } from "react";
import { useResource, useFetcher } from "rest-hooks";
import {
  LayerResource,
  ExtractorResource,
  ModelResource,
} from "../../resources";
import { AnnotationEntry } from "./AnnotationEntry";

import * as _ from "lodash";
import { Tag } from "../Paper";

function AnnotationModel(props: {
  paper_id: string;
  model_id: string;
  annotations: LayerResource[];
  display: {[k: string]: boolean};
  onDisplayChange: (id: string, value: boolean) => void;
  selectedLayer?: string;
  onSelectLayer: (_?: string) => void;
  selectedTag?: string;
  onSelectTag: (_: string) => void;
  color: boolean;
}) {
  const resource_id = { paperId: props.paper_id };

  const extractors_list = useResource(ExtractorResource.listShape(), {
    layer_id: props.model_id,
  });

  const model_api = useResource(ModelResource.detailShape(), {
    id: props.model_id,
  });

  const createAnnotationLayerREST = useFetcher(LayerResource.createShape());

  const createAnnotationLayer = async (name: string, from?: string) =>
    await createAnnotationLayerREST(
      resource_id,
      {
        kind: props.model_id,
        training: false,
        from,
        name,
      } as any,
      [
        [
          LayerResource.listShape(),
          resource_id,
          (newAnnotation: string, currentAnnotations: string[] | undefined) => [
            ...(currentAnnotations || []),
            newAnnotation,
          ],
        ],
      ]
    );

  return (
    <div key={"annot_" + props.model_id} style={{margin: "10px 0 10px 0", borderBottom: "solid gray 1px", backgroundColor: "#eaeaea"}}>
      <h2
        style={{
          fontVariant: "small-caps",
          backgroundColor: props.color ? "#fdd" : "white",
          padding: 10,
          display: "flex",
          flexDirection: "row",
          marginBottom: 4,
        }}
      >
        <button onClick={() => createAnnotationLayer("Untitled")}>+new</button>
        <select
          onChange={async (e: React.ChangeEvent<HTMLSelectElement>) => {
            let target = e.target;
            if (target.value != "") {
              target.disabled = true;
              await createAnnotationLayer("from." + target.value, target.value);
              target.disabled = false;
              target.value = "";
            }
          }}
        >
          <option value="">apply model</option>
          {extractors_list.map((ex) => (
            <option key={ex.id} value={ex.id}>
              {ex.id}
            </option>
          ))}
        </select>
        <div style={{ flex: 1 }}>
          {props.model_id + ": " + props.annotations.length}
        </div>
      </h2>
      <div
        style={{
          textAlign: "start",
          padding: 10,
        }}
      >
        <div>Set label to:</div>
        <nav>
          {model_api.labels.map((value: string, index: number) => {
            return (
              <button
                key={"label-" + value}
                onClick={() => props.onSelectTag(value)}
                disabled={props.selectedTag === value}
              >
                {value}
              </button>
            );
          })}
        </nav>
      </div>
      <Suspense fallback={<div>Loading..</div>}>
        {props.annotations.map((layer) => (
          <AnnotationEntry
            key={layer.id}
            layer={layer.id}
            id={props.paper_id}
            selected={props.selectedLayer === layer.id}
            onSelect={(v: boolean) =>{
              if (v) {
                props.onSelectLayer(layer.id);
              } else {
                props.onSelectLayer(undefined);
              }
          }
            }
            display={props.display[layer.id]}
            onDisplayChange={(value: boolean) => {
              props.onDisplayChange(layer.id, value);
            }}
          />
        ))}
      </Suspense>
    </div>
  );
}

export function AnnotationMenu(props: {
  id: string;
  onAddTag: (tag?: Tag) => void;
  display: {[k: string]: boolean};
  onDisplayChange: (id: string, value: boolean) => void;
}) {
  const models_list = useResource(ModelResource.listShape(), {});

  const annotations_list = useResource(LayerResource.listShape(), {
    paperId: props.id,
  });
  const annotations = _.groupBy(annotations_list, (k) => k.kind);

  const [currentTag, setCurrentTag] = useState<string|undefined>(undefined);
  const [currentModel, setCurrentModel] = useState<string|undefined>(undefined);
  const [currentLayer, setCurrentLayer] = useState<string|undefined>(undefined); 
  
  useEffect(() => {
    if (currentTag && currentLayer) {
      props.onAddTag({layer: currentLayer, label: currentTag})
    } else {
      props.onAddTag()
    }
  }, [currentTag && currentLayer])

  return (
    <div
      style={{
        backgroundColor: "#ddd",
        width: "30vw",
        minHeight: "30px",
        padding: 10,
      }}
    >
      {models_list.map((model) => (
        <AnnotationModel
          paper_id={props.id}
          model_id={model.id}
          annotations={annotations[model.id] ?? []}
          display={props.display}
          onDisplayChange={props.onDisplayChange}
          selectedLayer={currentLayer}
          onSelectLayer={(layer?: string) => {
            if (layer) {
              if (currentModel !== model.id) {
                setCurrentTag(undefined);
                setCurrentModel(model.id);
              }
              setCurrentLayer(layer);
            } else {
              setCurrentLayer(undefined);
            }
          }}
          selectedTag={currentTag}
          onSelectTag={(tag: string) => {
            if (currentModel !== model.id) {
              setCurrentLayer(undefined);
              setCurrentModel(model.id);
            }
            setCurrentTag(tag)
          }}
          color={(currentModel === model.id) && (currentTag !== undefined) && (currentLayer !== undefined)}
        />
      ))}
    </div>
  );
}
