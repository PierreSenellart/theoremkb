import React, { useState, useEffect } from "react";
import { useResource } from "rest-hooks";
import { AnnotationLayerResource, AnnotationClassResource } from "../../resources";

import * as _ from "lodash";
import { Tag } from "../Paper";
import { AnnotationClass } from "./menu/AnnotationClass";

export function AnnotationMenu(props: {
  id: string;
  onAddTag: (tag?: Tag) => void;
  display: { [k: string]: boolean };
  onDisplayChange: (id: string, value: boolean) => void;
}) {
  const classes = useResource(AnnotationClassResource.listShape(), {});

  const annotationList = useResource(AnnotationLayerResource.listShape(), {
    paperId: props.id,
  });
  const annotations = _.groupBy(annotationList, (k) => k.class);

  const [currentTag, setCurrentTag] = useState<string | undefined>(undefined);
  const [currentClass, setCurrentClass] = useState<string | undefined>(
    undefined
  );
  const [currentLayer, setCurrentLayer] = useState<string | undefined>(
    undefined
  );

  const onAddTag = props.onAddTag;
  useEffect(() => {
    if (currentTag && currentLayer) {
      onAddTag({
        layer: currentLayer,
        label: currentTag,
        parents: classes.find((x) => x.id == currentClass).parents,
      });
    } else {
      onAddTag();
    }
  }, [currentTag, currentLayer, classes, currentClass, onAddTag]);

  return (
    <>
      {classes.map((class_) => (
        <AnnotationClass
          key={class_.id}
          paperId={props.id}
          classId={class_.id}
          annotations={annotations[class_.id] ?? []}
          display={props.display}
          onDisplayChange={props.onDisplayChange}
          selectedLayer={currentLayer}
          onSelectLayer={(layer?: string) => {
            if (layer) {
              if (currentClass !== class_.id) {
                setCurrentTag(undefined);
                setCurrentClass(class_.id);
              }
              setCurrentLayer(layer);
            } else {
              setCurrentLayer(undefined);
            }
          }}
          selectedTag={currentTag}
          onSelectTag={(tag: string) => {
            if (currentClass !== class_.id) {
              setCurrentLayer(undefined);
              setCurrentClass(class_.id);
            }
            setCurrentTag(tag);
          }}
          color={
            currentClass === class_.id &&
            currentTag !== undefined &&
            currentLayer !== undefined
          }
        />
      ))}
    </>
  );
}
