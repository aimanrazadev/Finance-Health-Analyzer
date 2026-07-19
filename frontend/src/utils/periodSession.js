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

export const getPeriodDateRange = (monthValue, yearValue) => {
  if (monthValue == null || monthValue === '' || yearValue == null || yearValue === '') return {};

  const month = Number(monthValue);
  const year = Number(yearValue);

  if (!Number.isInteger(year) || month === -1) return {};

  const firstMonth = month === 0 ? 1 : month;
  const lastMonth = month === 0 ? 12 : month;
  if (firstMonth < 1 || lastMonth > 12) return {};

  const pad = (value) => String(value).padStart(2, '0');
  const lastDay = new Date(year, lastMonth, 0).getDate();

  return {
    startDate: `${year}-${pad(firstMonth)}-01T00:00:00`,
    endDate: `${year}-${pad(lastMonth)}-${pad(lastDay)}T23:59:59.999`,
  };
};

export const clearPeriodSelection = () => sessionStorage.removeItem(PERIOD_KEY);
