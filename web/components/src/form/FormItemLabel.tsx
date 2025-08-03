import React from "react";
import { IconHelpOctagonFilled } from "@tabler/icons-react";
import { Flex, Group, Text, Tooltip } from "@mantine/core";
import styles from "./FormItemLabel.module.css";

export const FormItemLabel = ({
  label,
  name,
  required = false,
  tooltip,
  style,
  align = "left",
}: {
  label: React.ReactNode;
  tooltip?: React.ReactNode;
  required?: boolean;
  name?: string;
  style?: React.CSSProperties;
  align?: "left" | "right";
}) => {
  const className = required
    ? align === "left"
      ? styles.requiredLabelRight
      : styles.requiredLabelLeft
    : "";

  return (
    <Flex align="center" h={36}>
      <label htmlFor={name} style={style}>
        <Group gap={4}>
          <Text size="sm" className={className}>
            {label}
          </Text>
          {tooltip !== undefined && (
            <Tooltip label={tooltip} withArrow={true}>
              <IconHelpOctagonFilled
                size={16}
                stroke={1.5}
                style={{ color: "var(--mantine-color-dimmed)" }}
              />
            </Tooltip>
          )}
        </Group>
      </label>
    </Flex>
  );
};
