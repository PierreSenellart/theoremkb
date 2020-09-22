import React, {
  useState,
  useCallback,
  useEffect,
  useRef,
  CSSProperties,
} from "react";
import { useHistory } from "react-router-dom";
import { useResource, useFetcher } from "rest-hooks";
import { useStatefulResource } from "@rest-hooks/legacy";
import { Table, Column, InfiniteLoader } from "react-virtualized";
import {
  PaperResource,
  AnnotationClassResource,
  AnnotationTagResource,
} from "../../resources";

import { IoIosClose, IoIosCheckmarkCircle } from "react-icons/io";
import _ from "lodash";

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

const CLASS_COLUMN_WIDTH = 150;

function ClassStatusColumn(props: { model: AnnotationClassResource }) {
  return (
    <Column
      key={props.model.id + "_status"}
      dataKey={props.model.id + "_status"}
      width={CLASS_COLUMN_WIDTH}
      label={props.model.id}
      cellRenderer={({ rowData }: { rowData: PaperResource }) => {
        if (rowData.classStatus) {
          return (
            <CellRendererClassStatus
              class={rowData.classStatus[props.model.id]}
            />
          );
        } else {
          return <div>..</div>;
        }
      }}
    />
  );
}

export function PaperListView(props: {
  width: number;
  height: number;
  query: any;
}): React.ReactElement {
  let groupList = useResource(AnnotationTagResource.listShape(), {});
  _.sortBy(groupList, (g) => g.name);

  const classList = useResource(AnnotationClassResource.listShape(), {});
  const classStatus = classList
    .filter((c) => c.id != "misc")
    .map((model) => <ClassStatusColumn model={model} />);

  const [selectedPaper, setSelectedPaper] = useState<number | null>(null);
  const history = useHistory();

  // paper data management.
  const papersFetcher = useFetcher(PaperResource.listShape(), true);

  const papersList = useStatefulResource(PaperResource.listShape(), {
    q: JSON.stringify({ ...props.query, limit: 0 }), // get count.
  });

  const infiniteLoaderRef = useRef<InfiniteLoader>();

  const [data, setData] = useState({});

  useEffect(() => {
    console.log("reset cache.");
    setData({});
  }, [props.query, infiniteLoaderRef]);

  useEffect(() => {
    if (Object.keys(data).length == 0) {
      console.log("load more rows");
      if (infiniteLoaderRef.current) {
        infiniteLoaderRef.current.resetLoadMoreRowsCache(true);
      }
    }
  }, [data]);

  const isRowLoaded = useCallback(
    ({ index }) => {
      return index in data;
    },
    [data]
  );

  const loadMoreRows = useCallback(
    async ({ startIndex, stopIndex }) => {
      while (startIndex in data && startIndex < stopIndex) {
        startIndex += 1;
      }
      while (stopIndex in data && stopIndex > startIndex) {
        stopIndex += 1;
      }
      const query = {
        ...props.query,
        offset: startIndex,
        limit: 1 + stopIndex - startIndex,
      };
      let dataPreUpdate = {};

      for (let i = startIndex; i < stopIndex + 1; i++) {
        dataPreUpdate[i] = null;
      }
      setData((curData) => {
        return { ...dataPreUpdate, ...curData };
      });

      console.log("starting fetch>" + startIndex + "/" + stopIndex);
      const result = await papersFetcher({ q: JSON.stringify(query) });
      let dataUpdate = {};
      for (const [index, paper] of result.papers.entries()) {
        dataUpdate[startIndex + index] = paper;
      }
      setData((curData) => {
        return { ...curData, ...dataUpdate };
      });
    },
    [props.query, data, setData, papersFetcher]
  );

  return (
    <InfiniteLoader
      isRowLoaded={isRowLoaded}
      loadMoreRows={loadMoreRows}
      rowCount={papersList.data?.count ?? 0}
      threshold={100}
      minimumBatchSize={25}
      ref={infiniteLoaderRef}
    >
      {({ onRowsRendered, registerChild }) => (
        <Table
          height={props.height}
          width={props.width}
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
              let style: CSSProperties = { borderTop: "solid gray 1px" };
              if (index % 2 == 0) {
                style.backgroundColor = "#f0f0f8";
              }
              return style;
            }
          }}
        >
          <Column dataKey="id" label="ID" width={CLASS_COLUMN_WIDTH} />
          <Column
            style={{ textAlign: "left" }}
            dataKey="title"
            label="Title"
            width={props.width - classStatus.length * CLASS_COLUMN_WIDTH}
          />
          {classStatus}
        </Table>
      )}
    </InfiniteLoader>
  );
}
