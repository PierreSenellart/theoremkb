
export interface AnnotationBox {
  pageNum: number;
  minH: number;
  maxH: number;
  minV: number;
  maxV: number;
  label: string;
}

export function normalize(box: AnnotationBox) {
  return {
    pageNum: box.pageNum,
    label: box.label,
    minH: Math.min(box.minH, box.maxH),
    minV: Math.min(box.minV, box.maxV),
    maxH: Math.max(box.minH, box.maxH),
    maxV: Math.max(box.minV, box.maxV),
  };
}

export interface AnnotationLayer {
  annotations: AnnotationBox[];
}
