interface OptionListProps {
  options: string[];
  onSelect: (index: number) => void;
  disabled?: boolean;
}

export function OptionList({ options, onSelect, disabled }: OptionListProps) {
  return (
    <ol className="option-list">
      {options.map((option, position) => {
        const index = position + 1;
        return (
          <li key={option}>
            <button
              type="button"
              className="option-list__item"
              onClick={() => onSelect(index)}
              disabled={disabled}
            >
              <span className="option-list__number">{index}.</span> {option}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
