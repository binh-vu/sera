import { IconSelector } from "@tabler/icons-react";
import {
  Button,
  Group,
  Menu,
  MenuDropdown,
  MenuItem,
  MenuTarget,
  Pagination,
  rem,
  Text,
  type MantineSize,
} from "@mantine/core";
import classes from "./TablePagination.module.css";

/// Pagination component for the table
export const TablePagination = ({
  total,
  pageIndex,
  pageSize,
  allowPageSizeChange = true,
  onUpdatePagination,
}: {
  total: number;
  pageIndex: number;
  pageSize: number;
  allowPageSizeChange?: boolean;
  onUpdatePagination: (pageIndex: number, pageSize: number) => void;
}) => {
  const pgnEl = (
    <Pagination
      size="sm"
      total={total}
      value={pageIndex + 1}
      onChange={(pageIndex) => onUpdatePagination(pageIndex - 1, pageSize)}
    />
  );
  if (allowPageSizeChange) {
    return (
      <Group gap="sm">
        <div>
          <Text size="sm" component="span" pr="xs" c="dimmed">
            Records per page
          </Text>
          <DataTablePageSizeSelector
            size={"sm"}
            values={["10", "20", "50", "100"]}
            value={pageSize.toString()}
            onChange={(val) => {
              onUpdatePagination(0, parseInt(val, 10));
            }}
          />
        </div>
        {pgnEl}
      </Group>
    );
  }

  return pgnEl;
};

const HEIGHT: Record<MantineSize, string> = {
  xs: rem(22),
  sm: rem(26),
  md: rem(32),
  lg: rem(38),
  xl: rem(44),
};

export function DataTablePageSizeSelector({
  size,
  values,
  value,
  onChange,
}: {
  size: MantineSize;
  values: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Menu withinPortal={true} withArrow={true} offset={2}>
      <MenuTarget>
        <Button
          size={size}
          variant="default"
          rightSection={<IconSelector size={16} stroke={1.5} />}
          style={[
            { fontWeight: "normal" },
            (theme) => ({
              height: HEIGHT[size],
              paddingLeft: theme.spacing[size],
              paddingRight: theme.spacing[size],
            }),
          ]}
          styles={{
            section: {
              marginInlineStart: 2,
            },
          }}
        >
          {value}
        </Button>
      </MenuTarget>
      <MenuDropdown>
        {values.map((v) => {
          const isCurrent = v === value;
          return (
            <MenuItem
              key={v}
              className={isCurrent ? classes.pageSizeSelectorActive : undefined}
              style={[
                { height: HEIGHT[size] },
                // isCurrent
                //   ? {
                //       color: "var(--mantine-color-text)",
                //       // backgroundColor: "var(--mantine-primary-color-filled)",
                //       opacity: 1,
                //     }
                //   : undefined,
              ]}
              // styles={{
              //   itemLabel: {
              //     fontWeight: isCurrent ? 700 : undefined,
              //   },
              // }}
              disabled={isCurrent}
              onClick={() => onChange(v)}
            >
              <Text component="div" size={size}>
                {v}
              </Text>
            </MenuItem>
          );
        })}
      </MenuDropdown>
    </Menu>
  );
}
