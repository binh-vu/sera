/**
 * For each field, you can either choose to filter by exact value matching (typeof string, number, boolean),
 * or choose to be max of a group (records are grouped by multiple fields in the value (hence value is (keyof R)[])),
 * or choose to be greater, less than (gt, lt, gte, lte) than a value (number only), or choose to be in an array of
 * values (string[] or number[])
 */
type QueryOp =
  | string
  | number
  | boolean
  | {
      op: "gt" | "lt" | "gte" | "lte" | "in";
      value: string | number | string[] | number[];
    };

export type QueryConditions<R> = Partial<Record<keyof R, QueryOp>>;

export interface Query<R> {
  limit: number;
  offset: number;
  fields?: (keyof R)[];
  conditions?: QueryConditions<R>;
  unique?: boolean;
  sortedBy?:
    | keyof R
    | { field: keyof R; order: "desc" | "asc" }
    | { field: keyof R; order: "desc" | "asc" }[];
  groupBy?: (keyof R)[];
  returnTotal?: boolean;
}

export const KEYWORDS = new Set([
  "field",
  "limit",
  "offset",
  "unique",
  "sorted_by",
  "group_by",
]);

export class QueryProcessor<R> {
  /// Rename field from the one used in the client to the name used in the server
  renameField: Partial<Record<keyof R, string>>;

  constructor(renameField: Partial<Record<keyof R, string>>) {
    this.renameField = renameField;
  }

  /// Prepare a query to send to the server
  prepare(query: Query<R>): object {
    let params: any = {
      limit: query.limit,
      offset: query.offset,
      unique: query.unique,
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
        let field = this.renameField[item.field] || item.field;
        return item.order === "asc" ? field : `-${field as string}`;
      });
    } else if (typeof query.sortedBy === "object") {
      let field =
        this.renameField[query.sortedBy.field] || query.sortedBy.field;
      params.sorted_by =
        query.sortedBy.order === "asc" ? field : `-${field as string}`;
    } else if (query.sortedBy !== undefined) {
      params.sorted_by = this.renameField[query.sortedBy] || query.sortedBy;
    }

    // normalize the group by field name
    if (query.groupBy !== undefined) {
      params.group_by = query.groupBy.map(
        (field) => this.renameField[field] || field
      );
    }

    // normalize the conditions
    if (query.conditions !== undefined) {
      const it: [keyof R, QueryOp][] = Object.entries(query.conditions) as any;

      for (let [field, opOrVal] of it) {
        let serverField: string =
          this.renameField[field as keyof R] || (field as string);

        if (KEYWORDS.has(serverField)) {
          serverField = `_${serverField}`;
        }

        if (typeof opOrVal === "object") {
          params[`${serverField}[${opOrVal.op}]`] = opOrVal.value;
        } else {
          params[field] = opOrVal;
        }
      }
    }

    return params;
  }
}
