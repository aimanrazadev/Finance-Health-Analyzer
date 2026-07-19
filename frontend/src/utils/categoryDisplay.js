export const CATEGORY_COLORS = {
  Refunds: '#22c55e',
  Bills: '#eab308',
  Subscriptions: '#8b5cf6',
  Education: '#2563eb',
  Entertainment: '#db2777',
  Food: '#ef4444',
  Friends: '#06b6d4',
  Laundry: '#64748b',
  Healthcare: '#10b981',
  Investments: '#4f46e5',
  Savings: '#0d9488',
  Transport: '#0284c7',
  Rent: '#9333ea',
  Salary: '#16a34a',
  Groceries: '#65a30d',
  Shopping: '#ea580c',
  Travel: '#0369a1',
  Other: '#6b7280',
  Uncategorized: '#64748b',
};

export const CATEGORY_COLOR_SEQUENCE = [
  CATEGORY_COLORS.Food,
  CATEGORY_COLORS.Healthcare,
  CATEGORY_COLORS.Friends,
  CATEGORY_COLORS.Groceries,
  CATEGORY_COLORS.Shopping,
  CATEGORY_COLORS.Subscriptions,
  CATEGORY_COLORS.Investments,
  CATEGORY_COLORS.Savings,
  CATEGORY_COLORS.Education,
  CATEGORY_COLORS.Transport,
  CATEGORY_COLORS.Bills,
  CATEGORY_COLORS.Rent,
  CATEGORY_COLORS.Other,
];

export const getCategoryColor = (categoryOrName) => {
  if (!categoryOrName) return CATEGORY_COLORS.Uncategorized;
  if (typeof categoryOrName === 'string') {
    return CATEGORY_COLORS[categoryOrName] || CATEGORY_COLORS.Uncategorized;
  }
  return CATEGORY_COLORS[categoryOrName.name] || CATEGORY_COLORS.Uncategorized;
};

export const getCategoryChartColor = (categoryOrName, index = 0) => {
  const categoryName = typeof categoryOrName === 'string'
    ? categoryOrName
    : categoryOrName?.name;

  return CATEGORY_COLORS[categoryName]
    || CATEGORY_COLOR_SEQUENCE[index % CATEGORY_COLOR_SEQUENCE.length];
};

export const getCategoryName = (category, fallback = 'Uncategorized') => (
  category?.name || fallback
);

export const getCategoryBadgeStyle = (categoryOrName) => ({
  '--category-color': getCategoryColor(categoryOrName),
});
