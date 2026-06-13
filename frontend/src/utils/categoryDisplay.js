export const CATEGORY_COLORS = {
  'Debt Cleared': '#5eead4',
  Refunds: '#86efac',
  Bills: '#fcd34d',
  Subscriptions: '#c4b5fd',
  Education: '#93c5fd',
  Entertainment: '#f9a8d4',
  Food: '#fca5a5',
  Friends: '#67e8f9',
  Laundry: '#cbd5e1',
  Healthcare: '#6ee7b7',
  Investments: '#a5b4fc',
  Transport: '#7dd3fc',
  Rent: '#d8b4fe',
  Salary: '#bbf7d0',
  Groceries: '#bef264',
  Shopping: '#fdba74',
  Travel: '#bae6fd',
  Other: '#cbd5e1',
  'Needs Review': '#fda4af',
  Uncategorized: '#cbd5e1',
};

export const CATEGORY_COLOR_SEQUENCE = [
  CATEGORY_COLORS.Food,
  CATEGORY_COLORS.Subscriptions,
  CATEGORY_COLORS.Investments,
  CATEGORY_COLORS.Education,
  CATEGORY_COLORS.Transport,
  CATEGORY_COLORS.Bills,
  CATEGORY_COLORS.Shopping,
  CATEGORY_COLORS.Healthcare,
  CATEGORY_COLORS.Rent,
  CATEGORY_COLORS.Other,
];

export const getCategoryColor = (categoryOrName) => {
  if (!categoryOrName) return CATEGORY_COLORS.Uncategorized;
  if (typeof categoryOrName === 'string') {
    return CATEGORY_COLORS[categoryOrName] || CATEGORY_COLORS.Uncategorized;
  }
  return CATEGORY_COLORS[categoryOrName.name] || categoryOrName.color || CATEGORY_COLORS.Uncategorized;
};

export const getCategoryChartColor = (categoryOrName, index = 0) => (
  getCategoryColor(categoryOrName) || CATEGORY_COLOR_SEQUENCE[index % CATEGORY_COLOR_SEQUENCE.length]
);

export const getCategoryName = (category, fallback = 'Uncategorized') => (
  category?.name || fallback
);

export const getCategoryBadgeStyle = (categoryOrName) => ({
  '--category-color': getCategoryColor(categoryOrName),
});
