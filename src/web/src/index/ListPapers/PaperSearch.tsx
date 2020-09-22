import React, { useEffect, useState } from "react";
import { useResource } from "rest-hooks";
import { Multiselect } from "multiselect-react-dropdown";
import { AnnotationTagResource } from "../../resources";

import _ from "lodash";

export function PaperSearch(props: {
  onQueryChange: (query: any) => void;
}): React.ReactElement {
  let groupList = useResource(AnnotationTagResource.listShape(), {});
  _.sortBy(groupList, (g) => g.name);

  const [titleSearch, setTitleSearch] = useState(null);
  const [filterTags, setFilterTags] = useState([]);

  let curQuery = { search: [...filterTags] };
  if (titleSearch) {
    curQuery.search.push(["Paper.title", titleSearch]);
  }

  useEffect(() => props.onQueryChange(curQuery), [JSON.stringify(curQuery)]);

  const onFilterChange = (selectedItems) => {
    setFilterTags(selectedItems.map(({ id }) => ["Paper.layers.tag", id]));
  };

  return (
    <>
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
      <div style={{ color: "black", maxWidth: 800, width: 500 }}>
        <Multiselect
          options={groupList}
          displayValue="name"
          placeholder="filter layers"
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
    </>
  );
}
