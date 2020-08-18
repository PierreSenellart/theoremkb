import React, { useState, CSSProperties, useEffect } from "react";
import { useResource, useFetcher } from "rest-hooks";
import { AnnotationLayerResource } from "../../../resources";

import {
  IoIosEye,
  IoIosEyeOff,
  IoMdSquareOutline,
  IoMdCheckbox,
  IoMdTrash,
} from "react-icons/io";
import {BsBoundingBoxCircles} from "react-icons/bs";

function Editable(props: {
  text: string;
  edit?: boolean;
  onEdit: (_: string) => void;
  style?: CSSProperties;
}) {
  const [editing, setEditing] = useState<boolean>(props.edit);
  const [curText, setCurText] = useState(props.text);

  const finishEdit = () => {
    setEditing(false);
  };

  const validateEdit = () => {
    finishEdit();
    props.onEdit(curText);
  };

  if (editing) {
    return (
      <input
        type="text"
        value={curText}
        onBlur={validateEdit}
        onKeyDown={(e) => {
          if (e.keyCode === 13) {
            validateEdit();
          } else if (e.keyCode === 27) {
            finishEdit();
          }
        }}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          setCurText(e.target.value)
        }
        autoFocus
      />
    );
  } else {
    return (
      <div
        onClick={() => {
          setCurText(props.text);
          setEditing(true);
        }}
        style={props.style}
      >
        {props.text}
      </div>
    );
  }
}


function IconToggle(props: {
  style?: CSSProperties;
  onElem: React.ReactChild;
  offElem: React.ReactChild;
  tooltip?: string;
  on: boolean;
  onChange: (x: boolean) => void;
}) {
  return (
    <div onClick={() => props.onChange(!props.on)} style={props.style}>
      <div style={{ cursor: "pointer" }} title={props.tooltip ?? ""}>
        {props.on ? props.onElem : props.offElem}
      </div>
    </div>
  );
}

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
  const annotationLayer = useResource(AnnotationLayerResource.detailShape(), document);

  const updateAnnotation = useFetcher(AnnotationLayerResource.partialUpdateShape());
  const deleteAnnotation = useFetcher(AnnotationLayerResource.deleteShape());

  const onDisplayChange = props.onDisplayChange;

  useEffect(() => {
    const v = localStorage.getItem(props.layer+"-display");
    if (v === null) {
      if (annotationLayer.training) {
        onDisplayChange(true)
      }
    } else {
      onDisplayChange(v === "true")
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div style={{ backgroundColor: "#eee" }}>
      <div
        style={{
          display: "flex",
          backgroundColor: "#f8f8f8",
          flexDirection: "row",
          borderLeft: (props.selected ? "solid red 10px" : "solid transparent 10px")
        }}
      >

        <div
            style={{ cursor: "pointer", margin: 10, display: "inline-block", color: props.selected ? "red" : "black" }}
            onClick={() => {
              props.onSelect(!props.selected);
              if (!props.selected) {
                props.onDisplayChange(true)
              }
            }}
            title="select layer for annotation"
          >
            <BsBoundingBoxCircles size="1.5em" />
        </div>
        <IconToggle
          tooltip="toggle display"
          style={{ padding: 10 }}
          onElem={<IoIosEye size="1.5em" />}
          offElem={<IoIosEyeOff size="1.5em" />}
          on={props.display}
          onChange={(v: boolean) => {
            localStorage.setItem(props.layer+"-display", v.toString());
            props.onDisplayChange(v);
          }}
        />
        <IconToggle
          tooltip="validate for training"
          style={{ padding: 10 }}
          onElem={<IoMdCheckbox size="1.5em" />}
          offElem={<IoMdSquareOutline size="1.5em" />}
          on={annotationLayer.training}
          onChange={(value: boolean) => {
            updateAnnotation(document, { training: value });
          }}
        />
        <Editable
          style={{ padding: 10, fontSize: "1.2em" }}
          text={annotationLayer.name}
          edit={props.new}
          onEdit={(name: string) => updateAnnotation(document, { name })}
        />
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
