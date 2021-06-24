import React, { Suspense, useState } from "react";
import { useResource, useFetcher } from "rest-hooks";
import {
  AnnotationLayerResource,
  AnnotationExtractorResource,
  AnnotationClassResource,
} from "../../../resources";
import { AnnotationEntry } from "./AnnotationEntry";
import { useAlert } from "react-alert";
import useHotkeys from "react-use-hotkeys";

import * as _ from "lodash";
import ColorHash from "color-hash";

function ClassHeaderSelectTag(props: {
  classId: string;
  onSelectTag: (_: string) => void;
  selectedTag?: string;
}) {
  const classInfo = useResource(AnnotationClassResource.detailShape(), {
    id: props.classId,
  });

  const shortcuts = classInfo.labels.reduce<{ [c: string]: string }>(
    (sc, label) => {
      for (let c of label) {
        if (!(c in sc)) {
          return { ...sc, [c]: label };
        }
      }
      console.log("Warning: unable to deduce shortcut for ", label);
      return sc;
    },
    {}
  );

  for (let c in shortcuts) {
    // hooks in loop allowed because classInfo.labels is const.
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useHotkeys(c.toUpperCase(), () => props.onSelectTag(shortcuts[c]), []);
  }

  const colorHash = new ColorHash({
    lightness: 0.5,
    saturation: 0.3,
  });

  const highlightShortcut = (value: string) => {
    let result = [];
    let shortcut = _.findKey(shortcuts, (v) => v == value);

    for (let c of value) {
      if (c == shortcut) {
        shortcut = null;

        result.push(<b key={c} style={{color: colorHash.hex(value)}}>[{c}]</b>);
      } else {
        result.push(c);
      }
    }

    return result;
  };

  return (
    <div
      style={{
        textAlign: "start",
        padding: 10,
      }}
    >
      <nav>
        {classInfo.labels.map((value: string, index: number) => {
          return (
            <button
              key={"label-" + value}
              onClick={() => props.onSelectTag(value)}
              disabled={props.selectedTag === value}
            >
              {highlightShortcut(value)}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

function Multisel(props: {
  paperId: string;
  reqs: string[];
  onChoose: (_: string[]) => void;
  onCancel: () => void;
}) {
  const resourceId = { paperId: props.paperId };
  const layers = useResource(AnnotationLayerResource.listShape(), resourceId);

  const layersByReq = props.reqs.map((rq) => {
    if (rq == "any") {
      return layers.filter((ly) => ly.class != "misc");
    } else {
      return layers.filter((ly) => ly.class == rq);
    }
  });

  const [chosenLayers, setChosenLayers] = useState(props.reqs.map(() => null));

  console.log(props.reqs);
  console.log(layersByReq);

  return (
    <div>
      {layersByReq.map((lyrs, i) => (
        <select
          key={"req_" + i}
          id={"req_" + i}
          onChange={(e) => {
            let newChosenLayer = [...chosenLayers];
            if (e.target.value == "") {
              newChosenLayer[i] = null;
            } else {
              newChosenLayer[i] = e.target.value;
            }
            setChosenLayers(newChosenLayer);
          }}
        >
          <option value="">model #{i}</option>
          {lyrs.map((lyr) => (
            <option key={lyr.id} value={lyr.id}>
              {lyr.class + " - " + lyr.created}
            </option>
          ))}
        </select>
      ))}
      <button
        onClick={() => {
          if (chosenLayers.every((x) => x != null)) {
            props.onChoose(chosenLayers);
          }
        }}
      >
        OK
      </button>
      <button onClick={props.onCancel}>Cancel</button>
    </div>
  );
}

function ClassHeaderCreateLayer(props: {
  paperId: string;
  classId: string;
  onNewLayer: (_: string) => void;
}) {
  const resourceId = { paperId: props.paperId };
  const alert = useAlert();

  const extractorList = useResource(AnnotationExtractorResource.listShape(), {
    classId: props.classId,
  }).filter((ex) => !ex.trainable || ex.trained);

  const createAnnotationLayerREST = useFetcher(
    AnnotationLayerResource.createShape()
  );

  const createAnnotationLayer = async (extractor?: string, reqs?: string[]) => {
    createAnnotationLayerREST(
      resourceId,
      {
        class: props.classId,
        extractor,
        reqs,
      } as any,
      [
        [
          AnnotationLayerResource.listShape(),
          resourceId,
          (newAnnotation: string, currentAnnotations: string[] | undefined) => {
            // announce newly created layer.
            props.onNewLayer(newAnnotation);

            return [...(currentAnnotations || []), newAnnotation];
          },
        ],
      ]
    );
  };

  const [newAnnLayer, setNewAnnLayer] = useState<string>(null);

  return (
    <>
      {props.classId != "misc" && (
        <button onClick={() => createAnnotationLayer()}>+layer</button>
      )}
      {extractorList.filter((extr) => !extr.trainable || extr.trained).length >
        0 &&
        (newAnnLayer ? (
          <Multisel
            paperId={props.paperId}
            reqs={
              extractorList.find((x) => x.id == newAnnLayer).classParameters
            }
            onChoose={async (v) => {
              await createAnnotationLayer(newAnnLayer, v).catch(async (e) => {
                // errors are untyped we assume it's a network error.
                let error = await e.response.json();
                alert.error(error.message);
              });
              setNewAnnLayer(null);
            }}
            onCancel={() => setNewAnnLayer(null)}
          />
        ) : (
          <select
            onChange={async (e: React.ChangeEvent<HTMLSelectElement>) => {
              let target = e.target;
              if (target.value !== "") {
                const extr = extractorList.find(
                  (extr) => extr.id == target.value
                );
                if (extr.classParameters.length == 0) {
                  // submit directly
                  target.disabled = true;
                  await createAnnotationLayer(target.value).catch(async (e) => {
                    // errors are untyped we assume it's a network error.
                    let error = await e.response.json();
                    alert.error(error.message);
                  });
                  target.disabled = false;
                  target.value = "";
                } else {
                  // switch to choose class mode.
                  setNewAnnLayer(target.value);
                }
              }
            }}
          >
            <option value="">+from model</option>
            {extractorList.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.id}
              </option>
            ))}
          </select>
        ))}
    </>
  );
}

function MenuModelHeader(props: {
  classId: string;
  paperId: string;
  color: boolean;
  selectedLayer: boolean;
  onSelectTag: (_: string) => void;
  selectedTag?: string;
  onNewLayer: (_: string) => void;
}) {
  return (
    <>
      <h2
        style={{
          fontVariant: "small-caps",
          backgroundColor: props.color ? "#fdd" : "white",
          padding: 10,
          display: "flex",
          flexDirection: "row",
          marginBottom: 4,
        }}
      >
        <ClassHeaderCreateLayer {...props} />
        <div style={{ flex: 1 }}>{props.classId}</div>
      </h2>
    </>
  );
}

export function AnnotationClass(props: {
  paperId: string;
  classId: string;
  annotations: AnnotationLayerResource[];
  display: { [k: string]: boolean };
  onDisplayChange: (id: string, value: boolean) => void;
  selectedLayer?: string;
  onSelectLayer: (_?: string) => void;
  selectedTag?: string;
  onSelectTag: (_: string) => void;
  color: boolean;
}) {
  const selectedLayer = props.annotations
    .map((x) => x.id)
    .includes(props.selectedLayer);

  const [newLayer, setNewLayer] = useState<null | string>(null);

  const onNewLayer = (id: string) => {
    props.onDisplayChange(id, true);
    setNewLayer(id);
  };

  return (
    <div
      key={"annot_" + props.classId}
      style={{
        margin: "10px 0 10px 0",
        borderBottom: "solid gray 1px",
        backgroundColor: "#eaeaea",
      }}
    >
      <MenuModelHeader
        {...props}
        selectedLayer={selectedLayer}
        onNewLayer={onNewLayer}
      />
      <Suspense fallback={<div>Loading..</div>}>
        {props.annotations.map((layer) => (
          <AnnotationEntry
            key={layer.id}
            layer={layer.id}
            id={props.paperId}
            selected={props.selectedLayer === layer.id}
            new={newLayer === layer.id}
            onSelect={(v: boolean) => {
              if (v) {
                props.onSelectLayer(layer.id);
              } else {
                props.onSelectLayer(undefined);
              }
            }}
            display={props.display[layer.id]}
            onDisplayChange={(value: boolean) => {
              props.onDisplayChange(layer.id, value);
            }}
          />
        ))}
      </Suspense>
      {selectedLayer && <ClassHeaderSelectTag {...props} />}
    </div>
  );
}
