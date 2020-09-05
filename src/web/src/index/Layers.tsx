import React from "react";
import { useResource, useFetcher } from "rest-hooks";
import {
  AnnotationClassResource,
  AnnotationExtractorResource,
  AnnotationLayerGroupResource,
} from "../resources";
import { Editable } from "../misc/Editable";
import { IconToggle } from "../misc/IconToggle";
import { IoMdCheckbox, IoMdSquareOutline } from "react-icons/io";

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

function LayerGroupsList(props: { class: string }) {
  let layergroups = useResource(
    AnnotationLayerGroupResource.listShape(),
    {}
  ).filter((x) => x.class == props.class);

  const updateGroup = useFetcher(
    AnnotationLayerGroupResource.partialUpdateShape()
  );

  return (
    <table>
      <thead>
        <tr>
          <th>name</th>
          <th>extractor</th>
          <th>#</th>
          <th>operations</th>
        </tr>
      </thead>
      <tbody>
        {layergroups.map((g) => (
          <tr>
            <td>
              <Editable
                text={g.name}
                onEdit={(name: string) => updateGroup({ id: g.id }, { name })}
              />
            </td>
            <td>
              {g.extractor}{g.extractorInfo && " - " + g.extractorInfo }
            </td>
            <td>{g.layerCount+  (g.trainingLayerCount > 0 && (" ("+g.trainingLayerCount+")"))}</td>
            <td></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function LayersOfClass(props: { class: string }) {
  let classInfo = useResource(AnnotationClassResource.detailShape(), {
    id: props.class,
  });

  return (
    <>
      <h1>{classInfo.id}</h1>
      <h3>extractors</h3>
      <ExtractorList class={props.class} />
      <h3 style={{ borderTop: "solid black 1px", paddingTop: 10 }}>
        layer groups
      </h3>
      <LayerGroupsList class={props.class} />
      <h3></h3>
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
        overflowY: "auto"
      }}
    >
      <div style={{ flex: 1, marginRight: 32 }}>
        <LayersOfClass class="segmentation" />
      </div>
      <div style={{ flex: 1, marginRight: 32 }}>
        <LayersOfClass class="header" />
      </div>
      <div style={{ flex: 1 }}>
        <LayersOfClass class="results" />
      </div>
    </div>
  );
}
