import { useState } from "react";
import { IconHelpOctagonFilled } from "@tabler/icons-react";
import { observer } from "mobx-react-lite";
import {
  DataProperty,
  DraftRecord,
  GenericRecord,
  isDraftRecord,
  ObjectProperty,
  Table,
  validators,
} from "sera-db";
import { Grid, Group, Input, Stack, Tooltip } from "@mantine/core";
import { MultiLingualString } from "../misc";
import { InputInterface } from "../data/inputs";
import { FormItemLabel } from "./FormItemLabel";

export interface FormItemHorizontalLayout {
  type: "horizontal";
  labelCol: number;
  itemCol: number;
  align?: "left" | "right";
}

export interface FormItemVerticalLayout {
  type: "vertical";
  helpAlwaysVisible?: boolean;
}

export type FormItemLayout = FormItemHorizontalLayout | FormItemVerticalLayout;

export interface FormItemProps<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>
> {
  store: Table<ID, R, DR>;
  /// the record being edited (new or edit)
  record: R | DR;
  /// the property being edited
  property: DataProperty | ObjectProperty;
  /// The component used to render the input field
  InputComponent:
    | React.FC<InputInterface<any>>
    | React.ComponentType<InputInterface<any>>;
  /// validator function for the form item
  validator: validators.ValueValidator;
  /// Whether the form item should be displayed horizontal (label and input on the same line) or vertical.
  layout?: FormItemLayout;
  freeze?: boolean;
}

const DEFAULT_LAYOUT: FormItemVerticalLayout = {
  type: "vertical",
  helpAlwaysVisible: false,
};

/**
 * FormItem component for creating form elements with labels, tooltips and layout options.
 *
 * Supports both horizontal and vertical layouts. In horizontal layout, the label and input are placed side by side in a grid.
 * In vertical layout, the label is positioned above the input using Mantine's Input.Wrapper.
 */
export const FormItem = observer(
  <
    ID extends string | number,
    R extends GenericRecord<ID, DR>,
    DR extends DraftRecord<ID>
  >({
    store,
    record,
    property,
    layout = DEFAULT_LAYOUT,
    InputComponent,
    validator,
    freeze = false,
  }: FormItemProps<ID, R, DR>) => {
    const [error, setError] = useState<string | undefined>(undefined);

    const value = (record as any)[property.tsName];
    const onChange = (value: any) => {
      if (isDraftRecord(record)) {
        (record as any)[property.updateFuncName](value);
      } else {
        const draft = record.toDraft();
        (draft as any)[property.updateFuncName](value);
        store.setDraft(draft);
      }

      const validateResult = validator(value);
      if (validateResult.isValid) {
        setError(undefined);
      } else {
        setError(
          validateResult.errorMessage?.t({ args: { name: property.label } })
        );
      }
    };
    if (isHorizontalLayout(layout)) {
      // we always need to use Stack because if the hierarchy changes, the input will lose focus
      // creating problem if users cannot keep typing
      return (
        <Stack gap={5}>
          <Grid gutter="sm">
            <Grid.Col
              span={layout.labelCol}
              style={{
                display: "flex",
                justifyContent: layout.align || "left",
              }}
            >
              <FormItemLabel
                label={<MultiLingualString value={property.label} />}
                name={property.name}
                required={property.isRequired}
                tooltip={
                  property.description !== undefined ? (
                    <MultiLingualString value={property.description} />
                  ) : undefined
                }
                align={layout.align}
              />
            </Grid.Col>
            <Grid.Col span={layout.itemCol}>
              <InputComponent
                db={store.db}
                property={property}
                value={value}
                error={error !== undefined}
                onChange={onChange}
                freeze={freeze}
              />
            </Grid.Col>
          </Grid>
          {error !== undefined && (
            <Grid gutter="sm">
              <Grid.Col span={layout.labelCol} />
              <Grid.Col span={layout.itemCol}>
                <Input.Error>{error}</Input.Error>
              </Grid.Col>
            </Grid>
          )}
        </Stack>
      );
    }

    let label = <MultiLingualString value={property.label} />;
    if (!layout.helpAlwaysVisible && property.description !== undefined) {
      label = (
        <Group gap={4} style={{ display: "inline-flex" }}>
          {label}
          <Tooltip
            label={<MultiLingualString value={property.description} />}
            withArrow={true}
          >
            <IconHelpOctagonFilled
              size={16}
              stroke={1.5}
              style={{ color: "var(--mantine-color-dimmed)" }}
            />
          </Tooltip>
        </Group>
      );
    }

    return (
      <Input.Wrapper
        label={label}
        description={
          layout.helpAlwaysVisible && property.description !== undefined ? (
            <MultiLingualString value={property.description} />
          ) : undefined
        }
        required={property.isRequired}
      >
        <InputComponent
          db={store.db}
          property={property}
          value={value}
          error={error}
          onChange={onChange}
          freeze={freeze}
        />
      </Input.Wrapper>
    );
  }
);

function isHorizontalLayout(
  layout: FormItemLayout
): layout is FormItemHorizontalLayout {
  return layout.type === "horizontal";
}
