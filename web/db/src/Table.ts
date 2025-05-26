import axios from "axios";
import { action, makeObservable, observable, runInAction } from "mobx";
import { Index } from "./TableIndex";
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
    this.indices = indices || [];
    this.queryProcessor = queryProcessor;
    this.refetch = refetch;
    this.db = db;

    this.db.register(this);

    makeObservable(this, {
      records: observable,
      draftRecords: observable,
      version: observable,
      set: action,
      remove: action,
      setDraft: action,
      batchSet: action,
      upsert: action,
      fetch: action,
      fetchById: action,
      fetchByIds: action,
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
    for (const id of ids) {
      const record = this.get(id);
      if (record !== null && record !== undefined) {
        results[id] = record;
      }
    }
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
      if (record === null) return Promise.resolve(undefined);
      return Promise.resolve(record);
    }

    try {
      let resp = await this.createFetchByIdRequest(id);

      runInAction(() => {
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
          this.remove(id);
        });
        return undefined;
      }

      throw error;
    }
  }

  /**
   * Test if we store a local copy of a record (INCLUDING NULL -- the record does not exist)
   */
  public has(id: ID): boolean {
    return this.records.has(id);
  }

  /**
   * Test if we have a draft record
   */
  public hasDraft(id: ID): boolean {
    return this.draftRecords.has(id);
  }

  /**
   * Get a local copy of a record
   */
  public get(id: ID): R | null | undefined {
    return this.records.get(id);
  }

  /**
   * Remove a record from the table
   */
  public remove(id: ID) {
    const m = this.records.get(id);
    if (m !== null && m !== undefined) {
      this.records.delete(id);
      this.deindex(m);
      this.version++;
    }
  }

  /**
   * Get a draft record
   */
  public getDraft(id: ID): DR | undefined {
    return this.draftRecords.get(id);
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
   * Save a draft record to the table
   *
   * @param m the draft record
   */
  public setDraft(m: DR) {
    this.draftRecords.set(m.id, m);
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
