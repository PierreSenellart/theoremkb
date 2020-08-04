import React, { useState, CSSProperties, useEffect } from "react";
import { useResource, useFetcher } from "rest-hooks";
import { LayerResource, AnnotationEnum, ModelResource } from "../../resources";

import {
  IoIosArrowDown,
  IoIosEye,
  IoIosEyeOff,
  IoMdSquareOutline,
  IoMdCheckbox,
  IoMdTrash,
} from "react-icons/io";
import {BsBoundingBoxCircles} from "react-icons/bs";

function Editable(props: {
  text: string;
  onEdit: (_: string) => void;
  style?: CSSProperties;
}) {
  const [editing, setEditing] = useState(false);
  const [curText, setCurText] = useState("");

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
          if (e.keyCode == 13) {
            validateEdit();
          } else if (e.keyCode == 27) {
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

function Checkbox(props: {
  label: string;
  checked: boolean;
  onChange: (_: boolean) => void;
}) {
  return (
    <div>
      {props.label}
      <input
        type="checkbox"
        checked={props.checked}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          props.onChange(e.target.checked)
        }
      />
    </div>
  );
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
}) {
  const document = {
    id: props.layer,
    paperId: props.id,
  };
  const annotation_layer = useResource(LayerResource.detailShape(), document);

  const updateAnnotation = useFetcher(LayerResource.partialUpdateShape());
  const deleteAnnotation = useFetcher(LayerResource.deleteShape());

  useEffect(() => {
    if (annotation_layer.training) {
      props.onDisplayChange(true)
    }
  }, [])

  //<Form schema={model_api.schema}/>
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
            onClick={() => props.onSelect(!props.selected)}
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
          onChange={props.onDisplayChange}
        />
        <IconToggle
          tooltip="validate for training"
          style={{ padding: 10 }}
          onElem={<IoMdCheckbox size="1.5em" />}
          offElem={<IoMdSquareOutline size="1.5em" />}
          on={annotation_layer.training}
          onChange={(value: boolean) => {
            updateAnnotation(document, { training: value });
          }}
        />
        <Editable
          style={{ padding: 10, fontSize: "1.2em" }}
          text={annotation_layer.name}
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
