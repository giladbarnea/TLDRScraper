export function createPointPositionReference(x, y) {
  return {
    kind: 'point',
    boundingRect: { x, y, top: y, left: x, right: x, bottom: y, width: 0, height: 0 },
    clientRects: [],
    placement: 'bottom-start',
    offsetPx: 0,
  }
}
