import React, {
  useState,
  useMemo,
  memo,
  CSSProperties,
  useCallback,
} from "react";
import { Document, Page } from "react-pdf";
import { PDFDocumentProxy } from "pdfjs-dist";
import { AnnotationOverlay } from "./AnnotationOverlay";
import { Tag } from "../Paper";
import { VariableSizeList as List, areEqual } from "react-window";
import { AutoSizer } from "react-virtualized";


const PaperPage = memo<{ index: number; style: CSSProperties; data: any }>(
  ({ index, style, data }) => {
    return (
      <div style={style} key={data.id + "-" + index}>
        <AnnotationOverlay
          pageNum={index + 1}
          addTag={data.addTag}
          id={data.id}
          scale={data.canvasWidth / data.pdfWidth[index]}
          width={data.canvasWidth}
          displayLayer={data.displayLayer}
        >
          <Page
            pageNumber={index + 1}
            width={data.canvasWidth}
            renderTextLayer={false}
          />
        </AnnotationOverlay>
      </div>
    );
  },
  areEqual
);

export function PaperRenderer(props: {
  id: string;
  addTag?: Tag;
  displayLayer: { [k: string]: boolean };
}) {
  const file = useMemo(() => "/api/papers/" + props.id + "/pdf", [props.id]);

  const [numPages, setNumPages] = useState<number>(0);
  const [pdfWidth, setPdfWidth] = useState({});
  const [pdfHeight, setPdfHeight] = useState({});

  const canvasWidth = 1100;

  const getPageHeight = useCallback(
    (index) => 1 + pdfHeight[index] * (canvasWidth / pdfWidth[index]),
    [canvasWidth, pdfHeight, pdfWidth]
  );

  const itemData = useMemo(
    () => ({
      id: props.id,
      addTag: props.addTag,
      displayLayer: props.displayLayer,
      canvasWidth,
      pdfWidth,
    }),
    [props.id, props.addTag, props.displayLayer, canvasWidth, pdfWidth]
  );


  return (
    <div
      style={{
        height: "100%",
        backgroundColor: "#eee",
      }}
    >
      <AutoSizer>
        {({ height, width }) => (
          <Document
            file={file}
            onLoadSuccess={async (pdf: PDFDocumentProxy) => {
              let width = {};
              let height = {};
              for (const page of Array(pdf.numPages).keys()) {
                const vp = (await pdf.getPage(page + 1)).getViewport({
                  scale: 1,
                });
                width[page] = vp.width;
                height[page] = vp.height;
              }
              setPdfWidth(width);
              setPdfHeight(height);
              setNumPages(pdf.numPages);
            }}
          >
            <List
              height={height}
              width={width}
              itemCount={numPages}
              itemData={itemData}
              itemSize={getPageHeight}
            >
              {PaperPage}
            </List>
          </Document>
        )}
      </AutoSizer>
    </div>
  );
}
