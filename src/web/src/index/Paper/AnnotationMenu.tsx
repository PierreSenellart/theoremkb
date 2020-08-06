import React, { useState, useEffect } from "react";
import { useResource } from "rest-hooks";
import {
  LayerResource,
  ModelResource,
} from "../../resources";

import * as _ from "lodash";
import { Tag } from "../Paper";
import { AnnotationModel } from "./menu/AnnotationModel";

export function AnnotationMenu(props: {
  id: string;
  onAddTag: (tag?: Tag) => void;
  display: { [k: string]: boolean };
  onDisplayChange: (id: string, value: boolean) => void;
}) {
  const models_list = useResource(ModelResource.listShape(), {});

  const annotations_list = useResource(LayerResource.listShape(), {
    paperId: props.id,
  });
  const annotations = _.groupBy(annotations_list, (k) => k.kind);

  const [currentTag, setCurrentTag] = useState<string | undefined>(undefined);
  const [currentModel, setCurrentModel] = useState<string | undefined>(
    undefined
  );
  const [currentLayer, setCurrentLayer] = useState<string | undefined>(
    undefined
  );

  const onAddTag = props.onAddTag;
  useEffect(() => {
    if (currentTag && currentLayer) {
      onAddTag({ layer: currentLayer, label: currentTag });
    } else {
      onAddTag();
    }
  }, [currentTag, currentLayer, onAddTag]);

  return (
    <>
      {models_list.map((model) => (
        <AnnotationModel
          key={model.id}
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
            setCurrentTag(tag);
          }}
          color={
            currentModel === model.id &&
            currentTag !== undefined &&
            currentLayer !== undefined
          }
        />
      ))}
    </>
  );
}
