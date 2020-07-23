import React, { useState, useMemo } from "react";
import { Document, Page } from "react-pdf";
import { PDFDocumentProxy } from "pdfjs-dist";
import { AnnotationLayer } from "./AnnotationBox";
import { AnnotationOverlay } from "./AnnotationOverlay";

export function PaperRenderer(props: {
  id: string;
  enableAddBoxLayer?: [string, string];
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
              enableAddBox={props.enableAddBoxLayer}
              id={props.id}
              scale={scale}
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
