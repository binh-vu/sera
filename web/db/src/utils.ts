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