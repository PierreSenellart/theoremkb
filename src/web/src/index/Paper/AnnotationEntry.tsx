import React, { useState, CSSProperties } from "react";
import { useResource, useFetcher } from "rest-hooks";
import { LayerResource, AnnotationEnum, ModelResource } from "../../resources";

import { IoIosArrowDown, IoIosEye, IoIosEyeOff } from "react-icons/io";

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
  on: boolean;
  onChange: (x: boolean) => void;
}) {
  return (
    <div onClick={() => props.onChange(!props.on)} style={props.style}>
      {props.on ? props.onElem : props.offElem}
    </div>
  );
}

export function AnnotationEntry(props: {
  layer: string;
  id: string;
  onLabelSelected: (value: string) => void;
  onDisplayChange: (value: boolean) => void;
}) {
  const document = {
    id: props.layer,
    paperId: props.id,
  };
  const annotation_layer = useResource(LayerResource.detailShape(), document);

  const updateAnnotation = useFetcher(LayerResource.partialUpdateShape());
  const deleteAnnotation = useFetcher(LayerResource.deleteShape());

  const model_api = useResource(ModelResource.detailShape(), {
    id: annotation_layer.kind,
  });

  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [display, setDisplay] = useState(false);

  const onLabelClicked = (value: string) => {
    setSelectedLabel(value);
    props.onLabelSelected(value);
  };

  //<Form schema={model_api.schema}/>
  return (
    <div style={{ backgroundColor: "#eee" }}>
      <div
        style={{
          display: "flex",
          backgroundColor: "#f8f8f8",
          flexDirection: "row",
        }}
      >
        <IconToggle
          style={{ padding: 10 }}
          onElem={<IoIosEye size="1.5em" />}
          offElem={<IoIosEyeOff size="1.5em" />}
          on={display}
          onChange={(value: boolean) => {
            props.onDisplayChange(value);
            setDisplay(value);
          }}
        />
        <Editable
          style={{ padding: 10, fontSize: "1.2em" }}
          text={annotation_layer.name}
          onEdit={(name: string) => updateAnnotation(document, { name })}
        />
        <div
          onClick={() => setCollapsed(!collapsed)}
          style={{ flex: 1, textAlign: "end" }}
        >
          <IoIosArrowDown
            style={{
              padding: 10,
              transform: collapsed ? "rotate(0deg)" : "rotate(180deg)",
              transition: "transform 500ms",
            }}
          />
        </div>
      </div>
      {!collapsed && (
        <div
          style={{
            textAlign: "start",
            borderTop: "solid #444 1px",
            padding: 10,
          }}
        >
          <div>Set label to:</div>
          <nav>
            {model_api.schema.properties.label.enum.map(
              (value: string, index: number) => {
                return (
                  <button
                    key={"label-" + value}
                    onClick={() => onLabelClicked(value)}
                    disabled={selectedLabel === value}
                  >
                    {model_api.schema.properties.label.enumNames[index]}
                  </button>
                );
              }
            )}
          </nav>
          <Checkbox
            label="Set as training:"
            checked={annotation_layer.training}
            onChange={(training) => updateAnnotation(document, { training })}
          />
          <button onClick={() => deleteAnnotation(document, undefined)}>
            delete
          </button>
        </div>
      )}
    </div>
  );
}
