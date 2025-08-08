import { useEffect, useMemo, useState } from "react";
import {
  ColumnDef,
  getCoreRowModel,
  Updater,
  useReactTable,
} from "@tanstack/react-table";
import {
  DraftRecord,
  FetchResult,
  GenericRecord,
  ObservableQuery,
  Query,
  Schema,
  SchemaType,
} from "sera-db";
import { Checkbox, Flex, Group, Paper, Text } from "@mantine/core";
import { SeraColumn } from "./makeColumns";
import { hasAction, SeraActionConfig, SeraTableAction } from "./TableAction";
import { SeraTableContent } from "./TableContent";
import { TablePagination } from "./TablePagination";

export interface SeraTableProps<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
> {
  // position of the pagination
  pagination?: {
    positions?: Set<"topRight" | "bottomLeft" | "bottomCenter" | "bottomRight">;
    showSizeChanger?: boolean;
  };
  schema: Schema<ID, R, DR, PF, F, ST>;
  // list of columns to display
  columns: SeraColumn<ST["cls"]>[];
  // an observable query to fetch the data
  query: ObservableQuery<ST["cls"]>;
  // function to fetch the data
  getData: (query: Query<ST["cls"]>) => Promise<FetchResult<ST["cls"]>>;
  // predefined actions that can be performed on the table
  actions?: SeraActionConfig<ST["id"]>;
}

export const DEFAULT_PAGINATION_POSITIONS = new Set<
  "topRight" | "bottomLeft" | "bottomRight"
>(["topRight", "bottomRight"]);

export const SeraTable = <
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
>(
  props: SeraTableProps<ID, R, DR, PF, F, ST>
) => {
  const [data, setData] = useState<FetchResult<ST["cls"]>>({
    records: [],
    total: 0,
  });
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState(
    {} as Record<string, boolean>
  );

  // function to update the data according to the query
  const loadData = (query: Query<ST["cls"]>) => {
    setLoading(true);
    props.getData(query).then((data) => {
      setData(data);
      setLoading(false);
    });
  };

  // manage the pagination from the query
  const updatePagination = (pageIndex: number, pageSize: number) => {
    const newQuery = {
      ...props.query.query,
      limit: pageSize,
      offset: pageIndex * pageSize,
    };
    props.query.update(newQuery);
  };

  const [pageSize, pageIndex, pageTotal] = useMemo(() => {
    const size = props.query.query.limit;
    const index = Math.floor(
      (props.query.query.offset || 0) / props.query.query.limit
    );
    const total = Math.ceil(data.total / props.query.query.limit);
    return [size, index, total];
  }, [props.query.query.limit, props.query.query.offset, data.total]);

  useEffect(() => {
    if (data.total == 0) {
      // typically, props.query won't change (only the inner query will change)
      // thus, this effect will only run once. the data.total === 0 check is to
      // avoid misusing the query property of this component. However, there can be a case
      // where the query returns no data so the check is ineffective but it's okay since it's very rare.
      loadData(props.query.query);
    }
    // return a function to unsubscribe from the query
    return props.query.subscribe(loadData);
  }, [props.query]);

  const listSelectedRowKeys = useMemo(() => {
    const normalizer = props.schema.normalizers[props.schema.primaryKey]!;
    return Object.keys(selectedRowKeys)
      .filter((key) => selectedRowKeys[key])
      .map((key) => normalizer(key));
  }, [selectedRowKeys]);

  // the top section of the table is often reserved for actions and pagination
  let topSection = undefined;
  // bottom section of the table is reserved for pagination
  let bottomSection = undefined;

  if (hasAction(props.actions)) {
    topSection = (
      <SeraTableAction
        actions={props.actions}
        reloadData={() => loadData(props.query.query)}
        selectedRowKeys={listSelectedRowKeys}
      />
    );
  }

  const paginationPositions =
    props.pagination?.positions || DEFAULT_PAGINATION_POSITIONS;
  if (paginationPositions.size > 0) {
    const pgnEl = (
      <TablePagination
        total={pageTotal}
        pageIndex={pageIndex}
        pageSize={pageSize}
        onUpdatePagination={updatePagination}
        allowPageSizeChange={props.pagination?.showSizeChanger}
      />
    );

    if (paginationPositions.has("topRight")) {
      if (topSection !== undefined) {
        topSection = (
          <Group justify="space-between" gap="sm">
            {topSection}
            {pgnEl}
          </Group>
        );
      } else {
        topSection = <Flex justify="flex-end">{pgnEl}</Flex>;
      }
    }

    if (
      paginationPositions.has("bottomRight") ||
      paginationPositions.has("bottomLeft") ||
      paginationPositions.has("bottomCenter")
    ) {
      // Determine position of pagination at bottom
      if (paginationPositions.has("bottomLeft")) {
        bottomSection = (
          <Flex justify="space-between" align="center">
            {pgnEl}
            <Text size="sm" c="dimmed">
              Showing {pageIndex * pageSize + 1} to{" "}
              {Math.min((pageIndex + 1) * pageSize, data.total)} of {data.total}{" "}
              records
            </Text>
          </Flex>
        );
      } else {
        bottomSection = (
          <Flex justify="space-between" align="center">
            <Text size="sm" c="dimmed">
              Showing {pageIndex * pageSize + 1} to{" "}
              {Math.min((pageIndex + 1) * pageSize, data.total)} of {data.total}{" "}
              records
            </Text>
            {pgnEl}
          </Flex>
        );
      }
    }
  }

  // render the table
  const tableEl = useMemo(() => {
    return (
      <SeraTableData<ID, R, DR, PF, F, ST>
        data={data}
        loading={loading}
        columns={props.columns}
        primaryKey={props.schema.primaryKey}
        selectedRowKeys={selectedRowKeys}
        setSelectedRowKeys={setSelectedRowKeys}
        hasTopSection={topSection !== undefined}
        hasBottomSection={bottomSection !== undefined}
      />
    );
  }, [
    data,
    loading,
    props.columns,
    props.schema.primaryKey,
    selectedRowKeys,
    setSelectedRowKeys,
    topSection !== undefined,
    bottomSection !== undefined,
  ]);

  if (topSection === undefined || bottomSection === undefined) {
    return tableEl;
  } else {
    return (
      <div>
        {topSection !== undefined && (
          <Paper
            withBorder={true}
            p="xs"
            style={{
              borderBottomLeftRadius: 0,
              borderBottomRightRadius: 0,
              borderBottom: "none",
            }}
          >
            {topSection}
          </Paper>
        )}
        {tableEl}
        {bottomSection !== undefined && (
          <Paper
            withBorder={true}
            p="xs"
            style={{
              borderTopLeftRadius: 0,
              borderTopRightRadius: 0,
              borderTop: "none",
            }}
          >
            {bottomSection}
          </Paper>
        )}
      </div>
    );
  }
};

const SeraTableData = <
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
>(props: {
  data: FetchResult<ST["cls"]>;
  loading: boolean;
  columns: SeraColumn<ST["cls"]>[];
  primaryKey: ST["publicProperties"];
  selectedRowKeys: Record<string, boolean>;
  setSelectedRowKeys: (keys: Updater<Record<string, boolean>>) => void;
  hasTopSection?: boolean;
  hasBottomSection?: boolean;
}) => {
  const columns: ColumnDef<ST["cls"]>[] = useMemo(() => {
    const columns: ColumnDef<ST["cls"]>[] = [
      {
        id: "selection",
        header: ({ table }) => (
          <Checkbox
            checked={table.getIsAllRowsSelected()}
            indeterminate={table.getIsSomeRowsSelected()}
            onChange={table.getToggleAllRowsSelectedHandler()}
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            disabled={!row.getCanSelect()}
            onChange={row.getToggleSelectedHandler()}
          />
        ),
      },
    ];
    props.columns.forEach((column) => {
      columns.push({
        id: column.key,
        header: column.title as any,
        accessorFn: column.render,
        cell: ({ row }) => {
          return column.render(row.original);
        },
      });
    });
    return columns;
  }, [props.columns]);

  const table = useReactTable({
    data: props.data.records,
    columns,
    getCoreRowModel: getCoreRowModel(),
    // convert to string, but we actually can get away with number
    getRowId: (row: ST["cls"]) => (row[props.primaryKey] as ID).toString(),
    state: {
      rowSelection: props.selectedRowKeys,
    },
    onRowSelectionChange: props.setSelectedRowKeys,
    manualPagination: true,
  });

  return (
    <SeraTableContent
      table={table}
      selectedRowKeys={props.selectedRowKeys}
      bordered={true}
      hasTopSection={props.hasTopSection}
      hasBottomSection={props.hasBottomSection}
    />
  );
};
