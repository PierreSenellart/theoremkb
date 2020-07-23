import React, { useState } from "react";
import { useResource, useFetcher } from "rest-hooks";
import {
  LayerResource,
  AnnotationEnum,
  ModelResource
} from "../../resources";

export function AnnotationEntry(props: {
  layer: string;
  id: string;
  onLabelSelected: (value: string) => void;
}) {
  const document = {
    id: props.layer,
    paperId: props.id,
  };
  const annotation_layer = useResource(LayerResource.detailShape(), document);

  const annotation_update = useFetcher(LayerResource.partialUpdateShape());

  const model_api = useResource(ModelResource.detailShape(), {
    id: annotation_layer.kind,
  });

  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);

  const onLabelClicked = (value: string) => {
    setSelectedLabel(value);
    props.onLabelSelected(value);
  };


  //<Form schema={model_api.schema}/>
  return <div>
  <h4>Set label to:</h4>
  <nav>
    {model_api.schema.properties.label.enum.map(
      (value: string, index: number) => {
        return (
          <button
            key={"label-" + value}
            onClick={() => onLabelClicked(value)}
            disabled={selectedLabel === value}
          >
            {model_api.schema.properties.label.enumNames[index]}
          </button>
        );
      }
    )}
  </nav>
</div>
}
