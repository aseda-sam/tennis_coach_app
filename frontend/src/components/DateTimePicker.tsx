import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/style.css';
import './DateTimePicker.css';

interface DateTimePickerProps {
  value: string; // ISO datetime string or ''
  onChange: (iso: string) => void;
  disabled?: boolean;
}

const HOURS = Array.from({ length: 12 }, (_, i) => i + 1); // 1–12
const MINUTES = Array.from({ length: 60 }, (_, i) => i); // 0–59
const VIEWPORT_MARGIN = 12;
const POPOVER_GAP = 6;

function parseValue(value: string): {
  date: Date | undefined;
  hour: number;
  minute: number;
  ampm: 'AM' | 'PM';
} {
  if (!value) {
    return { date: undefined, hour: 12, minute: 0, ampm: 'AM' };
  }
  // value is "YYYY-MM-DDTHH:mm" (datetime-local format)
  const d = new Date(value);
  if (isNaN(d.getTime())) {
    return { date: undefined, hour: 12, minute: 0, ampm: 'AM' };
  }
  const h24 = d.getHours();
  const ampm = h24 < 12 ? 'AM' : 'PM';
  const hour = h24 % 12 === 0 ? 12 : h24 % 12;
  return { date: d, hour, minute: d.getMinutes(), ampm };
}

function toDatetimeLocal(
  date: Date | undefined,
  hour: number,
  minute: number,
  ampm: 'AM' | 'PM'
): string {
  if (!date) return '';
  let h24 = hour % 12;
  if (ampm === 'PM') h24 += 12;
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const hh = String(h24).padStart(2, '0');
  const min = String(minute).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}T${hh}:${min}`;
}

function formatDisplay(
  date: Date | undefined,
  hour: number,
  minute: number,
  ampm: 'AM' | 'PM'
): string {
  if (!date) return '';
  const monthNames = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  const d = date.getDate();
  const m = monthNames[date.getMonth()];
  const y = date.getFullYear();
  const min = String(minute).padStart(2, '0');
  return `${m} ${d}, ${y} · ${hour}:${min} ${ampm}`;
}

const DateTimePicker: React.FC<DateTimePickerProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  const [open, setOpen] = useState(false);
  const { date, hour, minute, ampm } = parseValue(value);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(date);
  const [selectedHour, setSelectedHour] = useState(hour);
  const [selectedMinute, setSelectedMinute] = useState(minute);
  const [selectedAmPm, setSelectedAmPm] = useState<'AM' | 'PM'>(ampm);
  const [month, setMonth] = useState<Date>(date ?? new Date());
  const containerRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [popoverPosition, setPopoverPosition] = useState({ top: 0, left: 0 });

  const updatePopoverPosition = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const popoverWidth = popoverRef.current?.offsetWidth ?? 340;
    const popoverHeight = popoverRef.current?.offsetHeight ?? 430;

    let left = rect.left + rect.width / 2 - popoverWidth / 2;
    left = Math.max(
      VIEWPORT_MARGIN,
      Math.min(left, viewportWidth - popoverWidth - VIEWPORT_MARGIN)
    );

    let top = rect.bottom + POPOVER_GAP;
    if (top + popoverHeight > viewportHeight - VIEWPORT_MARGIN) {
      top = Math.max(VIEWPORT_MARGIN, rect.top - POPOVER_GAP - popoverHeight);
    }

    setPopoverPosition({ top, left });
  }, []);

  // Sync when value prop changes externally
  useEffect(() => {
    const parsed = parseValue(value);
    setSelectedDate(parsed.date);
    setSelectedHour(parsed.hour);
    setSelectedMinute(parsed.minute);
    setSelectedAmPm(parsed.ampm);
    if (parsed.date) setMonth(parsed.date);
  }, [value]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        containerRef.current &&
        !containerRef.current.contains(target) &&
        popoverRef.current &&
        !popoverRef.current.contains(target)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  useEffect(() => {
    if (!open) return;

    updatePopoverPosition();

    const handleScrollOrResize = () => updatePopoverPosition();
    window.addEventListener('resize', handleScrollOrResize);
    window.addEventListener('scroll', handleScrollOrResize, true);

    return () => {
      window.removeEventListener('resize', handleScrollOrResize);
      window.removeEventListener('scroll', handleScrollOrResize, true);
    };
  }, [open, updatePopoverPosition]);

  // Keyboard UX: Esc to close + trap tab focus inside the popover.
  useEffect(() => {
    if (!open) return;

    const focusableSelector =
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    const focusFirstElement = () => {
      if (!popoverRef.current) return;
      const focusableElements = Array.from(
        popoverRef.current.querySelectorAll<HTMLElement>(focusableSelector)
      );
      focusableElements[0]?.focus();
    };

    // Wait until portal content paints.
    requestAnimationFrame(focusFirstElement);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }

      if (e.key !== 'Tab' || !popoverRef.current) return;

      const focusableElements = Array.from(
        popoverRef.current.querySelectorAll<HTMLElement>(focusableSelector)
      );
      if (focusableElements.length === 0) return;

      const first = focusableElements[0];
      const last = focusableElements[focusableElements.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  const emit = useCallback(
    (d: Date | undefined, h: number, min: number, ap: 'AM' | 'PM') => {
      onChange(toDatetimeLocal(d, h, min, ap));
    },
    [onChange]
  );

  const handleDaySelect = (day: Date | undefined) => {
    setSelectedDate(day);
    emit(day, selectedHour, selectedMinute, selectedAmPm);
  };

  const handleHourChange = (h: number) => {
    setSelectedHour(h);
    emit(selectedDate, h, selectedMinute, selectedAmPm);
  };

  const handleMinuteChange = (min: number) => {
    setSelectedMinute(min);
    emit(selectedDate, selectedHour, min, selectedAmPm);
  };

  const handleAmPmToggle = (ap: 'AM' | 'PM') => {
    setSelectedAmPm(ap);
    emit(selectedDate, selectedHour, selectedMinute, ap);
  };

  const handleClear = () => {
    setSelectedDate(undefined);
    onChange('');
    setOpen(false);
  };

  const displayText = formatDisplay(
    selectedDate,
    selectedHour,
    selectedMinute,
    selectedAmPm
  );

  return (
    <div className="dtp-root" ref={containerRef}>
      <button
        type="button"
        ref={triggerRef}
        className={`dtp-trigger${open ? ' dtp-trigger--open' : ''}${disabled ? ' dtp-trigger--disabled' : ''}`}
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <svg
          className="dtp-trigger__icon"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <rect
            x="1"
            y="2"
            width="14"
            height="13"
            rx="2"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <path d="M1 6h14" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M5 1v2M11 1v2"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
        <span className={displayText ? '' : 'dtp-trigger__placeholder'}>
          {displayText || 'Set recording date & time'}
        </span>
      </button>
      {displayText && (
        <button
          type="button"
          className="dtp-clear-inline"
          onClick={(e) => {
            e.stopPropagation();
            handleClear();
          }}
          aria-label="Clear date"
        >
          ✕
        </button>
      )}

      {open &&
        createPortal(
          <div
            className="dtp-popover"
            ref={popoverRef}
            role="dialog"
            aria-label="Pick date and time"
            style={{
              top: `${popoverPosition.top}px`,
              left: `${popoverPosition.left}px`,
            }}
          >
            <div className="dtp-popover__inner">
              {/* Calendar */}
              <div className="dtp-calendar">
                <DayPicker
                  mode="single"
                  selected={selectedDate}
                  onSelect={handleDaySelect}
                  month={month}
                  onMonthChange={setMonth}
                  weekStartsOn={1}
                />
              </div>

              {/* Time picker */}
              <div className="dtp-time">
                <div className="dtp-time__label">Time</div>
                <div className="dtp-time__controls">
                  <div className="dtp-time__select-wrap">
                    <select
                      className="dtp-time__select"
                      value={selectedHour}
                      onChange={(e) => handleHourChange(Number(e.target.value))}
                      aria-label="Hour"
                    >
                      {HOURS.map((h) => (
                        <option key={h} value={h}>
                          {String(h).padStart(2, '0')}
                        </option>
                      ))}
                    </select>
                  </div>
                  <span className="dtp-time__sep">:</span>
                  <div className="dtp-time__select-wrap">
                    <select
                      className="dtp-time__select"
                      value={selectedMinute}
                      onChange={(e) =>
                        handleMinuteChange(Number(e.target.value))
                      }
                      aria-label="Minute"
                    >
                      {MINUTES.map((m) => (
                        <option key={m} value={m}>
                          {String(m).padStart(2, '0')}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="dtp-ampm">
                    <button
                      type="button"
                      className={`dtp-ampm__btn${selectedAmPm === 'AM' ? ' dtp-ampm__btn--active' : ''}`}
                      onClick={() => handleAmPmToggle('AM')}
                    >
                      AM
                    </button>
                    <button
                      type="button"
                      className={`dtp-ampm__btn${selectedAmPm === 'PM' ? ' dtp-ampm__btn--active' : ''}`}
                      onClick={() => handleAmPmToggle('PM')}
                    >
                      PM
                    </button>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="dtp-footer">
                <button
                  type="button"
                  className="dtp-footer__btn dtp-footer__btn--ghost"
                  onClick={handleClear}
                >
                  Clear
                </button>
                <button
                  type="button"
                  className="dtp-footer__btn dtp-footer__btn--primary"
                  onClick={() => setOpen(false)}
                >
                  Done
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </div>
  );
};

export default DateTimePicker;
