import axios from "axios";
import { action, makeObservable, observable, runInAction } from "mobx";
import { Index, SingleKeyIndex, SingleKeyUniqueIndex } from "./TableIndex";
import { Query, QueryConditions, QueryProcessor } from "./Query";
import { Record as DBRecord, DraftRecord, RecordClass } from "./Record";
import { DB } from "./DB";

export type FetchResult<R> = { records: R[]; total: number };

export class Table<
  ID extends string | number,
  R extends DBRecord<ID>,
  DR extends DraftRecord<ID>
> {
  records: Map<ID, R | null> = new Map();
  draftRecords: Map<ID, DR> = new Map();

  // Class of the record
  cls: RecordClass<R>;

  // Database contains all tables
  db: DB;

  // Query processor
  queryProcessor: QueryProcessor<R>;

  // Endpoint for this table (e.g. "/api/products")
  remoteURL: string;

  /// storing index, has to make it public to make it observable, but you should treat it as protected
  indices: Index<R>[] = [];

  /// storing index for unique foreign keys
  uniqueForeignKeyIndices: Map<keyof R, SingleKeyUniqueIndex<string | number, ID, R>> = new Map();

  /// storing index for non-unique foreign keys
  nonUniqueForeignKeyIndices: Map<keyof R, SingleKeyIndex<string | number, ID, R>> = new Map();

  // whether to reload the entity if the store already has an entity
  public refetch: boolean = true;

  /// approximate version of the data in the table -- this is a useful property to know whether the data has been potentially updated
  /// NOTE: this does not keep track of changes in the draft records
  public version: number = 0;

  /**
   * Constructor
   *
   * @param remoteURL Endpoint for this table (e.g. "/api/products")
   */
  constructor({
    cls,
    remoteURL,
    queryProcessor,
    indices = [],
    refetch = true,
    db,
  }: {
    cls: RecordClass<R>;
    remoteURL: string;
    queryProcessor: QueryProcessor<R>;
    indices?: Index<R>[];
    refetch?: boolean;
    db: DB;
  }) {
    this.cls = cls;
    this.remoteURL = remoteURL;
    this.indices = indices;
    this.queryProcessor = queryProcessor;
    this.refetch = refetch;
    this.db = db;

    this.db.register(this);

    makeObservable(this, {
      records: observable,
      draftRecords: observable,
      version: observable,
      indices: observable,
      uniqueForeignKeyIndices: observable,
      nonUniqueForeignKeyIndices: observable,
      set: action,
      remove: action,
      setDraft: action,
      batchSet: action,
      upsert: action,
      fetch: action,
      fetchOne: action,
      fetchById: action,
      fetchByIds: action,
      fetchByUniqueForeignKey: action,
      fetchByNonUniqueForeignKey: action,
      remoteSize: action,
      clear: action,
    });
  }

  get name(): string {
    return this.cls.name;
  }

  /**
   * Get the number of records in the table
   */
  async remoteSize(): Promise<number> {
    return (await this.fetch({ limit: 1, offset: 0 })).total;
  }

  /**
   * Creates or updates a record in the table. This function assumes the record has already been validated; ensure `isValid` is called beforehand.
   *
   * @param record - The record to create or update.
   *
   * @returns The newly created or updated record. If the record has been deleted on the server, it will be removed from the store and `undefined` will be returned.
   */
  async upsert(
    record: DR
  ): Promise<R | undefined> {
    if (record.isNewRecord()) {
      let resp = await axios.post(`${this.remoteURL}`, record.ser());
      runInAction(() => {
        record.id = resp.data.id;
        this.set(record.toRecord() as R);
        this.draftRecords.delete(record.id);
      });
    } else {
      try {
        await axios.put(`${this.remoteURL}/${record.id}`, record.ser());
        runInAction(() => {
          this.set(record.toRecord() as R);
          this.draftRecords.delete(record.id);
        });
      } catch (error: unknown) {
        // If the record does not exist, 404 is returned
        // and we will remove the record from the store!
        if (
          axios.isAxiosError(error) &&
          error.response &&
          error.response.status === 404
        ) {
          runInAction(() => {
            this.remove(record.id);
          });
          return undefined;
        }
        throw error;
      }
    }
    return this.records.get(record.id)!;
  }

  /** Fetch records by query */
  async fetch(query: Query<R>): Promise<FetchResult<R>> {
    if (query.fields !== undefined) {
      throw new Error(
        "Fetching specific fields is not supported in Table.fetch"
      );
    }

    let resp = await axios.get(`${this.remoteURL}`, {
      params: this.queryProcessor.prepare(query),
    });

    const output = runInAction(() => {
      return this.db.populateData(resp.data);
    });

    return {
      records: output[this.name],
      total: resp.data.total,
    };
  }

  /** Fetch one record by query */
  async fetchOne(conditions: QueryConditions<R>): Promise<R | undefined> {
    const result = await this.fetch({ conditions: this.queryProcessor.prepareConditions(conditions), limit: 1, offset: 0 });
    return result.records[0];
  }

  /**
   * Fetches multiple records by their IDs and returns them as a dictionary.
   *
   * @template ID - The type of the record IDs.
   * @template R - The type of the records being fetched.
   * @param ids - An array of IDs for the records to fetch.
   * @param force - A boolean flag indicating whether to force a fresh fetch
   *                (default is `false`).
   * @returns A promise that resolves to a dictionary where the keys are the
   *          provided IDs and the values are the corresponding records.
   */
  async fetchByIds(
    ids: ID[], force: boolean = false
  ): Promise<Record<ID, R>> {
    let sendoutIds = ids;
    if (!force && !this.refetch) {
      // no refetch, then we need to filter the list of ids
      sendoutIds = sendoutIds.filter((id) => !this.has(id));

      if (sendoutIds.length === 0) {
        const output = {} as Record<ID, R>;
        for (const id of ids) {
          const record = this.records.get(id);
          if (record !== null && record !== undefined) {
            output[id] = record;
          }
        }
        return Promise.resolve(output);
      }
    }

    if (sendoutIds.length === 1) {
      // if we only have one id, we can just fetch it directly
      await this.fetchById(sendoutIds[0], true);
    } else {
      // complier does not smart enough to allow create object with id as key
      // so we have to do it in two steps
      const conditions: QueryConditions<R> = {};
      conditions['id'] = {
        op: "in",
        value: sendoutIds
      };
      await this.fetch({
        offset: 0,
        limit: sendoutIds.length,
        conditions,
      });
    }

    const results: Record<ID, R> = {} as Record<ID, R>;
    runInAction(() => {
      for (const id of ids) {
        const record = this.get(id);
        if (record !== null && record !== undefined) {
          results[id] = record;
        } else {
          // If the record does not exist, we will store it as a null record
          // so that we can track that the record was requested
          this.records.set(id, null);
        }
      }
    });
    return results;
  }

  /**
   * Fetch a record from remote server.
   *
   * Use async instead of flow as we may want to override the function and call super.
   *
   * @param id the id of the record
   * @param force if true, force to fetch the record from remote server
   * @returns the record if it exists, undefined otherwise
   */
  async fetchById(id: ID, force: boolean = false): Promise<R | undefined> {
    if (!force && !this.refetch && this.has(id)) {
      const record = this.records.get(id);
      if (record === null) return undefined;
      return record;
    }

    try {
      let resp = await this.createFetchByIdRequest(id);

      runInAction(() => {
        // If the record does not exist, we will get a 404 error
        this.db.populateData(resp.data);
      });

      return this.records.get(id)!;
    } catch (error: unknown) {
      // If the record does not exist, 404 is returned
      if (
        axios.isAxiosError(error) &&
        error.response &&
        error.response.status === 404
      ) {
        runInAction(() => {
          if (!this.remove(id)) {
            // If the record does not exist, means that the id was never in the store, we 
            // should store it as a null record
            this.records.set(id, null);
          }
        });
        return undefined;
      }

      throw error;
    }
  }

  /**
   * Fetch a record by an unique foreign key.
   */
  async fetchByUniqueForeignKey(
    foreignKey: keyof R,
    foreignKeyValue: string | number,
    force: boolean = false
  ): Promise<R | undefined> {
    // Check if we already have the record in our unique foreign key index
    const uniqueIndex = this.uniqueForeignKeyIndices.get(foreignKey)!;
    if (uniqueIndex.has(foreignKeyValue) && !force && !this.refetch) {
      const recordId = uniqueIndex.get(foreignKeyValue);
      if (recordId === null || recordId === undefined) {
        return undefined; // The foreign key exists but has no associated record
      }
      return this.get(recordId)!;
    }

    // Fetch from remote
    const conditions: QueryConditions<R> = {};
    conditions[foreignKey] = foreignKeyValue;

    const result = await this.fetchOne(conditions);
    if (result === undefined) {
      runInAction(() => {
        uniqueIndex.set(foreignKeyValue, null);
      });
    }
    return result;
  }

  /**
   * Fetches multiple records from the table by a non-unique foreign key value.
   * 
   * @param foreignKey - The foreign key field name to search by
   * @param foreignKeyValue - The value to match against the foreign key field
   * @param force - Whether to force a fresh fetch from the database, bypassing any cache. Defaults to false
   * @returns A promise that resolves to an array of records matching the foreign key criteria
   * 
   * @example
   * ```typescript
   * // Fetch all orders for a specific customer
   * const orders = await orderTable.fetchByNonUniqueForeignKey('customerId', 123);
   * 
   * // Force a fresh fetch from database
   * const orders = await orderTable.fetchByNonUniqueForeignKey('customerId', 123, true);
   * ```
   */
  async fetchByNonUniqueForeignKey(
    foreignKey: keyof R,
    foreignKeyValue: string | number,
    force: boolean = false
  ): Promise<R[]> {
    // Check if we already have the records in our non-unique foreign key index
    const nonUniqueIndex = this.nonUniqueForeignKeyIndices.get(foreignKey)!;
    if (nonUniqueIndex.has(foreignKeyValue) && !force && !this.refetch) {
      const recordIds = nonUniqueIndex.get(foreignKeyValue)!;
      const records: R[] = [];
      for (const recordId of recordIds) {
        records.push(this.get(recordId)!);
      }
      return records;
    }

    // Fetch from remote
    const conditions: QueryConditions<R> = {};
    conditions[foreignKey] = foreignKeyValue;

    const result = await this.fetch({
      offset: 0,
      limit: 10000, // Use a reasonable default limit
      conditions: this.queryProcessor.prepareConditions(conditions),
    });

    // If no records are found, we will store an empty set in the index
    // because the indexing function won't be called if there are no records
    if (result.records.length === 0) {
      runInAction(() => {
        nonUniqueIndex.set(foreignKeyValue, new Set());
      });
      return [];
    }

    return result.records;
  }

  /**
   * Test if we store a local copy of a record (INCLUDING NULL -- the record does not exist)
   */
  public has(id: ID): boolean {
    return this.records.has(id);
  }

  /**
   * Get a local copy of a record
   */
  public get(id: ID): R | null | undefined {
    return this.records.get(id);
  }

  /**
   * Get local copies of existing records
   */
  public batchGetExist(ids: ID[]): R[] {
    const records = [];
    for (const id of ids) {
      const record = this.records.get(id);
      if (record !== null && record !== undefined) {
        records.push(record);
      }
    }
    return records;
  }

  /**
   * Save a record to the table
   *
   * @param m the record
   */
  public set(m: R) {
    const existing = this.records.get(m.id);
    if (existing !== null && existing !== undefined) {
      this.deindex(existing);
    }
    this.records.set(m.id, m);
    this.index(m);
    this.version++;
  }

  /**
   * Save multiple records to the table
   *
   */
  public batchSet(records: R[]) {
    for (const m of records) {
      const existing = this.records.get(m.id);
      if (existing !== null && existing !== undefined) {
        this.deindex(existing);
      }
      this.records.set(m.id, m);
      this.index(m);
      this.version++;
    }
  }

  /**
   * Remove a record from the table.
   * 
   * Return true if the record was removed, false if the record does not exist.
   */
  public remove(id: ID): boolean {
    const m = this.records.get(id);
    if (m !== null && m !== undefined) {
      this.records.delete(id);
      this.deindex(m);
      this.version++;
      return true;
    }
    return false;
  }

  /**
   * Test if we have a draft record
   */
  public hasDraft(id: ID): boolean {
    return this.draftRecords.has(id);
  }

  /**
   * Get a draft record
   */
  public getDraft(id: ID): DR | undefined {
    return this.draftRecords.get(id);
  }

  /**
   * Save a draft record to the table
   *
   * @param m the draft record
   */
  public setDraft(m: DR) {
    this.draftRecords.set(m.id, m);
  }

  /**
   * Retrieves a record by its unique foreign key value.
   * 
   * @param foreignKey - The foreign key field name to search by
   * @param foreignKeyValue - The value of the foreign key to match
   * @returns The record matching the foreign key value, or undefined if not found
   * 
   * @example
   * ```typescript
   * const user = table.getByUniqueForeignKey('userId', 123);
   * if (user) {
   *   console.log('Found user:', user);
   * }
   * ```
   */
  public getByUniqueForeignKey(
    foreignKey: keyof R,
    foreignKeyValue: string | number
  ): R | null | undefined {
    const uniqueIndex = this.uniqueForeignKeyIndices.get(foreignKey)!;
    const recordId = uniqueIndex.get(foreignKeyValue);
    if (recordId !== null && recordId !== undefined) {
      return this.get(recordId)!;
    }
    return recordId;
  }

  /**
   * Test if a record exists with the given unique foreign key value.
   *
   * @param foreignKey - The foreign key field name to search by
   * @param foreignKeyValue - The value of the foreign key to match
   * @returns True if the record exists, false otherwise
   */
  public hasUniqueForeignKey(
    foreignKey: keyof R,
    foreignKeyValue: string | number
  ): boolean {
    const uniqueIndex = this.uniqueForeignKeyIndices.get(foreignKey)!;
    return uniqueIndex.has(foreignKeyValue);
  }

  /**
   * Retrieves all records that match a specific foreign key value from a non-unique foreign key index.
   * 
   * @param foreignKey - The foreign key field name to search by
   * @param foreignKeyValue - The value to match against the foreign key field
   * @returns An array of records matching the foreign key criteria, or undefined if no records match
   * 
   * @example
   * ```typescript
   * // Get all orders for a specific customer
   * const customerOrders = orderTable.getByNonUniqueForeignKey('customerId', 123);
   * ```
   */
  public getByNonUniqueForeignKey(
    foreignKey: keyof R,
    foreignKeyValue: string | number
  ): R[] | undefined {
    const nonUniqueIndex = this.nonUniqueForeignKeyIndices.get(foreignKey)!;
    const recordIds = nonUniqueIndex.get(foreignKeyValue);

    const records: R[] = [];
    if (recordIds !== undefined) {
      for (const recordId of recordIds) {
        const record = this.get(recordId);
        if (record !== null && record !== undefined) {
          records.push(record);
        }
      }
    } else {
      return recordIds
    }
    return records;
  }

  /**
   * Checks if a record exists in the table with the specified non-unique foreign key value.
   * 
   * @param foreignKey - The foreign key column name to check against
   * @param foreignKeyValue - The value to search for in the foreign key column
   * @returns True if at least one record exists with the specified foreign key value, false otherwise
   */
  public hasByNonUniqueForeignKey(
    foreignKey: keyof R,
    foreignKeyValue: string | number
  ): boolean {
    const nonUniqueIndex = this.nonUniqueForeignKeyIndices.get(foreignKey)!;
    return nonUniqueIndex.has(foreignKeyValue);
  }

  /**
   * Iter through list of local copy of records in the table
   */
  public *iter(): Iterable<R> {
    for (const m of this.records.values()) {
      if (m !== null) {
        yield m;
      }
    }
  }

  /**
   * Get a list of local copy of records in the table
   */
  get list(): R[] {
    return Array.from(this.iter());
  }

  /**
   * Clear the table and remove all indices
   */
  clear() {
    this.records.clear();
    this.indices.forEach((index) => index.clear());
    this.version++;
  }

  /**
   * Filter records according to the filter function
   */
  public filter(fn: (r: R) => boolean): R[] {
    let output = [];
    for (const r of this.records.values()) {
      if (r !== null && fn(r)) {
        output.push(r);
      }
    }
    return output;
  }

  /**
   * Group records by values of some fields
   */
  public groupBy(groupedFields: (keyof R)[], records: R[]): R[][] {
    let output: { [k: string]: R[] } = {};
    for (const r of records) {
      const key = groupedFields.map((field) => r[field]).join("$");
      if (output[key] === undefined) {
        output[key] = [r];
      } else {
        output[key].push(r);
      }
    }
    return Object.values(output);
  }

  /**
   * Create a request for fetching a record by id. This is useful for
   * ID that contains special characters such as / that even encoded
   * will be decoded automatically by the server and cause an invalid request.
   */
  protected createFetchByIdRequest(id: ID) {
    return axios.get(`${this.remoteURL}/${id}`);
  }

  /**
   * Add a record to your indexes. Its implementation must be IDEMPOTENT
   */
  protected index(record: R): void {
    for (const index of this.indices) {
      index.add(record);
    }
  }

  /**
   * Remove a record to your indexes. Its implementation must be IDEMPOTENT
   */
  protected deindex(record: R): void {
    for (const index of this.indices) {
      index.remove(record);
    }
  }
}
