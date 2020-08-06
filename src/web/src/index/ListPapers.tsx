import React, { useState } from 'react';
import { useHistory } from "react-router-dom";
import { useResource } from 'rest-hooks';
import { Table, AutoSizer, Column } from 'react-virtualized';
import { PaperResource, ModelResource } from "../resources";

import {IoIosClose, IoIosCheckmarkCircle} from "react-icons/io"

function CellRendererLayerStatus(props: {layer: {count: number, training: boolean}}) {

  if (props.layer.count === 0) {
    return <IoIosClose />
  } else if (props.layer.training) {
    return <IoIosCheckmarkCircle />
  } else {
    return <div>{props.layer.count}</div>
  }
}

export function ListPapers() {
  const papersList = useResource(PaperResource.listShape(), {});
  const keys = Array.from(papersList.keys());

  const models_list = useResource(ModelResource.listShape(), {});
  
  let annotations_statuses = models_list.map(
    (model) => <Column
      key={model.id + "_status"}
      dataKey={model.id + "_status"}
      width={150}
      label={model.id}
      cellRenderer={({ rowData }: { rowData: PaperResource; }) => <CellRendererLayerStatus layer={rowData.layerStatus[model.id]}/>} />
  );

  const [selected_paper, set_selected_paper] = useState<number | null>(null);
  const [show, setShow] = useState<"all"|"not"|"par"|"ful">("all");
  const history = useHistory();

  // all cases are handled.
  // eslint-disable-next-line
  const renderedKeys = keys.filter((key) => {
    let entry = papersList[key];
    let has_training = models_list.some((model) => entry.layerStatus[model.id].training);
    let all_training = models_list.every((model) => entry.layerStatus[model.id].training);
    if (show === "all") {
      return true;
    } else if(show === "not") {
      return !has_training
    } else if(show === "par") {
      return has_training && !all_training
    } else if(show === "ful") {
      return all_training
    }
  })

  return <div>
    <div style={{textAlign: "left", padding: 15}}>
      Show: 
      <select onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {setShow(e.target.value as any)}}>
        <option value="all">all</option>
        <option value="not">not annotated</option>
        <option value="par">partially annotated</option>
        <option value="ful">fully annotated</option>
      </select>
    </div>
    <AutoSizer>
      {({ width }) => (
        <Table
          height={700}
          width={width}
          headerHeight={50}
          rowHeight={50}
          rowCount={renderedKeys.length}
          rowGetter={({ index }) => papersList[renderedKeys[index]]}
          onRowDoubleClick={({ rowData }: { rowData: PaperResource; }) => history.push("/paper/" + rowData.id)}
          onRowClick={({ index }) => set_selected_paper(index)}
          rowStyle={({ index }) => {
            if (index === selected_paper) {
              return { "backgroundColor": "#28c", "color": "#fff" };
            }
            else {
              return {};
            }
          }}>

          <Column
            dataKey="id"
            label="ID"
            width={200} />
          <Column
            dataKey="title"
            label="Title"
            width={500} />
          {annotations_statuses}
        </Table>
      )}
    </AutoSizer>
  </div>;
}
