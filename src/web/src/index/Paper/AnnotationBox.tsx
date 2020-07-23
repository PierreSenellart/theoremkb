
export interface AnnotationBox {
  page_num: number;
  min_h: number;
  max_h: number;
  min_v: number;
  max_v: number;
  label: string;
}

export function normalize(box: AnnotationBox) {
  return {
    page_num: box.page_num,
    label: box.label,
    min_h: Math.min(box.min_h, box.max_h),
    min_v: Math.min(box.min_v, box.max_v),
    max_h: Math.max(box.min_h, box.max_h),
    max_v: Math.max(box.min_v, box.max_v),
  };
}

export interface AnnotationLayer {
  annotations: AnnotationBox[];
}
