
export interface AnnotationBox {
  id: string;
  pageNum: number;
  minH: number;
  maxH: number;
  minV: number;
  maxV: number;
  label: string;
  userData?: any;
}

export function normalize(box: AnnotationBox) {
  return {
    ...box,
    minH: Math.min(box.minH, box.maxH),
    minV: Math.min(box.minV, box.maxV),
    maxH: Math.max(box.minH, box.maxH),
    maxV: Math.max(box.minV, box.maxV),
  };
}

export interface AnnotationLayer {
  annotations: AnnotationBox[];
}
