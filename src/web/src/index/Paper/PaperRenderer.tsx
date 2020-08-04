import React, { useState, useMemo } from "react";
import { Document, Page } from "react-pdf";
import { PDFDocumentProxy } from "pdfjs-dist";
import { AnnotationLayer } from "./AnnotationBox";
import { AnnotationOverlay } from "./AnnotationOverlay";
import { Tag } from "../Paper";

export function PaperRenderer(props: {
  id: string;
  addTag?: Tag;
  displayLayer: {[k: string]: boolean};
}) {
  const file = useMemo(
    () => "http://localhost:8000/papers/" + props.id + "/pdf",
    [props.id]
  );

  const [numPages, setNumPages] = useState<number | null>(null);
  const [pdfWidth, setPdfWidth] = useState(612);
  //const annotation_update = useFetcher(LayerResource.partialUpdateShape());
  const canvasWidth = 1100;
  const scale = canvasWidth / pdfWidth;

    console.log("reload..")
  return (
    <div
      style={{
        backgroundColor: "#eee",
        minHeight: "30px",
        overflow: "scroll",
        marginLeft: "auto",
        marginRight: "auto",
      }}
    >
      {
        <Document
          file={file}
          onLoadSuccess={async (pdf: PDFDocumentProxy) => {
            setNumPages(pdf.numPages);
            setPdfWidth((await pdf.getPage(1)).getViewport({ scale: 1 }).width);
          }}
        >
          {Array.from(new Array(numPages), (el, index) => (
            <AnnotationOverlay 
              key={index}
              page_number={index+1} 
              addTag={props.addTag}
              id={props.id}
              scale={scale}
              displayLayer={props.displayLayer}
            >
                <Page
                  pageNumber={index + 1}
                  width={canvasWidth}
                  renderTextLayer={false}
                />
            </AnnotationOverlay>
          ))}
        </Document>
      }
    </div>
  );
}
