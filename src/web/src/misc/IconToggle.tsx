import React, { CSSProperties } from "react";
export function IconToggle(props: {
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
