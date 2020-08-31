import React, { useState, useMemo, useCallback, useEffect } from "react";
import { useHistory } from "react-router-dom";
import { useResource, useFetcher } from "rest-hooks";
import { useStatefulResource } from "@rest-hooks/legacy";
import {
  Table,
  AutoSizer,
  Column,
  defaultTableRowRenderer,
  TableRowProps,
  InfiniteLoader,
} from "react-virtualized";

import { PaperResource, AnnotationClassResource } from "../resources";

import { IoIosClose, IoIosCheckmarkCircle } from "react-icons/io";
import { Header } from "./Header";

function CellRendererClassStatus(props: {
  class: { count: number; training: boolean };
}) {
  if (props.class.count === 0) {
    return <IoIosClose />;
  } else if (props.class.training) {
    return <IoIosCheckmarkCircle />;
  } else {
    return <div>{props.class.count}</div>;
  }
}

export function ListPapers(): React.ReactElement {
  const classList = useResource(AnnotationClassResource.listShape(), {});
  const classStatus = classList.map((model) => (
    <Column
      key={model.id + "_status"}
      dataKey={model.id + "_status"}
      width={150}
      label={model.id}
      cellRenderer={({ rowData }: { rowData: PaperResource }) => {
        if (rowData.classStatus) {
          return (
            <CellRendererClassStatus class={rowData.classStatus[model.id]} />
          );
        } else {
          return <div>..</div>;
        }
      }}
    />
  ));

  const [selectedPaper, setSelectedPaper] = useState<number | null>(null);
  const history = useHistory();

  // paper data management.
  const papersFetcher = useFetcher(PaperResource.listShape(), true);

  const [curQuery, setCurQuery] = useState({});
  const [data, setData] = useState({});

  const papersList = useStatefulResource(PaperResource.listShape(), {
    q: JSON.stringify({ ...curQuery, limit: 0 }),
  });
  console.log("ppl", papersList);

  const isRowLoaded = useCallback(
    ({ index }) => {
      return index in data;
    },
    [data]
  );

  const [lastloadedrows, setLastloadedrows] = useState({});

  const loadMoreRows = useCallback(
    async ({ startIndex, stopIndex }) => {
      setLastloadedrows({ startIndex, stopIndex });
      const query = {
        ...curQuery,
        offset: startIndex,
        limit: 1 + stopIndex - startIndex,
      };
      const result = await papersFetcher({ q: JSON.stringify(query) });
      let dataUpdate = { ...data };
      for (const [index, paper] of result.papers.entries()) {
        dataUpdate[startIndex + index] = paper;
      }
      setData(dataUpdate);
    },
    [curQuery, data, setData, papersFetcher]
  );

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <Header>
        <>
          <input
            type="text"
            placeholder="Search"
            onChange={(e) => {
              let request = e.target.value;
              if (request) {
                setCurQuery({ search: [["Paper.title", request]] });
              } else {
                setCurQuery({});
              }
              loadMoreRows(lastloadedrows);
            }}
          />
        </>
      </Header>
      <div style={{ flex: 1 }}>
        <AutoSizer>
          {({ width, height }) => (
            <InfiniteLoader
              isRowLoaded={isRowLoaded}
              loadMoreRows={loadMoreRows}
              rowCount={papersList.data?.count ?? 0}
              threshold={100}
              minimumBatchSize={25}
            >
              {({ onRowsRendered, registerChild }) => (
                <Table
                  height={height}
                  width={width}
                  headerHeight={50}
                  rowHeight={50}
                  rowCount={papersList.data?.count ?? 0}
                  rowGetter={({ index }) => data[index] ?? { id: "loading.." }}
                  ref={registerChild}
                  onRowsRendered={onRowsRendered}
                  onRowDoubleClick={({ rowData }: { rowData: PaperResource }) =>
                    history.push("/paper/" + rowData.id)
                  }
                  onRowClick={({ index }) => setSelectedPaper(index)}
                  rowStyle={({ index }) => {
                    if (index === selectedPaper) {
                      return { backgroundColor: "#28c", color: "#fff" };
                    } else {
                      return {};
                    }
                  }}
                >
                  <Column dataKey="id" label="ID" width={200} />
                  <Column
                    style={{ textAlign: "left" }}
                    dataKey="title"
                    label="Title"
                    width={700}
                  />
                  {classStatus}
                </Table>
              )}
            </InfiniteLoader>
          )}
        </AutoSizer>
      </div>
    </div>
  );
}
