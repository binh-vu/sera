import React from "react";
import { Input } from "@mantine/core";

export interface UrlInputProps {
  id: string;
  value: string;
  type: string;
  onChange: (e: { target: { value: string } }) => void;
  error?: boolean | React.ReactNode;
  disabled?: boolean;
  readonly?: boolean;
}

export const UrlInput: React.FC<UrlInputProps> = ({
  id,
  value,
  onChange,
  error,
  disabled = false,
}) => {
  return (
    <Input
      id={id}
      value={value || ""}
      type="url"
      onChange={(event) => {
        onChange({ target: { value: event.target.value } });
      }}
      onBlur={(event) => {
        const raw = event.target.value.trim();
        if (raw === "") {
          onChange({ target: { value: "" } });
          return;
        }
        if (!raw.startsWith("https://")) {
          onChange({ target: { value: `https://${raw}` } });
        }
      }}
      error={error}
      disabled={disabled}
    />
  );
};
