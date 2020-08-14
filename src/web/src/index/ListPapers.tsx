import React, { useState } from 'react';
import { useHistory } from "react-router-dom";
import { useResource } from 'rest-hooks';
import { Table, AutoSizer, Column } from 'react-virtualized';
import { PaperResource, AnnotationClassResource } from "../resources";

import {IoIosClose, IoIosCheckmarkCircle} from "react-icons/io"

function CellRendererClassStatus(props: {class: {count: number, training: boolean}}) {

  if (props.class.count === 0) {
    return <IoIosClose />
  } else if (props.class.training) {
    return <IoIosCheckmarkCircle />
  } else {
    return <div>{props.class.count}</div>
  }
}

export function ListPapers(): React.ReactElement {
  const papersList = useResource(PaperResource.listShape(), {});
  const keys = Array.from(papersList.keys());

  const classList = useResource(AnnotationClassResource.listShape(), {});
   
  const classStatus = classList.map(
    (model) => <Column
      key={model.id + "_status"}
      dataKey={model.id + "_status"}
      width={150}
      label={model.id}
      cellRenderer={({ rowData }: { rowData: PaperResource; }) => <CellRendererClassStatus class={rowData.classStatus[model.id]}/>} />
  );

  const [selectedPaper, setSelectedPaper] = useState<number | null>(null);
  const [show, setShow] = useState<"all"|"not"|"par"|"ful">("all");
  const history = useHistory();

  // all cases are handled.
  // eslint-disable-next-line
  const renderedKeys = keys.filter((key) => {
    const entry = papersList[key];
    const hasTraining = classList.some((model) => entry.classStatus[model.id].training);
    const allTraining = classList.every((model) => entry.classStatus[model.id].training);
    if (show === "all") {
      return true;
    } else if(show === "not") {
      return !hasTraining
    } else if(show === "par") {
      return hasTraining && !allTraining
    } else if(show === "ful") {
      return allTraining
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
          onRowClick={({ index }) => setSelectedPaper(index)}
          rowStyle={({ index }) => {
            if (index === selectedPaper) {
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
          {classStatus}
        </Table>
      )}
    </AutoSizer>
  </div>;
}
