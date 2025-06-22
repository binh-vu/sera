export type ValueNormalizer<T> = (value: string | T) => T;


/**
 * Normalizes a string or number value to a valid finite number.
 * 
 * @param value - The string or number value to normalize
 * @returns The normalized number value
 * @throws {Error} When the value cannot be converted to a valid finite number
 * 
 * @example
 * ```typescript
 * normalizeNumber("123") // returns 123
 * normalizeNumber(456) // returns 456
 * normalizeNumber("invalid") // throws Error: "Invalid number value"
 * normalizeNumber(Infinity) // throws Error: "Invalid number value"
 * ```
 */
export function normalizeNumber(value: string | number): number {
  const num = Number(value);
  if (isNaN(num) || !isFinite(num)) {
    throw new Error("Invalid number value");
  }
  return num;
}

/**
 * Normalizes a string, number, or undefined value to a valid finite number or undefined.
 * 
 * @param value - The string, number, or undefined value to normalize
 * @returns The normalized number value or undefined if the input is undefined
 * @throws {Error} When the value cannot be converted to a valid finite number (excluding undefined)
 * 
 * @example
 * ```typescript
 * normalizeOptionalNumber("123") // returns 123
 * normalizeOptionalNumber(456) // returns 456
 * normalizeOptionalNumber(undefined) // returns undefined
 * normalizeOptionalNumber("invalid") // throws Error: "Invalid number value"
 * normalizeOptionalNumber(null) // throws Error: "Invalid number value"
 * normalizeOptionalNumber("") // return undefined
 * ```
 */
export function normalizeOptionalNumber(value: string | number | undefined): number | undefined {
  if (value === undefined || (typeof value === "string" && value.trim() === "")) {
    return undefined;
  }
  return normalizeNumber(value);
}