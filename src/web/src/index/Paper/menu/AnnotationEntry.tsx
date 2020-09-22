import React, { useEffect, useRef, useState } from "react";
import { useResource, useFetcher } from "rest-hooks";
import {
  AnnotationLayerResource,
  AnnotationTagResource,
} from "../../../resources";

import { IoIosEye, IoIosEyeOff, IoMdTrash } from "react-icons/io";
import { BsBoundingBoxCircles } from "react-icons/bs";
import { IconToggle } from "../../../misc/IconToggle";
import { ActionMeta } from "react-select";
import CreatableSelect from "react-select/creatable";
import _ from "lodash";

export function AnnotationEntry(props: {
  layer: string;
  id: string;

  selected: boolean;
  onSelect: (_: boolean) => void;
  display: boolean;
  onDisplayChange: (value: boolean) => void;
  new: boolean;
}) {
  const document = {
    id: props.layer,
    paperId: props.id,
  };
  const annotationLayer = useResource(
    AnnotationLayerResource.detailShape(),
    document
  );

  const annotationLayersTag = useResource(
    AnnotationTagResource.listShape(),
    {layerId: props.layer, paperId: props.id}
  )

  let groupList = useResource(AnnotationTagResource.listShape(), {});
  _.sortBy(groupList, (g) => g.name);

  const addTag = useFetcher(AnnotationTagResource.createShape());
  const addLayerTag = useFetcher(AnnotationTagResource.updateShape());
  const removeLayerTag = useFetcher(AnnotationTagResource.deleteShape());

  const updateAnnotation = useFetcher(
    AnnotationLayerResource.partialUpdateShape()
  );
  const deleteAnnotation = useFetcher(AnnotationLayerResource.deleteShape());

  const onDisplayChange = props.onDisplayChange;

  useEffect(() => {
    const v = localStorage.getItem(props.layer + "-display");
    if (v !== null) {
      onDisplayChange(v === "true");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // select tags

  const [selectEnabled, setSelectEnabled] = useState(false);
  const selectRef = useRef<CreatableSelect<AnnotationTagResource>>();

  useEffect(() => {
    if (selectEnabled) {
      selectRef.current.focus();
    }
  }, [selectEnabled, selectRef]);

  const selectStyles = {
    multiValueRemove: (base, state) => {
      if (state.data.readonly || !selectEnabled) {
        return { ...base, display: "none" };
      } else {
        return base;
      }
    },
  };

  const orderOptions = (values) => {
    return values
      .filter((v) => v.readonly)
      .concat(values.filter((v) => !v.readonly));
  };

  const [tagList, setTagList] = useState(
    groupList.filter((x) => annotationLayersTag.map((y) => y.id).includes(x.id))
  );

  const onSelectChange = (
    value: AnnotationTagResource[],
    { action, removedValue, option }: ActionMeta<AnnotationTagResource>
  ) => {
    console.log(action, option);
    switch (action) {
      case "remove-value":
      case "pop-value":
        if (removedValue) {
          if (removedValue.readonly) {
            return;
          }
          removeLayerTag({layerId: props.layer, paperId: props.id, id: removedValue.id}, undefined)
        }
        break;
      case "clear":
        value = groupList.filter(
          (x) => x.readonly && annotationLayersTag.map((y) => y.id).includes(x.id)
        );
        break;
      case "select-option":
        addLayerTag({layerId: props.layer, paperId: props.id, id: option.id}, undefined)
        break;
    }

    setTagList(value ?? []);
  };

  return (
    <div style={{ backgroundColor: "#eee", borderBottom: "solid gray 1px" }}>
      <div
        style={{
          display: "flex",
          backgroundColor: "#f8f8f8",
          flexDirection: "row",
          alignItems: "center",
          borderLeft: props.selected
            ? "solid red 10px"
            : "solid transparent 10px",
        }}
      >
        <div
          style={{
            minWidth: 100,
            display: "flex",
            flexDirection: "row",
            gap: 6,
            justifyContent: "space-around",
            padding: 8,
          }}
        >
          {annotationLayer.class != "misc" && (
            <div
              style={{
                cursor: "pointer",
                display: "inline-block",
                color: props.selected ? "red" : "black",
              }}
              onClick={() => {
                props.onSelect(!props.selected);
                if (!props.selected) {
                  props.onDisplayChange(true);
                }
              }}
              title="select layer for annotation"
            >
              <BsBoundingBoxCircles size="1.5em" />
            </div>
          )}
          <IconToggle
            tooltip="toggle display"
            onElem={<IoIosEye size="1.5em" />}
            offElem={<IoIosEyeOff size="1.5em" />}
            on={props.display}
            onChange={(v: boolean) => {
              localStorage.setItem(props.layer + "-display", v.toString());
              props.onDisplayChange(v);
            }}
          />
          {annotationLayer.created}
        </div>
        <div
          style={{ flex: 1, textAlign: "left" }}
          onClick={() => {
            setSelectEnabled(true);
          }}
        >
          <CreatableSelect
            options={orderOptions(groupList.filter((x) => !x.readonly))}
            value={orderOptions(tagList)}
            isMulti
            getOptionLabel={(v) => v.name}
            getOptionValue={(v) => v.id}
            styles={selectStyles}
            onChange={onSelectChange}
            onBlur={() => setSelectEnabled(false)}
            isDisabled={!selectEnabled}
            isClearable={false}
            ref={selectRef}
            onCreateOption={async (inputValue) => {
              const newTag = await addTag({}, { name: inputValue }, [
                [
                  AnnotationTagResource.listShape(),
                  {},
                  (newTagID: string, TagIDs: string[] | undefined) => [
                    ...(TagIDs || []),
                    newTagID,
                  ],
                ],
              ]);
              
              onSelectChange([...tagList, newTag], { action: "select-option", option: newTag });
            }}
            getNewOptionData={(inputValue, optionLabel) => ({
              id: "__new__",
              name: "Create '" + inputValue + "'",
              readonly: false,
            })}
          />
        </div>
        <div style={{ textAlign: "end" }}>
          <div
            style={{ cursor: "pointer", margin: 10, display: "inline-block" }}
            onClick={() => deleteAnnotation(document, undefined)}
            title="delete layer"
          >
            <IoMdTrash size="1.5em" />
          </div>
        </div>
      </div>
    </div>
  );
}
