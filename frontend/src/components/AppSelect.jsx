import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown } from 'lucide-react';
import '../styles/AppSelect.css';

const AppSelect = ({
  value,
  options,
  onChange,
  ariaLabel,
  disabled = false,
  className = '',
  placeholder = 'Select option',
  name,
}) => {
  const id = useId();
  const rootRef = useRef(null);
  const menuRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [menuStyle, setMenuStyle] = useState({});

  const normalizedOptions = useMemo(() => options.map((option) => ({
    ...option,
    value: String(option.value),
  })), [options]);
  const stringValue = String(value ?? '');
  const selectedIndex = normalizedOptions.findIndex((option) => option.value === stringValue);
  const selectedOption = selectedIndex >= 0 ? normalizedOptions[selectedIndex] : null;

  const positionMenu = () => {
    const rect = rootRef.current?.getBoundingClientRect();
    if (!rect) return;
    const gap = 6;
    const spaceBelow = window.innerHeight - rect.bottom - gap;
    const spaceAbove = rect.top - gap;
    const openAbove = spaceBelow < 220 && spaceAbove > spaceBelow;
    const maxHeight = Math.max(160, Math.min(360, (openAbove ? spaceAbove : spaceBelow) - 10));
    setMenuStyle({
      left: rect.left,
      width: rect.width,
      maxHeight,
      ...(openAbove
        ? { bottom: window.innerHeight - rect.top + gap }
        : { top: rect.bottom + gap }),
    });
  };

  useEffect(() => {
    if (!open) return undefined;
    positionMenu();
    const closeOnOutsideClick = (event) => {
      if (!rootRef.current?.contains(event.target) && !menuRef.current?.contains(event.target)) setOpen(false);
    };
    const reposition = () => positionMenu();
    document.addEventListener('mousedown', closeOnOutsideClick);
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, true);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      window.removeEventListener('resize', reposition);
      window.removeEventListener('scroll', reposition, true);
    };
  }, [open]);

  const chooseOption = (option) => {
    if (option.disabled) return;
    onChange(option.value);
    setOpen(false);
    rootRef.current?.querySelector('button')?.focus();
  };

  const moveActive = (direction) => {
    if (!normalizedOptions.length) return;
    let next = activeIndex;
    do {
      next = (next + direction + normalizedOptions.length) % normalizedOptions.length;
    } while (normalizedOptions[next]?.disabled && next !== activeIndex);
    setActiveIndex(next);
  };

  const openMenu = () => {
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0);
    setOpen(true);
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') {
      setOpen(false);
      return;
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!open) openMenu();
      else moveActive(event.key === 'ArrowDown' ? 1 : -1);
      return;
    }
    if (event.key === 'Home' && open) {
      event.preventDefault();
      setActiveIndex(0);
      return;
    }
    if (event.key === 'End' && open) {
      event.preventDefault();
      setActiveIndex(normalizedOptions.length - 1);
      return;
    }
    if ((event.key === 'Enter' || event.key === ' ') && open) {
      event.preventDefault();
      chooseOption(normalizedOptions[activeIndex]);
    }
  };

  return (
    <div className={`app-select ${open ? 'is-open' : ''} ${disabled ? 'is-disabled' : ''} ${className}`.trim()} ref={rootRef}>
      {name && <input type="hidden" name={name} value={stringValue} />}
      <button
        type="button"
        className="app-select-trigger plain-button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-menu`}
        disabled={disabled}
        onClick={() => {
          if (open) setOpen(false);
          else openMenu();
        }}
        onKeyDown={handleKeyDown}
      >
        <span>{selectedOption?.label || placeholder}</span>
        <ChevronDown aria-hidden="true" />
      </button>
      {open && createPortal(
        <div
          id={`${id}-menu`}
          ref={menuRef}
          className="app-select-menu"
          role="listbox"
          aria-label={ariaLabel}
          style={menuStyle}
          onKeyDown={handleKeyDown}
        >
          {normalizedOptions.map((option, index) => (
            <button
              type="button"
              role="option"
              aria-selected={option.value === stringValue}
              className={`app-select-option ${option.value === stringValue ? 'is-selected' : ''} ${index === activeIndex ? 'is-active' : ''}`}
              disabled={option.disabled}
              key={`${option.value}-${option.label}`}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => chooseOption(option)}
            >
              {option.label}
            </button>
          ))}
        </div>,
        document.body,
      )}
    </div>
  );
};

export default AppSelect;
