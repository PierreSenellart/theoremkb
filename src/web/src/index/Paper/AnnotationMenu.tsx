import React, { Suspense, useState } from "react";
import { useResource, useFetcher } from "rest-hooks";
import { LayerResource, ExtractorResource, ModelResource } from "../../resources";
import { AnnotationEntry } from "./AnnotationEntry";

import * as _ from "lodash";

function AnnotationModel(props: {
  paper_id: string;
  layer_id: string;
  annotations: LayerResource[];
  collapsed: boolean;
  onCollapseChange: (_: boolean) => void;
  onDisplayChange: (id: string, value: boolean) => void;
  onAnnotationSelected: (model: string, label: string) => void;
}) {
  const resource_id = { paperId: props.paper_id };

  const extractors_list = useResource(ExtractorResource.listShape(), {
    layer_id: props.layer_id,
  });
  const createAnnotationLayer = useFetcher(LayerResource.createShape());

  return (
    <div key={"annot_" + props.layer_id}>
      <h2
        className="link"
        onClick={() => props.onCollapseChange(!props.collapsed)}
        style={{
          fontVariant: "small-caps",
          backgroundColor: "white",
          padding: 10,
          borderLeft: props.collapsed ? undefined : "solid #8ac 16px ",
        }}
      >
        {props.layer_id + ": " + props.annotations.length}
      </h2>
      <Suspense fallback={<div>Loading..</div>}>
        {!props.collapsed ? (
          <>
            {props.annotations.map((layer) => (
              <AnnotationEntry
                key={layer.id}
                layer={layer.id}
                id={props.paper_id}
                onLabelSelected={(value: string) =>
                  props.onAnnotationSelected(layer.id, value)
                }
                onDisplayChange={(value: boolean) => {
                  props.onDisplayChange(layer.id, value);
                }}
              />
            ))}
            <button
              onClick={() =>
                createAnnotationLayer(
                  resource_id,
                  {
                    kind: props.layer_id,
                    training: false,
                    name: "Untitled layer",
                  },
                  [
                    [
                      LayerResource.listShape(),
                      resource_id,
                      (
                        newAnnotation: string,
                        currentAnnotations: string[] | undefined
                      ) => [...(currentAnnotations || []), newAnnotation],
                    ],
                  ]
                )
              }
            >
              new layer
            </button>
            <select
              onChange={async (e: React.ChangeEvent<HTMLSelectElement>) => {
                let target = e.target;
                if (target.value != "") {
                  target.disabled = true;

                  await createAnnotationLayer(
                    resource_id,
                    {
                      kind: props.layer_id,
                      training: false,
                      name: "from." + target.value,
                      from: target.value,
                    } as any,
                    [
                      [
                        LayerResource.listShape(),
                        resource_id,
                        (
                          newAnnotation: string,
                          currentAnnotations: string[] | undefined
                        ) => [...(currentAnnotations || []), newAnnotation],
                      ],
                    ]
                  );

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
          </>
        ) : (
          <></>
        )}
      </Suspense>
    </div>
  );
}

export function AnnotationMenu(props: {
  id: string;
  onAnnotationSelected: (model_label?: [string, string]) => void;
  onDisplayChange: (id: string, value: boolean) => void;
}) {
  const models_list = useResource(ModelResource.listShape(), {});

  let [collapse_state, set_collapse_state] = useState<string | undefined>(
    undefined
  );

  const annotations_list = useResource(LayerResource.listShape(), {
    paperId: props.id,
  });
  const annotations = _.groupBy(annotations_list, (k) => k.kind);

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
          layer_id={model.id}
          annotations={annotations[model.id] ?? []}
          collapsed={collapse_state !== model.id}
          onCollapseChange={(v: boolean) => {
            if (v) {
              props.onAnnotationSelected();
              set_collapse_state(undefined);
            } else {
              set_collapse_state(model.id);
            }
          }}
          onDisplayChange={props.onDisplayChange}
          onAnnotationSelected={(model, label) =>
            props.onAnnotationSelected([model, label])
          }
        />
      ))}
    </div>
  );
}
