import React, { useState } from "react";
import { useResource } from "rest-hooks";
import { AnnotationTagResource } from "../../../resources";

export function ClickSelectCreate(props: {
  value: string;
  class: string;
  onCreate?: (_: string) => void;
  onSelect: (_: string) => void;
}) {
  const tags = useResource(AnnotationTagResource.listShape(), {});


  const [editing, setEditing] = useState(0);
  if (editing == 2) {
    return <input type="text" autoFocus onBlur={() => setEditing(0)} placeholder="tag name.." onKeyUp={(e) => {
      if (e.key == "Enter") {
        props.onCreate((e.target as HTMLInputElement).value);
        setEditing(0);
      }
    }} />;
  }
  else if (editing == 1) {
    return <select onBlur={() => setEditing(0)} autoFocus onChange={(e) => {
      if (e.target.value == "+") {
        setEditing(2);
      }
      else if (e.target.value != "") {
        props.onSelect(e.target.value);
        setEditing(0);
      }
    }}>
      <option value="">move to tag</option>
      {props.onCreate && <option value="+">+new tag</option>}
      {tags.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
    </select>;
  }
  else {
    return (
      <div onClick={() => setEditing(1)} className="link">
        {props.value}
      </div>
    );
  }
}
