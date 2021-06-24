import React, { useState, CSSProperties } from "react";
export function Editable(props: {
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
          }
          else if (e.keyCode === 27) {
            finishEdit();
          }
        }}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurText(e.target.value)}
        autoFocus />
    );
  }
  else {
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
