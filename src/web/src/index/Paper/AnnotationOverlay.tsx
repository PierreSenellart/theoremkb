import React, {
  useState,
  MouseEvent,
  Suspense,
  useRef,
  useEffect,
  CSSProperties,
} from "react";
import { useFetcher, useResource } from "rest-hooks";
import {
  AnnotationResource,
  LayerResource,
  ModelParent,
  ModelResource,
} from "../../resources";
import { AnnotationBox, normalize } from "./AnnotationBox";
import { Rnd } from "react-rnd";
import { Tag } from "../Paper";
import { read } from "fs";
import { IoIosRemove, IoIosTrash } from "react-icons/io";

function AnnotationDisplay(props: {
  layer: string;
  paper: string;
  label: string;
  id: string;
  page_number: number;
  annotation: AnnotationBox;
  scale: number;
  readonly?: boolean;
  onDrag?: (_: boolean) => void;
}) {
  const scale = props.scale;
  const ann = props.annotation;

  const resourceID = {
    layerId: props.layer,
    paperId: props.paper,
    id: props.id,
  };

  const layerInfo = useResource(LayerResource.detailShape(), {id: props.layer, paperId: props.paper});


  const updateAnnotation = useFetcher(AnnotationResource.updateShape());
  const deleteAnnotation = useFetcher(AnnotationResource.deleteShape());

  const [dragging, setDragging] = useState<{ x: number; y: number } | null>(
    null
  );

  const onDrag = props.onDrag;
  useEffect(() => {
    if (onDrag) {
      onDrag(dragging ? true : false);
    }
  }, [dragging, onDrag]);

  const propPosition = {
    x: ann.min_h * scale,
    y: ann.min_v * scale,
  };

  const [position, setPosition] = useState(propPosition);

  return (
    <Rnd
      ref={(node) => {
        if (node) {
          node.updateOffsetFromParent();
          node.forceUpdate();
        }
      }}
      size={{
        width: (ann.max_h - ann.min_h) * scale,
        height: (ann.max_v - ann.min_v) * scale,
      }}
      position={props.readonly && !dragging ? propPosition : position}
      disableDragging
      onDragStart={() => false}
      onResize={(e, d, e_, d_, position) => {
        setPosition(position);
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
        pointerEvents: "none",
        padding: 15,
      }}
      resizeHandleWrapperStyle={{
        pointerEvents: props.readonly && !dragging ? "none" : "auto",
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
          userSelect: "none",
          pointerEvents: props.readonly && !dragging ? "none" : "auto",
        }}
      >
        {!props.readonly && (
          <span
            onClick={() => deleteAnnotation(resourceID, undefined)}
            title="remove annotation"
            style={{
              cursor: "pointer",
            }}
          >
            <IoIosTrash size="1em" />
          </span>
        )}

        <span
          style={{
            cursor: "move",
          }}
          className={dragging ? "dragging" : ""}
          onMouseDown={(e) => {
            let page = document
              .getElementById("page_" + props.page_number)
              .getBoundingClientRect();
            setDragging({ x: e.pageX - page.x, y: e.pageY - page.y });
          }}
          onMouseMove={(e) => {
            if (dragging) {
              let page = document
                .getElementById("page_" + props.page_number)
                .getBoundingClientRect();

              setPosition((pos) => ({
                x: pos.x + e.pageX - page.x - dragging.x,
                y: pos.y + e.pageY - page.y - dragging.y,
              }));
              setDragging({ x: e.pageX - page.x, y: e.pageY - page.y });
            }
          }}
          onMouseUp={() => setDragging(null)}
          onMouseLeave={() => setDragging(null)}
        >
          {props.label}
        </span>
      </div>
    </Rnd>
  );
}

function AnnotationOverlayNewbox(props: {
  layerId: string;
  paperId: string;
  label: string;
  annotation: AnnotationBox;
  scale: number;
  page_number: number;
}) {
  const annotationLayer = useResource(LayerResource.detailShape(), {
    paperId: props.paperId,
    id: props.layerId,
  });

  return (
    <AnnotationDisplay
      layer={props.layerId}
      paper={props.paperId}
      label={
        annotationLayer.kind + "/" + annotationLayer.name + "/" + props.label
      }
      id={"__tmp__"}
      page_number={props.page_number}
      annotation={normalize(props.annotation)}
      scale={props.scale}
      readonly
    />
  );
}

function AnnotationOverlayLayer(props: {
  id: string;
  layerId: string;
  page_number: number;
  scale: number;
  readonly: boolean;
  onDrag: (_: boolean) => void;
}) {
  const layerContent = useResource(AnnotationResource.listShape(), {
    paperId: props.id,
    layerId: props.layerId,
  });

  const annotationLayer = useResource(LayerResource.detailShape(), {
    paperId: props.id,
    id: props.layerId,
  });

  const displayedLayerContent = layerContent.filter(
    (x) => x.page_num === props.page_number
  );

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
      }}
    >
      <div style={{ position: "relative" }}>
        {displayedLayerContent.map((ann: AnnotationResource) => (
          <AnnotationDisplay
            key={ann.id} 
            layer={ann.layerId}
            paper={ann.paperId}
            page_number={props.page_number}
            label={
              annotationLayer.kind +
              "/" +
              annotationLayer.name +
              "/" +
              ann.label
            }
            id={ann.id}
            annotation={ann}
            scale={props.scale}
            readonly={props.readonly}
            onDrag={props.onDrag}
          />
        ))}
      </div>
    </div>
  );
}

export function AnnotationOverlay(props: {
  id: string;
  page_number: number;
  children: React.ReactChild;
  addTag?: Tag;
  scale: number;
  width: number;
  displayLayer: { [k: string]: boolean };
}) {
  const scale = props.scale;
  const [pendingBox, setPendingBox] = useState<AnnotationBox | null>(null);

  const [dragging, setDragging] = useState(false);

  const addNewAnnotation = useFetcher(AnnotationResource.createShape());

  const annotationLayers = useResource(LayerResource.listShape(), {
    paperId: props.id,
  });

  const onMouseDown = (e: MouseEvent<HTMLDivElement>, page: number) => {
    if (props.addTag) {
      var rect = (e.target as HTMLDivElement).getBoundingClientRect();
      var x = e.clientX - rect.left; //x position within the element.
      var y = e.clientY - rect.top; //y position within the element.

      const newPendingBox: AnnotationBox = {
        page_num: page,
        label: props.addTag.label,
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

    if (pendingBox && page === pendingBox.page_num) {
      let newPendingBox: AnnotationBox = { ...pendingBox };
      newPendingBox.max_h = x / scale;
      newPendingBox.max_v = y / scale;

      setPendingBox(newPendingBox);
    }
  };

  const onMouseUp = (e: MouseEvent, page: number) => {
    if (props.addTag && pendingBox) {
      const layer = props.addTag.layer;
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
      id={"page_" + props.page_number}
      style={{
        position: "relative",
        width: props.width,
        margin: "auto",
        cursor: props.addTag ? "crosshair" : "",
        pointerEvents: "auto",
        borderBottom: "solid gray 1px",
      }}
    >
      <div
        onMouseDown={(e) => onMouseDown(e, props.page_number)}
        onMouseMove={(e) => onMouseMove(e, props.page_number)}
        onMouseUp={(e) => onMouseUp(e, props.page_number)}
        onMouseLeave={(e) => setPendingBox(null)}
      >
        {props.children}
      </div>
      <Suspense
        fallback={
          <div style={{ position: "absolute", top: "50%", left: "50%" }}>
            loading..
          </div>
        }
      >
        {pendingBox && props.addTag && (
          <AnnotationOverlayNewbox
            layerId={props.addTag.layer}
            paperId={props.id}
            label={props.addTag.label}
            page_number={props.page_number}
            annotation={normalize(pendingBox)}
            scale={props.scale}
          />
        )}
        {annotationLayers
          .filter((ann) => props.displayLayer[ann.id])
          .map((ann: LayerResource) => (
            <AnnotationOverlayLayer
              key={ann.id}
              id={props.id}
              layerId={ann.id}
              page_number={props.page_number}
              scale={props.scale}
              readonly={pendingBox ? true : dragging}
              onDrag={setDragging}
            />
          ))}
      </Suspense>
    </div>
  );
}
