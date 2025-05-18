export interface Record<ID> {
  id: ID;
}

export type RecordClass<R> = { new (...args: any[]): R } & {
  deser(data: any): R;
};

export interface DraftRecord<ID> {
  id: ID;
  stale: boolean;
}
