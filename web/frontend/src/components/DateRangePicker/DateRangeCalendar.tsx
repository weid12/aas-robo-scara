import { useState, useRef, useEffect } from "react";
import styles from "./DateRangeCalendar.module.css";

interface DateRange {
    from?: Date;
    to?: Date;
}

interface DateRangeCalendarProps {
    value?: DateRange;
    onChange: (range?: DateRange) => void;
    className?: string;
}

const MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
];

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function formatDateRange(from?: Date, to?: Date): string {
    if (!from && !to) return "Select period";
    const formatDate = (d: Date) => {
        const months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
        return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
    };
    if (from && to) {
        return `${formatDate(from)} - ${formatDate(to)}`;
    }
    return from ? formatDate(from) : formatDate(to!);
}

function isSameDay(d1?: Date, d2?: Date): boolean {
    if (!d1 || !d2) return false;
    return d1.getFullYear() === d2.getFullYear() &&
        d1.getMonth() === d2.getMonth() &&
        d1.getDate() === d2.getDate();
}

function isInRange(date: Date, from?: Date, to?: Date): boolean {
    if (!from || !to) return false;
    return date >= from && date <= to;
}

export default function DateRangeCalendar({ value, onChange, className }: DateRangeCalendarProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [selectingStart, setSelectingStart] = useState(true);
    const [tempRange, setTempRange] = useState<DateRange | undefined>(value);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);

    useEffect(() => {
        setTempRange(value);
    }, [value]);

    // Close on outside click
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        if (isOpen) {
            document.addEventListener("mousedown", handleClickOutside);
        }
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [isOpen]);

    const getDaysInMonth = (date: Date): Date[] => {
        const year = date.getFullYear();
        const month = date.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const days: Date[] = [];

        // Add previous month's days
        const firstDayOfWeek = firstDay.getDay();
        for (let i = firstDayOfWeek - 1; i >= 0; i--) {
            days.push(new Date(year, month, -i));
        }

        // Add current month's days
        for (let i = 1; i <= lastDay.getDate(); i++) {
            days.push(new Date(year, month, i));
        }

        // Add next month's days to complete the grid
        const remainingDays = 42 - days.length; // 6 rows * 7 days
        for (let i = 1; i <= remainingDays; i++) {
            days.push(new Date(year, month + 1, i));
        }

        return days;
    };

    const handleDayClick = (date: Date) => {
        if (selectingStart) {
            setTempRange({ from: date, to: undefined });
            setSelectingStart(false);
        } else {
            if (tempRange?.from && date < tempRange.from) {
                setTempRange({ from: date, to: tempRange.from });
            } else {
                setTempRange({ ...tempRange, to: date });
            }
            setSelectingStart(true);
        }
    };

    const handlePreset = (days: number) => {
        const to = new Date();
        const from = new Date();
        from.setDate(from.getDate() - days);
        setTempRange({ from, to });
    };

    const handleApply = () => {
        onChange(tempRange);
        setIsOpen(false);
    };

    const handleClear = () => {
        setTempRange(undefined);
        onChange(undefined);
        setIsOpen(false);
    };

    const prevMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
    };

    const nextMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
    };

    const days = getDaysInMonth(currentMonth);
    const today = new Date();

    return (
        <div className={`${styles.wrapper} ${className || ""}`.trim()} ref={dropdownRef}>
            <button
                ref={triggerRef}
                type="button"
                className={styles.trigger}
                onClick={() => setIsOpen(!isOpen)}
            >
                <svg className={styles.icon} viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeWidth="2" />
                    <line x1="16" y1="2" x2="16" y2="6" strokeWidth="2" />
                    <line x1="8" y1="2" x2="8" y2="6" strokeWidth="2" />
                    <line x1="3" y1="10" x2="21" y2="10" strokeWidth="2" />
                </svg>
                <span className={styles.triggerText}>
                    {formatDateRange(value?.from, value?.to)}
                </span>
                <svg className={`${styles.chevron} ${isOpen ? styles.chevronOpen : ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <polyline points="6 9 12 15 18 9" strokeWidth="2" />
                </svg>
            </button>

            {isOpen && (
                <div className={styles.dropdown}>
                    <div className={styles.presets}>
                        <button className={styles.presetBtn} onClick={() => handlePreset(0)}>Today</button>
                        <button className={styles.presetBtn} onClick={() => handlePreset(7)}>Last 7 days</button>
                        <button className={styles.presetBtn} onClick={() => handlePreset(30)}>Last 30 days</button>
                    </div>

                    <div className={styles.calendarHeader}>
                        <button className={styles.navBtn} onClick={prevMonth}>‹</button>
                        <span className={styles.monthYear}>
                            {MONTHS[currentMonth.getMonth()]} {currentMonth.getFullYear()}
                        </span>
                        <button className={styles.navBtn} onClick={nextMonth}>›</button>
                    </div>

                    <div className={styles.weekdays}>
                        {WEEKDAYS.map(day => (
                            <div key={day} className={styles.weekday}>{day}</div>
                        ))}
                    </div>

                    <div className={styles.daysGrid}>
                        {days.map((date, index) => {
                            const isCurrentMonth = date.getMonth() === currentMonth.getMonth();
                            const isToday = isSameDay(date, today);
                            const isStart = isSameDay(date, tempRange?.from);
                            const isEnd = isSameDay(date, tempRange?.to);
                            const inRange = isInRange(date, tempRange?.from, tempRange?.to);

                            return (
                                <button
                                    key={index}
                                    className={`
                    ${styles.day}
                    ${!isCurrentMonth ? styles.otherMonth : ""}
                    ${isToday ? styles.today : ""}
                    ${isStart || isEnd ? styles.selected : ""}
                    ${inRange ? styles.inRange : ""}
                  `.trim()}
                                    onClick={() => handleDayClick(date)}
                                >
                                    {date.getDate()}
                                </button>
                            );
                        })}
                    </div>

                    <div className={styles.actions}>
                        <button
                            type="button"
                            className={styles.btn}
                            onClick={handleClear}
                        >
                            Clear
                        </button>
                        <button
                            type="button"
                            className={`${styles.btn} ${styles.btnPrimary}`}
                            onClick={handleApply}
                        >
                            Apply
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
