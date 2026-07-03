import { getCategoryBadgeStyle, getCategoryName } from '../../utils/categoryDisplay';
import './CategoryBadge.css';

const CategoryBadge = ({ category, name }) => {
  const label = getCategoryName(category, name || 'Uncategorized');

  return (
    <span className="category-badge" style={getCategoryBadgeStyle(category || label)}>
      <span className="category-badge-dot" aria-hidden="true" />
      <span className="category-badge-label">{label}</span>
    </span>
  );
};

export default CategoryBadge;
