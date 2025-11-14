import * as React from "react";
import { Popover, PopoverTrigger, PopoverContent } from "../ui/Popover";
import { Button } from "../ui/Button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/Select";
import { Calendar } from "../ui/Calendar";

function fmtRange(range) {
  if (!range || (!range.from && !range.to)) return "Pick a date range";
  const ordinal = (n) => {
    const s = ["th","st","nd","rd"]; const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  };
  const fmt = (d) => {
    const date = new Date(d);
    const month = date.toLocaleString("en-US", { month: "long" });
    const day = ordinal(date.getDate());
    const year = date.getFullYear();
    return `${month} ${day}, ${year}`;
  };
  const from = range.from ? fmt(range.from) : "∞";
  const to = range.to ? fmt(range.to) : "Today";
  return range.from && range.to ? `${from} - ${to}` : from;
}

export default function DropdownRangeDatePicker({ value, onChange }) {
  const today = new Date();
  const [open, setOpen] = React.useState(false);
  const [selected, setSelected] = React.useState(value);
  const [month, setMonth] = React.useState(today.getMonth());
  const [year, setYear] = React.useState(today.getFullYear());

  React.useEffect(() => { setSelected(value); }, [value?.from, value?.to]);

  const displayMonth = new Date(year, month, 1);

  const apply = () => { onChange && onChange(selected); setOpen(false); };
  const clear = () => { setSelected(undefined); onChange && onChange(undefined); setOpen(false); };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" className="w-[280px] justify-start text-left font-normal">
          {/* calendar icon */}
          <svg className="mr-2 h-4 w-4 shrink-0" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="16" y1="2" x2="16" y2="6"></line>
            <line x1="8" y1="2" x2="8" y2="6"></line>
            <line x1="3" y1="10" x2="21" y2="10"></line>
          </svg>
          <span className="truncate overflow-hidden">{fmtRange(selected)}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-4" align="start">
        <div className="space-y-4">
          <div className="flex gap-2">
            <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Year" />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 40 }, (_, i) => year - 20 + i).map((y) => (
                  <SelectItem key={y} value={String(y)}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Month" />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 12 }, (_, i) => (
                  <SelectItem key={i} value={String(i)}>
                    {new Date(2000, i, 1).toLocaleDateString(undefined, { month: "long" })}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Calendar
            mode="range"
            selected={selected}
            onSelect={setSelected}
            month={displayMonth}
            onMonthChange={(d) => { setMonth(d.getMonth()); setYear(d.getFullYear()); }}
            className="rounded-md border"
          />

          <div className="flex justify-between pt-2">
            <Button size="sm" variant="ghost" onClick={clear} disabled={!selected || (!selected?.from && !selected?.to)}>Clear</Button>
            <Button size="sm" onClick={apply} disabled={!selected?.from || !selected?.to}>Apply</Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

