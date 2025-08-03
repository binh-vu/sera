import { ClassName } from "./Record";
import { Table } from "./Table";

export class DB {
  tables: { [name: ClassName]: Table<any, any, any> };
  cls2table: { [name: ClassName]: Table<any, any, any> };

  constructor() {
    this.tables = {};
    this.cls2table = {};
  }

  /// Get a table by its table class (UserTable)
  get<T extends Table<any, any, any>>(Table: { new(...args: any[]): T }): T {
    return this.cls2table[Table.name] as any;
  }

  /// Get a table by its name ("User")
  getByName(name: ClassName): Table<any, any, any> {
    return this.tables[name];
  }

  /// Register a table in the database
  register(table: Table<any, any, any>) {
    if (this.tables[table.name] !== undefined) {
      throw new Error(
        `Table ${table.name} is already registered in the database`
      );
    }
    if (this.cls2table[table.constructor.name] !== undefined) {
      throw new Error(
        `Table ${table.constructor.name} is already registered in the database`
      );
    }

    this.tables[table.name] = table;
    this.cls2table[table.constructor.name] = table;
  }

  /// Populate the database with data
  populateData(data: { [name: ClassName]: any[] }): { [name: ClassName]: any[] } {
    let output: { [name: ClassName]: any[] } = {};
    for (const name in data) {
      const table = this.tables[name];
      if (table === undefined) continue;
      // if the table is not registered, skip it
      const records = data[name].map(table.cls.deser.bind(table.cls));
      table.batchSet(records);
      output[name] = records;
    }

    return output;
  }

  /// Clear all records in the database
  clear() {
    for (const name in this.tables) {
      this.tables[name].clear();
    }
  }
}
