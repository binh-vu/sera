export function groupBy<R,>(items: R[], key: (item: R) => string | number): Record<string | number, R[]> {
  return items.reduce((acc, item) => {
    const k = key(item);
    if (!acc[k]) {
      acc[k] = [];
    }
    acc[k].push(item);
    return acc;
  }, {} as Record<string | number, R[]>);
}

export function groupByAsList<R,>(items: R[], key: (item: R) => string | number | undefined): R[][] {
  const output: R[][] = [];
  let undefinedIndex: number | undefined = undefined;

  items.reduce((acc, item) => {
    const k = key(item);

    if (k === undefined) {
      if (undefinedIndex === undefined) {
        undefinedIndex = output.length;
        output.push([]);
      }

      output[undefinedIndex].push(item);
    } else {
      if (acc[k] === undefined) {
        acc[k] = output.length;
        output.push([]);
      }
      output[acc[k]].push(item);
    }

    return acc;
  }, {} as Record<string | number, number>);
  return output;
}

export function uniqueList<R,>(items: R[], key: (item: R) => string | number): R[] {
  const seen = new Set<string | number>();
  return items.filter(item => {
    const k = key(item);
    if (seen.has(k)) {
      return false;
    }
    seen.add(k);
    return true;
  });
}

export class OrderedUniqueList<R> {
  private items: R[] = [];
  private seen = new Set<string | number>();

  add(item: R, keyFn: (item: R) => string | number): void {
    const key = keyFn(item);
    if (!this.seen.has(key)) {
      this.items.push(item);
      this.seen.add(key);
    }
  }

  toArray(): R[] {
    return this.items;
  }
}