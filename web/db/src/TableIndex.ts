import { action, makeObservable, observable } from "mobx";
import { Record } from "./Record";

type Key = string | number;

export interface Index<M extends Record<Key>> {
  // add record to the index
  add(record: M): void;

  // remove record from the index
  remove(record: M): void;

  // clear the index
  clear(): void;
}

/**
 * A unique index implementation that maps a single foreign key field to a primary key.
 * This index ensures one-to-one mapping between foreign key values and record IDs.
 * 
 * @template F - The type of the foreign key field value
 * @template K - The type of the primary key field value  
 * @template M - The record type that extends Record<Key>
 * 
 * @example
 * ```typescript
 * // Create an index on the 'userId' foreign key field
 * const userIndex = new SingleKeyUniqueIndex<string, number, UserRecord>('userId');
 * 
 * // Add a record to the index
 * userIndex.add({ id: 1, userId: 'user123', name: 'John' });
 * ```
 */
export class SingleKeyUniqueIndex<
  F extends Key,
  K extends Key,
  M extends Record<Key>
> implements Index<M> {

  public index: Map<F, K | null> = new Map();

  protected fkField: keyof M;
  protected idField: keyof M;

  constructor(field: keyof M, idField: keyof M = "id") {
    this.fkField = field;
    this.idField = idField;

    makeObservable(this, {
      index: observable,
      add: action,
      remove: action,
      clear: action,
    });
  }

  /**
   * Check if the index contains a given foreign key (including NULL -- meaning there is no record with the foreign key).
   */
  public has(key: F): boolean {
    return this.index.has(key);
  }

  /**
   * Get the primary key associated with a given foreign key.
   * Returns null if the foreign key has been created but has no associated record.
   */
  public get(key: F): K | null | undefined {
    return this.index.get(key);
  }

  /**
   * Sets a value in the index for the specified key.
   */
  public set(key: F, value: K | null) {
    this.index.set(key, value);
  }

  public add(record: M) {
    const key = record[this.fkField] as unknown as F;
    this.index.set(key, record[this.idField] as unknown as K);
  }

  public remove(record: M) {
    const key = record[this.fkField] as unknown as F;
    this.index.delete(key);
  }

  public clear() {
    this.index.clear();
  }
}

/**
 * An index (fk1) => rid[]
 */
export class SingleKeyIndex<F extends Key, K extends Key, M extends Record<Key>>
  implements Index<M> {
  public index: Map<F, Set<K>> = new Map();

  protected fkField: keyof M;
  protected idField: keyof M;

  constructor(field: keyof M, idField?: keyof M) {
    this.fkField = field;
    this.idField = idField || "id";
    makeObservable(this, {
      index: observable,
      add: action,
      remove: action,
      clear: action,
    });
  }

  /**
   * Check if the index contains a given foreign key (including NULL -- meaning there is no record with the foreign key).
   */
  public has(key: F): boolean {
    return this.index.has(key);
  }

  /**
   * Get the primary key associated with a given foreign key.
   * Returns null if the foreign key has been created but has no associated record.
   */
  public get(key: F): Set<K> | undefined {
    return this.index.get(key);
  }

  /**
   * Sets a value in the index for the specified key.
   */
  public set(key: F, value: Set<K>) {
    this.index.set(key, value);
  }

  public add(record: M) {
    const key = record[this.fkField] as unknown as F;

    if (!this.index.has(key)) {
      this.index.set(key, new Set());
    }

    this.index.get(key)!.add(record[this.idField] as unknown as K);
  }

  public remove(record: M) {
    const key = record[this.fkField] as unknown as F;
    this.index.get(key)?.delete(record[this.idField] as unknown as K);
  }

  public clear() {
    this.index.clear();
  }
}

/**
 * An index fk1 => fk2 => Set<rid>
 */
export class PairKeysIndex<
  F1 extends Key,
  F2 extends Key,
  K extends Key,
  M extends Record<Key>
> implements Index<M> {
  public index: Map<F1, Map<F2, Set<K>>> = new Map();

  protected fkField1: keyof M;
  protected fkField2: keyof M;
  protected idField: keyof M;

  constructor(fkField1: keyof M, fkField2: keyof M, idField?: keyof M) {
    this.fkField1 = fkField1;
    this.fkField2 = fkField2;
    this.idField = idField || "id";

    makeObservable(this, {
      index: observable,
      add: action,
      remove: action,
      clear: action,
    });
  }

  /**
   * Index record
   */
  public add(record: M) {
    const key1 = record[this.fkField1] as unknown as F1;
    const key2 = record[this.fkField2] as unknown as F2;

    if (!this.index.has(key1)) {
      this.index.set(key1, new Map());
    }

    let map = this.index.get(key1)!;
    if (!map.has(key2)) {
      map.set(key2, new Set());
    }
    map.get(key2)!.add(record[this.idField] as unknown as K);
  }

  public remove(record: M) {
    const key1 = record[this.fkField1] as unknown as F1;
    const key2 = record[this.fkField2] as unknown as F2;

    if (this.index.has(key1)) {
      this.index
        .get(key1)!
        .get(key2)
        ?.delete(record[this.idField] as unknown as K);
    }
  }

  public clear() {
    this.index.clear();
  }
}

/**
 * An index fk1 => fk2 => rid
 */
export class PairKeysUniqueIndex<
  F1 extends Key,
  F2 extends Key,
  K extends Key,
  M extends Record<Key>
> implements Index<M> {
  public index: Map<F1, Map<F2, K>> = new Map();

  protected fkField1: keyof M;
  protected fkField2: keyof M;
  protected idField: keyof M;

  constructor(fkField1: keyof M, fkField2: keyof M, idField?: keyof M) {
    this.fkField1 = fkField1;
    this.fkField2 = fkField2;
    this.idField = idField || "id";

    makeObservable(this, {
      index: observable,
      add: action,
      remove: action,
      clear: action,
    });
  }

  /**
   * Index record
   */
  public add(record: M) {
    const key1 = record[this.fkField1] as unknown as F1;
    const key2 = record[this.fkField2] as unknown as F2;

    if (!this.index.has(key1)) {
      this.index.set(key1, new Map());
    }

    let map = this.index.get(key1)!;
    map.set(key2, record[this.idField] as unknown as K);
  }

  public remove(record: M) {
    const key1 = record[this.fkField1] as unknown as F1;
    const key2 = record[this.fkField2] as unknown as F2;

    if (this.index.has(key1)) {
      this.index.get(key1)!.delete(key2);
    }
  }

  public clear() {
    this.index.clear();
  }
}

/**
 * An index fk1 => fk2 => Set<rid>
 */
export class TripleKeysIndex<
  F1 extends Key,
  F2 extends Key,
  F3 extends Key,
  K extends Key,
  M extends Record<Key>
> implements Index<M> {
  public index: Map<F1, Map<F2, Map<F3, Set<K>>>> = new Map();

  protected fkField1: keyof M;
  protected fkField2: keyof M;
  protected fkField3: keyof M;
  protected idField: keyof M;

  constructor(
    fkField1: keyof M,
    fkField2: keyof M,
    fkField3: keyof M,
    idField?: keyof M
  ) {
    this.fkField1 = fkField1;
    this.fkField2 = fkField2;
    this.fkField3 = fkField3;
    this.idField = idField || "id";

    makeObservable(this, {
      index: observable,
      add: action,
      remove: action,
      clear: action,
    });
  }

  /**
   * Index record
   */
  public add(record: M) {
    const key1 = record[this.fkField1] as unknown as F1;
    const key2 = record[this.fkField2] as unknown as F2;
    const key3 = record[this.fkField3] as unknown as F3;

    if (!this.index.has(key1)) {
      this.index.set(key1, new Map());
    }

    let map2 = this.index.get(key1)!;
    if (!map2.has(key2)) {
      map2.set(key2, new Map());
    }

    let map3 = map2.get(key2)!;
    if (!map3.has(key3)) {
      map3.set(key3, new Set());
    }

    map3.get(key3)!.add(record[this.idField] as unknown as K);
  }

  public remove(record: M) {
    const map2 = this.index.get(record[this.fkField1] as unknown as F1);
    if (map2 === undefined) return;

    const map3 = map2.get(record[this.fkField2] as unknown as F2);
    if (map3 === undefined) return;

    map3
      .get(record[this.fkField3] as unknown as F3)
      ?.delete(record[this.idField] as unknown as K);
  }

  public clear() {
    this.index.clear();
  }
}
