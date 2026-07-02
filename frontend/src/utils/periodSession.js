const PERIOD_KEY = 'finance_selected_period';

const currentPeriod = () => {
  const today = new Date();
  return { month: today.getMonth() + 1, year: today.getFullYear() };
};

const isValidPeriod = ({ month, year }) => (
  Number.isInteger(Number(month))
  && Number(month) >= 1
  && Number(month) <= 12
  && Number.isInteger(Number(year))
);

export const getPeriodSelection = () => {
  try {
    const stored = JSON.parse(sessionStorage.getItem(PERIOD_KEY));
    if (isValidPeriod(stored || {})) {
      return { month: Number(stored.month), year: Number(stored.year) };
    }
  } catch {
    // Fall back to the current month if session storage is unavailable or malformed.
  }
  return currentPeriod();
};

export const savePeriodSelection = (month, year) => {
  const period = { month: Number(month), year: Number(year) };
  if (isValidPeriod(period)) sessionStorage.setItem(PERIOD_KEY, JSON.stringify(period));
};

export const clearPeriodSelection = () => sessionStorage.removeItem(PERIOD_KEY);
