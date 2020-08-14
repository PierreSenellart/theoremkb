import React, { useState, useMemo, memo, CSSProperties } from "react";
import { Document, Page } from "react-pdf";
import { PDFDocumentProxy } from "pdfjs-dist";
import { AnnotationOverlay } from "./AnnotationOverlay";
import { Tag } from "../Paper";
import { VariableSizeList as List, areEqual } from "react-window";
import { AutoSizer } from "react-virtualized";

export function PaperRenderer(props: {
  id: string;
  addTag?: Tag;
  displayLayer: { [k: string]: boolean };
}) {
  const file = useMemo(
    () => "http://localhost:8000/papers/" + props.id + "/pdf",
    [props.id]
  );

  const [numPages, setNumPages] = useState<number>(0);
  const [pdfWidth, setPdfWidth] = useState({});
  const [pdfHeight, setPdfHeight] = useState({});


  const canvasWidth = 1100;

  const getPageHeight = (index) =>
    1 + pdfHeight[index] * (canvasWidth / pdfWidth[index]);

  const PaperPage = memo<{ index: number; style: CSSProperties }>(
    ({ index, style }) => {
      return (
        <div style={style}>
          <AnnotationOverlay
            key={index}
            page_number={index + 1}
            addTag={props.addTag}
            id={props.id}
            scale={canvasWidth / pdfWidth[index]}
            width={canvasWidth}
            displayLayer={props.displayLayer}
          >
            <Page
              pageNumber={index + 1}
              width={canvasWidth}
              renderTextLayer={false}
            />
          </AnnotationOverlay>
        </div>
      );
    },
    areEqual
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
