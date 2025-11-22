import { useMemo } from "react";
import { InputInterface } from ".";
import { Input, PasswordInput } from "@mantine/core";
import { PhoneNumberInput } from "./PhoneNumberInput";
import { UrlInput } from "./UrlInput";

export const TextInput: React.FC<InputInterface<string>> = ({
  property,
  error,
  value,
  onChange,
  freeze = false,
}) => {
  const [inputType, InputComponent] = useMemo(() => {
    // Handle different input types based on constraints
    if (property.constraints.includes("password")) {
      return ["password", PasswordInput];
    }
    if (property.constraints.includes("phone_number")) {
      return ["phone_number", PhoneNumberInput];
    }
    if (property.constraints.includes("url")) {
      return ["url", UrlInput];
    }
    const inputType = property.constraints.includes("email") ? "email" : "text";
    return [inputType, Input];
  }, [property.constraints]);

  return (
    <InputComponent
      id={property.name}
      value={value}
      type={inputType}
      onChange={(e) => onChange(e.target.value)}
      error={error}
      disabled={freeze}
    />
  );
};
