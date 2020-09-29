import React from "react";
import { useResource, useFetcher } from "rest-hooks";
import {
  AnnotationClassResource,
  AnnotationExtractorResource,
  AnnotationTagResource,
} from "../resources";

import _ from "lodash";
import { JsonTable } from "../misc/JsonTable";

function ExtractorList(props: { class: string }) {
  let extractors = useResource(AnnotationExtractorResource.listShape(), {
    classId: props.class,
  });

  return (
    <table>
      <thead>
        <tr>
          <th>name</th>
          <th>trained</th>
          <th>operations</th>
        </tr>
      </thead>
      <tbody>
        {extractors.map((ex) => (
          <tr>
            <td>{ex.id}</td>
            <td>{ex.trainable && (ex.trained ? "✓" : "✗")}</td>
            <td></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Tags() {
  const deleteTag = useFetcher(AnnotationTagResource.deleteShape());

  let tagList = useResource(AnnotationTagResource.listShape(), {
    addCounts: true,
  });

  tagList = _.sortBy(tagList, (v) => v.name);

  return (
    <div>
      <h2 style={{ borderTop: "solid black 1px", paddingTop: 10 }}>
        layer tags
      </h2>
      <table>
        <thead>
          <tr>
            <th>name</th>
            <th>RO</th>
            <th>description</th>
            <th>#segmentation</th>
            <th>#header</th>
            <th>#results</th>
            <th>#misc</th>
          </tr>
        </thead>
        <tbody>
          {tagList.map((t) => (
            <tr>
              <td>{t.name}</td>
              <td>{t.readonly ? "✓" : ""}</td>
              <td><JsonTable json={t.data} /></td>
              <td>{t.counts["segmentation"] ?? ""}</td>
              <td>{t.counts["header"] ?? ""}</td>
              <td>{t.counts["results"] ?? ""}</td>
              <td>{t.counts["misc"] ?? ""}</td>
              <td>
                {!t.readonly && _.sum(Object.values(t.counts)) == 0 && (
                  <button onClick={() => deleteTag({ id: t.id }, undefined)}>
                    DEL
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LayersOfClass(props: { class: string }) {
  let classInfo = useResource(AnnotationClassResource.detailShape(), {
    id: props.class,
  });

  return (
    <>
      <h2 style={{ borderTop: "solid black 1px", paddingTop: 10 }}>
        {classInfo.id}
      </h2>
      <ExtractorList class={props.class} />
    </>
  );
}

export function Layers() {
  return (
    <div
      style={{
        padding: 25,
        paddingTop: 0,
        display: "flex",
        flexDirection: "row",
        textAlign: "left",
        overflowY: "auto",
        gap: 32,
      }}
    >
      <div style={{ flex: 1 }}>
        <LayersOfClass class="segmentation" />
        <LayersOfClass class="header" />
        <LayersOfClass class="results" />
      </div>
      <div style={{ flex: 2 }}>
        <Tags />
      </div>
    </div>
  );
}
