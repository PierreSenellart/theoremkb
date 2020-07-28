import React, { Suspense, useState } from "react";
import { useResource, useFetcher } from "rest-hooks";
import { LayerResource } from "../../resources";
import { AnnotationEntry } from "./AnnotationEntry";

import * as _ from "lodash";

export function AnnotationMenu(props: {
  id: string;
  onAnnotationSelected: (model_label?: [string, string]) => void;
  onDisplayChange: (id: string, value: boolean) => void;
}) {
  const models = ["segmentation", "fulltext", "results"];
  let [collapse_state, set_collapse_state] = useState<string | undefined>(
    undefined
  );
  const resource_id = { paperId: props.id };
  const annotations_list = useResource(LayerResource.listShape(), resource_id);
  const createAnnotationLayer = useFetcher(LayerResource.createShape());

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
      {models.map((model) => (
        <div key={"annot_" + model}>
          <h2
            className="link"
            onClick={() => {
              const target = model === collapse_state ? undefined : model;
              set_collapse_state(target);
              if (target == null) {
                props.onAnnotationSelected();
              }
            }}
            style={{
              fontVariant: "small-caps",
              backgroundColor: "white",
              padding: 10,
              borderLeft:
                model === collapse_state ? "solid #8ac 16px " : undefined,
            }}
          >
            {model + ": " + (annotations[model] ?? []).length}
          </h2>
          <Suspense fallback={<div>Loading..</div>}>
            {collapse_state === model ? (
              <>
                {(annotations[model] ?? []).map((layer) => (
                  <AnnotationEntry
                    key={layer.id}
                    layer={layer.id}
                    id={props.id}
                    onLabelSelected={(value: string) =>
                      props.onAnnotationSelected([layer.id, value])
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
                        kind: model,
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
                <button
                  onClick={() =>
                    createAnnotationLayer(
                      resource_id,
                      {
                        kind: model,
                        training: false,
                        name: "CRF",
                        from: "crf",
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
                    )
                  }
                >
                  apply model
                </button>
              </>
            ) : (
              <></>
            )}
          </Suspense>
        </div>
      ))}
    </div>
  );
}
