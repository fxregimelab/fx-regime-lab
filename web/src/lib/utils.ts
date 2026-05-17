type ClassValue =
  | string
  | number
  | boolean
  | undefined
  | null
  | ClassArray
  | ClassDictionary;

interface ClassArray extends Array<ClassValue> {}

interface ClassDictionary {
  [id: string]: boolean | undefined | null;
}

function toVal(mix: ClassValue): string {
  let str = "";
  if (typeof mix === "string" || typeof mix === "number") {
    str += mix;
  } else if (typeof mix === "object" && mix !== null) {
    if (Array.isArray(mix)) {
      for (const v of mix) {
        const tmp = toVal(v);
        if (tmp) str += (str ? " " : "") + tmp;
      }
    } else {
      for (const key in mix) {
        if ((mix as Record<string, boolean>)[key]) {
          str += (str ? " " : "") + key;
        }
      }
    }
  }
  return str;
}

export function cn(...inputs: ClassValue[]): string {
  let str = "";
  for (const input of inputs) {
    const tmp = toVal(input);
    if (tmp) str += (str ? " " : "") + tmp;
  }
  return str;
}

export function formatSpot(value: number, decimals = 4): string {
  return value.toFixed(decimals);
}

export function formatConfidence(value: number): string {
  return `${Math.round(value)}%`;
}

export function formatPercent(value: number, decimals = 2): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatDate(
  date: string | Date,
  options?: Intl.DateTimeFormatOptions,
): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    ...options,
  };
  return d.toLocaleDateString("en-US", defaultOptions);
}
