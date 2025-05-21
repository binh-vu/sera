export interface Record<ID> {
  id: ID;
}

export type RecordClass<R> = { new(...args: any[]): R } & {
  deser(data: any): R;
};

export interface DraftRecord<ID> {
  id: ID;
  stale: boolean;

  /// Check if the draft record is a new record
  isNewRecord(): boolean;

  /// Check if the draft is valid (only check the required fields as the non-required fields if it's invalid will be set to undefined)
  isValid(): boolean;

  /// Serialize the draft to communicate with the server. `isValid` must be called first to ensure all data is valid
  ser(): any;
}
