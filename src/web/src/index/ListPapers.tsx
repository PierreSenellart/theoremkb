import React, {
  useState,
  useMemo,
  useCallback,
  useEffect,
  useRef,
  CSSProperties,
} from "react";
import { useHistory, Link } from "react-router-dom";
import { useResource, useFetcher } from "rest-hooks";
import { useStatefulResource } from "@rest-hooks/legacy";
import { Table, AutoSizer, Column, InfiniteLoader } from "react-virtualized";
import { Multiselect } from "multiselect-react-dropdown";
import {
  PaperResource,
  AnnotationClassResource,
  AnnotationLayerGroupResource,
} from "../resources";

import { IoIosClose, IoIosCheckmarkCircle } from "react-icons/io";
import { Header } from "./Header";
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

export function ListPapers(): React.ReactElement {
  const CLASS_COLUMN_WIDTH = 150;

  let groupList = useResource(AnnotationLayerGroupResource.listShape(), {});
  _.sortBy(groupList, (g) => g.name);

  const classList = useResource(AnnotationClassResource.listShape(), {});
  const classStatus = classList
    .filter((c) => c.id != "misc")
    .map((model) => (
      <Column
        key={model.id + "_status"}
        dataKey={model.id + "_status"}
        width={CLASS_COLUMN_WIDTH}
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

  const [titleSearch, setTitleSearch] = useState(null);
  const [filterGroups, setFilterGroups] = useState([]);
  const [data, setData] = useState({});

  let curQuery = { search: [...filterGroups] };
  if (titleSearch) {
    curQuery.search.push(["Paper.title", titleSearch]);
  }

  const papersList = useStatefulResource(PaperResource.listShape(), {
    q: JSON.stringify({ ...curQuery, limit: 0 }),
  });

  const infiniteLoaderRef = useRef<InfiniteLoader>();

  useEffect(() => {
    console.log("reset cache.");
    setData({});
  }, [titleSearch, filterGroups, infiniteLoaderRef, setData]);

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
        ...curQuery,
        offset: startIndex,
        limit: 1 + stopIndex - startIndex,
      };
      let dataPreUpdate = {};

      for (let i = startIndex; i < stopIndex + 1; i++) {
        dataPreUpdate[i] = null;
      }
      setData((curData) => {
        return {...dataPreUpdate, ...curData}
      });

      console.log("starting fetch>"+startIndex+"/"+stopIndex);
      const result = await papersFetcher({ q: JSON.stringify(query) });
      let dataUpdate = {};
      for (const [index, paper] of result.papers.entries()) {
        dataUpdate[startIndex + index] = paper;
      }
      setData((curData) => {
        return {...curData,...dataUpdate}
      });
    },
    [curQuery, data, setData, papersFetcher]
  );

  const onFilterChange = (selectedItems) => {
    setFilterGroups(selectedItems.map(({ id }) => ["Paper.layers.group", id]));
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <Header>
        <div style={{ display: "flex", flexDirection: "row", alignItems: "baseline" }}>
          <Link to="/layers" style={{ paddingRight: 30 }}>&gt; layers and extractors</Link>
          <input
            type="text"
            placeholder="Search"
            style={{
              padding: 5,
              paddingTop: 8,
              minHeight: 22,
            }}
            onChange={(e) => {
              let request = e.target.value;
              if (request) {
                setTitleSearch(request);
              } else {
                setTitleSearch(null);
              }
            }}
          />
          <div style={{ color: "black", maxWidth: "800px" }}>
            <Multiselect
              options={groupList}
              displayValue="name"
              placeholder="filter layers"
              groupBy="class"
              style={{
                inputField: { color: "white" },
                chips: {
                  background: "#468",
                },
              }}
              onSelect={onFilterChange}
              onRemove={onFilterChange}
            />
          </div>
        </div>
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
              ref={infiniteLoaderRef}
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
                      let style: CSSProperties = {borderTop: "solid gray 1px"};
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
                    width={width - classStatus.length * CLASS_COLUMN_WIDTH}
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
