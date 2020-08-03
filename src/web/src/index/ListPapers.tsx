import React, { useState } from 'react';
import { useHistory } from "react-router-dom";
import { useResource } from 'rest-hooks';
import { Table, AutoSizer, Column } from 'react-virtualized';
import { PaperResource } from "../resources";

export function ListPapers() {
  const papersList = useResource(PaperResource.listShape(), {});
  const keys = Array.from(papersList.keys());

  let annotations_statuses = ["segmentation"].map(
    (model) => <Column
      key={model + "_status"}
      dataKey={model + "_status"}
      width={150}
      label={model}
      cellRenderer={({ rowData }: { rowData: PaperResource; }) => <div>{rowData.layerStatus[model].count}</div>} />
  );

  const [selected_paper, set_selected_paper] = useState<number | null>(null);
  const history = useHistory();

  return <div>
    <AutoSizer>
      {({ width }) => (
        <Table
          height={600}
          width={width}
          headerHeight={50}
          rowHeight={50}
          rowCount={keys.length}
          rowGetter={({ index }) => papersList[keys[index]]}
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
          {annotations_statuses}
        </Table>
      )}
    </AutoSizer>
  </div>;
}
