import { Constraint } from "./Schema";

import validator from 'validator';
import memoizeOne from 'memoize-one';

import { DynamicMultiLingualString, I18NStore } from "./I18N";
import validatorTranslations from "./assets/i18n/validators.json";

I18NStore.getInstance().registerTranslations(validatorTranslations)

export interface ValidationResult {
  isValid: boolean;
  errorMessage?: DynamicMultiLingualString<"name">;
}

export type ValueValidator = (value: any) => ValidationResult;

/**
 * Memoizes each validator function in the provided object using `memoizeOne`.
 * This function takes an object where the values are validator functions and
 * returns a new object with the same keys, but where each validator function
 * is memoized to improve performance by caching the result of the last invocation.
 *
 * @template KV - A record type where the keys are strings and the values are validator functions.
 * @param validators - An object containing validator functions to be memoized.
 * @returns A new object with the same keys as the input, but with memoized validator functions.
 */
export function memoizeOneValidators<KV extends { [key: string]: ValueValidator }>(validators: KV): KV {
  return Object.entries(validators).reduce((acc, [key, validator]) => {
    (acc[key] as any) = memoizeOne(validator);
    return acc;
  }, {} as KV);
}

/**
 * Creates a validator function based on provided constraints.
 * 
 * The validator checks if a value meets all the specified constraints.
 * Supports the following constraint types:
 * - required: Value must not be empty/falsy
 * - minLength: Value's length must be at least the constraint value
 * - maxLength: Value's length must not exceed the constraint value
 * - pattern: Value must match the regular expression pattern
 * 
 * @param constraints - Array of constraints to validate against
 * @returns A validation function that returns true if the value meets all constraints, false otherwise
 * @example
 * const validator = getValidator([
 *   { type: 'required' },
 *   { type: 'minLength', value: 3 }
 * ]);
 * validator('abc'); // returns true
 * validator(''); // returns false
 */
export function getValidator(constraints: Constraint[]): ValueValidator {
  if (constraints.length === 0) {
    return alwaysValid;
  }

  if (constraints.length === 1) {
    return constraintToValidator(constraints[0]);
  }

  // For multiple constraints, create a composite validator for AND logic
  return (value: any): ValidationResult => {
    for (const constraint of constraints) {
      const validator = constraintToValidator(constraint);
      const result = validator(value);
      if (!result.isValid) {
        return result;
      }
    }
    return { isValid: true };
  };
}

export function constraintToValidator(constraint: Constraint): ValueValidator {
  switch (constraint) {
    case "not_empty": return notEmpty;
    case "password": return validatePassword;
    case "email": return validateEmail;
    case "url": return validateURL;
    case "phone_number": return validatePhoneNumber;
    case "username": return validateUsername;
    case "positive_number": return validatePositiveNumber;
    case "non_negative_number": return validateNonNegativeNumber;
    default: throw new Error(`Not Implemented Error: ${constraint}`);
  }
}


/**
 * A validator function that always returns valid.
 * @param value - Any value to validate.
 * @returns An object with `isValid` set to true and an optional `errorMessage` property.
 */
export function alwaysValid(_value: any): ValidationResult {
  return { isValid: true };
}

/**
 * A validator function that checks if a value is empty or not.
 * @param value - The value to validate.
 * @returns An object with `isValid` set to true if the value is not empty, false otherwise.
 */
export function notEmpty(value: any): ValidationResult {
  const isValid = value !== undefined && value !== null && value !== "";
  return {
    isValid,
    errorMessage: isValid ? undefined : new DynamicMultiLingualString("validator.not_empty"),
  };
}


/**
 * Validates a password against security requirements.
 * 
 * The password must meet the following criteria:
 * - Between 8 and 32 characters (inclusive)
 * - At least one uppercase letter
 * - At least one number
 * 
 * @param value - The password string to validate
 * @returns A ValidationResult object containing:
 *          - isValid: boolean indicating if the password meets all requirements
 *          - errorMessage: undefined if valid, otherwise a DynamicMultiLingualString with the error
 */
export function validatePassword(value: any): ValidationResult {
  const hasMinLength = value.length >= 8;
  const hasValidLength = value.length <= 32;
  const hasUppercase = /[A-Z]/.test(value);
  const hasNumber = /[0-9]/.test(value);

  const isValid = hasMinLength && hasValidLength && hasUppercase && hasNumber;
  return {
    isValid,
    errorMessage: isValid
      ? undefined
      : new DynamicMultiLingualString("validator.password"),
  };
}

/**
 * Validates whether a given value is a valid email address.
 * 
 * @param value - The value to validate as an email address
 * @returns A ValidationResult object containing:
 *   - isValid: boolean indicating if the value is a valid email
 *   - errorMessage: undefined if valid, otherwise a DynamicMultiLingualString with the error key
 * 
 * @example
 * const result = validateEmail("user@example.com");
 * // result: { isValid: true, errorMessage: undefined }
 * 
 * @example
 * const result = validateEmail("invalid-email");
 * // result: { isValid: false, errorMessage: DynamicMultiLingualString("validator.email") }
 */
export function validateEmail(value: any): ValidationResult {
  const isValid = validator.isEmail(value);
  return {
    isValid,
    errorMessage: isValid ? undefined : new DynamicMultiLingualString("validator.email"),
  };
}

export function validateURL(value: any): ValidationResult {
  const isValid = validator.isURL(value);
  return {
    isValid,
    errorMessage: isValid ? undefined : new DynamicMultiLingualString("validator.url"),
  };
}
/**
 * Validates whether a given value is a valid phone number.
 * 
 * Uses validator.isMobilePhone to check if the value is a valid phone number.
 * 
 * @param value - The value to validate as a phone number
 * @returns A ValidationResult object containing:
 *   - isValid: boolean indicating if the value is a valid phone number
 *   - errorMessage: undefined if valid, otherwise a DynamicMultiLingualString with the error key
 */
export function validatePhoneNumber(value: any): ValidationResult {
  // Accept any locale for more flexible validation
  const isValid = validator.isMobilePhone(String(value), 'any');
  return {
    isValid,
    errorMessage: isValid ? undefined : new DynamicMultiLingualString("validator.phone_number"),
  };
}

/**
 * Validates a username according to specific rules.
 * The username must:
 * - Start with a letter (a-z, A-Z)
 * - Contain only alphanumeric characters, hyphens, underscores, or periods
 * - Be between 3 and 20 characters long (inclusive)
 * 
 * @param value - The value to validate as a username
 * @returns A ValidationResult object containing:
 *   - isValid: boolean indicating if the username is valid
 *   - errorMessage: undefined if valid, or a DynamicMultiLingualString with error key if invalid
 */
export function validateUsername(value: any): ValidationResult {

  const regex = /^[a-zA-Z][a-zA-Z0-9-_.]{2,19}$/;
  const isValid = regex.test(value);
  return {
    isValid,
    errorMessage: isValid ? undefined : new DynamicMultiLingualString("validator.username"),
  };
}

/**
 * Validates whether a given value is a positive number.
 * A positive number is any number greater than 0.
 * 
 * @param value - The value to validate as a positive number
 * @returns A ValidationResult object containing:
 *   - isValid: boolean indicating if the value is a positive number
 *   - errorMessage: undefined if valid, otherwise a DynamicMultiLingualString with the error key
 */
export function validatePositiveNumber(value: any): ValidationResult {
  const num = Number(value);
  const isValid = !isNaN(num) && isFinite(num) && num > 0;
  return {
    isValid,
    errorMessage: isValid ? undefined : new DynamicMultiLingualString("validator.positive_number"),
  };
}

/**
 * Validates whether a given value is a non-negative number.
 * A non-negative number is any number greater than or equal to 0.
 * 
 * @param value - The value to validate as a non-negative number
 * @returns A ValidationResult object containing:
 *   - isValid: boolean indicating if the value is a non-negative number
 *   - errorMessage: undefined if valid, otherwise a DynamicMultiLingualString with the error key
 */
export function validateNonNegativeNumber(value: any): ValidationResult {
  const num = Number(value);
  const isValid = !isNaN(num) && isFinite(num) && num >= 0;
  return {
    isValid,
    errorMessage: isValid ? undefined : new DynamicMultiLingualString("validator.non_negative_number"),
  };
}