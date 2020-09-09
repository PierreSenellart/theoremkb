import React, { useEffect } from "react";
import { useResource, useFetcher } from "rest-hooks";
import {
  AnnotationLayerResource,
  AnnotationLayerGroupResource,
} from "../../../resources";

import {
  IoIosEye,
  IoIosEyeOff,
  IoMdSquareOutline,
  IoMdCheckbox,
  IoMdTrash,
} from "react-icons/io";
import { BsBoundingBoxCircles } from "react-icons/bs";
import { Editable } from "../../../misc/Editable";
import { IconToggle } from "../../../misc/IconToggle";
import { update } from "lodash";
import { ClickSelectCreate } from "./ClickSelectCreate";

export function AnnotationEntry(props: {
  layer: string;
  id: string;

  selected: boolean;
  onSelect: (_: boolean) => void;
  display: boolean;
  onDisplayChange: (value: boolean) => void;
  new: boolean;
}) {
  const document = {
    id: props.layer,
    paperId: props.id,
  };
  const annotationLayer = useResource(
    AnnotationLayerResource.detailShape(),
    document
  );
  const annotationLayerGroup = useResource(
    AnnotationLayerGroupResource.detailShape(),
    {
      id: annotationLayer.groupId,
    }
  );

  const updateAnnotation = useFetcher(
    AnnotationLayerResource.partialUpdateShape()
  );
  const deleteAnnotation = useFetcher(AnnotationLayerResource.deleteShape());

  const onDisplayChange = props.onDisplayChange;

  useEffect(() => {
    const v = localStorage.getItem(props.layer + "-display");
    if (v === null) {
      if (annotationLayer.training) {
        onDisplayChange(true);
      }
    } else {
      onDisplayChange(v === "true");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ backgroundColor: "#eee" }}>
      <div
        style={{
          display: "flex",
          backgroundColor: "#f8f8f8",
          flexDirection: "row",
          borderLeft: props.selected
            ? "solid red 10px"
            : "solid transparent 10px",
        }}
      >
        {annotationLayerGroup.class != "misc" && (
          <div
            style={{
              cursor: "pointer",
              margin: 10,
              display: "inline-block",
              color: props.selected ? "red" : "black",
            }}
            onClick={() => {
              props.onSelect(!props.selected);
              if (!props.selected) {
                props.onDisplayChange(true);
              }
            }}
            title="select layer for annotation"
          >
            <BsBoundingBoxCircles size="1.5em" />
          </div>
        )}
        <IconToggle
          tooltip="toggle display"
          style={{ padding: 10 }}
          onElem={<IoIosEye size="1.5em" />}
          offElem={<IoIosEyeOff size="1.5em" />}
          on={props.display}
          onChange={(v: boolean) => {
            localStorage.setItem(props.layer + "-display", v.toString());
            props.onDisplayChange(v);
          }}
        />
        {annotationLayerGroup.class != "misc" && (
          <IconToggle
            style={{ padding: 10 }}
            tooltip="validate for training"
            onElem={<IoMdCheckbox size="1.5em" />}
            offElem={<IoMdSquareOutline size="1.5em" />}
            on={annotationLayer.training}
            onChange={(value: boolean) =>
              updateAnnotation({ id: annotationLayer.id }, { training: value })
            }
          />
        )}

        <div style={{ padding: 10, fontSize: "1.2em" }}>
          <ClickSelectCreate
            value={annotationLayerGroup.name}
            class={annotationLayerGroup.class}
            onCreate={(name) => {
              updateAnnotation({ id: annotationLayer.id }, { newgroup: name } as any)
            }}
            onSelect={(id) => {
              updateAnnotation({ id: annotationLayer.id }, { groupId: id })
            }}
          />
        </div>
        <div style={{ flex: 1, textAlign: "end" }}>
          <div
            style={{ cursor: "pointer", margin: 10, display: "inline-block" }}
            onClick={() => deleteAnnotation(document, undefined)}
            title="delete layer"
          >
            <IoMdTrash size="1.5em" />
          </div>
        </div>
      </div>
    </div>
  );
}
