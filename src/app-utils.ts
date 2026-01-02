export type Level0Entry = {
  day: number;
  hour: number;
  value: number;
  size: number;
};

export const normalizeLevel0 = (entries: unknown): Level0Entry[] => {
  if (!Array.isArray(entries)) {
    return [];
  }
  return entries
    .map((entry) => {
      if (typeof entry !== 'object' || entry === null) {
        return null;
      }
      const record = entry as Record<string, string | number>;
      const day = Number(record.day);
      const hour = Number(record.hour);
      const value = Number(record.value);
      const size = Number(record.size);
      if (Number.isNaN(day) || Number.isNaN(hour) || Number.isNaN(value) || Number.isNaN(size)) {
        return null;
      }
      return { day, hour, value, size };
    })
    .filter((entry): entry is Level0Entry => entry !== null);
};
