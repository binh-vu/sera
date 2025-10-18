/**
 * Creates a new object by omitting specified keys from the source object.
 * 
 * @param obj - The source object from which to omit keys
 * @param keys - An array of key names to be excluded from the result
 * @returns A new object containing all properties from the source object except those specified in the keys array
 * 
 * @example
 * ```ts
 * const user = { id: 1, name: 'John', password: 'secret' };
 * const publicUser = omit(user, ['password']);
 * // Result: { id: 1, name: 'John' }
 * ```
 */
export function omit(obj: any, keys: string[]) {
  const omitKeys = new Set(keys);
  const result: any = {};
  for (let key of Object.keys(obj)) {
    if (!omitKeys.has(key)) {
      result[key] = obj[key];
    }
  }
  return result;
}

/**
 * Creates a new object with all properties from the input object, excluding properties with undefined values.
 * 
 * @template T - The type of the input object, must extend object
 * @param obj - The source object to filter
 * @returns A partial object containing only the properties from the input object that have defined values
 * 
 * @example
 * ```ts
 * const input = { a: 1, b: undefined, c: 'hello' };
 * const result = omitUndefined(input);
 * // result: { a: 1, c: 'hello' }
 * ```
 */
export function omitUndefined<T extends object>(obj: T): Partial<T> {
  const result: Partial<T> = {};
  for (let key of Object.keys(obj) as (keyof T)[]) {
    if (obj[key] !== undefined) {
      result[key] = obj[key];
    }
  }
  return result;
}