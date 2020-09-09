import React, {
  useState,
  MouseEvent,
  Suspense,
  useRef,
  useEffect,
  CSSProperties,
  useContext,
} from "react";
import { useFetcher, useResource } from "rest-hooks";
import {
  AnnotationResource,
  AnnotationLayerResource,
  AnnotationLayerGroupResource,
} from "../../resources";
import { AnnotationBox, normalize } from "./AnnotationBox";
import { Rnd } from "react-rnd";
import { Tag, InfoboxSetter } from "../Paper";
import { IoIosTrash } from "react-icons/io";

function AnnotationDisplay(props: {
  layer: string;
  paper: string;
  label: string;
  labelFull: string;
  id: string;
  pageNum: number;
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

  const layerInfo = useResource(AnnotationLayerResource.detailShape(), {
    id: props.layer,
    paperId: props.paper,
  });

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
    x: ann.minH * scale,
    y: ann.minV * scale,
  };

  const [position, setPosition] = useState(propPosition);
  const [showAll, setShowAll] = useState(false);

  return (
    <Rnd
      ref={(node) => {
        if (node) {
          node.updateOffsetFromParent();
          node.forceUpdate();
        }
      }}
      size={{
        width: (ann.maxH - ann.minH) * scale,
        height: (ann.maxV - ann.minV) * scale,
      }}
      position={props.readonly && !dragging ? propPosition : position}
      disableDragging
      onDragStart={() => false}
      onResize={(e, d, e_, d_, position) => {
        setPosition(position);
      }}
      onResizeStop={(e, _, r, delta, position) => {
        let newAnnotation = { ...ann };
        newAnnotation.minH = position.x / scale;
        newAnnotation.maxH =
          position.x / scale + delta.width / scale + ann.maxH - ann.minH;
        newAnnotation.minV = position.y / scale;
        newAnnotation.maxV =
          position.y / scale + delta.height / scale + ann.maxV - ann.minV;
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
          right: 0,
          padding: "2px 8px",
          color: "white",
          backgroundColor: "#000a",
          userSelect: "none",
          width: "max-content",
          pointerEvents: props.readonly && !dragging ? "none" : "auto",
        }}
        onMouseLeave={() => setShowAll(false)}
        onMouseEnter={() => setShowAll(true)}
      >
        <span
          style={{
            cursor: "move",
          }}
          className={dragging ? "dragging" : ""}
          onMouseDown={(e) => {
            let page = document
              .getElementById("page_" + props.pageNum)
              .getBoundingClientRect();
            setDragging({ x: e.pageX - page.x, y: e.pageY - page.y });
          }}
          onMouseMove={(e) => {
            if (dragging) {
              let page = document
                .getElementById("page_" + props.pageNum)
                .getBoundingClientRect();

              setPosition((pos) => ({
                x: pos.x + e.pageX - page.x - dragging.x,
                y: pos.y + e.pageY - page.y - dragging.y,
              }));
              setDragging({ x: e.pageX - page.x, y: e.pageY - page.y });
            }
          }}
          onMouseUp={() => {
            setDragging(null);

            let newAnnotation = { ...ann };
            newAnnotation.minH = position.x / scale;
            newAnnotation.maxH = position.x / scale + ann.maxH - ann.minH;
            newAnnotation.minV = position.y / scale;
            newAnnotation.maxV = position.y / scale + ann.maxV - ann.minV;
            updateAnnotation(resourceID, newAnnotation);
          }}
          onMouseLeave={() => {
            setDragging(null);
          }}
        >
          {showAll ? props.labelFull : props.label}
        </span>
        {!props.readonly && showAll && (
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
      </div>
    </Rnd>
  );
}

function AnnotationDisplayTooltip(props: {
  annotation: AnnotationBox;
  scale: number;
}) {
  const ann = props.annotation;
  const scale = props.scale;

  const pos = {
    left: ann.minH * scale,
    top: ann.minV * scale,
  };
  const divPosition: CSSProperties = {
    position: "absolute",
    width: (ann.maxH - ann.minH) * scale,
    height: (ann.maxV - ann.minV) * scale,
    ...pos,
  };

  const { setInfobox } = useContext(InfoboxSetter);
  const [clicked, setClicked] = useState(false);

  return (
    <div
      onMouseEnter={() => setInfobox(ann.userData)}
      onClick={() => setClicked(!clicked)}
      onMouseLeave={() => !clicked && setInfobox(null)}
      style={{ ...divPosition, cursor: "pointer" }}
      className={clicked ? "border" : "hover-border"}
    ></div>
  );
}

function AnnotationOverlayNewbox(props: {
  layerId: string;
  paperId: string;
  label: string;
  annotation: AnnotationBox;
  scale: number;
  pageNum: number;
}) {
  const annotationLayer = useResource(AnnotationLayerResource.detailShape(), {
    paperId: props.paperId,
    id: props.layerId,
  });
  const annotationLayerGroup = useResource(
    AnnotationLayerGroupResource.detailShape(),
    {
      id: annotationLayer.groupId,
    }
  );

  return (
    <AnnotationDisplay
      layer={props.layerId}
      paper={props.paperId}
      label={props.label}
      labelFull={props.label}
      id={"__tmp__"}
      pageNum={props.pageNum}
      annotation={normalize(props.annotation)}
      scale={props.scale}
      readonly
    />
  );
}

function AnnotationOverlayLayer(props: {
  id: string;
  layerId: string;
  pageNum: number;
  scale: number;
  readonly: boolean;
  onDrag: (_: boolean) => void;
}) {
  const layerContent = useResource(AnnotationResource.listShape(), {
    paperId: props.id,
    layerId: props.layerId,
  });

  const annotationLayer = useResource(AnnotationLayerResource.detailShape(), {
    paperId: props.id,
    id: props.layerId,
  });

  const displayedLayerContent = layerContent.filter(
    (x) => x.pageNum === props.pageNum
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
        {displayedLayerContent.map((ann: AnnotationResource) =>
          ann.userData ? (
            <AnnotationDisplayTooltip
              key={ann.id}
              annotation={ann}
              scale={props.scale}
            />
          ) : (
            <AnnotationDisplay
              key={ann.id}
              layer={ann.layerId}
              paper={ann.paperId}
              pageNum={props.pageNum}
              labelFull={
                annotationLayer.class +
                "/" +
                annotationLayer.name +
                "/" +
                ann.label
              }
              label={ann.label}
              id={ann.id}
              annotation={ann}
              scale={props.scale}
              readonly={props.readonly}
              onDrag={props.onDrag}
            />
          )
        )}
      </div>
    </div>
  );
}

export function AnnotationOverlay(props: {
  id: string;
  pageNum: number;
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

  const annotationLayers = useResource(AnnotationLayerResource.listShape(), {
    paperId: props.id,
  });

  const onMouseDown = (e: MouseEvent<HTMLDivElement>, page: number) => {
    if (props.addTag) {
      var rect = (e.target as HTMLDivElement).getBoundingClientRect();
      var x = e.clientX - rect.left; //x position within the element.
      var y = e.clientY - rect.top; //y position within the element.

      const newPendingBox: AnnotationBox = {
        id: "__new__",
        pageNum: page,
        label: props.addTag.label,
        minH: x / scale,
        minV: y / scale,
        maxH: x / scale,
        maxV: y / scale,
      };

      setPendingBox(newPendingBox);
    }
  };

  const onMouseMove = (e: MouseEvent, page: number) => {
    var rect = (e.target as HTMLDivElement).getBoundingClientRect();
    var x = e.clientX - rect.left; //x position within the element.
    var y = e.clientY - rect.top; //y position within the element.

    if (pendingBox && page === pendingBox.pageNum) {
      let newPendingBox: AnnotationBox = { ...pendingBox };
      newPendingBox.maxH = x / scale;
      newPendingBox.maxV = y / scale;

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
      id={"page_" + props.pageNum}
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
        onMouseDown={(e) => onMouseDown(e, props.pageNum)}
        onMouseMove={(e) => onMouseMove(e, props.pageNum)}
        onMouseUp={(e) => onMouseUp(e, props.pageNum)}
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
            pageNum={props.pageNum}
            annotation={normalize(pendingBox)}
            scale={props.scale}
          />
        )}
        {annotationLayers
          .filter((ann) => props.displayLayer[ann.id])
          .map((ann: AnnotationLayerResource) => (
            <AnnotationOverlayLayer
              key={ann.id}
              id={props.id}
              layerId={ann.id}
              pageNum={props.pageNum}
              scale={props.scale}
              readonly={pendingBox ? true : dragging}
              onDrag={setDragging}
            />
          ))}
      </Suspense>
    </div>
  );
}
