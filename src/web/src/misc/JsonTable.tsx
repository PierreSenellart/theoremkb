import React from "react";
import "./JsonTable.css";

export function JsonTable(props: { json: any }) {
  const json = props.json;
  const type = typeof json;

  if (type == "string") {
    return json;
  } else if (type == "boolean") {
    return json ? "✔": "✘";
  } else if (type == "number") {
    return json.toFixed(2);
  } else if (type == "object") {
    return (
      <table style={{ border: "solid black 1px", width: "100%" }}>
        <tbody >
          {Object.entries(json).map((kv) => {
            const [key, value] = kv;
            
            return (
              <tr key={key} className="jsontable-alt">
                <td>{key}</td>
                <td className="jsontable-right"><JsonTable json={value} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }
}
