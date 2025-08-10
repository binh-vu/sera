import { action, makeObservable, observable } from "mobx";
import { DataProperty, ObjectProperty } from "./Schema";

type DOP = DataProperty | ObjectProperty;

/**
 * For each field, you can either choose to filter by exact value matching (typeof string, number, boolean),
 * or choose to be max of a group (records are grouped by multiple fields in the value (hence value is (keyof R)[])),
 * or choose to be greater, less than (gt, lt, gte, lte) than a value (number only), or choose to be in an array of
 * values (string[] or number[])
 */
export type QueryOp =
  | string
  | number
  | boolean
  | {
    op: "gt" | "lt" | "gte" | "lte" | "in";
    value: string | number | string[] | number[] | (string | number)[];
  };

export type QueryConditions<R> = Partial<Record<keyof R, QueryOp>>;

export interface Query<R> {
  limit: number;
  offset: number;
  /// List of fields to return in the result
  fields?: (keyof R)[];
  /// Conditions to filter the records
  conditions?: QueryConditions<R>;
  /// Whether to return unique records (no duplicates)
  unique?: boolean;
  /// Sort the records by a field or multiple fields, the order by default is asc
  sortedBy?:
  | keyof R
  | { field: keyof R; order: "desc" | "asc" }
  | { field: keyof R; order: "desc" | "asc" }[];
  /// Group the records by a field or multiple fields
  groupBy?: (keyof R)[];
  /// Whether to return the total number of records that match the query
  returnTotal?: boolean;
}

export interface Query2J<P, S> {
  limit: number;
  offset: number;
  /// List of fields to return in the result
  fields?: (keyof P)[];
  /// Conditions to filter the records
  conditions?: QueryConditions<P>;
  /// Conditions of the secondary class
  joinConditions: {
    prop: DOP;
    /// default is inner
    joinType?: "inner" | "left" | "full";
    /// List of fields to return in the results
    fields?: (keyof S)[];
    /// default is empty
    conditions?: QueryConditions<S>;
  };
  /// Whether to return unique records (no duplicates)
  unique?: boolean;
  /// Sort the records by a field or multiple fields, the order by default is asc
  sortedBy?:
  | keyof P
  | { field: keyof P; order: "desc" | "asc" }
  | { field: keyof S; order?: "desc" | "asc", prop: DOP }
  | ({ field: keyof P; order: "desc" | "asc" } | { field: keyof S; order: "desc" | "asc", prop: DOP })[];
  /// Group the records by a field or multiple fields
  groupBy?: (keyof P | { field: keyof S, prop: DOP })[];
  /// Whether to return the total number of records that match the query
  returnTotal?: boolean;
}

export class QueryProcessor<R> {
  /// Rename field from the one used in the client to the name used in the server
  renameField: Partial<Record<keyof R, string>>;

  constructor(renameField: Partial<Record<keyof R, string>>) {
    this.renameField = renameField;
  }

  /// Prepare a join query to send to the server
  static prepareJoinQuery<P, S>(primary: QueryProcessor<P>, secondary: QueryProcessor<S>, query: Query2J<P, S>): object {
    let params: any = {
      limit: query.limit,
      offset: query.offset,
      unique: query.unique,
      return_total: query.returnTotal,
      join_conditions: {
        prop: query.joinConditions.prop.name,
        join_type: query.joinConditions.joinType || "inner",
      }
    };

    // normalize the selected field name
    if (query.fields !== undefined) {
      params.fields = query.fields.map(
        (field) => primary.renameField[field] || field
      );
    }
    if (query.joinConditions.fields !== undefined) {
      params.join_conditions.fields = query.joinConditions.fields.map(
        (field) => secondary.renameField[field] || field
      );
    }

    // normalize the sort by field name
    if (Array.isArray(query.sortedBy)) {
      params.sorted_by = query.sortedBy.map((item) => {
        if ("prop" in item) {
          return { field: secondary.renameField[item.field] || item.field, order: item.order || "asc", prop: item.prop.name };
        } else {
          return { field: primary.renameField[item.field] || item.field, order: item.order || "asc" };
        }
      });
    } else if (typeof query.sortedBy === "object") {
      if ("prop" in query.sortedBy) {
        params.sorted_by = [{ field: secondary.renameField[query.sortedBy.field] || query.sortedBy.field, order: query.sortedBy.order || "asc", prop: query.sortedBy.prop.name }];
      } else {
        params.sorted_by = [{ field: primary.renameField[query.sortedBy.field] || query.sortedBy.field, order: query.sortedBy.order }];
      }
    } else if (query.sortedBy !== undefined) {
      params.sorted_by = [{ field: primary.renameField[query.sortedBy] || query.sortedBy, order: "asc" }]
    }

    // normalize the group by field name
    if (query.groupBy !== undefined) {
      params.group_by = query.groupBy.map(
        (field) => {
          if (typeof field === "object") {
            return { field: secondary.renameField[field.field] || field.field, prop: field.prop.name };
          } else {
            return { field: primary.renameField[field] || field };
          }
        }
      );
    }

    // normalize the conditions
    if (query.conditions !== undefined) {
      params.conditions = primary.prepareConditions(query.conditions);
    }
    if (query.joinConditions.conditions !== undefined) {
      params.join_conditions.conditions = secondary.prepareConditions(query.joinConditions.conditions);
    }

    return params;
  }

  /// Prepare a query to send to the server
  prepare(query: Query<R>): object {
    let params: any = {
      limit: query.limit,
      offset: query.offset,
      unique: query.unique,
      return_total: query.returnTotal,
    };

    // normalize the selected field name
    if (query.fields !== undefined) {
      params.fields = query.fields.map(
        (field) => this.renameField[field] || field
      );
    }

    // normalize the sort by field name
    if (Array.isArray(query.sortedBy)) {
      params.sorted_by = query.sortedBy.map((item) => {
        return { field: this.renameField[item.field] || item.field, order: item.order };
      });
    } else if (typeof query.sortedBy === "object") {
      params.sorted_by = [{ field: this.renameField[query.sortedBy.field] || query.sortedBy.field, order: query.sortedBy.order }];
    } else if (query.sortedBy !== undefined) {
      params.sorted_by = [{ field: this.renameField[query.sortedBy] || query.sortedBy, order: "asc" }];
    }

    // normalize the group by field name
    if (query.groupBy !== undefined) {
      params.group_by = query.groupBy.map(
        (field) => this.renameField[field] || field
      );
    }

    // normalize the conditions
    if (query.conditions !== undefined) {
      params.conditions = this.prepareConditions(query.conditions);
    }

    return params;
  }

  prepareConditions(
    conditions: QueryConditions<R>
  ): object {
    const params: any = {};
    const it: [keyof R, QueryOp][] = Object.entries(conditions) as any;

    for (let [field, opOrVal] of it) {
      let serverField: string =
        this.renameField[field as keyof R] || (field as string);

      if (typeof opOrVal === "object") {
        params[serverField] = opOrVal;
      } else {
        params[serverField] = { eq: opOrVal };
      }
    }

    return params;
  }
}

/// A class that allows to subscribe to query changes
export class ObservableQuery<Q> {
  public query: Q;
  private subscribers: ((query: Q) => void)[] = [];

  constructor(query: Q) {
    this.query = query;

    makeObservable(this, {
      query: observable,
      update: action,
    });
  }

  /// Update the query and notify all subscribers
  update(query: Q): void {
    this.query = query;
    this.notify(query);
  }

  /// Subscribe to query changes and return an unsubscribe function
  /// The callback will be called with the new query whenever it changes
  subscribe(callback: (query: Q) => void): () => void {
    this.subscribers.push(callback);
    return () => {
      this.subscribers = this.subscribers.filter((cb) => cb !== callback);
    };
  }

  /// Notify all subscribers about the query change
  private notify(query: Q): void {
    for (const subscriber of this.subscribers) {
      subscriber(query);
    }
  }
}