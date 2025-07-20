import { expect, test } from "vitest";
import { normalizers } from "sera-db";

test("normalize date isoformat", () => {
  expect(normalizers.normalizeDate("2023-10-01T00:00:00Z")).toEqual(new Date("2023-10-01T00:00:00Z"));
});

test("normalize date string", () => {
  expect(normalizers.normalizeDate("2023-10-01")).toEqual(new Date("2023-10-01"));
});

test("normalize date", () => {
  expect(normalizers.normalizeDate(new Date("2023-10-01"))).toEqual(new Date("2023-10-01"));
});

test("normalize invalid date throw error", () => {
  expect(() => normalizers.normalizeDate("invalid date")).toThrowError("Invalid date value");
  expect(() => normalizers.normalizeDate("")).toThrowError("Invalid date value");
});