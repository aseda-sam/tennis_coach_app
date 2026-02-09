import './TimeFilter.css';

interface TimeFilterProps {
  value: string;
  onChange: (period: string) => void;
}

const OPTIONS = [
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' },
  { value: 'all', label: 'All Time' },
];

function TimeFilter({ value, onChange }: TimeFilterProps) {
  return (
    <div className="time-filter" role="group" aria-label="Time period filter">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          className={`time-filter-btn ${value === opt.value ? 'active' : ''}`}
          onClick={() => onChange(opt.value)}
          aria-pressed={value === opt.value}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export default TimeFilter;
