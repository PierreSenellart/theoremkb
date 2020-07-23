import React, { useState, MouseEvent, CSSProperties } from "react";
import { useFetcher, useResource } from "rest-hooks";
import { AnnotationResource, LayerResource } from "../../resources";
import { AnnotationLayer, AnnotationBox, normalize } from "./AnnotationBox";
import { Rnd } from "react-rnd";
import { ContextMenu, MenuItem, ContextMenuTrigger } from "react-contextmenu";

function AnnotationDisplay(props: {
  layer: string;
  paper: string;
  id: string;
  annotation: AnnotationBox;
  scale: number;
  showHandles?: boolean;
}) {
  const scale = props.scale;
  const ann = props.annotation;

  const resourceID = {
    layerId: props.layer,
    paperId: props.paper,
    id: props.id,
  };

  const [showMenu, setShowMenu] = useState(false);

  const annotationLayer = useResource(LayerResource.detailShape(), {
    paperId: props.paper,
    id: props.layer
  });

  const updateAnnotation = useFetcher(AnnotationResource.updateShape());
  const deleteAnnotation = useFetcher(AnnotationResource.deleteShape());

  return (
    <Rnd
      size={{
        width: (ann.max_h - ann.min_h) * scale,
        height: (ann.max_v - ann.min_v) * scale,
      }}
      position={{
        x: ann.min_h * scale,
        y: ann.min_v * scale,
      }}
      onDragStart={() => false}
      onDragStop={(e, d) => {
        let newAnnotation = { ...ann };
        newAnnotation.min_h = d.x / scale;
        newAnnotation.max_h = d.x / scale + ann.max_h - ann.min_h;
        newAnnotation.min_v = d.y / scale;
        newAnnotation.max_v = d.y / scale + ann.max_v - ann.min_v;
        updateAnnotation(resourceID, newAnnotation);
      }}
      onResizeStop={(e, _, r, delta, position) => {
        let newAnnotation = { ...ann };
        newAnnotation.min_h = position.x / scale;
        newAnnotation.max_h =
          position.x / scale + delta.width / scale + ann.max_h - ann.min_h;
        newAnnotation.min_v = position.y / scale;
        newAnnotation.max_v =
          position.y / scale + delta.height / scale + ann.max_v - ann.min_v;
        updateAnnotation(resourceID, newAnnotation);
      }}
      style={{
        border: "solid black 1px",
        pointerEvents: props.showHandles ? "visible" : "none",
        padding: 15,
      }}
    >
      <div
        style={{
          fontVariant: "small-caps",
          position: "absolute",
          bottom: 0,
          left: 0,
          padding: "2px 8px",
          color: "white",
          backgroundColor: "#000a",
          cursor: "pointer",
          userSelect: "none",
        }}
        onClick={() => setShowMenu(!showMenu)}
      >
        {annotationLayer.kind + "/" + ann.label}
      </div>
      {showMenu && (
        <div
          style={{
            fontVariant: "small-caps",
            position: "absolute",
            bottom: -22,
            height: "20px",
            left: 0,
          }}
        >
          <button onClick={() => deleteAnnotation(resourceID, undefined)}>
            delete
          </button>
        </div>
      )}
    </Rnd>
  );
}

export function AnnotationOverlay(props: {
  id: string;
  page_number: number;
  children: React.ReactChild;
  enableAddBox?: [string, string];
  scale: number;
}) {
  const scale = props.scale;
  const [pendingBox, setPendingBox] = useState<AnnotationBox | null>(null);

  const addNewAnnotation = useFetcher(AnnotationResource.createShape());

  const annotationLayers = useResource(LayerResource.listShape(), {
    paperId: props.id,
  });
  const annotationLayersContent: AnnotationResource[][] = (useResource as any) (
    ...annotationLayers.map((layer) => [
      AnnotationResource.listShape(),
      {
        paperId: props.id,
        layerId: layer.id,
      },
    ])
  ); 

  const renderedBox = pendingBox ? normalize(pendingBox) : null;
  const pendingBoxLayer: AnnotationResource[] = renderedBox
    ? [
        {
          ...renderedBox,
          id: "tmp",
          paperId: props.id,
          layerId: (props.enableAddBox ?? [""])[0],
          pk: () => "",
          url: "",
        },
      ]
    : [];

  const annotations_by_page = annotationLayersContent
    .concat([pendingBoxLayer])
    .flat()
    .reduce<{ [key: number]: AnnotationResource[] }>((acc, v) => {
      acc[v.page_num] = [...(acc[v.page_num] || []), v];
      return acc;
    }, {});

  const onMouseDown = (e: MouseEvent<HTMLDivElement>, page: number) => {
    if (props.enableAddBox) {
      var rect = (e.target as HTMLDivElement).getBoundingClientRect();
      var x = e.clientX - rect.left; //x position within the element.
      var y = e.clientY - rect.top; //y position within the element.

      const newPendingBox: AnnotationBox = {
        page_num: page,
        label: props.enableAddBox[1],
        min_h: x / scale,
        min_v: y / scale,
        max_h: x / scale,
        max_v: y / scale,
      };
      setPendingBox(newPendingBox);
    }
  };

  const onMouseMove = (e: MouseEvent, page: number) => {
    var rect = (e.target as HTMLDivElement).getBoundingClientRect();
    var x = e.clientX - rect.left; //x position within the element.
    var y = e.clientY - rect.top; //y position within the element.

    if (pendingBox && page == pendingBox.page_num) {
      let newPendingBox: AnnotationBox = { ...pendingBox };
      newPendingBox.max_h = x / scale;
      newPendingBox.max_v = y / scale;
      setPendingBox(newPendingBox);
    }
  };

  const onMouseUp = (e: MouseEvent, page: number) => {
    if (props.enableAddBox && pendingBox) {
      const [layer] = props.enableAddBox;
      addNewAnnotation(
        { layerId: layer, paperId: props.id },
        normalize(pendingBox),
        [
          [
            AnnotationResource.listShape(),
            { layerId: layer, paperId: props.id },
            (
              newAnnotation: string,
              currentAnnotations: string[] | undefined
            ) => [...(currentAnnotations || []), newAnnotation],
          ],
        ]
      );
    }
    setPendingBox(null);
  };

  return (
    <div
      style={{
        position: "relative",
        cursor: props.enableAddBox ? "crosshair" : "",
      }}
    >
      <div
        id="kk"
        onMouseDown={(e) => onMouseDown(e, props.page_number)}
        onMouseMove={(e) => onMouseMove(e, props.page_number)}
        onMouseUp={(e) => onMouseUp(e, props.page_number)}
        onMouseLeave={() => setPendingBox(null)}
      >
        {props.children}
      </div>
      {(annotations_by_page[props.page_number] || []).map(
        (ann: AnnotationResource, idx: number) => (
          <AnnotationDisplay
            key={idx}
            layer={ann.layerId}
            paper={ann.paperId}
            id={ann.id}
            annotation={ann}
            scale={scale}
            showHandles={pendingBox ? false : true}
          />
        )
      )}
    </div>
  );
}
